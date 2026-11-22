"""Pré-processamento: descarta pedidos e corredores que nunca podem fazer parte de uma boa solução.

Isso reduz o tamanho do modelo exato e acelera a heurística.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .instance import Instance


@dataclass
class Reduced:
    orders: np.ndarray  # índices dos pedidos candidatos
    aisles: np.ndarray  # índices dos corredores úteis
    removed_orders: int
    removed_aisles: int


def preprocess(inst: Instance) -> Reduced:
    keep = np.ones(inst.n_orders, dtype=bool)

    # 1) Pedido maior que UB nunca cabe na wave.
    keep &= inst.order_size <= inst.ub

    # 2) Pedido vazio não soma unidades: não ajuda o objetivo.
    keep &= inst.order_size > 0

    # 3) Pedido que pede mais unidades de um item do que existe no armazém inteiro.
    coo = inst.order_items.tocoo()
    impossible = coo.data > inst.item_stock[coo.col]
    keep[np.unique(coo.row[impossible])] = False

    orders = np.nonzero(keep)[0]

    # 4) Corredor sem nenhum item pedido pelos pedidos candidatos nunca vale a pena visitar.
    demanded = np.asarray(inst.order_items[orders].sum(axis=0)).ravel() > 0
    useful = np.asarray(inst.aisle_items[:, np.nonzero(demanded)[0]].sum(axis=1)).ravel() > 0
    aisles = np.nonzero(useful)[0]

    return Reduced(orders, aisles, inst.n_orders - orders.size, inst.n_aisles - aisles.size)
