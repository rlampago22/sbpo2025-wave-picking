# Roteiro da apresentação

Cada integrante apresenta o que fez na sua issue. A exceção é o Juliano: como ele montou os slides, ele apresenta o problema, que pela regra precisa de **pelo menos 5 minutos**.

| Ordem | Quem | Issue | Slides | Tempo |
|---|---|---|---|---|
| 1 | Juliano Brum | #6 Apresentação | 1–8: o problema | ~6,5 min |
| 2 | Gustavo Almeida | #3 Heurística e busca local | 9–11: estratégia, gulosa, ILS | ~2,5 min |
| 3 | Kelvin Camargo | #4 Modelo exato | 12–13: Dinkelbach, variante híbrida | ~2,5 min |
| 4 | Vinicius Gonçalves | #5 Gurobi | 14–15: CP-SAT × Gurobi, evolução | ~2 min |
| 5 | Marcus Querol | #2 Coordenação e experimentos | 16–19: resultados, instâncias, conclusões, encerramento | ~2,5 min |
| | | | **Total** | **~16 min** (regra: 10 a 20) |

As falas abaixo também estão nas notas de cada slide. Não precisa decorar: o ideal é falar com as próprias palavras, usando a figura do slide como apoio. Evitem termos que não dominam; a professora pediu explicação em alto nível, mas coerente.

---

## 1. Juliano: o problema (slides 1 a 8, ~6,5 min)

**Slide 1, capa (20 s).** Boa tarde. Nosso trabalho é o desafio da SBPO 2025, proposto pelo Mercado Livre: o Wave Order Picking. A figura mostra um armazém visto de cima. Se escolhermos bem os pedidos, o separador só passa pelos corredores laranjas.

**Slide 2, o cenário (50 s).** Num centro de distribuição chegam milhares de pedidos, e cada produto fica em algum corredor. Buscar um pedido de cada vez faz o funcionário atravessar o armazém o dia todo. Por isso se juntam pedidos num lote, a *wave*, e se separa tudo de uma vez. A pergunta do desafio: quais pedidos colocar na wave e por quais corredores passar?

**Slide 3, entrada e decisão (50 s).** Os dados têm três partes: os pedidos (produtos e quantidades), os corredores (estoque de alguns produtos) e os limites da wave, LB (mínimo) e UB (máximo) de unidades. Nós decidimos só duas coisas, as duas de sim ou não: quais pedidos entram e quais corredores visitar.

**Slide 4, objetivo (50 s).** O objetivo é uma divisão: unidades separadas ÷ corredores visitados. O modelo não calcula rota, só conta corredores. No exemplo, a wave 2 separa mais unidades, mas usa 5 corredores; a wave 1 rende 20 por corredor e ganha. Pegar mais pedidos nem sempre compensa.

**Slide 5, regras (60 s).** Três regras. (1) O total de unidades fica entre LB e UB. (2) Para cada produto, o que os pedidos pedem cabe no estoque somado dos corredores escolhidos. (3) O pedido é tudo ou nada. Se uma regra falha, a wave é inviável, e no trabalho isso vale zero na instância. Por isso tudo passa pelo verificador oficial.

**Slide 6, exemplo oficial (60 s).** O exemplo do enunciado: produtos de A a E, cada cor um produto. A melhor wave, em laranja: pedidos 0, 1, 2 e 4, que somam 10 unidades, tirando dos corredores 1 e 3. Conferindo o produto A: o pedido 0 pede 3, e os corredores 1 e 3 têm 2 cada, total 4, cabe. Resultado: 10 ÷ 2 = 5, o ótimo deste exemplo.

**Slide 7, várias waves (45 s).** O mesmo exemplo tem muitas waves possíveis. Com os pedidos 0 e 4 a produtividade é 2,5; com 0, 2 e 3 sobe para 4; duas waves bem diferentes empatam no ótimo, 5. E pegar todos os pedidos dá 15 unidades, acima do máximo 12: inviável.

**Slide 8, por que é difícil (60 s).** A maior instância tem 68 mil pedidos, 54 mil produtos e 483 corredores. Só para escolher corredores são 2^483 combinações, um número com 146 dígitos; o número de átomos do universo tem uns 80. Testar tudo é impossível. Além disso, o objetivo é uma divisão, e os solvers otimizam somas; precisamos de um truque.

