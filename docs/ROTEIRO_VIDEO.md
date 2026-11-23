# Roteiro do vídeo — Grupo 05 — Propagação de Fake News

**Alvo: 13 min** (limite 10–15 min). Tudo roda no computador do Matheus,
numa chamada (Meet/Teams/Zoom/Discord) gravada, com as câmeras ligadas.

Formato exigido: MP4, H.264, 1280×720, 30 fps, áudio AAC estéreo 44,1 kHz,
**sem marca d'água**. Nome: `AAAA-MM-DD - Grupo 05 - FakeNews.mp4`
(ex.: `2026-11-30 - Grupo 05 - FakeNews.mp4`).

## Como funciona a divisão

O vídeo está montado para **Matheus e Leonardo conseguirem gravar sozinhos**.
Vinicius e Carlos têm **um bloco curto cada (≈ 1,5 min), opcional**: se
estiverem na chamada, apresentam; se não, quem está marcado como
**substituto** lê o mesmo texto. Nada mais muda.

| # | Bloco | Quem | Substituto | Slides | Tempo |
|---|---|---|---|---|---|
| 1 | Abertura | Matheus | — | 1–2 | 0:00–0:40 |
| 2 | Modelo e sequencial | Matheus | — | 3–5 | 0:40–2:40 |
| 3 | Paralela (threads e processos) | Leonardo | — | 6–8, 15 | 2:40–5:40 |
| 4 | Distribuída (sockets) | Matheus | — | 9–11 | 5:40–8:40 |
| 5 | Desempenho: speedup e comunicação | **Vinicius** *(opcional)* | Matheus | 12–14, 16 | 8:40–10:10 |
| 6 | Desempenho: tamanho, gerações, otimizações | Leonardo | — | 17–19 | 10:10–11:10 |
| 7 | Extensões do modelo | **Carlos** *(opcional)* | Matheus | 20–21, 24 | 11:10–12:30 |
| 8 | Limitações, contribuição, conclusões | Leonardo + Matheus (+ todos no slide 25) | — | 22–23, 25–28 | 12:30–13:30 |

Fala aproximada: Matheus 6–9 min · Leonardo ≈ 4,5 min · Vinicius ≈ 1,5 min · Carlos ≈ 1,5 min.

**Antes de entregar:**
- Os 4 apresentaram → usar `docs/apresentacao.pdf` (slide 25 com os 4 papéis).
- Vinicius e/ou Carlos não apresentaram → usar `docs/apresentacao_2integrantes.pdf`
  (slide 25 com "não participou") — ou editar só a linha de quem faltou no
  slide 25 de `docs/apresentacao.html` e imprimir de novo como PDF no Edge
  (sem cabeçalhos e rodapés). O slide de contribuição precisa refletir o que
  aconteceu de fato.
- Pelas regras, quem não aparecer no vídeo fica com zero; por isso Vinicius e
  Carlos devem ficar com **câmera ligada durante toda a gravação**, não só no
  próprio bloco.

## Mensagem para mandar ao Vinicius e ao Carlos

> "Vamos gravar o vídeo [dia/hora] pelo [Meet/Discord]. Cada um de vocês tem um
> bloco de ~1,5 min já escrito no roteiro (arquivo ROTEIRO_VIDEO.md, blocos 5 e
> 7). Vinicius: resultados de desempenho (slides 13, 14 e 16). Carlos: extensões
> do modelo (slides 20, 21 e 24). Leiam o texto e os slides antes; precisam ficar
> de câmera ligada a gravação inteira (~15 min). Se não der para entrar, me avisem
> até [horário] que a gente grava sem vocês."

---

## Preparação (no computador do Matheus)

1. **OBS Studio** → Configurações:
   - Vídeo: resolução base e de saída **1280×720**, **30 FPS**;
   - Saída → Gravação: formato **MP4**, codificador **x264** (H.264);
   - Áudio: **44,1 kHz**, estéreo (o OBS grava em AAC);
   - Cena: captura de tela + captura da janela da chamada (câmeras de todos).
   - Alternativa: gravar pela própria ferramenta de chamada; se o arquivo não
     sair em MP4 720p, converter no HandBrake (preset "Fast 720p30").
