"""Compara CP-SAT × Gurobi no Dinkelbach, nas mesmas condições.

Para cada instância:
    1. roda pré-processamento + heurística UMA vez (as duas execuções partem da MESMA solução);
    2. roda o Dinkelbach com cada solver, com o mesmo limite de tempo e o mesmo nº de threads;
    3. valida o resultado com o verificador (mesmas regras do checker oficial).

Saídas:
    results/solvers.csv              histórico (uma linha por instância × solver, acumulativo)
    results/comparacao_solvers.md    tabela da última execução (copiar para docs/experimentos.md)

Exemplos:
    uv run python scripts/compare_solvers.py                       # as 5 instâncias padrão, 120 s
    uv run python scripts/compare_solvers.py --time 60 --instances a/instance_0001 a/instance_0017
"""

from __future__ import annotations

import argparse
import csv
import os
import socket
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wavepick import evaluate, read_instance  # noqa: E402
from wavepick.exact.dinkelbach import dinkelbach  # noqa: E402
from wavepick.exact.dinkelbach_gurobi import GurobiUnavailable, dinkelbach_gurobi, gurobi_status  # noqa: E402
from wavepick.heuristics.greedy import greedy  # noqa: E402
from wavepick.heuristics.local_search import improve  # noqa: E402
from wavepick.preprocess import preprocess  # noqa: E402

VENDOR = ROOT / "vendor" / "challenge-sbpo-2025"
DATA = VENDOR / "datasets"
BEST = VENDOR / "best_solutions" / "best_objectives.csv"
OUT_CSV = ROOT / "results" / "solvers.csv"
OUT_MD = ROOT / "results" / "comparacao_solvers.md"

# 2 de A, 2 de B, 1 de X: as instâncias mais distantes da referência na 1ª rodada
# (é onde um solver mais forte pode fazer diferença).
DEFAULT_INSTANCES = ["a/instance_0005", "a/instance_0011", "b/instance_0002", "b/instance_0006", "x/instance_0006"]
SOLVERS = {"cpsat": dinkelbach, "gurobi": dinkelbach_gurobi}


def load_reference() -> dict[str, float]:
    if not BEST.exists():
        return {}
    with BEST.open(encoding="utf-8") as fh:
        return {f"{r['dataset']}/{r['instance'].removesuffix('.txt')}": float(r["best_objective"])
                for r in csv.DictReader(fh)}


def time_to_best(history: list[dict], final: float, start: float) -> float:
    """Momento (s) em que o Dinkelbach chegou na razão final; 0 se não melhorou a solução inicial."""
    if final <= start + 1e-9:
        return 0.0
    hits = [h["time"] for h in history if h.get("ratio") is not None and h["ratio"] >= final - 1e-9]
    return min(hits) if hits else float("nan")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--instances", nargs="+", default=DEFAULT_INSTANCES, help="ex.: a/instance_0005")
    p.add_argument("--time", type=float, default=120.0, help="segundos do Dinkelbach para CADA solver")
    p.add_argument("--heur-time", type=float, default=15.0, help="segundos da heurística (compartilhada)")
    p.add_argument("--workers", type=int, default=None, help="threads (iguais para os dois solvers)")
    p.add_argument("--solvers", nargs="+", choices=list(SOLVERS), default=list(SOLVERS))
    p.add_argument("--no-start", action="store_true",
                   help="Dinkelbach sem solução inicial (mede só a força do solver)")
    p.add_argument("--quiet", action="store_true", help="esconde o log das iterações")
    p.add_argument("--tag", default="", help="rótulo livre no results/solvers.csv")
    args = p.parse_args()

    if not DATA.exists():
        raise SystemExit("Dados não encontrados em vendor/ (veja o README).")
    workers = args.workers or os.cpu_count() or 4
    status = gurobi_status()
    heur = "desligada" if args.no_start else f"{args.heur_time:.0f}s"
    print(f"{status}\nThreads: {workers} | Dinkelbach: {args.time:.0f}s por solver | heurística: {heur}\n")

    ref = load_reference()
    log = (lambda *_: None) if args.quiet else print
    rows = []
    for name in args.instances:
        ds, inst_name = name.split("/")
        inst = read_instance(DATA / ds / f"{inst_name}.txt")
        red = preprocess(inst)
        print(f"== {name}: {len(red.orders)} pedidos, {len(red.aisles)} corredores (após pré-processamento)")
        start = None
        if not args.no_start:
            start = greedy(inst, red, time_limit=args.heur_time)
            if start is not None:
                start = improve(inst, red, start)
        start_obj = start.objective(inst) if start else 0.0
        print(f"  solução inicial: {start_obj:.4f}" + (" (sem heurística)" if args.no_start else " (heurística)"))

        for solver in args.solvers:
            print(f"  -- {solver}")
            t = time.perf_counter()
            row = {"instancia": name, "solver": solver, "inicial": start_obj, "referencia": ref.get(name, ""),
                   "objetivo": "", "otimo_provado": "", "iteracoes": "", "t_melhor": "", "segundos": "", "obs": ""}
            try:
                res = SOLVERS[solver](inst, red, initial=start, time_limit=args.time, workers=workers, log=log)
            except GurobiUnavailable as e:
                row["obs"] = "sem licença p/ este tamanho"
                print(f"  {solver}: {e}")
                rows.append(row)
                continue
            secs = time.perf_counter() - t
            ev = evaluate(inst, res.solution) if res.solution else None
            obj = ev.objective if ev and ev.feasible else 0.0
            if ev and not ev.feasible:
                row["obs"] = f"INVIÁVEL: {ev.message}"
            row.update(objetivo=obj, otimo_provado=res.proven_optimal, iteracoes=res.iterations,
                       t_melhor=time_to_best(res.history, obj, start_obj), segundos=secs)
            print(f"  {solver}: {obj:.4f}{' (ótimo provado)' if res.proven_optimal else ''} "
                  f"em {secs:.1f}s, {res.iterations} iterações")
            rows.append(row)
        print()

    _save_csv(rows, args, workers)
    md = _markdown(rows, args, workers, status)
    OUT_MD.write_text(md, encoding="utf-8")
    print(md)
    print(f"Tabela salva em {OUT_MD.relative_to(ROOT)} e histórico em {OUT_CSV.relative_to(ROOT)}")


