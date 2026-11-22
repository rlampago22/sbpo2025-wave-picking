"""Representação, verificação e escrita de soluções.

A verificação reproduz exatamente as regras do checker.py oficial:
    1. LB <= total de unidades <= UB
    2. para cada item: demanda dos pedidos escolhidos <= estoque dos corredores escolhidos
Objetivo = total de unidades / número de corredores.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .instance import Instance


@dataclass
class Solution:
    orders: list[int]
    aisles: list[int]

    def __post_init__(self) -> None:
        self.orders = sorted(set(int(o) for o in self.orders))
        self.aisles = sorted(set(int(a) for a in self.aisles))

    def units(self, inst: Instance) -> int:
        return int(inst.order_size[self.orders].sum()) if self.orders else 0

    def objective(self, inst: Instance) -> float:
        return self.units(inst) / len(self.aisles) if self.aisles else 0.0


@dataclass
class Evaluation:
    feasible: bool
    objective: float
    units: int
    n_aisles: int
    message: str


def evaluate(inst: Instance, sol: Solution) -> Evaluation:
    units = sol.units(inst)
    n_aisles = len(sol.aisles)

    if n_aisles == 0:
        return Evaluation(False, 0.0, units, 0, "nenhum corredor (o checker oficial divide por zero)")
    if any(o < 0 or o >= inst.n_orders for o in sol.orders):
        return Evaluation(False, 0.0, units, n_aisles, "índice de pedido inválido")
    if any(a < 0 or a >= inst.n_aisles for a in sol.aisles):
        return Evaluation(False, 0.0, units, n_aisles, "índice de corredor inválido")

    objective = units / n_aisles
    if not (inst.lb <= units <= inst.ub):
        return Evaluation(False, objective, units, n_aisles, f"total {units} fora de [LB={inst.lb}, UB={inst.ub}]")

    demand = _sum_rows(inst.order_items, sol.orders, inst.n_items)
    stock = _sum_rows(inst.aisle_items, sol.aisles, inst.n_items)
    short = np.nonzero(demand > stock)[0]
    if short.size:
        i = int(short[0])
        return Evaluation(
            False, objective, units, n_aisles,
            f"{short.size} item(ns) sem estoque suficiente (ex.: item {i}: pede {demand[i]}, tem {stock[i]})",
        )
    return Evaluation(True, objective, units, n_aisles, "ok")


def _sum_rows(matrix, rows: list[int], n_cols: int) -> np.ndarray:
    if not rows:
        return np.zeros(n_cols, dtype=np.int64)
    return np.asarray(matrix[rows].sum(axis=0)).ravel()


def write_solution(sol: Solution, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [str(len(sol.orders)), *map(str, sol.orders), str(len(sol.aisles)), *map(str, sol.aisles)]
    path.write_text("\n".join(lines) + "\n")


def read_solution(path: str | Path) -> Solution:
    values = [int(v) for v in Path(path).read_text().split()]
    n_orders = values[0]
    orders = values[1 : 1 + n_orders]
    n_aisles = values[1 + n_orders]
    aisles = values[2 + n_orders : 2 + n_orders + n_aisles]
    return Solution(orders, aisles)
