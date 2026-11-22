"""Compara as soluções em solutions/ com os melhores valores conhecidos (best_objectives.csv).

Valida cada solução com o nosso verificador e, com --official, também com o checker.py oficial.
Gera results/comparacao.csv e results/comparacao.md (tabela pronta para a apresentação).

    uv run python scripts/compare.py --official
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wavepick import evaluate, read_instance, read_solution  # noqa: E402

VENDOR = ROOT / "vendor" / "challenge-sbpo-2025"
DATA = VENDOR / "datasets"
BEST = VENDOR / "best_solutions" / "best_objectives.csv"
SOLUTIONS = ROOT / "solutions"
OUT = ROOT / "results"


def official_check(instance: Path, solution: Path) -> tuple[bool, float | None]:
    r = subprocess.run(
        [sys.executable, str(VENDOR / "checker.py"), str(instance), str(solution)],
        capture_output=True, text=True,
    )
    feasible = "Is solution feasible: True" in r.stdout
    obj = None
    for line in r.stdout.splitlines():
        if line.startswith("Objective function value:"):
            obj = float(line.split(":")[1])
    return feasible, obj


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser()
    p.add_argument("--official", action="store_true", help="também roda o checker.py oficial")
    args = p.parse_args()

    rows = []
    with BEST.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            ds, name, best = r["dataset"], r["instance"], float(r["best_objective"])
            sol_path = SOLUTIONS / ds / name
            row = {"dataset": ds, "instancia": name, "referencia": best, "nosso": 0.0,
                   "pct_referencia": 0.0, "viavel": False, "checker_oficial": ""}
            if sol_path.exists():
                inst = read_instance(DATA / ds / name)
                ev = evaluate(inst, read_solution(sol_path))
                row["viavel"] = ev.feasible
                row["nosso"] = ev.objective if ev.feasible else 0.0
                if args.official:
                    ok, obj = official_check(DATA / ds / name, sol_path)
                    row["checker_oficial"] = "ok" if ok else "INVÁLIDA"
                    if ok != ev.feasible or (ok and abs(obj - ev.objective) > 1e-6):
                        print(f"ATENÇÃO: divergência com o checker oficial em {ds}/{name}")
                    if not ok:
                        row["nosso"] = 0.0
                row["pct_referencia"] = 100 * row["nosso"] / best
            rows.append(row)

    OUT.mkdir(exist_ok=True)
    with (OUT / "comparacao.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    lines = ["| Dataset | Instância | Referência | Nosso | % da referência | Checker |", "|---|---|---:|---:|---:|---|"]
    for r in rows:
        lines.append(f"| {r['dataset'].upper()} | {r['instancia'].removesuffix('.txt')} | {r['referencia']:.2f} | "
                     f"{r['nosso']:.2f} | {r['pct_referencia']:.1f}% | {r['checker_oficial'] or ('ok' if r['viavel'] else '—')} |")
    lines.append("")
    lines.append("| Dataset | Instâncias resolvidas | Média % da referência |")
    lines.append("|---|---:|---:|")
    for ds in sorted({r["dataset"] for r in rows}) + ["total"]:
        sub = [r for r in rows if ds == "total" or r["dataset"] == ds]
        solved = sum(1 for r in sub if r["nosso"] > 0)
        mean = sum(r["pct_referencia"] for r in sub) / len(sub)
        lines.append(f"| {ds.upper()} | {solved}/{len(sub)} | {mean:.1f}% |")
    (OUT / "comparacao.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
