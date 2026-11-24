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


@dataclass
class ModelParts:
    model: cp_model.CpModel
    x: dict
    y: dict
    units: object
    n_aisles: object
    k_cap: object  # restrição K <= cap (domínio ajustado a cada iteração)
    n_floor: object  # restrição LB <= N <= UB (domínio ajustado no modo "k fixo")


def build_model(inst: Instance, red: Reduced, strengthen: bool = False) -> ModelParts:
    """Cria o modelo base (sem função objetivo).

    strengthen=True adiciona o corte de ligação x_o <= z_i <= Σ_{a ∈ A_i} y_a para cada item i
    do pedido o: o pedido só entra se algum corredor que tenha o item i for aberto. Isso é implicado
    pelas restrições de estoque, mas só na relaxação linear de forma fraca (estoque agregado).
    """
    model = cp_model.CpModel()
    orders = red.orders.tolist()
    aisles = red.aisles.tolist()
    x = {o: model.new_bool_var(f"x{o}") for o in orders}
    y = {a: model.new_bool_var(f"y{a}") for a in aisles}

    units = cp_model.LinearExpr.weighted_sum([x[o] for o in orders], inst.order_size[red.orders].tolist())
    n_aisles = sum(y.values())

    # (2) e (3): tamanho da wave
    n_floor = model.add_linear_constraint(units, inst.lb, inst.ub)

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
        if strengthen:
            if a_rows.size == 0:
                for r in o_rows:
                    model.add(x[orders[r]] == 0)
            else:
                z = model.new_bool_var(f"z{i}")
                model.add(z <= sum(y[aisles[r]] for r in a_rows))
                for r in o_rows:
                    model.add(x[orders[r]] <= z)

    # Pelo menos um corredor; o limite superior é ajustado a cada iteração (corte UB/λ)
    model.add(n_aisles >= 1)
    k_cap = model.add(n_aisles <= len(aisles))
    return ModelParts(model, x, y, units, n_aisles, k_cap, n_floor)


def _apply_params(solver: cp_model.CpSolver, time_s: float, workers: int | None, solver_log: bool, params: dict | None):
    solver.parameters.max_time_in_seconds = time_s
    solver.parameters.num_workers = workers or os.cpu_count() or 4
    solver.parameters.log_search_progress = solver_log
    for k, v in (params or {}).items():
        setattr(solver.parameters, k, v)


def _hint(model: cp_model.CpModel, x: dict, y: dict, sol: Solution | None) -> None:
    model.clear_hints()
    if sol is None:
        return
    chosen_o, chosen_a = set(sol.orders), set(sol.aisles)
    for o, var in x.items():
        model.add_hint(var, o in chosen_o)
    for a, var in y.items():
        model.add_hint(var, a in chosen_a)


def _extract(inst: Instance, solver: cp_model.CpSolver, x: dict, y: dict) -> Solution:
    orders = [o for o, var in x.items() if solver.boolean_value(var)]
    aisles = [a for a, var in y.items() if solver.boolean_value(var)]
    return Solution(orders, remove_redundant_aisles(inst, orders, aisles))


def dinkelbach(
    inst: Instance,
    red: Reduced,
    initial: Solution | None = None,
    time_limit: float = 60.0,
    iter_time_limit: float | None = None,
    workers: int | None = None,
    log: Callable[[str], None] = print,
    solver_log: bool = False,
    strengthen: bool = False,
    params: dict | None = None,
) -> DinkelbachResult:
    t0 = time.perf_counter()
    parts = build_model(inst, red, strengthen)
    model, x, y, units, n_aisles, k_cap = parts.model, parts.x, parts.y, parts.units, parts.n_aisles, parts.k_cap
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

        _hint(model, x, y, best)

        solver = cp_model.CpSolver()
        _apply_params(solver, remaining if final_attempt else min(remaining, iter_time_limit), workers, solver_log, params)
        status = solver.solve(model)
        status_name = solver.status_name(status)

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            cand = _extract(inst, solver, x, y)
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


