"""Leitura das instâncias no formato oficial do desafio.

Formato do arquivo:
    o i a                      nº de pedidos, nº de itens, nº de corredores
    k item qtd item qtd ...    uma linha por pedido
    k item qtd item qtd ...    uma linha por corredor
    LB UB                      limites do tamanho da wave
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import scipy.sparse as sp


@dataclass
class Instance:
    name: str
    n_orders: int
    n_items: int
    n_aisles: int
    orders: list[dict[int, int]]  # orders[o] = {item: unidades pedidas}
    aisles: list[dict[int, int]]  # aisles[a] = {item: unidades em estoque}
    lb: int
    ub: int

    # Campos derivados (preenchidos em __post_init__)
    order_size: np.ndarray = field(init=False, repr=False)  # U_o = total de unidades do pedido
    order_items: sp.csr_matrix = field(init=False, repr=False)  # pedidos x itens (u_oi)
    aisle_items: sp.csr_matrix = field(init=False, repr=False)  # corredores x itens (u_ai)
    item_stock: np.ndarray = field(init=False, repr=False)  # estoque total de cada item

    def __post_init__(self) -> None:
        self.order_size = np.array([sum(o.values()) for o in self.orders], dtype=np.int64)
        self.order_items = _to_csr(self.orders, self.n_items)
        self.aisle_items = _to_csr(self.aisles, self.n_items)
        self.item_stock = np.asarray(self.aisle_items.sum(axis=0)).ravel().astype(np.int64)

    def __repr__(self) -> str:
        return (
            f"Instance({self.name}: {self.n_orders} pedidos, {self.n_items} itens, "
            f"{self.n_aisles} corredores, LB={self.lb}, UB={self.ub})"
        )


def _to_csr(rows: list[dict[int, int]], n_cols: int) -> sp.csr_matrix:
    indptr = [0]
    indices: list[int] = []
    data: list[int] = []
    for row in rows:
        indices.extend(row.keys())
        data.extend(row.values())
        indptr.append(len(indices))
    return sp.csr_matrix(
        (np.array(data, dtype=np.int64), np.array(indices, dtype=np.int64), np.array(indptr, dtype=np.int64)),
        shape=(len(rows), n_cols),
    )


def _read_rows(values: list[int], pos: int, count: int) -> tuple[list[dict[int, int]], int]:
    rows = []
    for _ in range(count):
        k = values[pos]
        pos += 1
        row: dict[int, int] = {}
        for _ in range(k):
            # Igual ao checker oficial: item repetido na linha sobrescreve o anterior
            row[values[pos]] = values[pos + 1]
            pos += 2
        rows.append(row)
    return rows, pos


def read_instance(path: str | Path) -> Instance:
    path = Path(path)
    values = list(map(int, path.read_text().split()))
    n_orders, n_items, n_aisles = values[0], values[1], values[2]
    orders, pos = _read_rows(values, 3, n_orders)
    aisles, pos = _read_rows(values, pos, n_aisles)
    lb, ub = values[pos], values[pos + 1]
    name = f"{path.parent.name}/{path.name}" if path.parent.name else path.name
    return Instance(name, n_orders, n_items, n_aisles, orders, aisles, lb, ub)
