"""Testes dos movimentos de busca local e da ILS (issue #3)."""

import time

import numpy as np
import pytest
from test_example import EXAMPLE

from wavepick import Solution, evaluate, read_instance
from wavepick.heuristics.greedy import greedy
from wavepick.heuristics.local_search import ils, local_search, swap_aisles, swap_orders
from wavepick.pipeline import solve
from wavepick.preprocess import preprocess

# 1 item, 1 corredor com 10 unidades, UB=10, pedidos de 6, 5 e 5 unidades.
# A gulosa pega o de 6 e trava; o ótimo troca-o pelos dois de 5.
TROCA = """3 1 1
1 0 6
1 0 5
1 0 5
1 0 10
1 10
"""


# O corredor 0 dá razão 10. O ótimo (15) exige os corredores 1 e 2 juntos: o pedido de 30
# unidades pede um item de cada. Nenhum movimento de um corredor por vez chega lá.
ARMADILHA = """2 3 3
1 0 10
2 1 15 2 15
1 0 10
1 1 15
1 2 15
1 30
"""


def _read(tmp_path, text):
    p = tmp_path / "inst.txt"
    p.write_text(text)
    return read_instance(p)


@pytest.fixture
def exemplo(tmp_path):
    return _read(tmp_path, EXAMPLE)


@pytest.fixture
def troca(tmp_path):
    return _read(tmp_path, TROCA)


def test_troca_de_corredor_melhora_a_razao(exemplo):
    start = Solution([0, 2, 3], [1, 3, 4])  # razão 4.0
    ev = evaluate(exemplo, swap_aisles(exemplo, preprocess(exemplo), start))
    assert ev.feasible and ev.objective > 4.0


def test_troca_de_corredor_nao_mexe_no_otimo(exemplo):
    best = Solution([0, 1, 2, 4], [1, 3])  # razão 5.0 (ótimo)
    assert swap_aisles(exemplo, preprocess(exemplo), best) == best


def test_troca_de_pedidos_soma_mais_unidades(troca):
    sol = swap_orders(troca, preprocess(troca), Solution([0], [0]))
    assert sol == Solution([1, 2], [0])
    assert evaluate(troca, sol).feasible


def test_ils_chega_ao_otimo_do_exemplo(exemplo):
    start = Solution([0, 2, 3], [1, 3, 4])
    sol = ils(exemplo, preprocess(exemplo), start, time_limit=2)
    ev = evaluate(exemplo, sol)
    assert ev.feasible and ev.objective == 5.0


def test_ils_nunca_piora_e_respeita_o_tempo(exemplo):
    best = Solution([0, 1, 2, 4], [1, 3])
    t0 = time.perf_counter()
    sol = ils(exemplo, preprocess(exemplo), best, time_limit=1)
    assert time.perf_counter() - t0 < 3
    assert evaluate(exemplo, sol).feasible and sol.objective(exemplo) == 5.0


def test_perturbacao_escapa_de_otimo_local(tmp_path):
    inst = _read(tmp_path, ARMADILHA)
    red = preprocess(inst)
    start = Solution([0], [0])
    assert local_search(inst, red, start) == start  # a busca local sozinha fica presa
    assert ils(inst, red, start, time_limit=1) == Solution([1], [1, 2])


def test_ils_sai_de_solucao_abaixo_do_lb(tmp_path):
    inst = _read(tmp_path, TROCA.replace("1 10\n", "8 10\n"))
    start = Solution([1], [0])  # 5 unidades, LB = 8
    assert not evaluate(inst, start).feasible
    ev = evaluate(inst, ils(inst, preprocess(inst), start, time_limit=1))
    assert ev.feasible and ev.units == 10


def test_troca_de_corredor_nao_aceita_solucao_abaixo_do_lb(tmp_path):
    # Só o corredor 0 daria razão 10, mas 10 unidades ficam abaixo de LB = 20.
    inst = _read(tmp_path, ARMADILHA.replace("1 30\n", "20 30\n"))
    start = Solution([1], [1, 2])
    assert swap_aisles(inst, preprocess(inst), start) == start


@pytest.mark.parametrize("seed", range(8))
def test_ils_em_instancias_aleatorias_e_viavel_e_nao_piora(tmp_path, seed):
    rng = np.random.default_rng(seed)

    def linha(max_itens, max_qtd):
        itens = rng.choice(8, size=int(rng.integers(1, max_itens + 1)), replace=False)
        return " ".join([str(itens.size), *(f"{i} {rng.integers(1, max_qtd + 1)}" for i in itens)])

    linhas = ["30 8 10", *(linha(3, 3) for _ in range(30)), *(linha(5, 8) for _ in range(10)), "5 40"]
    inst = _read(tmp_path, "\n".join(linhas) + "\n")
    red = preprocess(inst)
    start = greedy(inst, red)
    assert start is not None
    ev = evaluate(inst, ils(inst, red, start, time_limit=0.3, seed=seed))
    assert ev.feasible and ev.objective >= start.objective(inst)


def test_pipeline_so_heuristica_usa_a_busca_local(troca):
    res = solve(troca, time_limit=3, use_exact=False, verbose=False)
    assert res.evaluation.objective == 10.0
    assert res.heuristic_objective == 10.0
