# Arquitetura e abordagem

## Visão geral

```
instância.txt
   │
   ▼
1. Pré-processamento        remove pedidos impossíveis e corredores inúteis
   │
   ▼
2. Heurística gulosa        abre corredores um a um e enche a wave de pedidos  → solução inicial
   │
   ▼
3. Melhoria local           tira corredores redundantes e encaixa mais pedidos
   │
   ▼
4. Dinkelbach + CP-SAT      método exato; parte da solução heurística
   │
   ▼
5. Verificação              mesmas regras do checker.py oficial (inviável = zero na nota)
   │
   ▼
solutions/<dataset>/instance_XXXX.txt
```

## Por que Python + OR-Tools (CP-SAT)

- **Python:** o grupo já domina a linguagem. O trabalho pesado fica com o solver (escrito em C++), então a lentidão do Python não é gargalo.
- **CP-SAT:** é gratuito e sem licença, então todo o grupo roda. Usa várias threads e é muito forte em problemas só com variáveis binárias e coeficientes inteiros, que é exatamente o nosso caso.
- **Gurobi (próximo passo):** tem licença acadêmica gratuita. Vamos comparar os dois nas mesmas instâncias e ficar com o melhor (ver o plano de execução).

## O modelo

Variáveis: `x_o ∈ {0,1}` (pedido `o` na wave) e `y_a ∈ {0,1}` (corredor `a` visitado). `U_o` = unidades do pedido.

```
max   N/K      com  N = Σ_o U_o·x_o   e   K = Σ_a y_a

s.a.  LB ≤ N ≤ UB
      Σ_o u_oi·x_o ≤ Σ_a u_ai·y_a     ∀ item i
      K ≥ 1
```

## Dinkelbach: como resolver um objetivo que é uma fração

Solvers só otimizam funções **lineares**, e `N/K` não é linear. O truque de Dinkelbach (1967):

1. Começamos com um palpite `λ`, a razão da solução heurística.
2. Resolvemos o problema **linear** `F(λ) = max N − λ·K`, com as mesmas restrições.
3. Se `F(λ) > 0`, a solução encontrada tem `N/K > λ`. Atualizamos `λ ← N/K` e voltamos ao passo 2.
4. Se `F(λ) = 0` e o solver provou otimalidade, não existe razão maior que `λ`: **`λ` é o ótimo**.

A sequência de `λ` é estritamente crescente e converge em poucas iterações.

Detalhes da implementação ([`exact/dinkelbach.py`](../src/wavepick/exact/dinkelbach.py)):

- **Coeficientes inteiros:** `λ = num/den`, e otimizamos `den·N − num·K`, porque o CP-SAT só aceita inteiros.
- **Corte `K ≤ ⌊UB/λ⌋`:** como `N ≤ UB`, uma solução melhor que `λ` precisa de `K < UB/λ` corredores. Isso corta a maior parte do espaço de busca nas instâncias grandes.
- **Warm start:** a melhor solução atual é passada como dica (*hint*) ao solver.
- **Tempo por iteração:** iterações curtas fazem `λ` subir rápido. Quando uma iteração não melhora, ganha todo o tempo restante.
- Toda solução do solver passa por `remove_redundant_aisles`, que tira os corredores sobrando.

## Heurística gulosa ([`heuristics/greedy.py`](../src/wavepick/heuristics/greedy.py))

- **Escolha do próximo corredor:** o que mais cobre a demanda ainda não atendida.
- **Preenchimento:** os pedidos são tentados em ordem de `unidades / consumo relativo do estoque`, ou seja, primeiro os que usam itens abundantes nos corredores abertos. Cada pedido entra se couber no estoque e não passar de UB.
- **Poda:** se `UB/k` já é menor que a melhor razão encontrada, abrir mais corredores não adianta.
- **Diversificação:** repete a construção a partir de 10 corredores iniciais diferentes.

## Mapa do código

| Arquivo | Responsabilidade |
|---|---|
| `src/wavepick/instance.py` | leitura da instância; matrizes esparsas pedidos×itens e corredores×itens |
| `src/wavepick/solution.py` | solução, verificação (igual ao checker oficial), leitura e escrita |
| `src/wavepick/preprocess.py` | redução do problema |
| `src/wavepick/heuristics/greedy.py` | construção gulosa |
| `src/wavepick/heuristics/local_search.py` | melhoria local (**ponto de extensão principal**) |
| `src/wavepick/exact/dinkelbach.py` | modelo CP-SAT + Dinkelbach |
| `src/wavepick/pipeline.py` | junta tudo para uma instância (CLI) |
| `scripts/run_all.py` | roda várias instâncias; só salva se melhorar |
| `scripts/compare.py` | tabela contra os valores de referência (+ checker oficial) |
| `tests/test_example.py` | exemplo do PDF (ótimo = 5) |