2. Deixar abertos: `docs/apresentacao.pdf` (tela cheia); VS Code na pasta
   `fake_news/`; **3 terminais PowerShell** na pasta `fake_news/` lado a lado
   (fonte ~18 pt); `experimentos/figuras/animacao.gif`.
3. Rodar todos os comandos de demo uma vez antes de gravar.
4. O Matheus controla a tela; os outros pedem "próximo slide" ou "abre o
   arquivo X" quando for a vez deles. Microfone aberto só para quem está falando.

---

## Bloco 1 · 0:00–0:40 · Abertura — Matheus (slides 1–2)

> "Somos o grupo 05: [dizer os nomes de quem está na chamada]. O trabalho
> simula a propagação de uma fake news numa população representada por uma
> matriz e transforma o código sequencial fornecido em versões paralela — com
> threads e com processos — e distribuída, com sockets. Vamos mostrar o código,
> as decisões de implementação e os resultados de desempenho."

## Bloco 2 · 0:40–2:40 · Modelo e versão sequencial — Matheus (slides 3–5)

- Slide 3: três estados, regra do limiar, vizinhança de Moore, atualização
  síncrona. *"Cada célula só depende dos 8 vizinhos da geração anterior: dá para
  dividir a matriz e sincronizar apenas as bordas."*
- Slide 4: o que mudou do original. **VS Code** `fakenews/modelo.py`:
  - `criar_estado`: mesmo sorteio do `FakeNews.py`, mesma grade inicial;
  - comentário do topo: grade achatada em `bytearray` + moldura de células-fantasma;
  - `passo_referencia`: 8 vizinhos sem `if` de borda, contagem junto com o
    cálculo, buffer duplo em vez de `deepcopy`.
- Slide 5: *"Todas as versões chamam esse mesmo kernel com uma faixa de linhas
  `[r0, r1)`; ele só escreve nessas linhas."*
- **Demo (20 s):**
  ```powershell
  python -m fakenews.sequencial --linhas 100 --colunas 100 --geracoes 50 --percentual 0.05 --limiar 3
  ```
  Apontar a assinatura SHA-256 no final (`2fa7d01cf1283f12`): *"vamos comparar
  esse hash com as outras versões."*

## Bloco 3 · 2:40–5:40 · Versão paralela — Leonardo (slides 6–8, 15)

- Slide 6: divisão em faixas horizontais; `dividir_linhas` (diferença de no
  máximo 1 linha); halo.
- **VS Code** `fakenews/paralelo_threads.py`, função `trabalhador`:
  - *"na geração g todos leem `buffers[g % 2]` e escrevem em `buffers[(g+1) % 2]`"*;
  - `barreira.wait()`: *"ninguém começa a próxima geração — que sobrescreve o
    buffer que está sendo lido — antes de todos terminarem; isso evita condição
    de corrida"*;
  - `parciais[g][t]`: posição exclusiva por thread, sem lock; todas somam e
    decidem parar na mesma geração.
- Slide 7: *"Está correto, mas no CPython 3.11 fica 0,74×: o GIL deixa só uma
  thread executar Python por vez."*
- **VS Code** `fakenews/paralelo_processos.py`: `SharedMemory`, `Barrier`,
  `RawArray`, e o trecho `copia_local`. Slide 15: *"medimos que ler direto da
  memória compartilhada deixava 19% mais lento; agora cada processo copia sua
  faixa mais o halo para memória local a cada geração."*
- **Demo (40 s):**
  ```powershell
  python -m fakenews.paralelo_threads --threads 4 --linhas 100 --colunas 100 --geracoes 50 --percentual 0.05 --limiar 3 --quieto
  ```
  ```powershell
  python -m fakenews.paralelo_processos --processos 6 --linhas 1000 --colunas 1000 --geracoes 10 --limiar 2 --sem-parada --quieto
  ```
  Primeiro: mesmo hash `2fa7d01cf1283f12`. Segundo: ~2,3 s de computação contra
  ~10 s do sequencial com os mesmos parâmetros.

## Bloco 4 · 5:40–8:40 · Versão distribuída — Matheus (slides 9–11)

