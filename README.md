# SBPO 2025: Wave Order Picking

Trabalho final de PA: algoritmos para o [Desafio Mercado Livre de Otimização (SBPO 2025)](https://github.com/mercadolibre/challenge-sbpo-2025).

**Problema:** escolher um subconjunto de pedidos (a *wave*) e de corredores para maximizar **unidades coletadas / corredores visitados**, com o tamanho da wave entre LB e UB e estoque suficiente nos corredores escolhidos.

📖 Explicação detalhada: [docs/01-entendendo-o-problema.md](docs/01-entendendo-o-problema.md)

## Status

- [x] Entendimento do problema
- [ ] Arquitetura aprovada
- [ ] Leitura de instâncias + verificador
- [ ] Heurística construtiva
- [ ] Modelo exato
- [ ] Soluções de todas as instâncias
- [ ] Comparação com os valores de referência
- [ ] Apresentação (5 min)

## Dados

As instâncias e o `checker.py` são do repositório oficial (não versionados aqui):

```sh
git clone --depth 1 https://github.com/mercadolibre/challenge-sbpo-2025 vendor/challenge-sbpo-2025
```