> **Passagem:** “Passo para o Gustavo, que explica como atacamos o problema.”

**Perguntas prováveis**
- *O modelo considera a distância percorrida?* Não. O desafio mede só o número de corredores visitados.
- *Um produto pode vir de mais de um corredor?* Sim, o estoque dos corredores escolhidos é somado.

---

## 2. Gustavo: heurística e busca local (slides 9 a 11, ~2,5 min)

**Slide 9, estratégia (45 s).** Nossa solução é um pipeline de cinco etapas: preparar os dados, construir uma solução rápida com uma heurística gulosa, melhorar com busca local, otimizar com um método exato e verificar com as regras do verificador oficial. A barra mostra a divisão do tempo: 15% para a gulosa, 10% para a busca local e o resto para o método exato. Se o solver não terminar, ficamos com a melhor solução que já temos.

**Slide 10, gulosa (60 s).** A gulosa abre um corredor de cada vez, sempre o que mais cobre a demanda que ainda falta, e enche a wave com os pedidos que cabem. O gráfico é real, da instância X/0006. Até 8 corredores a wave nem atinge o mínimo. Depois a produtividade sobe até 163 com 15 corredores. Aí a wave bate no máximo UB, e cada corredor a mais só aumenta o denominador. A gulosa guarda o pico e repete a partir de 10 corredores iniciais diferentes. Leva segundos, mas a linha tracejada mostra que dá para chegar a 191,9.

**Slide 11, busca local e ILS (60 s).** Cada wave é um ponto da paisagem, e a altura é a produtividade. A busca local faz pequenas mudanças: trocar um corredor, trocar pedidos. Só aceita se melhorar, então para no topo do primeiro morro, o ótimo local. A ILS resolve isso: quando nada melhora, sorteia 2 ou 3 corredores para trocar, cai em outra encosta e sobe de novo, guardando sempre a melhor wave. A figura é só uma ilustração.

> **Passagem:** “Com essa solução em mãos, o Kelvin mostra o método exato.”

**Perguntas prováveis**
- *Por que não usar só a heurística?* Ela é rápida, mas para em ótimos locais. Em X/0006 ela chegou a 163, contra 191,9 no final.
- *A ILS é aleatória?* Tem sorteio com semente fixa, mas como para por tempo, o resultado pode variar um pouco entre máquinas.

---

## 3. Kelvin: modelo exato (slides 12 e 13, ~2,5 min)

**Slide 12, Dinkelbach (70 s).** O objetivo é uma divisão, e os solvers só otimizam somas. O método de Dinkelbach resolve isso. Começamos com um chute λ, a produtividade da melhor wave que já temos. Perguntamos ao solver: existe wave em que unidades − λ × corredores dá positivo? Isso é uma soma, que o solver resolve. Se existe, ela é melhor: atualizamos λ e repetimos. Se o solver prova que não existe, λ é o ótimo. O gráfico é real, da A/0011: a gulosa chegou a 12,56, o LNS a 13,58, e cada rodada subiu um degrau até 16,85, exatamente a referência. Reparem nos corredores: a melhor wave usa só 20, e a heurística ficava presa em waves com mais de 60.

**Slide 13, variante híbrida (60 s).** Eu testei seis variantes do método exato, e a híbrida virou o padrão. Na primeira metade do tempo ela usa o LNS: fixa quase tudo e deixa o solver mexer só perto da solução atual. É um problema pequeno, então melhora rápido, e se travar a vizinhança cresce. Na segunda metade, o solver resolve o modelo completo partindo da solução do LNS, e pode provar o ótimo. Na X/0010, com o mesmo tempo, o modelo completo sozinho chegava a 927,2 e a híbrida a 962,8, quase a referência.

> **Passagem:** “Agora o Vinicius mostra qual solver usamos dentro desse método.”

**Perguntas prováveis**
- *O que é provar o ótimo?* O solver mostra que nenhuma wave tem produtividade maior que λ. Conseguimos isso em parte das instâncias (por exemplo A/0006, A/0007, X/0004, X/0015); nas outras, paramos pelo tempo.
- *Quais foram as seis variantes?* base, strong (cortes extras), kfixed (número de corredores fixo), lns, lns-strong e hybrid. Detalhes em [04-modelo-exato.md](04-modelo-exato.md).

