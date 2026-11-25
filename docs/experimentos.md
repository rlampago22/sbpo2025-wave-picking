# Experimentos

## CP-SAT × Gurobi no Dinkelbach

**Responsável:** Vinicius Gonçalves · **Código:** [`src/wavepick/exact/dinkelbach_gurobi.py`](../src/wavepick/exact/dinkelbach_gurobi.py) · **Script:** [`scripts/compare_solvers.py`](../scripts/compare_solvers.py) · **Dados brutos:** [`results/solvers.csv`](../results/solvers.csv)

### O que foi comparado

Os dois solvers resolvem **exatamente o mesmo modelo** dentro do **mesmo laço de Dinkelbach** (veja [02 · Arquitetura](02-arquitetura.md)). Para um palpite λ = num/den, cada iteração resolve:

```
F(λ) = max  den·N(x) − num·K(y)
s.a.   LB ≤ N(x) ≤ UB
       Σ_o u_oi·x_o ≤ Σ_a u_ai·y_a       para todo item i
       1 ≤ K(y) ≤ ⌊UB·den/num⌋           (corte: razão > λ exige K < UB/λ)
       x, y binários
```

Para a comparação ser justa:

- **mesma solução inicial**: a heurística roda uma vez só por instância, e as duas execuções partem dela;
- **mesmo tempo** para o Dinkelbach, contando a montagem do modelo;
- **mesmo número de threads** (8, num MacBook Pro);
- mesma estratégia de tempo por iteração (`max(10 s, T/5)` e uma tentativa final com o tempo que sobra);
- toda solução é validada com o verificador, que usa as mesmas regras do `checker.py` oficial.

### O que muda no Gurobi

| | CP-SAT (OR-Tools) | Gurobi |
|---|---|---|
| Técnica principal | programação por restrições + SAT, com busca em portfólio | *branch-and-cut* com relaxação linear (simplex) |
| Montagem do modelo | uma restrição por vez | **matricial** (`MVar` × matriz esparsa do SciPy) |
| Nova iteração | `model.maximize(...)` | só troca o atributo `Obj` das variáveis |
| Solução inicial | *hint* (dica) | **MIP start** (vira o incumbente com F = 0) |
| Prova de otimalidade | status `OPTIMAL` com ganho 0 | `MIPGapAbs = 0.99`: como F(λ) é inteiro, um limitante < 1 com incumbente 0 prova F(λ) = 0 |
| Licença | livre | acadêmica (gratuita); a do `pip` só aceita até 2000 variáveis/restrições |

A diferença de fundo: o Gurobi usa a **relaxação linear** (o limitante superior de F(λ)) para podar a busca. Isso ajuda muito a **provar** que λ é ótimo, que é justamente o passo em que o CP-SAT não terminava a tempo na 1ª rodada (0 de 30 provas em B e X).

### Limitação: licença

Não foi possível emitir a licença acadêmica completa: o Gurobi exige que o pedido saia da rede da universidade, e isso ainda não foi possível. Por isso os experimentos usam a licença **restrita** que vem com o `gurobipy` (máx. 2000 variáveis e 2000 restrições). Depois do pré-processamento, só 8 das 50 instâncias cabem nela (todas do dataset A).

Quando a licença acadêmica estiver instalada (`~/gurobi.lic`), basta rodar de novo o comando da seção 2 para completar a tabela.

### 1. Instâncias que cabem na licença restrita

Aqui a heurística já encontra o ótimo nessas instâncias, então ela foi **desligada** (`--no-start`). Assim se mede só a força de cada solver: os dois partem de λ = 0.

```bash
python scripts/compare_solvers.py --time 60 --no-start --instances a/instance_0001 a/instance_0003 a/instance_0004 a/instance_0009 a/instance_0012 a/instance_0017
```

