# SBPO 2025: Wave Order Picking

Trabalho final de APA: algoritmos para o [Desafio Mercado Livre de Otimização (SBPO 2025)](https://github.com/mercadolibre/challenge-sbpo-2025).

**Problema:** escolher um subconjunto de pedidos (a *wave*) e de corredores para maximizar **unidades coletadas / corredores visitados**, com o tamanho da wave entre LB e UB e estoque suficiente nos corredores escolhidos.

**Abordagem:** pré-processamento → heurística gulosa + melhoria local → **Dinkelbach com CP-SAT (OR-Tools)** → verificação.

## 📚 Documentação (leia nesta ordem)

1. [Entendendo o problema](docs/01-entendendo-o-problema.md)
2. [Arquitetura e abordagem](docs/02-arquitetura.md)
3. [**Plano de execução: tarefas de cada um**](docs/03-plano-de-execucao.md)

## Instalação

Pré-requisitos: [Git](https://git-scm.com/) e [uv](https://docs.astral.sh/uv/getting-started/installation/) (gerenciador de Python; instale com `pip install uv` ou `winget install astral-sh.uv`).

```powershell
git clone https://github.com/rlampago22/sbpo2025-wave-picking
cd sbpo2025-wave-picking
git clone --depth 1 https://github.com/mercadolibre/challenge-sbpo-2025 vendor/challenge-sbpo-2025
uv sync
uv run pytest
```

O `uv sync` cria o ambiente com Python 3.13 e instala OR-Tools, NumPy e SciPy. As instâncias e o `checker.py` oficial ficam em `vendor/` (não versionado).

## Uso

```powershell
# Uma instância
uv run python -m wavepick.pipeline vendor/challenge-sbpo-2025/datasets/a/instance_0010.txt tmp/a10.txt --time 60

# Checker oficial
uv run python vendor/challenge-sbpo-2025/checker.py vendor/challenge-sbpo-2025/datasets/a/instance_0010.txt tmp/a10.txt

# Todas as instâncias de um dataset (só salva em solutions/ se melhorar)
uv run python scripts/run_all.py --datasets a --time 60 --tag minha-versao

# Tabela de comparação com os valores de referência (gera results/comparacao.md)
uv run python scripts/compare.py --official
```

## Estrutura

```
src/wavepick/
  instance.py            leitura das instâncias
  solution.py            solução + verificação (mesmas regras do checker oficial)
  preprocess.py          redução do problema
  heuristics/            gulosa e busca local
  exact/                 Dinkelbach + CP-SAT
  pipeline.py            junta tudo (CLI)
scripts/                 run_all.py, compare.py
solutions/a|b|x/         melhores soluções encontradas (entregável)
results/                 comparacao.md/csv e histórico runs.csv
tests/                   exemplo do PDF
docs/                    documentação e plano
```

## Status

- [x] Entendimento do problema e arquitetura
- [x] Pipeline completo (heurística + Dinkelbach/CP-SAT + verificador)
- [x] Primeira rodada em A, B e X: 50/50 válidas, **97,6%** da referência em média ([resultados](results/comparacao.md))
- [ ] Busca local mais forte (Pessoa 2)
- [ ] Variantes do modelo exato e Gurobi (Pessoas 1 e 3)
- [ ] Apresentação (Pessoa 4)
