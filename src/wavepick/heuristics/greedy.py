"""Heurística construtiva gulosa.

Ideia: abrir corredores um a um (sempre o que mais cobre a demanda ainda não atendida)
e, a cada novo corredor, preencher a wave com pedidos que cabem no estoque disponível.
Guardamos a melhor razão unidades/corredores vista no caminho.

Serve para (1) dar uma solução inicial boa e rápida ao método exato e
(2) ser a solução de reserva caso o solver não termine a tempo.
"""

from __future__ import annotations

import time

import numpy as np

from ..instance import Instance
from ..preprocess import Reduced
from ..solution import Solution


def fill_orders(
    inst: Instance,
    candidates: np.ndarray,
    stock: np.ndarray,
    start: list[int] | None = None,
) -> tuple[list[int], int]:
    """Escolhe gulosamente pedidos que cabem em `stock` (estoque por item) sem passar de UB.

    Os pedidos em `start` são mantidos (supõe-se que já cabem). Os demais são tentados
    em ordem de prioridade: unidades / consumo relativo do estoque. Pedidos que usam
    itens abundantes nos corredores abertos vêm primeiro.
    """
    remaining = stock.astype(np.int64).tolist()
    chosen: list[int] = []
    total = 0
    in_start: set[int] = set()
    for o in start or []:
        for i, q in inst.orders[o].items():
            remaining[i] -= q
        total += int(inst.order_size[o])
        chosen.append(o)
        in_start.add(o)

    # Prioridade dos pedidos (vetorizada)
    sub = inst.order_items[candidates]
    stock_f = stock.astype(np.float64)
    inv = np.zeros_like(stock_f)
    np.divide(1.0, stock_f, out=inv, where=stock_f > 0)
    missing = (sub @ (stock_f <= 0).astype(np.float64)) > 0  # pede item que não está nos corredores
    cost = sub @ inv
    sizes = inst.order_size[candidates]
    valid = ~missing & (cost > 0)
    score = np.zeros(candidates.size)
    score[valid] = sizes[valid] / cost[valid]
    ordered = candidates[valid][np.argsort(-score[valid], kind="stable")]

    ub = inst.ub
    for o in ordered.tolist():
        if o in in_start:
            continue
        size = int(inst.order_size[o])
        if total + size > ub:
            continue
        items = inst.orders[o]
        if all(remaining[i] >= q for i, q in items.items()):
            for i, q in items.items():
                remaining[i] -= q
            total += size
            chosen.append(o)
            if total == ub:
                break
    return chosen, total


def greedy(
    inst: Instance,
    red: Reduced,
    n_starts: int = 10,
    time_limit: float | None = None,
) -> Solution | None:
    """Executa a construção gulosa a partir de `n_starts` corredores iniciais diferentes."""
    t0 = time.perf_counter()
    if red.orders.size == 0 or red.aisles.size == 0:
        return None

    aisle_mat = inst.aisle_items[red.aisles].tocoo()  # linhas = posição em red.aisles
    total_demand = np.asarray(inst.order_items[red.orders].sum(axis=0)).ravel()

    def aisle_values(unmet: np.ndarray) -> np.ndarray:
        """Quanto da demanda não atendida cada corredor cobriria."""
        covered = np.minimum(aisle_mat.data, unmet[aisle_mat.col])
        return np.bincount(aisle_mat.row, weights=covered, minlength=red.aisles.size)

    initial_values = aisle_values(total_demand)
    starts = np.argsort(-initial_values, kind="stable")[:n_starts]

    best: Solution | None = None
    best_ratio = -1.0

    for s in starts.tolist():
        used = np.zeros(red.aisles.size, dtype=bool)
        used[s] = True
        chosen = [int(red.aisles[s])]
        stock = inst.aisle_items[chosen[0]].toarray().ravel().astype(np.int64)
        k = 1
        while True:
            if inst.ub / k <= best_ratio:  # nem com UB unidades bateríamos o melhor
                break
            orders, units = fill_orders(inst, red.orders, stock)
            if units >= inst.lb and units / k > best_ratio:
                best_ratio = units / k
                best = Solution(orders, list(chosen))

            unmet = np.clip(total_demand - stock, 0, None)
            values = aisle_values(unmet)
            values[used] = -1
            nxt = int(np.argmax(values))
            if values[nxt] <= 0:
                break
            used[nxt] = True
            a = int(red.aisles[nxt])
            chosen.append(a)
            stock += inst.aisle_items[a].toarray().ravel()
            k += 1
            if time_limit is not None and time.perf_counter() - t0 > time_limit:
                break
        if time_limit is not None and time.perf_counter() - t0 > time_limit:
            break
    return best
