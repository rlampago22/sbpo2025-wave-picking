"""Método de Dinkelbach com o solver Gurobi (programação linear inteira).

É o MESMO modelo e o MESMO laço do `dinkelbach.py` (CP-SAT); muda só o solver que resolve
cada subproblema linear. Recapitulando:

    max  N(x) / K(y)       N(x) = Σ_o U_o·x_o  (unidades)     K(y) = Σ_a y_a  (corredores)

Para um palpite λ = num/den, resolvemos o subproblema LINEAR
    F(λ) = max  den·N(x) − num·K(y)
    s.a.  LB ≤ N(x) ≤ UB
          Σ_o u_oi·x_o ≤ Σ_a u_ai·y_a      para todo item i
          1 ≤ K(y) ≤ ⌊UB·den/num⌋          (corte: razão > λ exige K < UB/λ)
          x, y binários

    - F(λ) > 0  → a solução tem razão maior que λ: atualizamos λ e repetimos;
    - F(λ) = 0 provado → nenhuma solução supera λ: λ é ótimo.

Diferenças em relação ao CP-SAT (o que o Gurobi permite fazer melhor):
    * O modelo é montado de forma MATRICIAL (MVar + matrizes esparsas do SciPy), o que é
      muito mais rápido que montar restrição por restrição nas instâncias grandes.
    * O objetivo é trocado só mudando o atributo Obj das variáveis; o modelo não é recriado.
    * A melhor solução conhecida entra como MIP start (atributo Start), não apenas como dica.
    * Como os coeficientes são inteiros, F(λ) é inteiro. Usamos MIPGapAbs < 1: quando o
      Gurobi diz OPTIMAL com incumbente 0, isso prova que F(λ) ≤ 0, ou seja, λ é ótimo.

Licença: o `pip install gurobipy` traz uma licença restrita (até 2000 variáveis e 2000
restrições). Instâncias maiores exigem a licença acadêmica (gratuita). Se o modelo não
couber na licença, levantamos `GurobiUnavailable` e o pipeline volta para o CP-SAT.
"""

from __future__ import annotations

import math
import os
import time
from typing import Callable

import numpy as np
import scipy.sparse as sp

from ..heuristics.local_search import remove_redundant_aisles
from ..instance import Instance
from ..preprocess import Reduced
from ..solution import Solution
from .dinkelbach import DinkelbachResult

try:  # gurobipy é opcional: sem ele o resto do projeto continua funcionando
    import gurobipy as gp
    from gurobipy import GRB
except ImportError:  # pragma: no cover
    gp = None
    GRB = None


class GurobiUnavailable(RuntimeError):
    """Gurobi não instalado, sem licença ou modelo grande demais para a licença atual."""


# Códigos de erro do Gurobi que significam "problema de licença", não bug no modelo.
_LICENSE_ERRORS = {10009, 10010}  # NO_LICENSE, SIZE_LIMIT_EXCEEDED

# Parâmetros padrão. MIPGapAbs < 1 vale porque o objetivo den·N − num·K é inteiro.
DEFAULT_PARAMS: dict[str, float | int] = {
    "MIPGapAbs": 0.99,
    "MIPFocus": 1,  # prioriza achar soluções melhores (é o que faz λ subir)
}


def gurobi_status() -> str:
    """Descreve o estado do Gurobi nesta máquina (útil para diagnosticar a licença)."""
    if gp is None:
        return "gurobipy não instalado"
    v = ".".join(map(str, gp.gurobi.version()))
    try:
        with gp.Env(params={"OutputFlag": 0}) as env, gp.Model(env=env) as m:
            # A licença restrita do pip aceita no máximo 2000 variáveis: testamos com 2001.
            m.addMVar(2001, ub=1.0)
            m.optimize()
            return f"Gurobi {v}: licença completa"
    except gp.GurobiError as e:
        if e.errno == 10010:
            return f"Gurobi {v}: licença RESTRITA (máx. 2000 variáveis/restrições)"
        return f"Gurobi {v}: sem licença ({e})"


def build_model(inst: Instance, red: Reduced, env):
    """Cria o modelo base (o objetivo é definido a cada iteração). Devolve (modelo, x, y, restrição de K)."""
    m = gp.Model("wave_picking", env=env)
    n_o, n_a = red.orders.size, red.aisles.size
    x = m.addMVar(n_o, vtype=GRB.BINARY, name="x")
    y = m.addMVar(n_a, vtype=GRB.BINARY, name="y")

    sizes = inst.order_size[red.orders].astype(float)

    # (2) e (3): tamanho da wave
    m.addConstr(sizes @ x >= inst.lb, name="LB")
    m.addConstr(sizes @ x <= inst.ub, name="UB")

    # (4): para cada item pedido, demanda dos pedidos <= estoque dos corredores.
    #      Em forma matricial: [Oᵀ  −Aᵀ] · [x; y] ≤ 0, só nas linhas de itens com demanda.
    om = inst.order_items[red.orders].T.tocsr()  # itens x pedidos
    am = inst.aisle_items[red.aisles].T.tocsr()  # itens x corredores
    demanded = np.nonzero(np.diff(om.indptr))[0]
    om, am = om[demanded].astype(float), am[demanded].astype(float)
    m.addConstr(om @ x - am @ y <= np.zeros(demanded.size), name="estoque")

    # Pelo menos um corredor; o limite superior é ajustado a cada iteração (corte UB/λ).
    m.addConstr(y.sum() >= 1, name="Kmin")
    k_cap = m.addConstr(y.sum() <= n_a, name="Kmax")
    m.ModelSense = GRB.MAXIMIZE
    return m, x, y, sizes, k_cap


