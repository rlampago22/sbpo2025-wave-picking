"""Pipeline completo para UMA instância:

    pré-processamento → heurística gulosa → melhoria local → Dinkelbach (CP-SAT) → verificação → arquivo

Uso:
    uv run python -m wavepick.pipeline <instancia.txt> <saida.txt> [--time 60]
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from .exact.dinkelbach import dinkelbach, kfixed, lns
from .heuristics.greedy import greedy
from .heuristics.local_search import improve
from .instance import Instance, read_instance
from .preprocess import preprocess
from .solution import Evaluation, Solution, evaluate, write_solution


HYBRID_LNS_SHARE = 0.5

# Variantes do método exato (ver docs/04-modelo-exato.md)
VARIANTS = ("base", "strong", "kfixed", "lns", "lns-strong", "hybrid")


def run_exact(variant, inst, red, sol, time_limit, workers, log, solver_log):
    """Despacha para a variante pedida do método exato."""
    kw = dict(initial=sol, time_limit=time_limit, workers=workers, log=log, solver_log=solver_log)
    if variant == "base":
        return dinkelbach(inst, red, **kw)
    if variant == "strong":
        return dinkelbach(inst, red, strengthen=True, **kw)
    if variant == "kfixed":
        return kfixed(inst, red, **kw)
    if variant == "lns":
        return lns(inst, red, **kw)
    if variant == "hybrid":
        # LNS primeiro (sobe rápido), depois Dinkelbach no modelo completo a partir da solução do LNS.
        t0 = time.perf_counter()
        r1 = lns(inst, red, **{**kw, "time_limit": time_limit * HYBRID_LNS_SHARE})
        kw2 = {**kw, "initial": r1.solution or sol, "time_limit": time_limit - (time.perf_counter() - t0)}
        return dinkelbach(inst, red, **kw2)
    if variant == "lns-strong":
        return lns(inst, red, strengthen=True, **kw)
    raise ValueError(f"variante desconhecida: {variant} (use uma de {VARIANTS})")


@dataclass
class RunResult:
    solution: Solution | None
    evaluation: Evaluation | None
    method: str
    proven_optimal: bool
    heuristic_objective: float
    seconds: float


def solve(
    inst: Instance,
    time_limit: float = 60.0,
    heuristic_share: float = 0.15,
    workers: int | None = None,
    use_exact: bool = True,
    verbose: bool = True,
    solver_log: bool = False,
    variant: str = "hybrid",
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

    method, proven = "heuristica", False
    if use_exact:
        remaining = time_limit - (time.perf_counter() - t0)
        res = run_exact(variant, inst, red, sol, remaining, workers, log, solver_log)
        if res.solution is not None and (sol is None or res.solution.objective(inst) >= sol.objective(inst)):
            if sol is None or res.solution.objective(inst) > sol.objective(inst):
                method = variant
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
    return RunResult(sol, ev, method, proven, h_obj, secs)


def main() -> None:
    p = argparse.ArgumentParser(description="Resolve uma instância do Wave Order Picking.")
    p.add_argument("instance", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--time", type=float, default=60.0, help="limite de tempo total em segundos")
    p.add_argument("--workers", type=int, default=None, help="threads do CP-SAT (padrão: todas)")
    p.add_argument("--variant", choices=VARIANTS, default="hybrid", help="variante do método exato")
    p.add_argument("--no-exact", action="store_true", help="só heurística")
    p.add_argument("--solver-log", action="store_true", help="mostra o log do CP-SAT")
    args = p.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    inst = read_instance(args.instance)
    res = solve(inst, args.time, workers=args.workers, use_exact=not args.no_exact, solver_log=args.solver_log,
                variant=args.variant)
    if res.solution is None:
        raise SystemExit("Nenhuma solução viável encontrada.")
    write_solution(res.solution, args.output)
    print(f"Solução salva em {args.output}")


if __name__ == "__main__":
    main()
