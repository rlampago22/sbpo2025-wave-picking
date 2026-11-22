"""Método de Dinkelbach com o solver CP-SAT (OR-Tools).

Problema original (objetivo fracionário):
    max  N(x) / K(y)       N(x) = Σ_o U_o·x_o  (unidades)     K(y) = Σ_a y_a  (corredores)

Dinkelbach transforma a fração numa sequência de problemas LINEARES. Para um palpite λ:
    F(λ) = max  N(x) − λ·K(y)    (mesmas restrições)

    - Se F(λ) > 0, a solução encontrada tem N/K > λ: atualizamos λ ← N/K e repetimos.
    - Se F(λ) = 0 (provado pelo solver), nenhuma solução tem razão maior que λ: λ é ótimo.

Como λ = num/den é uma fração de inteiros, multiplicamos por den para manter coeficientes
inteiros (o CP-SAT só aceita inteiros):  max  den·N(x) − num·K(y).

Corte extra: como N ≤ UB, qualquer solução com razão > λ precisa de K < UB/λ corredores.
Então adicionamos K(y) ≤ ⌊UB·den/num⌋, o que reduz muito o espaço de busca.
"""

from __future__ import annotations

import math
import os
import time
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
from ortools.sat.python import cp_model

from ..instance import Instance
from ..preprocess import Reduced
from ..solution import Solution
from ..heuristics.local_search import remove_redundant_aisles


@dataclass
class DinkelbachResult:
    solution: Solution | None
    proven_optimal: bool
    iterations: int
    history: list[dict] = field(default_factory=list)


def build_model(inst: Instance, red: Reduced):
    """Cria o modelo base (sem função objetivo). Devolve (modelo, x, y, N, K, restrição de K)."""
    model = cp_model.CpModel()
    orders = red.orders.tolist()
    aisles = red.aisles.tolist()
    x = {o: model.new_bool_var(f"x{o}") for o in orders}
    y = {a: model.new_bool_var(f"y{a}") for a in aisles}

    units = cp_model.LinearExpr.weighted_sum([x[o] for o in orders], inst.order_size[red.orders].tolist())
    n_aisles = sum(y.values())

    # (2) e (3): tamanho da wave
    model.add(units >= inst.lb)
    model.add(units <= inst.ub)

    # (4): para cada item, demanda dos pedidos <= estoque dos corredores
    om = inst.order_items[red.orders].tocsc()
    am = inst.aisle_items[red.aisles].tocsc()
    for i in np.nonzero(np.diff(om.indptr))[0].tolist():
        o_rows = om.indices[om.indptr[i] : om.indptr[i + 1]]
        o_q = om.data[om.indptr[i] : om.indptr[i + 1]]
        a_rows = am.indices[am.indptr[i] : am.indptr[i + 1]]
        a_q = am.data[am.indptr[i] : am.indptr[i + 1]]
        lhs = cp_model.LinearExpr.weighted_sum([x[orders[r]] for r in o_rows], o_q.tolist())
        rhs = cp_model.LinearExpr.weighted_sum([y[aisles[r]] for r in a_rows], a_q.tolist())
        model.add(lhs <= rhs)

    # Pelo menos um corredor; o limite superior é ajustado a cada iteração (corte UB/λ)
    model.add(n_aisles >= 1)
    k_cap = model.add(n_aisles <= len(aisles))
    return model, x, y, units, n_aisles, k_cap


def dinkelbach(
    inst: Instance,
    red: Reduced,
    initial: Solution | None = None,
    time_limit: float = 60.0,
    iter_time_limit: float | None = None,
    workers: int | None = None,
    log: Callable[[str], None] = print,
    solver_log: bool = False,
) -> DinkelbachResult:
    t0 = time.perf_counter()
    model, x, y, units, n_aisles, k_cap = build_model(inst, red)
    log(f"  modelo: {len(x)} pedidos, {len(y)} corredores, montado em {time.perf_counter() - t0:.1f}s")

    best = initial
    num, den = (best.units(inst), len(best.aisles)) if best else (0, 1)
    history: list[dict] = []
    proven = False
    it = 0
    # Tempo por iteração: iterações curtas deixam λ subir rápido (λ maior → corte K ≤ UB/λ mais forte).
    # Quando uma iteração não melhora, damos todo o tempo restante numa tentativa final.
    if iter_time_limit is None:
        iter_time_limit = max(10.0, time_limit / 5)
    final_attempt = False

    while True:
        remaining = time_limit - (time.perf_counter() - t0)
        if remaining <= 1:
            break
        it += 1
        g = math.gcd(num, den) or 1
        num, den = num // g, den // g

        model.maximize(den * units - num * n_aisles)
        cap = (inst.ub * den) // num if num > 0 else len(y)
        k_cap.proto.linear.domain[0] = 0
        k_cap.proto.linear.domain[1] = min(cap, len(y))

        model.clear_hints()
        if best is not None:
            chosen_o, chosen_a = set(best.orders), set(best.aisles)
            for o, var in x.items():
                model.add_hint(var, o in chosen_o)
            for a, var in y.items():
                model.add_hint(var, a in chosen_a)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = remaining if final_attempt else min(remaining, iter_time_limit)
        solver.parameters.num_workers = workers or os.cpu_count() or 4
        solver.parameters.log_search_progress = solver_log
        status = solver.solve(model)
        status_name = solver.status_name(status)

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            orders = [o for o, var in x.items() if solver.boolean_value(var)]
            aisles = [a for a, var in y.items() if solver.boolean_value(var)]
            aisles = remove_redundant_aisles(inst, orders, aisles)
            cand = Solution(orders, aisles)
            n, k = cand.units(inst), len(cand.aisles)
            gain = den * n - num * k
            history.append({"iter": it, "lambda": num / den, "status": status_name, "ratio": n / k, "time": time.perf_counter() - t0})
            log(f"  iter {it}: λ={num / den:.4f} → razão {n}/{k} = {n / k:.4f} [{status_name}]")
            if gain > 0:
                best, num, den = cand, n, k
                final_attempt = False
                continue
            proven = status == cp_model.OPTIMAL
            if not proven and not final_attempt and time_limit - (time.perf_counter() - t0) > 2:
                final_attempt = True
                continue
            break
        if status == cp_model.INFEASIBLE:
            # Nenhuma solução com K <= cap: λ atual já é ótimo (ou o problema é inviável).
            proven = best is not None
            history.append({"iter": it, "lambda": num / den, "status": status_name, "ratio": None, "time": time.perf_counter() - t0})
            log(f"  iter {it}: λ={num / den:.4f} [{status_name}]")
            break
        log(f"  iter {it}: λ={num / den:.4f} [{status_name}] (sem solução no tempo)")
        if not final_attempt and time_limit - (time.perf_counter() - t0) > 2:
            final_attempt = True
            continue
        break

    return DinkelbachResult(best, proven, it, history)
