"""Pipeline completo para UMA instância:

    pré-processamento → heurística gulosa → melhoria local → Dinkelbach (CP-SAT ou Gurobi) → verificação → arquivo

Uso:
    uv run python -m wavepick.pipeline <instancia.txt> <saida.txt> [--time 60] [--solver cpsat|gurobi|auto]

Solvers do Dinkelbach:
    cpsat   OR-Tools CP-SAT (sempre disponível)
    gurobi  Gurobi; se não houver licença (ou o modelo não couber na licença restrita do pip),
            cai automaticamente para o CP-SAT com o tempo que sobrou
    auto    usa DEFAULT_SOLVER, escolhido a partir da comparação em docs/experimentos.md
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from .exact.dinkelbach import dinkelbach
from .exact.dinkelbach_gurobi import GurobiUnavailable, dinkelbach_gurobi
from .heuristics.greedy import greedy
from .heuristics.local_search import improve
from .instance import Instance, read_instance
from .preprocess import preprocess
from .solution import Evaluation, Solution, evaluate, write_solution


SOLVERS = ("cpsat", "gurobi", "auto")
# Solver usado com --solver auto. Ver a comparação CP-SAT × Gurobi em docs/experimentos.md.
DEFAULT_SOLVER = "cpsat"


@dataclass
class RunResult:
    solution: Solution | None
    evaluation: Evaluation | None
    method: str
    proven_optimal: bool
    heuristic_objective: float
    seconds: float
    solver: str = ""  # solver que realmente rodou o Dinkelbach (após um eventual fallback)


def solve(
    inst: Instance,
    time_limit: float = 60.0,
    heuristic_share: float = 0.15,
    workers: int | None = None,
    use_exact: bool = True,
    verbose: bool = True,
    solver_log: bool = False,
    solver: str = "auto",
) -> RunResult:
    log = print if verbose else (lambda *_: None)
    t0 = time.perf_counter()
    log(f"{inst}")

    red = preprocess(inst)
    log(f"  pré-processamento: -{red.removed_orders} pedidos, -{red.removed_aisles} corredores")

    sol = greedy(inst, red, time_limit=time_limit * heuristic_share)
    if sol is not None:
        sol = improve(inst, red, sol)
    h_obj = sol.objective(inst) if sol else 0.0
    log(f"  heurística: {h_obj:.4f} ({time.perf_counter() - t0:.1f}s)")

    method, proven, used = "heuristica", False, ""
    if use_exact:
        res, used = _run_exact(inst, red, sol, time_limit - (time.perf_counter() - t0), t0, time_limit,
                               solver, workers, log, solver_log)
        if res.solution is not None and (sol is None or res.solution.objective(inst) >= sol.objective(inst)):
            if sol is None or res.solution.objective(inst) > sol.objective(inst):
                method = "dinkelbach" if used == "cpsat" else f"dinkelbach-{used}"
            sol = res.solution
        proven = res.proven_optimal

    ev = evaluate(inst, sol) if sol else None
    if ev is not None and not ev.feasible:  # nunca deveria acontecer; protege a nota
        log(f"  ATENÇÃO: solução inviável ({ev.message})")
        sol, ev = None, None

    secs = time.perf_counter() - t0
    if ev:
        log(f"  final: {ev.objective:.4f} ({ev.units} unidades / {ev.n_aisles} corredores)"
            f"{' ÓTIMO PROVADO' if proven else ''} em {secs:.1f}s")
    return RunResult(sol, ev, method, proven, h_obj, secs, used)


def _run_exact(inst, red, sol, remaining, t0, time_limit, solver, workers, log, solver_log):
    """Roda o Dinkelbach com o solver pedido. Devolve (resultado, nome do solver usado)."""
    if solver == "auto":
        solver = DEFAULT_SOLVER
    if solver not in ("cpsat", "gurobi"):
        raise ValueError(f"solver desconhecido: {solver!r} (use {', '.join(SOLVERS)})")
    if solver == "gurobi":
        log("  solver: Gurobi")
        try:
            return dinkelbach_gurobi(inst, red, initial=sol, time_limit=remaining, workers=workers,
                                     log=log, solver_log=solver_log), "gurobi"
        except GurobiUnavailable as e:
            log(f"  Gurobi indisponível ({e}); usando CP-SAT")
            remaining = time_limit - (time.perf_counter() - t0)
    log("  solver: CP-SAT")
    return dinkelbach(inst, red, initial=sol, time_limit=remaining, workers=workers,
                      log=log, solver_log=solver_log), "cpsat"


def main() -> None:
    p = argparse.ArgumentParser(description="Resolve uma instância do Wave Order Picking.")
    p.add_argument("instance", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--time", type=float, default=60.0, help="limite de tempo total em segundos")
    p.add_argument("--workers", type=int, default=None, help="threads do solver (padrão: todas)")
    p.add_argument("--solver", choices=SOLVERS, default="auto",
                   help=f"solver do Dinkelbach (auto = {DEFAULT_SOLVER})")
    p.add_argument("--no-exact", action="store_true", help="só heurística")
    p.add_argument("--solver-log", action="store_true", help="mostra o log do solver")
    args = p.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    inst = read_instance(args.instance)
    res = solve(inst, args.time, workers=args.workers, use_exact=not args.no_exact,
                solver_log=args.solver_log, solver=args.solver)
    if res.solution is None:
        raise SystemExit("Nenhuma solução viável encontrada.")
    write_solution(res.solution, args.output)
    print(f"Solução salva em {args.output}")


if __name__ == "__main__":
    main()
