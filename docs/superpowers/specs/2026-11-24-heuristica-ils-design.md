# Heurística e busca local (issue #3): desenho

## Objetivo
Fazer a heurística sozinha melhorar a média do dataset A em relação à versão atual
(coluna `heuristica` do `results/runs.csv`).

## Fora do escopo
Modelo exato, Gurobi, apresentação, rodadas finais e atualização das soluções do grupo.

## Abordagens consideradas
| Abordagem | A favor | Contra |
|---|---|---|
| **ILS** (escolhida) | poucos parâmetros, reaproveita o código atual, fácil de explicar | cada busca local pode ser cara nas instâncias grandes |
| Simulated Annealing | escapa bem de ótimos locais | exige calibrar temperatura e muitas iterações |

## Como funciona
Em `src/wavepick/heuristics/local_search.py`:

1. **Troca de corredor:** sai um, entra outro, os pedidos são re-preenchidos. Aceita se
   unidades/corredores aumentar. Testo também só tirar ou só colocar um corredor.
2. **Troca de pedidos:** com os corredores fixos, sai um pedido e entram outros. Aceita
   se o total de unidades aumentar, sem passar de UB.
3. **ILS:** parte da solução gulosa; repete até acabar o tempo: troca 2 ou 3 corredores
   da melhor solução ao acaso, aplica a busca local e guarda o resultado se for melhor.

Para não ficar lento, a troca de corredor testa primeiro os candidatos mais promissores
(os que mais cobrem a demanda não atendida) e aceita a primeira melhora.

## Regras
- Toda solução devolvida é viável (estoque, LB e UB) e nunca pior que a recebida.
- Uma semente fixa controla o sorteio. Com limite de tempo, o resultado ainda pode
  variar conforme a máquina.
- Sem bibliotecas novas.

## Tempo (`pipeline.py`)
- Com `--no-exact`: a ILS usa todo o tempo que sobra.
- Pipeline completo: a ILS usa no máximo 10% do tempo total, para não prejudicar o solver.

## Testes
Cada movimento e a ILS: solução viável, nunca pior, e ótimo 5 no exemplo do PDF.
Os testes atuais continuam passando.

## Medição
Antes de mudar o código, rodar a versão atual na mesma máquina (comparação justa):

    uv run python scripts/run_all.py --no-exact --time 30 --datasets a --no-save --tag heur-v1

Depois, o mesmo comando com `--tag heur-v2`. `--no-save` não altera `solutions/`.

**Pronto:** média de `heur-v2` maior que a de `heur-v1` nas 20 instâncias.

## A cargo da implementação
Quantos candidatos testar por troca e quando recomeçar da melhor solução, decididos
pelas medições.