def _save_csv(rows, args, workers) -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    new = not OUT_CSV.exists()
    with OUT_CSV.open("a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["data", "maquina", "tag", "tempo_limite", "threads", "instancia", "solver", "inicial",
                        "objetivo", "referencia", "otimo_provado", "iteracoes", "t_melhor", "segundos", "obs"])
        now = datetime.now().isoformat(timespec="seconds")
        for r in rows:
            w.writerow([now, socket.gethostname(), args.tag, args.time, workers, r["instancia"], r["solver"],
                        _f(r["inicial"]), _f(r["objetivo"]), _f(r["referencia"]), r["otimo_provado"],
                        r["iteracoes"], _f(r["t_melhor"], 1), _f(r["segundos"], 1), r["obs"]])


def _f(v, d: int = 6) -> str:
    return f"{v:.{d}f}" if isinstance(v, float) else str(v)


def _markdown(rows, args, workers, status) -> str:
    by_inst: dict[str, dict[str, dict]] = {}
    for r in rows:
        by_inst.setdefault(r["instancia"], {})[r["solver"]] = r
    solvers = args.solvers
    head = ["Instância", "Referência", "Heurística"]
    for s in solvers:
        head += [f"{s} obj", f"{s} % ref", f"{s} t. melhor (s)", f"{s} t. total (s)", f"{s} ótimo?"]
    head.append("Vencedor")
    start = ("partindo do zero (sem heurística)" if args.no_start
             else f"mesma solução inicial (heurística de {args.heur_time:.0f} s)")
    lines = [
        f"Dinkelbach com **{args.time:.0f} s por solver**, {workers} threads, {start}. {status}.",
        "",
        "| " + " | ".join(head) + " |",
        "|" + "|".join(["---"] + ["---:"] * (len(head) - 2) + ["---"]) + "|",
    ]
    wins = {s: 0 for s in solvers}
    for name, per in by_inst.items():
        any_r = next(iter(per.values()))
        refv = any_r["referencia"]
        cells = [name.upper().replace("/INSTANCE_", "/"), _num(refv), _num(any_r["inicial"])]
        objs = {}
        for s in solvers:
            r = per.get(s)
            if r is None or r["objetivo"] == "":
                cells += ["—", "—", "—", "—", r["obs"] if r else "—"]
                continue
            objs[s] = r["objetivo"]
            pct = f"{100 * r['objetivo'] / refv:.1f}%" if refv else "—"
            cells += [_num(r["objetivo"]), pct, _num(r["t_melhor"], 1), _num(r["segundos"], 1),
                      "sim" if r["otimo_provado"] else "não"]
        winner = _winner(objs, per)
        if winner in wins:
            wins[winner] += 1
        cells.append(winner)
        lines.append("| " + " | ".join(cells) + " |")
    lines += ["", "Vitórias: " + ", ".join(f"{s} {n}" for s, n in wins.items())
              + " (critério: maior objetivo; empate → menor tempo até a melhor solução).", ""]
    return "\n".join(lines)


def _winner(objs: dict[str, float], per: dict[str, dict]) -> str:
    if len(objs) < 2:
        return "—"
    best = max(objs.values())
    top = [s for s, v in objs.items() if v >= best - 1e-9]
    if len(top) == 1:
        return top[0]
    times = {s: per[s]["t_melhor"] for s in top}
    fastest = min(times.values())
    fast = [s for s in top if times[s] <= fastest + 0.5]
    return fast[0] if len(fast) == 1 else "empate"


def _num(v, d: int = 2) -> str:
    return f"{v:.{d}f}" if isinstance(v, float) else "—"


if __name__ == "__main__":
    main()
