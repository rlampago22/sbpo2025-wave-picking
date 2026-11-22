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

**Primeira rodada (notebook com 4 núcleos; 30 s por instância em A, 120 s em B e X): 50/50 soluções válidas no checker oficial, 97,6% da referência em média.**

| Dataset | Média % da referência | Mais fracas |
|---|---:|---|
| A | 96,7% | A/05 (80%), A/11 (81%), A/08 (87%), A/10 (89,5%) |
| B | 98,1% | B/06 (91%), B/02 (92%), B/03 (94,5%) |
| X | 98,4% | X/06 (95%), X/10 (95,5%), X/08 (96%) |

- Em B e X, o Dinkelbach melhorou a solução da heurística em 24 de 30 instâncias, mas **não provou otimalidade em nenhuma**: o tempo acaba antes.
- As instâncias mais fracas são o alvo de todo mundo. Qualquer melhoria deve ser medida nelas primeiro.

**Conclusão:** heurística melhor (Gustavo) dá um ponto de partida mais alto ao solver, e solver mais rápido (Kelvin e Vinicius) sobe mais degraus no mesmo tempo. As duas frentes se somam.

## Divisão de tarefas

Cada tarefa tem uma **issue no GitHub** com o mesmo checklist. É lá que se marca o progresso e se tiram dúvidas. A divisão é uma sugestão: quem quiser trocar, combina com o grupo e avisa o Marcus.

| Integrante | Frente | Arquivos principais |
|---|---|---|
| **Marcus Querol** | Coordenação, experimentos e integração | `scripts/`, `results/`, `solutions/` |
| **Gustavo Almeida** | Heurística e busca local | `src/wavepick/heuristics/` |
| **Kelvin Camargo** | Modelo exato (CP-SAT) | `src/wavepick/exact/dinkelbach.py` |
| **Vinicius Gonçalves** | Solver Gurobi e comparação de solvers | `src/wavepick/exact/dinkelbach_gurobi.py` (novo) |
| **Juliano Brum** | Apresentação (5 min) | slides e `docs/apresentacao.md` (novo) |

### Marcus Querol — Coordenação, experimentos e integração

- [ ] Confirmar com o professor:
  - o tempo limite por instância;
  - quais datasets são avaliados (A, B, X?);
  - se podemos usar as soluções publicadas pelo desafio. Por enquanto **não usamos**, só comparamos.
- [ ] Revisar e aceitar os PRs. Depois de cada PR aceito, rodar de novo as instâncias afetadas com `scripts/run_all.py`.
- [ ] Rodadas longas (`--time 600`) nas instâncias mais distantes da referência.
- [ ] Manter `results/comparacao.md` atualizado (`scripts/compare.py --official`) e passar os números ao Juliano.
- [ ] Entrega final: código + `solutions/` + slides.

**Pronto quando:** todas as instâncias avaliadas têm solução válida no checker oficial e a entrega foi feita.

### Gustavo Almeida — Heurística e busca local

Arquivo: `src/wavepick/heuristics/local_search.py`. É a frente que mais pesa na nota das instâncias grandes.

- [ ] **Troca de corredor:** tira um corredor, coloca outro e re-preenche os pedidos. Aceita se a razão melhorar.
- [ ] **Troca de pedidos:** tira 1 pedido e tenta colocar outros que somem mais unidades.
- [ ] Uma meta-heurística sobre esses movimentos: ILS (perturba + busca local) ou Simulated Annealing.
- [ ] Medir o ganho só da heurística: `uv run python scripts/run_all.py --no-exact --time 30 --datasets a --tag heur-v2`. Isso deixa um registro em `results/runs.csv`.

**Pronto quando:** a heurística sozinha melhora a média do dataset A em relação à versão atual (coluna `heuristica` do `runs.csv`).

### Kelvin Camargo — Modelo exato (CP-SAT)

Arquivo: `src/wavepick/exact/dinkelbach.py`.

- [ ] **Abordagem alternativa "k fixo":** para cada número de corredores `k`, maximizar `N` com `Σ y_a = k` e guardar o melhor `N/k`. Comparar com o Dinkelbach.
- [ ] **Fortalecer o modelo:** testar a restrição `x_o ≤ Σ_{a ∈ A_i} y_a` (o pedido só entra se algum corredor com o item `i` for aberto) e ver se acelera.
- [ ] **Instâncias grandes:** o CP-SAT não acha nada em 120 s com 68 mil pedidos. Testar um **modelo restrito**, só com os corredores e pedidos "próximos" da solução heurística (vizinhança), em vez do modelo inteiro.
- [ ] Ajustar `iter_time_limit` e os parâmetros do CP-SAT. O `--solver-log` mostra o log.

**Pronto quando:** existe uma variante que melhora pelo menos 3 instâncias com o mesmo tempo, e ela está integrada ao `pipeline.py`.

### Vinicius Gonçalves — Solver Gurobi

- [ ] Pedir a licença acadêmica do Gurobi (gratuita, com o e-mail da universidade) e instalar o `gurobipy` (`uv add gurobipy`).
- [ ] Criar `src/wavepick/exact/dinkelbach_gurobi.py` com o **mesmo** modelo, mas no Gurobi. Usar o `dinkelbach.py` como molde.
- [ ] Adicionar uma opção `--solver cpsat|gurobi` no `pipeline.py` e no `run_all.py`.
- [ ] Comparar CP-SAT × Gurobi em 5 instâncias (2 de A, 2 de B, 1 de X) com o mesmo tempo, e anotar a tabela em `docs/experimentos.md`.

**Pronto quando:** existe a tabela comparando os dois solvers e o pipeline consegue usar o melhor deles.

### Juliano Brum — Apresentação (5 min)

- [ ] **Slides de 0:00 a 2:00 — o problema.** Usar o exemplo do PDF com animação: mostrar a wave {0,1,2,4} nos corredores {1,3} e o empate com {1,2} no corredor 4. Mostrar o trade-off "mais corredores = mais estoque, mas denominador maior".
- [ ] **Slides de 2:00 a 5:00 — abordagem e resultados.** Diagrama do pipeline, o Dinkelbach em 1 slide, e o gráfico "% da referência por instância" feito a partir de `results/comparacao.csv`.
- [ ] Roteiro de fala cronometrado. Combinar com o grupo quem apresenta cada parte.
- [ ] Lista de perguntas prováveis da banca, com respostas, em `docs/apresentacao.md`. Por exemplo:
  - por que Dinkelbach converge;
  - o que é o corte `K ≤ UB/λ`;
  - por que não usar só heurística;
  - qual a complexidade do problema.

**Pronto quando:** o ensaio cronometrado cabe em 5 minutos.

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
