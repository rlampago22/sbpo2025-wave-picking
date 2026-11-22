"""Melhoria local de uma solução.

Versão inicial com dois movimentos simples, repetidos até não melhorar:
    1. remover corredores redundantes (o estoque dos outros já cobre a demanda);
    2. com os corredores atuais, tentar encaixar mais pedidos na sobra de estoque.

Ambos nunca pioram a razão unidades/corredores.

TODO (grupo): movimentos mais fortes, por exemplo
    - troca de corredor (sai um, entra outro) seguida de re-preenchimento;
    - troca de pedidos (sai um pedido pequeno, entram outros maiores);
    - perturbação + busca local (ILS) ou Simulated Annealing.
"""

from __future__ import annotations

import numpy as np

from ..instance import Instance
from ..preprocess import Reduced
from ..solution import Solution
from .greedy import fill_orders


def _sum_rows(matrix, rows: list[int], n_cols: int) -> np.ndarray:
    if not rows:
        return np.zeros(n_cols, dtype=np.int64)
    return np.asarray(matrix[rows].sum(axis=0)).ravel().astype(np.int64)


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
        if cand.objective(inst) <= best.objective(inst) + 1e-12:
            break
        best = cand
    return best
