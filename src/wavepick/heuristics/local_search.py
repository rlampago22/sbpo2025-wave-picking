"""Melhoria local de uma solução e ILS (Iterated Local Search).

Movimentos:
    1. remover corredores redundantes (o estoque dos outros já cobre a demanda);
    2. com os corredores atuais, encaixar mais pedidos na sobra de estoque;
    3. troca de corredor: tirar um, trocar um por outro ou colocar um, e re-preencher;
    4. troca de pedidos: tirar um pedido e colocar outros que somem mais unidades.

`improve` aplica 1 e 2. A `ils` repete: perturba a melhor solução (troca alguns corredores
ao acaso), aplica a busca local (3, 4 e `improve`) e guarda o resultado se for melhor.

`improve`, `swap_aisles`, `swap_orders`, `local_search` e `ils` nunca devolvem solução pior
que a recebida.
"""

from __future__ import annotations

import time
from collections.abc import Iterator

import numpy as np

from ..instance import Instance
from ..preprocess import Reduced
from ..solution import Solution
from .greedy import fill_orders

EPS = 1e-12  # tolerância para comparar razões (ponto flutuante)
SWAP_OUT = 5  # troca de corredor: quantos candidatos a sair são testados
SWAP_IN = 10  # troca de corredor: quantos candidatos a entrar são testados
ORDER_TRIES = 20  # troca de pedidos: quantos pedidos tentamos tirar
PERTURB_MIN, PERTURB_MAX = 2, 3  # perturbação: quantos corredores saem


def _sum_rows(matrix, rows: list[int], n_cols: int) -> np.ndarray:
    if not rows:
        return np.zeros(n_cols, dtype=np.int64)
    return np.asarray(matrix[rows].sum(axis=0)).ravel().astype(np.int64)


def _expired(deadline: float | None) -> bool:
    return deadline is not None and time.perf_counter() >= deadline


def _score(inst: Instance, sol: Solution) -> float:
    """Razão unidades/corredores; -1 se não atinge LB (qualquer solução válida é melhor)."""
    if not sol.aisles or sol.units(inst) < inst.lb:
        return -1.0
    return sol.objective(inst)


def remove_redundant_aisles(inst: Instance, orders: list[int], aisles: list[int]) -> list[int]:
    demand = _sum_rows(inst.order_items, orders, inst.n_items)
    stock = _sum_rows(inst.aisle_items, aisles, inst.n_items)

    # Tenta remover primeiro os corredores que menos contribuem para a demanda
    def useful(a: int) -> int:
        row = inst.aisle_items[a]
        return int(np.minimum(row.data, demand[row.indices]).sum())

    kept = list(aisles)
    for a in sorted(aisles, key=useful):
        if len(kept) == 1:
            break
        row = inst.aisle_items[a]
        idx, q = row.indices, row.data
        if np.all(stock[idx] - q >= demand[idx]):
            stock[idx] -= q
            kept.remove(a)
    return kept


def improve(inst: Instance, red: Reduced, sol: Solution, max_rounds: int = 5) -> Solution:
    best = sol
    for _ in range(max_rounds):
        aisles = remove_redundant_aisles(inst, best.orders, best.aisles)
        stock = _sum_rows(inst.aisle_items, aisles, inst.n_items)
        orders, _ = fill_orders(inst, red.orders, stock, start=best.orders)
        cand = Solution(orders, aisles)
        if cand.objective(inst) <= best.objective(inst) + EPS:
            break
        best = cand
    return best


def _fill_aisles(inst: Instance, red: Reduced, aisles: list[int]) -> Solution:
    """Monta a wave do zero para um conjunto de corredores e descarta os que sobrarem."""
    stock = _sum_rows(inst.aisle_items, aisles, inst.n_items)
    orders, _ = fill_orders(inst, red.orders, stock)
    return Solution(orders, remove_redundant_aisles(inst, orders, aisles))


