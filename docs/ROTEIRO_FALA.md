# Roteiro de fala — Grupo 05 (slide a slide, com o código a mostrar)

Duração estimada: **≈ 13 min** falando em ritmo calmo.
Nada é executado ao vivo: o funcionamento é demonstrado pelo log das execuções
já feitas (`experimentos/resultados/benchmark_log.txt`) e pelos testes.

## Legenda

- **[TELA]** = o que deve estar na tela.
- **[CÓDIGO]** = no VS Code: `Ctrl+P` → nome do arquivo → `Enter`;
  `Ctrl+G` → número da linha → `Enter`; selecione o intervalo indicado
  (clique na 1ª linha, `Shift`+clique na última).
- Texto em itálico entre aspas = fala, uma frase por linha.
- **Quem fala:** MATHEUS na maior parte; LEONARDO nos blocos dele;
  VINICIUS e CARLOS em blocos opcionais — se não estiverem, o MATHEUS lê o mesmo texto.

## Antes de gravar

- VS Code aberto na pasta `fake_news/`, zoom aumentado 2–3× (`Ctrl+=`),
  barra lateral fechada (`Ctrl+B`), minimapa desligado.
- Abas já abertas, nesta ordem: `modelo.py`, `paralelo_threads.py`,
  `paralelo_processos.py`, `distribuido.py`, `benchmark_log.txt`.
- `docs/apresentacao.pdf` em tela cheia em outra janela; `experimentos/figuras/animacao.gif` aberto no visualizador de imagens.
- OBS com 2 cenas: **Slides** e **VS Code**, ambas com a(s) câmera(s) no canto inferior direito.

---

## Bloco 1 — MATHEUS — abertura (0:00–0:40)

### Slide 1 — Capa
**[TELA]** slide 1.
- *"Olá, nós somos o grupo 05."*
- *"Eu sou o Matheus, e comigo estão [nomes de quem está na chamada]."*
- *"Nosso trabalho é sobre a propagação de fake news em sistemas paralelos e distribuídos."*
- *"Partimos do código sequencial fornecido e construímos uma versão paralela com threads, outra com processos, e uma versão distribuída com sockets."*

### Slide 2 — O problema
**[TELA]** slide 2.
- *"A motivação é que notícias falsas se espalham mais rápido e mais longe que as verdadeiras, como mostrou um estudo publicado na Science em 2018."*
- *"A gente simula isso numa população em forma de grade, onde cada célula é uma pessoa que interage com seus oito vizinhos."*
- *"À direita estão os requisitos atendidos: divisão explícita da matriz, sem bibliotecas de paralelização automática, e o mesmo resultado do sequencial em todas as versões."*

## Bloco 2 — MATHEUS — modelo e sequencial (0:40–2:40)

### Slide 3 — Modelo computacional
**[TELA]** slide 3.
- *"Cada pessoa tem um de três estados: ignorante, espalhador ou inativo, como no modelo clássico de rumores de Daley e Kendall."*
- *"A regra: um ignorante com pelo menos 'limiar' vizinhos espalhadores vira espalhador; o espalhador vira inativo, e o inativo continua inativo."*
- *"O ponto-chave para paralelizar é este: cada célula depende só dos oito vizinhos da geração anterior. Então dá para dividir a grade em pedaços e sincronizar apenas as bordas."*

### Slide 4 — Solução sequencial
**[TELA]** slide 4.
- *"O código original usava lista de listas, copiava a grade inteira a cada geração e testava os limites da matriz para cada vizinho."*
- *"Nós refatoramos: a grade virou um bytearray, com um byte por pessoa."*
- *"Colocamos uma moldura de células-fantasma, sempre ignorantes, ao redor da matriz; assim toda célula real tem oito vizinhos e os testes de limite somem."*
- *"E trocamos a cópia por dois buffers que se alternam."*

**[CÓDIGO]** `modelo.py` → linha **145**, selecionar **145–152**.
- *"Aqui a grade é criada com a moldura, e os espalhadores iniciais são sorteados exatamente como no código original, com a mesma semente; então a grade inicial é idêntica."*

**[CÓDIGO]** `modelo.py` → linha **252**, selecionar **252–279**.
- *"Este é o kernel, a função que calcula uma geração."*
- *"Ela recebe a grade de leitura, src, a grade de escrita, dst, e um intervalo de linhas, de r0 a r1."*
- *"Para cada célula ignorante, soma os oito vizinhos de uma vez, sem nenhum if de borda, por causa da moldura."*