---

## 4. Vinicius: Gurobi (slides 14 e 15, ~2 min)

**Slide 14, CP-SAT × Gurobi (60 s).** Começamos com o CP-SAT, do OR-Tools, que é gratuito. Depois comparamos com o Gurobi, com a licença acadêmica da universidade. A comparação foi justa: mesmo modelo, mesma solução inicial, 120 segundos cada, mesma máquina. Bolinha cinza é o CP-SAT, laranja é o Gurobi. O Gurobi venceu as cinco: +11 pontos na A/0005, +9 na X/0006, e na B/0002 os dois chegaram a 100%, mas o Gurobi chegou em 72 s. O Gurobi usa a relaxação linear para descartar partes ruins da busca, enquanto o CP-SAT depende mais de muitos núcleos em paralelo. Por isso virou o padrão; quem não tem licença cai automaticamente no CP-SAT.

**Slide 15, evolução (45 s).** Este gráfico mostra a evolução do projeto. A primeira versão, só com a gulosa e o CP-SAT, já chegava a 97,6% da referência. Com a busca local do Gustavo e a variante híbrida do Kelvin, fomos a 98,5%. Com o Gurobi e mais tempo, 99,1%. Rodando o Gurobi nas 13 instâncias mais fracas, 99,8%, e a A/0011 com 900 s fechou em 99,9%.

> **Passagem:** “O Marcus apresenta os números finais.”

**Perguntas prováveis**
- *Por que não usar só o Gurobi desde o começo?* A licença completa exige estar na rede da universidade para gerar; até lá usamos o CP-SAT, que é livre e roda em qualquer máquina.
- *O que é relaxação linear?* É resolver o problema permitindo valores fracionários (por exemplo, “meio corredor”). Isso dá um limite de quanto ainda dá para ganhar e permite cortar caminhos sem futuro.

---

## 5. Marcus: resultados e encerramento (slides 16 a 19, ~2,5 min)

**Slide 16, resultados (60 s).** As 50 soluções dos três conjuntos passaram no verificador oficial: nenhuma inviável. Em média chegamos a 99,9% do melhor valor publicado no desafio: A com 99,95%, B com 99,83% e X com 99,91%. A barra mostra quantas chegaram exatamente à referência: 17 de 20 no A, 6 de 15 no B e 10 de 15 no X, 33 no total.

**Slide 17, instância a instância (40 s).** Cada bolinha azul é uma instância que ainda não chegou à referência; as laranjas juntam as que chegaram. O eixo vai só de 99,5% a 100%: até a pior, a B/0011, está a menos de meio por cento do melhor valor publicado.

**Slide 18, o que aprendemos (45 s).** Três lições. Combinar uma heurística rápida com um método exato funcionou: um dá o ponto de partida, o outro refina. A melhor wave nem sempre é a maior: na A/0011 ela tem 20 corredores, e a heurística insistia em mais de 60. E os limites: o ótimo foi provado só em parte das instâncias, e o resultado depende do tempo e do solver. No trabalho em grupo, cada um teve sua branch e sua issue, e nada entrou sem passar pelo verificador oficial.

**Slide 19, encerramento.** Obrigado! Abrimos para perguntas; cada um responde sobre a sua parte.

**Perguntas prováveis**
- *Quanto tempo por instância?* Rodadas de 30 a 300 s, e 900 s na A/0011. Os resultados foram obtidos numa máquina de 4 núcleos com o Gurobi.
- *Vocês usaram as soluções publicadas?* Não. Só os valores de referência, para comparar.
- *Onde está o código?* github.com/rlampago22/sbpo2025-wave-picking

---

## Checklist para o dia

- [ ] Ensaiar uma vez cronometrando (alvo: 15 a 17 min).
- [ ] Juliano: a parte do problema precisa passar de 5 minutos.
- [ ] Ter o PDF dos slides num pendrive, caso a internet falhe.
- [ ] Cada um passar a palavra para o próximo com a frase da “Passagem”.