# --------------------------------------------------------------------------------------
# Variante "k fixo": para cada número de corredores k, maximiza N com Σ y_a = k.
# --------------------------------------------------------------------------------------
def kfixed(
    inst: Instance,
    red: Reduced,
    initial: Solution | None = None,
    time_limit: float = 60.0,
    workers: int | None = None,
    log: Callable[[str], None] = print,
    solver_log: bool = False,
    strengthen: bool = False,
    params: dict | None = None,
) -> DinkelbachResult:
    """Resolve um problema inteiro LINEAR por k (sem Dinkelbach) e guarda o melhor N/k.

    Para cada k exigimos N ≥ ⌊λ·k⌋ + 1, onde λ é a melhor razão conhecida: só interessa uma solução
    estritamente melhor. Se o solver prova INFEASIBLE, aquele k está descartado. Como N ≤ UB, só
    precisamos olhar k < UB/λ. Os k são visitados do mais próximo ao k da solução inicial para o mais
    distante, e o tempo restante é dividido igualmente entre os k pendentes.
    """
    t0 = time.perf_counter()
    parts = build_model(inst, red, strengthen)
    model, x, y = parts.model, parts.x, parts.y
    log(f"  modelo (k fixo): {len(x)} pedidos, {len(y)} corredores, montado em {time.perf_counter() - t0:.1f}s")

    best = initial
    history: list[dict] = []
    k0 = len(best.aisles) if best else max(1, len(y) // 2)
    done: set[int] = set()  # k já resolvidos (provado que não há solução melhor)
    n_solves = 0
    while True:
        num, den = (best.units(inst), len(best.aisles)) if best else (0, 1)
        kmax = min(len(y), (inst.ub * den - 1) // num if num > 0 else len(y))  # k < UB/λ
        pending = sorted((k for k in range(1, kmax + 1) if k not in done), key=lambda k: (abs(k - k0), k))
        remaining = time_limit - (time.perf_counter() - t0)
        if not pending or remaining <= 1:
            break
        k = pending[0]
        slice_s = max(1.0, remaining / len(pending))
        floor_n = max(inst.lb, (num * k) // den + 1) if num > 0 else inst.lb
        parts.k_cap.proto.linear.domain[0] = k
        parts.k_cap.proto.linear.domain[1] = k
        parts.n_floor.proto.linear.domain[0] = floor_n
        parts.n_floor.proto.linear.domain[1] = inst.ub
        model.maximize(parts.units)
        _hint(model, x, y, best if best and len(best.aisles) == k else None)

        solver = cp_model.CpSolver()
        _apply_params(solver, min(remaining, slice_s), workers, solver_log, params)
        status = solver.solve(model)
        n_solves += 1
        name = solver.status_name(status)
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            cand = _extract(inst, solver, x, y)
            n, kk = cand.units(inst), len(cand.aisles)
            history.append({"k": k, "status": name, "ratio": n / kk, "time": time.perf_counter() - t0})
            log(f"  k={k}: N={n} → razão {n}/{kk} = {n / kk:.4f} [{name}]")
            if n * den > num * kk:
                best = cand
                k0 = kk
                done.discard(kk)
                if status == cp_model.OPTIMAL:
                    done.add(k)
            else:  # não melhorou (ex.: remove_redundant reduziu a razão?) — não repete este k
                done.add(k)
        else:
            history.append({"k": k, "status": name, "ratio": None, "time": time.perf_counter() - t0})
            log(f"  k={k}: [{name}]")
            done.add(k)  # INFEASIBLE: provado; UNKNOWN: sem tempo — não insiste

    num, den = (best.units(inst), len(best.aisles)) if best else (0, 1)
    kmax = min(len(y), (inst.ub * den - 1) // num if num > 0 else len(y))
    proven = best is not None and all(k in done for k in range(1, kmax + 1))
    return DinkelbachResult(best, proven, n_solves, history)


# --------------------------------------------------------------------------------------
# Variante "vizinhança" (LNS): modelo restrito em torno da solução atual.
# --------------------------------------------------------------------------------------
def neighborhood(
    inst: Instance,
    red: Reduced,
    sol: Solution,
    max_aisles: int,
    max_orders: int,
    rng: np.random.Generator | None = None,
) -> Reduced:
    """Sub-instância "próxima" de `sol`: seus corredores + os que mais cobrem os itens que ela pede,
    e os pedidos que cabem nesses corredores (os de `sol` + os de melhor unidades/consumo de estoque).
    """
    demand = np.zeros(inst.n_items, dtype=np.int64)
    for o in sol.orders:
        for i, q in inst.orders[o].items():
            demand[i] += q

    # --- corredores: os de sol + os de maior cobertura da demanda de sol (com um pouco de aleatoriedade)
    am = inst.aisle_items[red.aisles].tocoo()
    cover = np.bincount(am.row, weights=np.minimum(am.data, demand[am.col]), minlength=red.aisles.size)
    if rng is not None:
        cover = cover * rng.uniform(0.7, 1.3, size=cover.size)
    in_sol = np.isin(red.aisles, sol.aisles)
    cover[in_sol] = np.inf
    take = np.argsort(-cover, kind="stable")[: max(max_aisles, len(sol.aisles))]
    aisles = np.sort(red.aisles[take])

    # --- pedidos: cabem no estoque total dos corredores escolhidos
    stock = np.asarray(inst.aisle_items[aisles].sum(axis=0)).ravel().astype(np.float64)
    om = inst.order_items[red.orders].tocoo()
    bad = om.data > stock[om.col]
    ok = np.ones(red.orders.size, dtype=bool)
    ok[np.unique(om.row[bad])] = False
    inv = np.zeros_like(stock)
    np.divide(1.0, stock, out=inv, where=stock > 0)
    cost = np.bincount(om.row, weights=om.data * inv[om.col], minlength=red.orders.size)
    score = np.where(ok & (cost > 0), inst.order_size[red.orders] / np.maximum(cost, 1e-12), -1.0)
    score[np.isin(red.orders, sol.orders)] = np.inf
    if rng is not None:
        score = score * rng.uniform(0.8, 1.2, size=score.size)
    cand = np.nonzero(score > 0)[0]
    cand = cand[np.argsort(-score[cand], kind="stable")][: max(max_orders, len(sol.orders))]
    orders = np.sort(red.orders[cand])
    return Reduced(orders, aisles, inst.n_orders - orders.size, inst.n_aisles - aisles.size)


def lns(
    inst: Instance,
    red: Reduced,
    initial: Solution | None = None,
    time_limit: float = 60.0,
    workers: int | None = None,
    log: Callable[[str], None] = print,
    solver_log: bool = False,
    strengthen: bool = False,
    params: dict | None = None,
    round_share: float = 0.25,
    seed: int = 0,
) -> DinkelbachResult:
    """Dinkelbach sobre modelos pequenos em torno da melhor solução (busca em vizinhança grande).

    Cada rodada resolve (com Dinkelbach) o submodelo restrito, partindo da solução atual. Se a rodada
    não melhora, a vizinhança cresce (e ganha aleatoriedade); se melhora, ela é recentralizada.
    Nunca prova otimalidade global (o espaço é restrito).
    """
    if initial is None:
        return dinkelbach(inst, red, None, time_limit, None, workers, log, solver_log, strengthen, params)
    t0 = time.perf_counter()
    rng = np.random.default_rng(seed)
    best = initial
    history: list[dict] = []
    max_aisles = max(30, 3 * len(best.aisles))
    max_orders = 2000
    rounds = 0
    while True:
        remaining = time_limit - (time.perf_counter() - t0)
        if remaining <= 2 or (max_aisles >= red.aisles.size and max_orders >= red.orders.size and rounds > 0):
            break
        rounds += 1
        sub = neighborhood(inst, red, best, max_aisles, max_orders, rng if rounds > 1 else None)
        res = dinkelbach(
            inst, sub, best, time_limit=min(remaining, max(5.0, time_limit * round_share)), workers=workers,
            log=lambda *_: None, solver_log=solver_log, strengthen=strengthen, params=params,
        )
        old = best.objective(inst)
        improved = res.solution is not None and res.solution.objective(inst) > old + 1e-12
        if improved:
            best = res.solution
        history.append({"round": rounds, "aisles": sub.aisles.size, "orders": sub.orders.size,
                        "ratio": best.objective(inst), "time": time.perf_counter() - t0})
        log(f"  LNS rodada {rounds}: {sub.aisles.size} corredores × {sub.orders.size} pedidos → "
            f"{best.objective(inst):.4f}{' (melhorou)' if improved else ''}")
        if improved:
            max_aisles = max(30, 3 * len(best.aisles))
        else:
            max_aisles = int(max_aisles * 1.6) + 1
            max_orders = int(max_orders * 1.6) + 1
    return DinkelbachResult(best, False, rounds, history)