def dinkelbach_gurobi(
    inst: Instance,
    red: Reduced,
    initial: Solution | None = None,
    time_limit: float = 60.0,
    iter_time_limit: float | None = None,
    workers: int | None = None,
    log: Callable[[str], None] = print,
    solver_log: bool = False,
    params: dict | None = None,
) -> DinkelbachResult:
    if gp is None:
        raise GurobiUnavailable("gurobipy não está instalado (uv add gurobipy)")

    t0 = time.perf_counter()
    try:
        env = gp.Env(empty=True)
        env.setParam("OutputFlag", 1 if solver_log else 0)
        env.start()
    except gp.GurobiError as e:
        raise GurobiUnavailable(f"licença do Gurobi indisponível: {e}") from e

    try:
        return _solve(inst, red, env, initial, time_limit, iter_time_limit, workers, log, params, t0)
    except gp.GurobiError as e:
        if e.errno in _LICENSE_ERRORS:
            raise GurobiUnavailable(f"modelo não cabe na licença do Gurobi: {e}") from e
        raise
    finally:
        env.dispose()


def _solve(inst, red, env, initial, time_limit, iter_time_limit, workers, log, params, t0) -> DinkelbachResult:
    m, x, y, sizes, k_cap = build_model(inst, red, env)
    m.setParam("Threads", workers or os.cpu_count() or 4)
    for k, v in {**DEFAULT_PARAMS, **(params or {})}.items():
        m.setParam(k, v)
    m.update()
    log(f"  modelo Gurobi: {red.orders.size} pedidos, {red.aisles.size} corredores, "
        f"{m.NumConstrs} restrições, montado em {time.perf_counter() - t0:.1f}s")

    order_ids, aisle_ids = red.orders, red.aisles
    pos_o = {int(o): i for i, o in enumerate(order_ids)}
    pos_a = {int(a): i for i, a in enumerate(aisle_ids)}

    best = initial
    num, den = (best.units(inst), len(best.aisles)) if best else (0, 1)
    history: list[dict] = []
    proven = False
    it = 0
    # Mesma estratégia de tempo do CP-SAT: iterações curtas para λ subir rápido e, quando uma
    # iteração não melhora, uma tentativa final com todo o tempo restante.
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

        # Objetivo den·N − num·K: basta trocar os coeficientes das variáveis.
        x.Obj = den * sizes
        y.Obj = np.full(aisle_ids.size, -float(num))
        cap = (inst.ub * den) // num if num > 0 else aisle_ids.size
        k_cap.RHS = np.array([min(cap, aisle_ids.size)], dtype=float)

        # MIP start com a melhor solução conhecida (vira o incumbente com F = 0).
        if best is not None:
            xs = np.zeros(order_ids.size)
            ys = np.zeros(aisle_ids.size)
            xs[[pos_o[o] for o in best.orders if o in pos_o]] = 1
            ys[[pos_a[a] for a in best.aisles if a in pos_a]] = 1
            x.Start, y.Start = xs, ys

        m.Params.TimeLimit = remaining if final_attempt else min(remaining, iter_time_limit)
        m.optimize()
        status = m.Status
        status_name = _STATUS.get(status, str(status))

        if m.SolCount > 0:
            xv, yv = x.X > 0.5, y.X > 0.5
            orders = order_ids[xv].tolist()
            aisles = aisle_ids[yv].tolist()
            aisles = remove_redundant_aisles(inst, orders, aisles)
            cand = Solution(orders, aisles)
            n, k = cand.units(inst), len(cand.aisles)
            gain = den * n - num * k if k > 0 else -1
            history.append({"iter": it, "lambda": num / den, "status": status_name,
                            "ratio": n / k if k else None, "bound": m.ObjBound,
                            "time": time.perf_counter() - t0})
            log(f"  iter {it}: λ={num / den:.4f} → razão {n}/{k} = {n / k:.4f} "
                f"[{status_name}, limitante F≤{m.ObjBound:.1f}]")
            if gain > 0:
                best, num, den = cand, n, k
                final_attempt = False
                continue
            # Sem ganho: se o Gurobi provou o ótimo de F(λ), então F(λ) = 0 e λ é ótimo.
            proven = status == GRB.OPTIMAL and best is not None
            if not proven and not final_attempt and time_limit - (time.perf_counter() - t0) > 2:
                final_attempt = True
                continue
            break
        if status in (GRB.INFEASIBLE, GRB.INF_OR_UNBD):
            # Nenhuma solução com K ≤ cap: λ atual já é ótimo (ou o problema é inviável).
            proven = best is not None
            history.append({"iter": it, "lambda": num / den, "status": status_name, "ratio": None,
                            "bound": None, "time": time.perf_counter() - t0})
            log(f"  iter {it}: λ={num / den:.4f} [{status_name}]")
            break
        log(f"  iter {it}: λ={num / den:.4f} [{status_name}] (sem solução no tempo)")
        if not final_attempt and time_limit - (time.perf_counter() - t0) > 2:
            final_attempt = True
            continue
        break

    m.dispose()
    return DinkelbachResult(best, proven, it, history)


_STATUS = {}
if GRB is not None:
    _STATUS = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INTERRUPTED: "INTERRUPTED",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
    }