### Slide 5 — Um núcleo, quatro execuções
**[TELA]** slide 5.
- *"Essa é a decisão mais importante do projeto: todas as versões chamam exatamente esse mesmo kernel."*
- *"O sequencial chama com a grade inteira; cada thread, processo ou trabalhador chama só com a sua faixa de linhas."*
- *"Como o kernel escreve apenas nas linhas que recebeu, duas faixas diferentes nunca escrevem no mesmo lugar."*

## Bloco 3 — LEONARDO — versão paralela (2:40–5:20)

### Slide 6 — Divisão da matriz
**[TELA]** slide 6.
- *"Agora eu vou falar da versão paralela."*
- *"A matriz é dividida em faixas horizontais contíguas, e os tamanhos diferem em no máximo uma linha, para equilibrar a carga."*
- *"Para calcular sua faixa, cada trabalhador precisa da última linha da faixa de cima e da primeira da faixa de baixo. Essas linhas extras são o halo."*
- *"Faixas horizontais têm uma vantagem: cada fronteira é uma única linha, que cabe numa só mensagem."*

### Slide 7 — Threads
**[TELA]** slide 7.
- *"A primeira versão usa threads."*

**[CÓDIGO]** `paralelo_threads.py` → linha **58**, selecionar **58–67**.
- *"Na geração g, todas as threads leem o buffer g módulo 2 e escrevem no outro."*
- *"Cada thread chama o kernel só com as suas linhas, de r0 a r1."*
- *"Na linha 64 está a barreira: nenhuma thread começa a próxima geração, que vai sobrescrever o buffer que ainda está sendo lido, antes de todas terminarem. É isso que evita condição de corrida."*
- *"Cada thread grava suas contagens numa posição só dela, então não precisamos de lock."*

**[TELA]** volta ao slide 7.
- *"O problema é o GIL do Python: só uma thread executa código Python por vez."*
- *"Então essa versão é correta, mas não acelera; ficou até um pouco mais lenta que o sequencial."*

### Slide 8 — Multiprocessing
**[TELA]** slide 8.
- *"Para ter paralelismo de verdade usamos multiprocessing, que o enunciado permite."*
- *"Os dois buffers da grade ficam em memória compartilhada, então nenhum processo copia a matriz inteira, e a sincronização continua sendo uma barreira por geração."*

**[CÓDIGO]** `paralelo_processos.py` → linha **64**, selecionar **64–78**.
- *"Este é o laço de cada processo."*
- *"Nas linhas 67 a 69 está uma otimização que fizemos depois de medir: o processo copia a sua faixa mais o halo para uma memória local, calcula, e grava de volta só as suas linhas."*
- *"Na linha 74 está a barreira de fim de geração."*

### Slide 15 — Gargalos (pular para o slide 15 e voltar depois)
**[TELA]** slide 15.
- *"Por que essa cópia local? Na primeira versão o kernel lia direto da memória compartilhada, e com um processo só ficava dezenove por cento mais lento que o sequencial."*
- *"Com a cópia local o ganho chegou a 1,21 vez."*

## Bloco 4 — MATHEUS — versão distribuída (5:20–8:30)

### Slide 9 — Versão distribuída
**[TELA]** slide 9.
- *"Agora a versão distribuída, com sockets TCP."*
- *"Temos um coordenador e vários trabalhadores, cada um num processo separado, que só se comunicam pela rede."*
- *"O coordenador cria a grade, envia para cada trabalhador a sua faixa mais as duas linhas de halo, e no fim junta o resultado."*
- *"Implementamos duas topologias: na estrela, as bordas passam pelo coordenador; na p2p, os vizinhos trocam bordas diretamente."*

**[CÓDIGO]** `distribuido.py` → linha **249**, selecionar **243–251**.
- *"Aqui o coordenador envia a cada trabalhador sua configuração, os endereços dos vizinhos e as linhas da sua faixa com o halo."*

**[CÓDIGO]** `distribuido.py` → linha **139**, selecionar **139–145**.
- *"Para não ter deadlock, a ordem é fixa: cada trabalhador primeiro conecta ao vizinho de baixo, que já está escutando, e só depois aceita o de cima."*

