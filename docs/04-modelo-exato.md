# Modelo exato: variantes testadas (Kelvin)

Código: [`exact/dinkelbach.py`](../src/wavepick/exact/dinkelbach.py), escolha da variante em `pipeline.py` (`--variant`).

| Variante | O que faz |
|---|---|
| `base` | Dinkelbach + CP-SAT no modelo completo (versão anterior) |
| `strong` | `base` + corte `x_o ≤ z_i ≤ Σ_{a∈A_i} y_a` para cada item `i` do pedido `o` |
| `kfixed` | para cada `k`: `Σy = k`, `N ≥ ⌊λk⌋+1`, maximiza `N`; só `k < UB/λ`; `INFEASIBLE` descarta o `k` |
| `lns` | Dinkelbach em submodelos pequenos em torno da melhor solução (corredores que mais cobrem a demanda dela + pedidos que cabem neles); se não melhora, a vizinhança cresce ×1,6 com aleatoriedade |
| `hybrid` (**padrão**) | 50% do tempo em `lns`, o resto em `base` partindo da solução do LNS |

## Resultados (mesmo tempo: A 30 s, B/X 120 s; notebook de 12 núcleos; `--no-save`)

| Instância | heurística | base | strong | kfixed | lns | lns-strong | hybrid | ref. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A/05 | 141,9 | 157,9 | 156,2 | 169,5 | **177,9** | 158,9 | 154,7 | 177,9 |
| A/08 | | 162,2 | 156,2 | 157,8 | **162,9** | **162,9** | **162,9** | 162,9 |
| A/10 | | 16,44 | 16,33 | 16,12 | 16,40 | 16,50 | 16,32 | 17,11 |
| A/11 | | 15,35 | 15,56 | 14,42 | 14,01 | 14,04 | 14,98 | 16,85 |
| B/06 | 71,7 | 83,57 | | | 83,13 | | **83,89** | |
| X/06 | 170,1 | 191,50 | | | 191,86 | | **191,86** | |
| X/10 | 921,3 | 927,2 | | | **964,6** | | 962,8 | |
| B/02, B/03, X/08 | | = | | | = | | = | |

## Conclusões

- **LNS é a variante que mais ajuda**, principalmente nas instâncias grandes (X/10: +4,0%; A/05 e A/08 chegam à referência). O `hybrid` nunca ficou abaixo da `base` em B/X e melhora B/06, X/06 e X/10 (3 instâncias); em A/08 também.
- **Modelo fortalecido (`strong`) não acelerou**: o corte é implicado pelo estoque e só aumenta o modelo. Fica documentado como resultado negativo.
- **`kfixed`** ajudou só em A/05 (169,5 vs 157,9) e perdeu nas demais: dividir o tempo entre muitos `k` prejudica.
- **A/11 piora** com LNS (o ótimo tem estrutura que a vizinhança da heurística não alcança); nela vale `base`.
- **Ruído:** CP-SAT multithread não é determinístico. A/05 com `lns` deu 177,9 numa rodada e 158,8 em outra. Para a rodada final, rodar `base`, `lns` e `hybrid` e deixar o `run_all.py` guardar o melhor.
- Não houve ajuste fino de parâmetros do CP-SAT (`params` está exposto nas funções para isso).

Reprodução: `uv run python scripts/run_all.py --datasets a --time 30 --only instance_0005 --variant lns --no-save --tag exp-lns`
