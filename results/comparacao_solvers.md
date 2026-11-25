Dinkelbach com **120 s por solver**, 4 threads, mesma solução inicial (heurística de 15 s). Gurobi 14.0.0: licença completa.

| Instância | Referência | Heurística | cpsat obj | cpsat % ref | cpsat t. melhor (s) | cpsat t. total (s) | cpsat ótimo? | gurobi obj | gurobi % ref | gurobi t. melhor (s) | gurobi t. total (s) | gurobi ótimo? | Vencedor |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| A/0005 | 177.88 | 141.91 | 152.23 | 85.6% | 120.7 | 120.7 | não | 172.44 | 96.9% | 120.0 | 120.1 | não | gurobi |
| A/0011 | 16.85 | 12.41 | 14.67 | 87.0% | 72.5 | 120.1 | não | 15.66 | 92.9% | 73.3 | 120.1 | não | gurobi |
| B/0002 | 180.64 | 129.52 | 180.64 | 100.0% | 120.2 | 120.2 | não | 180.64 | 100.0% | 72.2 | 120.1 | não | gurobi |
| B/0006 | 84.03 | 71.67 | 81.45 | 96.9% | 120.4 | 120.4 | não | 82.40 | 98.1% | 120.0 | 120.1 | não | gurobi |
| X/0006 | 191.86 | 170.13 | 173.60 | 90.5% | 49.1 | 120.3 | não | 191.50 | 99.8% | 72.3 | 120.1 | não | gurobi |

Vitórias: cpsat 0, gurobi 5 (critério: maior objetivo; empate → menor tempo até a melhor solução).