**[CÓDIGO]** `distribuido.py` → linha **157**, selecionar **157–181**.
- *"Este é o laço de cada trabalhador na topologia p2p, em quatro passos."*
- *"Em (a), ele calcula primeiro as duas linhas de borda."*
- *"Em (b), já envia essas bordas para os vizinhos."*
- *"Em (c), calcula o miolo da faixa enquanto as bordas ainda estão trafegando; assim a comunicação fica escondida atrás do cálculo."*
- *"Em (d), recebe os halos dos vizinhos. Esse recv bloqueante funciona como uma barreira entre vizinhos: ninguém avança sem a borda da geração atual."*
- *"Por fim, manda as contagens ao coordenador, que decide se todos continuam ou param."*

### Slide 10 — Sincronização
**[TELA]** slide 10.
- *"Esta tabela resume a sincronização das três versões."*
- *"Um detalhe importante: o random do Python depende da ordem em que as células são visitadas, e essa ordem muda quando dividimos a matriz."*
- *"Por isso usamos um gerador baseado em contador: o número sorteado depende só da semente, da geração e da posição da célula. O resultado fica igual em qualquer divisão."*

### Slide 11 — Validação
**[TELA]** slide 11.
- *"Para provar que tudo dá o mesmo resultado, escrevemos oito testes automáticos."*

**[CÓDIGO]** `benchmark_log.txt` (aba já aberta) → linha **1**, selecionar **1–24**.
- *"E aqui está o log das execuções do experimento principal, uma matriz de mil por mil, com vinte gerações."*
- *"A última coluna é o hash SHA-256 da grade final. Ele é exatamente o mesmo em todas as linhas: todas as versões chegaram à mesma grade."*
- *"E dá para ver os tempos caindo: dezesseis segundos no sequencial, e menos de três segundos com doze trabalhadores na distribuída."*

## Bloco 5 — VINICIUS (opcional; senão MATHEUS) — desempenho (8:30–10:00)

### Slide 12 — Configuração experimental
**[TELA]** slide 12.
- *"Os experimentos rodaram num Xeon E5-2620 v3, com seis núcleos físicos e doze lógicos, 16 gigabytes de RAM, Windows 10 e Python 3.11."*
- *"Cada cenário rodou três vezes e usamos a mediana, num total de 330 execuções."*

### Slide 13 — Speedup
**[TELA]** slide 13.
- *"Neste gráfico está o speedup, que é o tempo sequencial dividido pelo tempo paralelo."*
- *"Com seis processos ficou 3,7 vezes mais rápido, e a distribuída p2p chegou a 4,2 vezes."*
- *"Com doze trabalhadores, a p2p chegou a seis vezes."*
- *"A linha amarela de baixo são as threads, abaixo de um, por causa do GIL."*

### Slide 14 — Eficiência
**[TELA]** slide 14.
- *"A eficiência é o speedup dividido pelo número de processos."*
- *"Ela cai depois de seis porque a máquina só tem seis núcleos físicos; os outros seis são Hyper-Threading, que dividem o mesmo núcleo."*
- *"A métrica de Karp-Flatt, na última coluna, estima a parte serial; ela não cresce com o número de processos, então o limite é o hardware, não o código."*

### Slide 15 — (já apresentado no bloco 3)
**[TELA]** passar direto pelo slide 15.
- *"Os gargalos da versão paralela o Leonardo já mostrou."*

### Slide 16 — Comunicação
**[TELA]** slide 16.
- *"Aqui o custo de comunicação da versão distribuída."*
- *"Na p2p, a comunicação ocupa menos de dois por cento do tempo de cada trabalhador."*
- *"Na estrela sobe para seis a treze por cento, porque todas as bordas passam pelo coordenador, e ele vira gargalo."*

## Bloco 6 — LEONARDO — tamanho, gerações e otimizações (10:00–11:00)

### Slide 17 — Tamanho da matriz
**[TELA]** slide 17.
- *"Este slide mostra o efeito do tamanho da matriz, com seis processos."*
- *"Mas à direita, no tempo total, a grade de 250 por 250 fica mais lenta que o sequencial, porque criar seis processos no Windows custa cerca de meio segundo."*
- *"Na grade de dois mil por dois mil chega a 3,9 vezes: problemas maiores escalam melhor."*

### Slide 18 — Gerações e percentual
**[TELA]** slide 18.
- *"À esquerda, mais gerações diluem esse custo fixo de inicialização, e o speedup total sobe."*
- *"À direita, mais espalhadores iniciais deixam o cálculo mais rápido, porque só os ignorantes precisam contar vizinhos. O speedup se mantém em torno de quatro vezes."*