| Instância | Referência | CP-SAT | Gurobi | CP-SAT: tempo até provar o ótimo | Gurobi: tempo até provar o ótimo |
|---|---:|---:|---:|---:|---:|
| A/0001 | 15,00 | 15,00 ✔ | 15,00 ✔ | 0,1 s | 0,1 s |
| A/0003 | 12,00 | 12,00 ✔ | 12,00 ✔ | 0,2 s | 0,1 s |
| A/0004 | 3,50 | 3,50 ✔ | 3,50 ✔ | 0,0 s | 0,0 s |
| A/0009 | 4,42 | 4,42 ✔ | 4,42 ✔ | 0,4 s | 0,3 s |
| A/0012 | 11,25 | 11,25 ✔ | 11,25 ✔ | 2,5 s | **0,7 s** |
| A/0017 | 36,50 | 36,50 ✔ | 36,50 ✔ | 3,9 s | **2,7 s** |

✔ = ótimo provado. Os dois solvers acham e provam o ótimo (igual à referência) em todas, com o mesmo número de iterações do Dinkelbach (4 ou 5). O Gurobi foi **mais rápido em todas as instâncias não triviais**: 3,6× em A/0012 e 1,4× em A/0017.

### 2. As 5 instâncias da comparação (2 de A, 2 de B, 1 de X)

Escolhemos as instâncias mais distantes da referência na 1ª rodada, porque é nelas que um solver melhor pode fazer diferença.

```bash
python scripts/compare_solvers.py --time 120
```

Dinkelbach com 120 s por solver, 8 threads, mesma solução inicial (heurística de 15 s), licença **restrita** do Gurobi.

| Instância | Pedidos × corredores | Referência | Heurística | CP-SAT | % ref. | Ótimo provado? | Gurobi |
|---|---:|---:|---:|---:|---:|---|---|
| A/0005 | 2587 × 161 | 177,88 | 141,91 | 174,25 | 98,0% | não | sem licença p/ este tamanho |
| A/0011 | 1013 × 375 | 16,85 | 12,41 | 15,63 | 92,7% | não | sem licença p/ este tamanho |
| B/0002 | 2106 × 165 | 180,64 | 129,52 | **180,64** | 100,0% | **sim** (79 s) | sem licença p/ este tamanho |
| B/0006 | 1833 × 165 | 84,03 | 71,67 | 83,03 | 98,8% | não | sem licença p/ este tamanho |
| X/0006 | 2659 × 168 | 191,86 | 170,13 | 191,50 | 99,8% | não | sem licença p/ este tamanho |

A coluna do Gurobi fica vazia até a licença acadêmica ser instalada: com a licença restrita, o modelo dessas instâncias (milhares de variáveis) é recusado e o pipeline cai para o CP-SAT.

Observação: com 8 threads e 120 s, o CP-SAT ficou **bem acima da 1ª rodada** (notebook de 4 núcleos) nessas 5 instâncias: A/0005 passou de 80% para 98% da referência, A/0011 de 81% para 93% e B/0002 de 92% para 100%, com o **ótimo provado**. O `compare_solvers.py` não salva soluções. Para levar esses ganhos ao `solutions/`, é preciso rodar o `run_all.py` nessas instâncias com o mesmo tempo.

### Conclusão e escolha do solver

- **Com licença completa**, o Gurobi é o candidato mais forte. Nas 6 instâncias em que os dois rodaram, ele chegou ao mesmo ótimo e **provou** a otimalidade mais rápido em todas as não triviais. Isso pesa no Dinkelbach: o ponto fraco do CP-SAT na 1ª rodada foi justamente a prova (a última iteração).
- **Sem licença completa** (a situação atual do grupo), o Gurobi não roda em 42 das 50 instâncias. Por isso o padrão do pipeline continua **`--solver auto` = CP-SAT** (`DEFAULT_SOLVER` em [`pipeline.py`](../src/wavepick/pipeline.py)).
- Quem tiver a licença acadêmica pode usar `--solver gurobi` já. Se o modelo não couber na licença, o pipeline volta sozinho para o CP-SAT, então a opção nunca piora o resultado por falta de licença.
- **Próximo passo:** com a licença instalada, rodar `python scripts/compare_solvers.py --time 120`. Se o Gurobi vencer a maioria das 5 instâncias, trocar `DEFAULT_SOLVER` para `"gurobi"`.
