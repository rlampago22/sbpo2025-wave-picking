"""Testes com o exemplo do PDF oficial (5 pedidos, 5 itens, 5 corredores, ótimo = 5)."""

from pathlib import Path

import pytest

from wavepick import Solution, evaluate, read_instance, read_solution, write_solution
from wavepick.exact.dinkelbach import dinkelbach, kfixed, lns, neighborhood
from wavepick.heuristics.greedy import greedy
from wavepick.preprocess import preprocess

EXAMPLE = """5 5 5
2 0 3 2 1
2 1 1 3 1
2 2 1 4 2
4 0 1 2 2 3 1 4 1
1 1 1
4 0 2 1 1 2 1 4 1
4 0 2 1 1 2 2 4 1
3 1 2 3 1 4 2
4 0 2 1 1 3 1 4 1
4 1 1 2 2 3 1 4 2
5 12
"""

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "vendor" / "challenge-sbpo-2025" / "checker.py"


@pytest.fixture
def inst(tmp_path):
    p = tmp_path / "exemplo.txt"
    p.write_text(EXAMPLE)
    return read_instance(p)


def test_leitura(inst):
    assert (inst.n_orders, inst.n_items, inst.n_aisles) == (5, 5, 5)
    assert (inst.lb, inst.ub) == (5, 12)
    assert inst.order_size.tolist() == [4, 2, 3, 5, 1]


def test_solucoes_do_pdf(inst):
    assert evaluate(inst, Solution([0, 4], [0, 1])).objective == 2.5
    assert evaluate(inst, Solution([0, 2, 3], [1, 3, 4])).objective == 4.0
    ev = evaluate(inst, Solution([0, 1, 2, 4], [1, 3]))
    assert ev.feasible and ev.objective == 5.0


def test_inviaveis(inst):
    assert not evaluate(inst, Solution([0, 1, 2, 3, 4], [0, 1, 2, 3, 4])).feasible  # passa do UB
    assert not evaluate(inst, Solution([4], [0])).feasible  # abaixo do LB
    assert not evaluate(inst, Solution([0, 1, 2, 4], [1])).feasible  # falta estoque
    assert not evaluate(inst, Solution([0], [])).feasible  # sem corredor


def test_heuristica_viavel(inst):
    sol = greedy(inst, preprocess(inst))
    assert sol is not None and evaluate(inst, sol).feasible


def test_dinkelbach_otimo(inst):
    res = dinkelbach(inst, preprocess(inst), time_limit=10, log=lambda *_: None)
    assert res.proven_optimal
    assert evaluate(inst, res.solution).objective == 5.0


def test_dinkelbach_modelo_fortalecido_mesmo_otimo(inst):
    res = dinkelbach(inst, preprocess(inst), time_limit=10, log=lambda *_: None, strengthen=True)
    assert res.proven_optimal
    assert evaluate(inst, res.solution).objective == 5.0


def test_k_fixo_otimo(inst):
    res = kfixed(inst, preprocess(inst), time_limit=20, log=lambda *_: None)
    assert res.proven_optimal
    assert evaluate(inst, res.solution).objective == 5.0


def test_k_fixo_com_modelo_fortalecido(inst):
    res = kfixed(inst, preprocess(inst), time_limit=20, log=lambda *_: None, strengthen=True)
    assert evaluate(inst, res.solution).objective == 5.0


def test_vizinhanca_contem_solucao_e_lns_nao_piora(inst):
    red = preprocess(inst)
    start = Solution([0, 2, 3], [1, 3, 4])  # razão 4.0
    sub = neighborhood(inst, red, start, max_aisles=2, max_orders=1)
    assert set(start.aisles) <= set(sub.aisles.tolist())
    assert set(start.orders) <= set(sub.orders.tolist())
    res = lns(inst, red, initial=start, time_limit=10, log=lambda *_: None)
    ev = evaluate(inst, res.solution)
    assert ev.feasible and ev.objective >= 4.0


def test_escrita_e_checker_oficial(inst, tmp_path):
    sol = Solution([0, 1, 2, 4], [1, 3])
    out = tmp_path / "sol.txt"
    write_solution(sol, out)
    assert read_solution(out) == sol
    if not CHECKER.exists():
        pytest.skip("checker oficial não baixado em vendor/")
    import subprocess
    import sys

    inst_path = tmp_path / "exemplo.txt"
    r = subprocess.run([sys.executable, str(CHECKER), str(inst_path), str(out)], capture_output=True, text=True)
    assert "Is solution feasible: True" in r.stdout
    assert "Objective function value: 5.0" in r.stdout


# ---------------------------------------------------------------- Gurobi
from wavepick.exact.dinkelbach_gurobi import GurobiUnavailable, dinkelbach_gurobi  # noqa: E402
from wavepick.pipeline import solve  # noqa: E402


def _gurobi_or_skip(fn):
    try:
        return fn()
    except GurobiUnavailable as e:
        pytest.skip(f"Gurobi indisponível: {e}")


def test_dinkelbach_gurobi_otimo(inst):
    res = _gurobi_or_skip(lambda: dinkelbach_gurobi(inst, preprocess(inst), time_limit=10, log=lambda *_: None))
    assert res.proven_optimal
    assert evaluate(inst, res.solution).objective == 5.0


def test_dinkelbach_gurobi_com_solucao_inicial(inst):
    start = greedy(inst, preprocess(inst))
    res = _gurobi_or_skip(lambda: dinkelbach_gurobi(inst, preprocess(inst), initial=start, time_limit=10,
                                                    log=lambda *_: None))
    assert res.proven_optimal and evaluate(inst, res.solution).objective == 5.0


@pytest.mark.parametrize("solver", ["cpsat", "gurobi", "auto"])
def test_pipeline_com_solver(inst, solver):
    # Com --solver gurobi sem licença o pipeline cai para o CP-SAT: tem que funcionar sempre.
    res = solve(inst, time_limit=10, verbose=False, solver=solver)
    assert res.evaluation.feasible and res.evaluation.objective == 5.0
    assert res.solver in ("cpsat", "gurobi")
    if solver == "cpsat":
        assert res.solver == "cpsat"


def test_pipeline_solver_invalido(inst):
    with pytest.raises(ValueError):
        solve(inst, time_limit=5, verbose=False, solver="cplex")


def test_pipeline_gurobi_sem_licenca_cai_para_cpsat(inst, monkeypatch):
    import wavepick.pipeline as pl

    def sem_licenca(*_, **__):
        raise GurobiUnavailable("simulado")

    monkeypatch.setattr(pl, "dinkelbach_gurobi", sem_licenca)
    res = solve(inst, time_limit=10, verbose=False, solver="gurobi")
    assert res.solver == "cpsat" and res.evaluation.objective == 5.0


@pytest.mark.parametrize("variant", ["base", "hybrid", "lns"])
def test_pipeline_variante_com_gurobi(inst, variant):
    # --solver gurobi com qualquer variante: Gurobi onde se aplica, CP-SAT no resto (ou sem licença).
    res = solve(inst, time_limit=10, verbose=False, variant=variant, solver="gurobi")
    assert res.evaluation.feasible and res.evaluation.objective == 5.0
    if variant == "lns":
        assert res.solver == "cpsat"