- Slide 9: coordenador + trabalhadores; p2p × estrela; formato das mensagens.
- **VS Code** `fakenews/distribuido.py`:
  - `coordenador`: envia faixa + 2 linhas de halo (`grade[ini*W:(fim+2)*W]`) e o
    endereço dos vizinhos;
  - laço p2p do `trabalhador`: (a) calcula as bordas, (b) envia aos vizinhos,
    (c) calcula o miolo enquanto as bordas trafegam, (d) recebe os halos e manda
    as contagens; *"o recv bloqueante funciona como barreira entre vizinhos"*;
  - conecta ao vizinho de baixo e depois aceita o de cima: *"evita deadlock"*;
  - *"nada de pickle na rede: mensagens binárias com tamanho e tipo; TCP_NODELAY."*
- Slide 10: tabela de sincronização; gerador por contador para o modelo aleatório.
- **Demo (60 s) — 3 terminais no mesmo computador.** Cada um é um processo
  independente que só conversa por TCP; em máquinas diferentes bastaria trocar
  `127.0.0.1` pelo IP do coordenador.
  ```powershell
  # terminal 1 — coordenador
  python -m fakenews.distribuido coordenador --porta 5000 --trabalhadores 2 --linhas 100 --colunas 100 --geracoes 50 --percentual 0.05 --limiar 3
  ```
  ```powershell
  # terminais 2 e 3 — trabalhadores
  python -m fakenews.distribuido trabalhador --host 127.0.0.1 --porta 5000 --verbose
  ```
  Mostrar: cada trabalhador imprime sua faixa (linhas 0..49 e 50..99) e o
  coordenador termina com o mesmo hash `2fa7d01cf1283f12`. Depois:
  ```powershell
  python -m fakenews.distribuido local --trabalhadores 6 --linhas 1000 --colunas 1000 --geracoes 10 --limiar 2 --sem-parada --quieto
  ```
  Comentar `t_com_medio_s` pequeno: comunicação ≈ 1% do tempo.
- Slide 11 (10 s): *"8 testes automáticos garantem que tudo dá o mesmo resultado."*

## Bloco 5 · 8:40–10:10 · Desempenho — Vinicius *(opcional; substituto: Matheus)* (slides 12–14, 16)

Texto para ler (≈ 1,5 min):

- **Slide 12:** *"Os testes foram feitos num Xeon E5-2620 v3, com 6 núcleos
  físicos e 12 lógicos, 16 GB de RAM, Windows 10 e Python 3.11. Cada cenário
  rodou 3 vezes e usamos a mediana — no total foram 330 execuções."*
- **Slide 13:** *"Numa matriz de mil por mil, com 20 gerações, o sequencial leva
  16 segundos. Com 6 processos ficou 3,7 vezes mais rápido; a versão distribuída
  p2p chegou a 4,2 vezes com 6 trabalhadores e a 6 vezes com 12. As threads
  ficaram mais lentas que o sequencial, por causa do GIL do Python."*
- **Slide 14:** *"A eficiência cai depois de 6 porque a máquina só tem 6 núcleos
  físicos; os outros 6 são Hyper-Threading. A métrica de Karp-Flatt ficou entre
  0,07 e 0,16 e não cresce com o número de processos: o que limita é custo fixo
  e hardware, não uma parte sequencial do código."*
- **Slide 16:** *"Na versão distribuída ponto a ponto, a comunicação ocupa menos de
  2% do tempo, porque cada trabalhador só troca uma linha com cada vizinho. Na
  topologia estrela, onde tudo passa pelo coordenador, sobe para 6 a 13%: o
  coordenador vira gargalo."*

O que o Vinicius precisa entender: speedup = tempo sequencial ÷ tempo
paralelo; eficiência = speedup ÷ número de processos; p2p = trabalhadores
trocam bordas direto entre si; estrela = tudo passa pelo coordenador.

## Bloco 6 · 10:10–11:10 · Desempenho (continuação) — Leonardo (slides 17–19)

- Slides 17–18: *"Em matriz pequena o paralelismo não compensa — criar 6
  processos no Windows custa ~0,5 s. Mais gerações amortizam esse custo fixo.
  E mais espalhadores iniciais significam menos trabalho, porque só os
  ignorantes precisam contar vizinhos; o speedup continua em torno de 4×."*
- Slide 19: *"Só otimizando o núcleo sequencial ganhamos 3,5× e 7,5× sobre o
  original; juntando com 8 processos, o tempo por célula cai cerca de 42×."*