### Slide 19 — Otimizações do núcleo
**[TELA]** slide 19.
- *"Também otimizamos o código sequencial."*
- *"A refatoração deixou o código 3,5 vezes mais rápido que o original, e o kernel otimizado, 7,5 vezes, sempre com o mesmo resultado."*
- *"Juntando o kernel otimizado com oito processos, o tempo por célula ficou cerca de 42 vezes menor que no código original."*

## Bloco 7 — CARLOS (opcional; senão MATHEUS) — extensões do modelo (11:00–12:15)

### Slide 20 — Melhorias no modelo
**[TELA]** slide 20.
- *"Além do modelo original, implementamos quatro extensões baseadas na literatura."*
- *"Primeiro, probabilidade: cada contato com um espalhador convence com uma certa probabilidade."*
- *"Segundo, influenciadores: quando espalham, contam como três vizinhos."*
- *"Terceiro, bots: espalham em todas as gerações e nunca param."*
- *"Quarto, céticos: precisam de dois vizinhos a mais para serem convencidos."*

**[TELA]** abrir `animacao.gif` por 5–10 s.
- *"Aqui a propagação ao longo das gerações: o vermelho está espalhando, e o azul já ficou inativo."*

### Slide 21 — Resultados do modelo
**[TELA]** slide 21.
- *"Numa grade de duzentos por duzentos, o modelo original atinge 32 por cento da população."*
- *"Com apenas um por cento de influenciadores, o alcance quase dobra, de 24 para 44 por cento."*
- *"Já com trinta por cento de céticos, cai para 6 por cento."*

## Bloco 8 — encerramento (12:15–13:15)

### Slide 22 — Limitações (LEONARDO)
**[TELA]** slide 22.
- *"As principais limitações: o GIL, os seis núcleos físicos da máquina, o custo de criar processos em grades pequenas, e a versão distribuída testada num único computador."*

### Slide 23 — Dificuldades (LEONARDO)
**[TELA]** slide 23.
- *"As maiores dificuldades foram provar que todas as versões davam o mesmo resultado, manter o sorteio aleatório igual em paralelo, evitar deadlock ao abrir as conexões, e fazer todos pararem na mesma geração."*

### Slide 24 — Melhorias implementadas (MATHEUS, ou CARLOS se estiver)
**[TELA]** slide 24.
- *"Aqui estão as nove melhorias que implementamos, cada uma com a justificativa e o resultado medido."*

### Slide 25 — Contribuição individual (cada um fala a sua linha)
**[TELA]** slide 25.
- MATHEUS: *"Eu fiz a refatoração do sequencial, o núcleo de cálculo e a versão distribuída com sockets."*
- LEONARDO: *"Eu fiz as versões paralelas com threads e multiprocessing e a análise de desempenho."*
- VINICIUS (se estiver): *"Eu apresentei a análise de desempenho."*
- CARLOS (se estiver): *"Eu apresentei as extensões do modelo."*

### Slide 26 — Conclusões (MATHEUS)
**[TELA]** slide 26.
- *"Para concluir: as três versões reproduzem exatamente o resultado do código original."*
- *"Em Python, o paralelismo real precisou de processos; chegamos a 5,3 vezes com multiprocessing e 6 vezes com a versão distribuída."*
- *"E otimizar o algoritmo rendeu tanto quanto paralelizar, e os dois ganhos se somam."*

### Slides 27 e 28 — Referências (MATHEUS)
**[TELA]** slide 27, depois 28 (2–3 s cada).
- *"Aqui estão as referências que fundamentam o modelo e as técnicas de paralelização, incluindo o uso de IA generativa como apoio."*
- *"Obrigado pela atenção."*

---

## Conferência rápida

| Bloco | Quem | Até |
|---|---|---|
| 1–2 | Matheus | 2:40 |
| 3 | Leonardo | 5:20 |
| 4 | Matheus | 8:30 |
| 5 | Vinicius / Matheus | 10:00 |
| 6 | Leonardo | 11:00 |
| 7 | Carlos / Matheus | 12:15 |
| 8 | todos | 13:15 |

Se passar de 15 min: encurte as falas do slide 10 e do slide 18.
Se ficar abaixo de 10 min: fale mais devagar nos trechos de código.
