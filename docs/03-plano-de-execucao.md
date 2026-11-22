# Plano de execução do grupo

> **Antes de tudo, todos leem:** [01 · Entendendo o problema](01-entendendo-o-problema.md) e [02 · Arquitetura](02-arquitetura.md).
> Na banca, **qualquer pessoa** pode ser perguntada sobre o modelo e sobre o Dinkelbach.

## Onde estamos

Já existe uma versão **completa e funcionando** do início ao fim:

- leitura das instâncias;
- verificador com as mesmas regras do `checker.py` oficial;
- heurística gulosa e uma melhoria local simples;
- método exato (Dinkelbach + CP-SAT);
- scripts para rodar tudo e comparar com os valores de referência;
- testes.

**Agora o trabalho é melhorar o resultado e preparar a apresentação.** A nota da solução é relativa à melhor equipe da turma, então cada ponto percentual conta.

Resultados atuais: [`results/comparacao.md`](../results/comparacao.md).

**Primeira rodada (30 s por instância, notebook com 4 núcleos):**

- **Dataset A:** 20/20 válidas no checker oficial, **96,7%** da referência em média, 13 instâncias no valor de referência.
- **Os pontos fracos** são A/05 (80%), A/11 (81%), A/08 (87%) e A/10 (89,5%).
- **X/14** (a maior: 68 mil pedidos): 99,3% da referência, mas **toda a qualidade veio da heurística**. O CP-SAT não achou solução melhor em 120 s.

**Conclusão:** nas instâncias grandes (B e X), a **heurística é o que garante a nota** (Pessoa 2), e o solver precisa de ajuda (Pessoas 1 e 3). B e X ainda não foram rodados por inteiro.

## Divisão de tarefas

Se o grupo tiver 3 pessoas, a Pessoa 4 é dividida entre todos.

### Pessoa 1 — Experimentos e solver Gurobi · responsável: ________

- [ ] Rodar **B** e **X** completos (`--time 120` ou mais) e commitar as soluções.
- [ ] Pedir a licença acadêmica do Gurobi (gratuita, com o e-mail da universidade) e instalar o `gurobipy`.
- [ ] Criar `src/wavepick/exact/dinkelbach_gurobi.py` com o **mesmo** modelo, mas no Gurobi. Usar o `dinkelbach.py` como molde.
- [ ] Comparar CP-SAT × Gurobi em 5 instâncias (2 de A, 2 de B, 1 de X) com o mesmo tempo, e anotar a tabela em `docs/experimentos.md`.
- [ ] Rodar as instâncias mais longe da referência com mais tempo (ex.: `--time 600`).

**Pronto quando:** existe a tabela comparando os dois solvers e o pipeline usa o melhor deles.

### Pessoa 2 — Heurística / busca local · responsável: ________

Arquivo: `src/wavepick/heuristics/local_search.py`.

- [ ] **Troca de corredor:** tira um corredor, coloca outro e re-preenche os pedidos. Aceita se a razão melhorar.
- [ ] **Troca de pedidos:** tira 1 pedido e tenta colocar outros que somem mais unidades.
- [ ] Uma meta-heurística simples sobre esses movimentos: ILS (perturba + busca local) ou Simulated Annealing.
- [ ] Medir o ganho só da heurística: `uv run python scripts/run_all.py --no-exact --time 30 --datasets a --tag heur-v2`. Isso deixa um registro em `results/runs.csv`.

**Pronto quando:** a heurística sozinha melhora a média do dataset A em relação à versão atual (ver `heuristica` no `runs.csv`).

### Pessoa 3 — Modelo exato · responsável: ________

Arquivo: `src/wavepick/exact/`.

- [ ] **Abordagem alternativa "k fixo":** para cada número de corredores `k`, maximizar `N` com `Σ y_a = k` e guardar o melhor `N/k`. Comparar com o Dinkelbach.
- [ ] **Fortalecer o modelo:** testar a restrição `x_o ≤ Σ_{a ∈ A_i} y_a` (o pedido só entra se algum corredor com o item `i` for aberto) e ver se acelera.
- [ ] Ajustar o tempo por iteração do Dinkelbach (`iter_time_limit`) e os parâmetros do CP-SAT.
- [ ] Investigar as instâncias em que o solver não fecha. O `--solver-log` mostra o log.

**Pronto quando:** existe uma variante que melhora pelo menos 3 instâncias com o mesmo tempo, e ela está integrada ao `pipeline.py`.

### Pessoa 4 — Apresentação (5 min) · responsável: ________

- [ ] **Slides de 0:00 a 2:00 — o problema.** Usar o exemplo do PDF com animação: mostrar a wave {0,1,2,4} nos corredores {1,3} e o empate com {1,2} no corredor 4. Mostrar o trade-off "mais corredores = mais estoque, mas denominador maior".
- [ ] **Slides de 2:00 a 5:00 — abordagem e resultados.** Diagrama do pipeline, o Dinkelbach em 1 slide, e o gráfico "% da referência por instância" feito a partir de `results/comparacao.csv`.
- [ ] Roteiro de fala cronometrado.
- [ ] Lista de perguntas prováveis da banca com respostas, por exemplo:
  - por que Dinkelbach converge;
  - o que é o corte `K ≤ UB/λ`;
  - por que não usar só heurística;
  - qual a complexidade do problema.

**Pronto quando:** o ensaio cronometrado cabe em 5 minutos.

### Coordenação · responsável: ________

- [ ] Confirmar com o professor:
  - o tempo limite por instância;
  - quais datasets são avaliados (A, B, X?);
  - se podemos usar as soluções publicadas pelo desafio. Por enquanto **não usamos**, só comparamos.
- [ ] Revisar e aceitar os PRs, e rodar `scripts/compare.py --official` antes da entrega.
- [ ] Entrega final: código + `solutions/` + slides.

## Como trabalhar no repositório

```powershell
git clone https://github.com/rlampago22/sbpo2025-wave-picking
cd sbpo2025-wave-picking
git clone --depth 1 https://github.com/mercadolibre/challenge-sbpo-2025 vendor/challenge-sbpo-2025
uv sync
uv run pytest
```

Regras:

1. **Uma branch por tarefa** (`git checkout -b heuristica-swap`) e **Pull Request** para a `main`. Não fazer commit direto na `main`.
2. **Rodar `uv run pytest` antes de abrir o PR.**
3. **Soluções só entram via `scripts/run_all.py`.** Ele só sobrescreve se a nova solução for melhor, então a pasta `solutions/` guarda sempre o melhor que o grupo já achou.
4. Sempre que testar algo, usar `--tag nome-do-teste`. O `results/runs.csv` vira o histórico de experimentos, que é material para a apresentação.
5. Nunca commitar a pasta `vendor/`: os dados oficiais são baixados por cada um.

## Cronograma sugerido

| Etapa | O quê | Até |
|---|---|---|
| 1 | Todos leem os docs 01 e 02, instalam e rodam os testes | ___/___ |
| 2 | Cada pessoa entrega a primeira versão da sua tarefa (PR) | ___/___ |
| 3 | Rodada final longa em todas as instâncias + `compare.py --official` | ___/___ |
| 4 | Slides prontos + 2 ensaios cronometrados | ___/___ |
| 5 | Apresentação | ___/___ |