def swap_aisles(
    inst: Instance,
    red: Reduced,
    sol: Solution,
    deadline: float | None = None,
    n_out: int = SWAP_OUT,
    n_in: int = SWAP_IN,
) -> Solution:
    """Primeira melhora entre: tirar um corredor, trocar um por outro, ou colocar um.

    Só testa os candidatos mais promissores: saem os `n_out` que menos atendem a wave atual e
    entram os `n_in` que mais cobrem a demanda que o estoque atual ainda não cobre.
    """
    best = _score(inst, sol)
    demand = _sum_rows(inst.order_items, sol.orders, inst.n_items)
    stock = _sum_rows(inst.aisle_items, sol.aisles, inst.n_items)
    total_demand = _sum_rows(inst.order_items, red.orders.tolist(), inst.n_items)
    am = inst.aisle_items[red.aisles].tocoo()  # linhas = posição em red.aisles

    def coverage(wanted: np.ndarray) -> np.ndarray:
        return np.bincount(am.row, weights=np.minimum(am.data, wanted[am.col]), minlength=red.aisles.size)

    contribution = dict(zip(red.aisles.tolist(), coverage(demand).tolist(), strict=True))
    leaving = sorted(sol.aisles, key=lambda a: contribution.get(a, 0))[:n_out]

    gain = coverage(np.clip(total_demand - stock, 0, None))
    gain[np.isin(red.aisles, sol.aisles)] = -1
    ranked = np.argsort(-gain, kind="stable")[:n_in]
    entering = [int(red.aisles[i]) for i in ranked if gain[i] > 0]

    current = set(sol.aisles)

    def moves() -> Iterator[set[int]]:
        if len(current) > 1:
            for a in leaving:
                yield current - {a}
        for a in leaving:
            for b in entering:
                yield (current - {a}) | {b}
        for b in entering:
            yield current | {b}

    for aisles in moves():
        if _expired(deadline):
            break
        if inst.ub / len(aisles) <= best:  # nem com UB unidades melhoraria
            continue
        cand = _fill_aisles(inst, red, sorted(aisles))
        if _score(inst, cand) > best + EPS:
            return cand
    return sol


def swap_orders(
    inst: Instance,
    red: Reduced,
    sol: Solution,
    deadline: float | None = None,
    max_tries: int = ORDER_TRIES,
) -> Solution:
    """Com os corredores fixos, tira um pedido e põe outros; aceita se somar mais unidades.

    Tenta tirar primeiro os menores pedidos (no máximo `max_tries`).
    """
    units = sol.units(inst)
    if units >= inst.ub:
        return sol
    stock = _sum_rows(inst.aisle_items, sol.aisles, inst.n_items)
    for out in sorted(sol.orders, key=lambda o: int(inst.order_size[o]))[:max_tries]:
        if _expired(deadline):
            break
        kept = [o for o in sol.orders if o != out]
        orders, total = fill_orders(inst, red.orders[red.orders != out], stock, start=kept)
        if total > units and total >= inst.lb:
            return Solution(orders, sol.aisles)
    return sol


def local_search(inst: Instance, red: Reduced, sol: Solution, deadline: float | None = None) -> Solution:
    """Aplica os movimentos enquanto algum melhorar a solução."""
    best = improve(inst, red, sol)  # primeiro completa a wave com o que ainda cabe
    while not _expired(deadline):
        cand = swap_aisles(inst, red, best, deadline)
        if cand == best:
            cand = swap_orders(inst, red, best, deadline)
        if cand == best:
            break
        better = improve(inst, red, cand)
        best = better if _score(inst, better) >= _score(inst, cand) else cand
    return best


def _perturb(inst: Instance, red: Reduced, sol: Solution, rng: np.random.Generator) -> Solution:
    """Tira de PERTURB_MIN a PERTURB_MAX corredores ao acaso e coloca outros (às vezes um a mais ou a menos)."""
    unused = np.setdiff1d(red.aisles, sol.aisles)
    n_out = min(int(rng.integers(PERTURB_MIN, PERTURB_MAX + 1)), len(sol.aisles))
    n_in = min(max(1, n_out + int(rng.integers(-1, 2))), unused.size)
    aisles = set(sol.aisles) - set(rng.choice(sol.aisles, size=n_out, replace=False).tolist())
    aisles |= set(rng.choice(unused, size=n_in, replace=False).tolist())
    if not aisles:
        return sol
    return _fill_aisles(inst, red, sorted(aisles))


def ils(
    inst: Instance,
    red: Reduced,
    initial: Solution,
    time_limit: float,
    seed: int = 0,
) -> Solution:
    """Iterated Local Search a partir de `initial`, por no máximo cerca de `time_limit` segundos."""
    deadline = time.perf_counter() + time_limit
    rng = np.random.default_rng(seed)
    best = local_search(inst, red, initial, deadline)
    while not _expired(deadline):
        if len(best.aisles) == 1 and best.units(inst) >= inst.ub:  # UB/1: não há como melhorar
            break
        cand = local_search(inst, red, _perturb(inst, red, best, rng), deadline)
        if _score(inst, cand) > _score(inst, best) + EPS:
            best = cand
    return best