## Bloco 7 · 11:10–12:30 · Extensões do modelo — Carlos *(opcional; substituto: Matheus)* (slides 20–21, 24)

Texto para ler (≈ 1,5 min):

- **Slide 20:** *"Além do modelo original, implementamos quatro extensões baseadas
  na literatura. Primeiro, a probabilidade: cada contato com um espalhador
  convence com probabilidade p. Segundo, influenciadores: quando espalham,
  contam como três vizinhos. Terceiro, bots: espalham em todas as gerações e
  nunca param. Quarto, céticos: precisam de dois vizinhos a mais para serem
  convencidos."*
- **Mostrar o GIF** `experimentos/figuras/animacao.gif`: *"Aqui a propagação ao
  longo das gerações: vermelho espalha, azul já ficou inativo."*
- **Slide 21:** *"Numa grade de 200 por 200, o modelo original atinge 32% da
  população. Só 1% de influenciadores quase dobra o alcance, de 24 para 44%. Já
  30% de céticos derrubam para 6%. Repetimos com 10 sementes e o desvio-padrão
  ficou entre 0,2 e 3,7 pontos."*
- **Slide 24:** *"Este slide resume as nove melhorias implementadas, cada uma com
  a justificativa e o resultado medido."*

O que o Carlos precisa entender: alcance = porcentagem da população que
recebeu a fake news; semente = número que fixa o sorteio aleatório, para os
resultados serem reproduzíveis.

## Bloco 8 · 12:30–13:30 · Encerramento (slides 22–23, 25–28)

- **Leonardo** (slides 22–23): limitações (GIL, 6 núcleos, distribuída testada
  num só computador) e dificuldades (deadlock, aleatoriedade em paralelo, spawn
  no Windows).
- **Slide 25**: cada um que está na chamada diz em uma frase o que fez.
- **Matheus** (slide 26 + referências): conclusões; *"as referências e o uso de
  IA generativa estão nos slides finais e em `docs/REFERENCIAS.md`."*

---

## Perguntas prováveis do professor

| Pergunta | Resposta curta |
|---|---|
| Por que threads não aceleraram? | GIL do CPython: uma thread executa bytecode por vez; a tarefa é CPU-bound. |
| Onde poderia haver condição de corrida e como evitaram? | Escrever na grade que outro ainda lê. Buffer duplo + faixas disjuntas + barreira por geração. |
| Por que faixas horizontais e não blocos 2D? | A borda é 1 linha contígua (1 mensagem, cópia barata). Blocos 2D só reduzem o perímetro para p grande; com p ≤ 12 a comunicação já é < 2%. |
| Como garantem que todos param na mesma geração? | Threads/processos: todos somam as mesmas contagens após a barreira. Distribuída: o coordenador soma e responde CONTINUA/PARA. |
| Como o modelo aleatório dá o mesmo resultado em paralelo? | Gerador baseado em contador: o número depende de (semente, geração, célula), não da ordem de visita. |
| Por que a distribuída ficou mais rápida que multiprocessing? | Memória privada e sincronização só entre vizinhos, sem barreira global de 12 processos. |
| Vocês testaram em várias máquinas? | Não, só num computador (processos separados conversando por TCP local). O código aceita IPs reais; em rede, cada mensagem custaria ~0,1–1 ms, contra ~180 ms de cálculo por geração. |
| Quanto custa a comunicação? | 1 linha (C+2 bytes) por fronteira e sentido + 24 bytes de contagem por geração. |

## Checklist final

- [ ] Duração entre 10:00 e 15:00 (alvo 13 min)
- [ ] Todos que aparecem no slide 25 como apresentadores falaram, com câmera ligada a gravação toda
- [ ] PDF certo no ZIP: `apresentacao.pdf` (4 apresentaram) ou `apresentacao_2integrantes.pdf` (só 2)
- [ ] Demos da paralela e da distribuída rodando
- [ ] MP4 H.264 1280×720 30 fps, AAC 44,1 kHz estéreo, sem marca d'água
- [ ] Nome: `AAAA-MM-DD - Grupo 05 - FakeNews.mp4`
- [ ] ZIP com código + PDF + vídeo (ou link público, se exceder o limite do Moodle)
