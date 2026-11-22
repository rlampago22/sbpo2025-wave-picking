# Entendendo o problema — Wave Order Picking (SBPO 2025 / Mercado Livre)

> Fonte oficial: [`pt_problem_description.pdf`](https://github.com/mercadolibre/challenge-sbpo-2025/blob/master/docs/pt_problem_description.pdf)

## 1. A ideia em uma frase

Um armazém tem uma fila de pedidos esperando (o **backlog**). Queremos escolher um **lote de pedidos** para separar agora (a **wave**) e **quais corredores visitar** para buscar tudo, de modo a **coletar o máximo de unidades por corredor visitado**.

Menos corredores para a mesma quantidade de produtos = rotas mais curtas = operação mais produtiva.

## 2. Os ingredientes (o que vem no arquivo de entrada)

| Elemento | O que é | Exemplo |
|---|---|---|
| **Pedido** `o` | lista de (item, quantidade) que um cliente pediu | pedido 0 = {item0: 3, item2: 1} → 4 unidades |
| **Corredor** `a` | lista de (item, quantidade) em estoque naquele corredor | corredor 1 = {item0: 2, item1: 1, item2: 2, item4: 1} |
| **LB / UB** | mínimo e máximo de unidades que a wave pode ter | LB = 5, UB = 12 |

Notação: `u_oi` = unidades do item `i` no pedido `o`; `u_ai` = unidades do item `i` no corredor `a`.

## 3. O que decidimos

1. **Quais pedidos entram na wave** → conjunto `O'`
2. **Quais corredores visitar** → conjunto `A'`

## 4. Objetivo

```
            total de unidades dos pedidos escolhidos
maximizar  ------------------------------------------
                 número de corredores visitados
```

É uma **razão** (produtividade = unidades por corredor), não uma soma. Isso é o que torna o problema diferente dos exercícios usuais.

## 5. Restrições

1. **Tamanho da wave:** `LB ≤ total de unidades ≤ UB`.
2. **Estoque:** para **cada item**, a soma do que os pedidos escolhidos pedem tem que ser **≤** a soma do que os corredores escolhidos têm daquele item.

Detalhes que importam:

- **Pedido é tudo ou nada.** Não dá para atender metade de um pedido.
- **Corredor conta 1** no denominador, não importa quanto se pegue nele.
- O estoque de um item **soma entre corredores**: se o pedido quer 3 unidades e há 2 no corredor 1 e 2 no corredor 3, visitando os dois corredores está atendido.
- Não existe distância, rota ou ordem de visita. A "eficiência" é medida só pela contagem de corredores.

## 6. O exemplo do PDF, passo a passo

5 pedidos, 5 itens, 5 corredores, LB = 5, UB = 12.

**Pedidos (unidades por item):**

| Pedido | I0 | I1 | I2 | I3 | I4 | Total |
|---|---|---|---|---|---|---|
| 0 | 3 | 0 | 1 | 0 | 0 | 4 |
| 1 | 0 | 1 | 0 | 1 | 0 | 2 |
| 2 | 0 | 0 | 1 | 0 | 2 | 3 |
| 3 | 1 | 0 | 2 | 1 | 1 | 5 |
| 4 | 0 | 1 | 0 | 0 | 0 | 1 |

**Corredores (estoque por item):**

| Corredor | I0 | I1 | I2 | I3 | I4 |
|---|---|---|---|---|---|
| 0 | 2 | 1 | 1 | 0 | 1 |
| 1 | 2 | 1 | 2 | 0 | 1 |
| 2 | 0 | 2 | 0 | 1 | 2 |
| 3 | 2 | 1 | 0 | 1 | 1 |
| 4 | 0 | 1 | 2 | 1 | 2 |

**Solução ótima apresentada no PDF:** pedidos {0, 1, 2, 4} e corredores {1, 3}.

| | I0 | I1 | I2 | I3 | I4 |
|---|---|---|---|---|---|
| Demanda (0+1+2+4) | 3 | 2 | 2 | 1 | 2 |
| Estoque (corr. 1 + corr. 3) | 4 | 2 | 2 | 1 | 2 |
| Cabe? | ✓ | ✓ | ✓ | ✓ | ✓ |

Total = 4 + 2 + 3 + 1 = **10 unidades**, dentro de [5, 12]. Corredores = 2. Objetivo = 10 / 2 = **5**.

Por que não colocar o pedido 3 também? O total iria para 15 > UB = 12. E nem haveria estoque do item 2 suficiente.

**Curiosidade:** existe outro ótimo empatado: pedidos {1, 2} só com o corredor 4 → 5 unidades / 1 corredor = 5. Ou seja, o ótimo pode ser atingido com conjuntos de tamanhos muito diferentes, e o problema costuma ter **vários ótimos**.

**O trade-off central:** abrir mais um corredor traz mais estoque (cabem mais pedidos, o numerador sobe), mas aumenta o denominador. O algoritmo precisa achar o ponto de equilíbrio.

## 7. Formato de entrada e saída

Entrada (`datasets/<a|b|x>/instance_XXXX.txt`):

```
o i a                  ← nº de pedidos, nº de itens, nº de corredores
k item qtd item qtd …  ← uma linha por pedido (k = nº de itens distintos)
…
k item qtd item qtd …  ← uma linha por corredor
LB UB
```

Saída (o que entregamos):

```
n            ← nº de pedidos na wave
id_pedido    ← um por linha
…
m            ← nº de corredores visitados
id_corredor  ← um por linha
…
```

O `checker.py` oficial lê a saída, verifica as restrições 1 e 2 e calcula o objetivo. **Solução inviável = zero na instância.**

## 8. Por que é difícil

- **A função objetivo é uma fração.** Solvers de programação linear inteira só otimizam funções lineares, então é preciso um truque (Dinkelbach ou fixar o número de corredores; ver a proposta de arquitetura).
- **Mesmo com os corredores fixos, escolher os pedidos é uma mochila multidimensional** (uma "mochila" por item, mais a de LB/UB), que é NP-difícil.
- **Escala:** as instâncias vão de 5 pedidos até **68 mil pedidos e 54 mil itens**. Em compensação, o número de **corredores é pequeno (no máximo 483)**, e boa parte das estratégias explora isso.

| Dataset | Instâncias | Pedidos (faixa) | Corredores (faixa) |
|---|---|---|---|
| A | 20 | 5 a 12.402 | 5 a 413 |
| B | 15 | 1.841 a 45.112 | 163 a 483 |
| X | 15 | 1.949 a 68.064 | 164 a 483 |

## 9. Modelo matemático (versão compacta)

Variáveis binárias: `x_o = 1` se o pedido `o` entra na wave; `y_a = 1` se o corredor `a` é visitado. Seja `U_o = Σ_i u_oi` o tamanho do pedido.

```
max   Σ_o U_o·x_o  /  Σ_a y_a

s.a.  LB ≤ Σ_o U_o·x_o ≤ UB
      Σ_o u_oi·x_o ≤ Σ_a u_ai·y_a      para todo item i
      Σ_a y_a ≥ 1
      x_o, y_a ∈ {0, 1}
```

## 10. Valores de referência

O repositório oficial publica o melhor objetivo conhecido de cada instância em [`best_solutions/best_objectives.csv`](https://github.com/mercadolibre/challenge-sbpo-2025/blob/master/best_solutions/best_objectives.csv). Na nota do trabalho, nosso desempenho é comparado com o da melhor equipe da turma, então a meta é ficar o mais perto possível desses valores em todas as instâncias.
