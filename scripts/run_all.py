"""Roda o pipeline em todas as instâncias e salva as soluções em solutions/<dataset>/.

Por padrão SÓ SOBRESCREVE uma solução se a nova for melhor (a pasta solutions/ guarda
sempre o melhor resultado que o grupo já obteve). Cada execução também é registrada em
results/runs.csv para acompanharmos a evolução.

Exemplos:
    uv run python scripts/run_all.py --datasets a --time 60
    uv run python scripts/run_all.py --datasets b x --time 300 --only instance_0011
"""

from __future__ import annotations

import argparse
import csv
import socket
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wavepick import evaluate, read_instance, read_solution, write_solution  # noqa: E402
from wavepick.pipeline import solve  # noqa: E402

DATA = ROOT / "vendor" / "challenge-sbpo-2025" / "datasets"
SOLUTIONS = ROOT / "solutions"
RUNS = ROOT / "results" / "runs.csv"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser()
    p.add_argument("--datasets", nargs="+", default=["a", "b", "x"])
    p.add_argument("--time", type=float, default=60.0, help="segundos por instância")
    p.add_argument("--only", nargs="*", default=None, help="filtra por nome (ex.: instance_0001)")
    p.add_argument("--workers", type=int, default=None)
    p.add_argument("--no-exact", action="store_true")
    p.add_argument("--overwrite", action="store_true", help="salva mesmo se for pior que a atual")
    p.add_argument("--tag", default="", help="rótulo livre para identificar a execução no runs.csv")
    args = p.parse_args()

    if not DATA.exists():
        raise SystemExit(
            "Dados não encontrados. Rode:\n"
            "  git clone --depth 1 https://github.com/mercadolibre/challenge-sbpo-2025 vendor/challenge-sbpo-2025"
        )

    RUNS.parent.mkdir(parents=True, exist_ok=True)
    new_file = not RUNS.exists()
    with RUNS.open("a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new_file:
            w.writerow(["data", "maquina", "tag", "dataset", "instancia", "tempo_limite", "segundos",
                        "metodo", "heuristica", "objetivo", "otimo_provado", "salvo"])
        for ds in args.datasets:
            for path in sorted((DATA / ds).glob("instance_*.txt")):
                if args.only and not any(f in path.name for f in args.only):
                    continue
                inst = read_instance(path)
                res = solve(inst, args.time, workers=args.workers, use_exact=not args.no_exact)
                out = SOLUTIONS / ds / path.name
                saved = False
                if res.solution is not None:
                    old = evaluate(inst, read_solution(out)) if out.exists() else None
                    new_obj = res.evaluation.objective
                    if args.overwrite or old is None or not old.feasible or new_obj > old.objective + 1e-9:
                        write_solution(res.solution, out)
                        saved = True
                    else:
                        print(f"  (mantida solução anterior: {old.objective:.4f} >= {new_obj:.4f})")
                w.writerow([
                    datetime.now().isoformat(timespec="seconds"), socket.gethostname(), args.tag, ds, path.name,
                    args.time, f"{res.seconds:.1f}", res.method, f"{res.heuristic_objective:.6f}",
                    f"{res.evaluation.objective:.6f}" if res.evaluation else "", res.proven_optimal, saved,
                ])
                fh.flush()
                print()


if __name__ == "__main__":
    t = time.perf_counter()
    main()
    print(f"Tempo total: {time.perf_counter() - t:.0f}s")
