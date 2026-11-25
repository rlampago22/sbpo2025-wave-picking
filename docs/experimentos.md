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

**Como obter a licença (para quem usa o `gurobipy` do pip):**

1. Criar uma conta "Academic" no site do Gurobi com o e-mail da universidade.
2. **Conectado à rede da Unipampa** (ou a uma VPN da universidade com *full tunnel*), entrar em *User Portal → Licenses → Request* e clicar em **GENERATE NOW** no bloco **WLS Academic**.
3. Baixar o arquivo `gurobi.lic` e salvá-lo na pasta do usuário (`C:\Users\<usuario>\gurobi.lic` ou `~/gurobi.lic`).

Detalhes:

- A WLS só precisa da rede da universidade **na hora de gerar**. Depois funciona em qualquer lugar com internet.
- Vale 90 dias e é renovável.
- É **pessoal**: só quem gerou pode usar.
- Não precisa do `grbgetkey`, que não vem no `gurobipy` do pip.

Fontes: [academic license](https://support.gurobi.com/hc/en-us/articles/360040541251-How-do-I-obtain-a-free-academic-license), [remote student](https://support.gurobi.com/hc/en-us/articles/43876824710673-As-a-remote-student-how-do-I-request-a-Free-Academic-License).

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

### 3. Com a licença acadêmica completa (WLS)

A licença acadêmica foi gerada na rede da Unipampa (Marcus). Rodamos o mesmo comando da seção 2:

```bash
python scripts/compare_solvers.py --time 120 --tag licenca-academica-wls
```

Condições: Dinkelbach com 120 s por solver, **4 threads** (notebook do Marcus), mesma solução inicial (heurística de 15 s).

| Instância | Referência | Heurística | CP-SAT | % ref. | Gurobi | % ref. | Vencedor |
|---|---:|---:|---:|---:|---:|---:|---|
| A/0005 | 177,88 | 141,91 | 152,23 | 85,6% | **172,44** | **96,9%** | Gurobi |
| A/0011 | 16,85 | 12,41 | 14,67 | 87,0% | **15,66** | **92,9%** | Gurobi |
| B/0002 | 180,64 | 129,52 | 180,64 | 100,0% | 180,64 | 100,0% | Gurobi (achou em 72 s × 120 s) |
| B/0006 | 84,03 | 71,67 | 81,45 | 96,9% | **82,40** | **98,1%** | Gurobi |
| X/0006 | 191,86 | 170,13 | 173,60 | 90,5% | **191,50** | **99,8%** | Gurobi |

**O Gurobi venceu as 5.** A vantagem é maior com 4 threads do que nos resultados de 8 threads: o CP-SAT depende mais de paralelismo (busca em portfólio), enquanto o Gurobi se apoia na relaxação linear. Nenhum dos dois provou otimalidade em 120 s. Dados brutos em [`results/solvers.csv`](../results/solvers.csv) e [`results/comparacao_solvers.md`](../results/comparacao_solvers.md).

### 4. Rodada longa com Gurobi nas 13 instâncias mais fracas

Pegamos as 13 instâncias abaixo de 99,5% da referência e rodamos o pipeline completo com o Gurobi, 300 s por instância e 4 threads (cerca de 33 min no total):

```bash
uv run python scripts/run_all.py --datasets a --only instance_0006 instance_0007 instance_0010 instance_0011 --time 300 --solver gurobi --tag gurobi-300s
uv run python scripts/run_all.py --datasets b --only instance_0006 instance_0015 --time 300 --solver gurobi --tag gurobi-300s
uv run python scripts/run_all.py --datasets x --only instance_0001 instance_0004 instance_0007 instance_0008 instance_0009 instance_0014 instance_0015 --time 300 --solver gurobi --tag gurobi-300s
```

| Instância | Referência | Antes | Depois (Gurobi, 300 s) | % ref. | Ótimo provado? |
|---|---:|---:|---:|---:|---|
| A/0006 | 691,00 | 99,0% | 691,00 | **100,0%** | sim |
| A/0007 | 392,25 | 99,0% | 392,25 | **100,0%** | sim |
| A/0010 | 17,11 | 92,7% | 17,05 | **99,6%** | não |
| A/0011 | 16,85 | 87,7% | 15,83 | **94,0%** | não |
| B/0006 | 84,03 | 99,0% | 83,97 | **99,9%** | não |
| B/0015 | 166,14 | 97,6% | 166,14 | **100,0%** | não |
| X/0001 | 70,85 | 98,9% | 70,85 | **100,0%** | não |
| X/0004 | 202,75 | 97,3% | 202,75 | **100,0%** | sim |
| X/0007 | 115,15 | 97,9% | 115,15 | **100,0%** | não |
| X/0008 | 438,22 | 95,9% | 438,22 | **100,0%** | não |
| X/0009 | 819,88 | 99,1% | 819,88 | **100,0%** | não |
| X/0014 | 1633,67 | 99,3% | 1630,00 | **99,8%** | não |
| X/0015 | 263,91 | 98,1% | 263,91 | **100,0%** | sim |

As 13 melhoraram, e 10 chegaram ao valor de referência. Em 4 delas, o Gurobi também **provou** que a solução é ótima.

A média geral foi de **99,1% para 99,8%** da referência: A 99,7%, B 99,8% e X 99,9%. As 50 soluções foram aprovadas pelo `checker.py` oficial. Depois dessa rodada, só a **A/0011** (94,0%) ficou abaixo de 99,5%.

### 5. A/0011 com 900 s

```bash
uv run python scripts/run_all.py --datasets a --only instance_0011 --time 900 --solver gurobi --tag gurobi-900s
```

O Gurobi chegou a **16,85 = referência (100%)**. A trajetória do Dinkelbach mostra por que essa instância era difícil:

| Etapa | Razão | Unidades / corredores |
|---|---:|---:|
| Gulosa + ILS | 12,56 | |
| LNS | 13,58 | |
| Iteração 1 | 15,06 | 1747 / 116 |
| Iteração 2 | 15,80 | 1090 / 69 |
| Iteração 3 | 15,83 | 1029 / 65 |
| Iteração 4 | 16,44 | 444 / 27 |
| Iteração 5 | **16,85** | **337 / 20** |

A melhor wave é **pequena**: 337 unidades, quase no mínimo LB = 330, com só 20 corredores. A heurística e as rodadas curtas ficavam presas em waves grandes, com 65 ou mais corredores. Com mais tempo, o Gurobi saiu desse ótimo local.

**Situação final:** média de **99,9%** da referência (A 99,95%, B 99,83%, X 99,91%). 33 das 50 instâncias atingiram o valor de referência e todas ficaram acima de 99,5%. As 50 soluções foram aprovadas pelo `checker.py` oficial.

### Conclusão e escolha do solver

- **`DEFAULT_SOLVER = "gurobi"`** ([`pipeline.py`](../src/wavepick/pipeline.py)): `--solver auto` agora usa o Gurobi.
- **Quem não tem licença completa não é afetado.** O pipeline detecta que o modelo não cabe na licença restrita e volta sozinho para o CP-SAT.
- **As rodadas finais devem ser feitas na máquina com a licença** (notebook do Marcus). A licença WLS é pessoal e precisa de internet durante a execução.
