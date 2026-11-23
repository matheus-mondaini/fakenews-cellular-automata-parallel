# Relatório técnico — Propagação de Fake News: sequencial, paralela e distribuída

> Números = mediana de 3 repetições. Dados brutos: `experimentos/resultados/resultados.csv`;
> todas as tabelas: `experimentos/resultados/tabelas.md`; figuras: `experimentos/figuras/`.

## 1. Problema e modelo

População numa grade L×C; cada célula é um indivíduo em um de três estados
(Ignorante 0, Espalhador 1, Inativo 2), como no modelo de rumor de Daley &
Kendall (1964). Em cada geração (atualização síncrona, autômato celular):

* Ignorante com ≥ *limiar* vizinhos espalhadores (vizinhança de Moore, 8
  vizinhos) → Espalhador — modelo de limiar de Granovetter (1978);
* Espalhador → Inativo; Inativo → Inativo.

A geração g+1 depende apenas da geração g e da vizinhança imediata: é um
problema de **estêncil 2D** (*stencil*), naturalmente paralelizável por
decomposição de domínio, com comunicação só nas fronteiras (Foster, 1995).

## 2. Versão sequencial refatorada (`fakenews/sequencial.py`, `fakenews/modelo.py`)

| Mudança | Motivo |
|---|---|
| `bytearray` achatado (1 byte/célula) | menos memória e acesso mais rápido que lista de listas |
| moldura de células-fantasma sempre 0 | elimina os testes de limite no laço interno; vira o "halo" nas versões distribuídas |
| buffer duplo com troca de referências | elimina o `deepcopy` de toda a grade por geração |
| contagem dentro do kernel | elimina a 2ª varredura (`contar_estados`) |
| mesma sequência de `random` | grade inicial idêntica à do `FakeNews.py` |

Resultado (E5, 500², 20 gerações): original 14,85 s → refatorado 4,24 s
(**3,5×**) → kernel otimizado 1,99 s (**7,5×**), todos com a mesma grade final.

O kernel otimizado usa somas por coluna (`col[j] = cima[j]+meio[j]+baixo[j]`;
para uma célula ignorante, vizinhos = `col[j-1]+col[j]+col[j+1]`) e pula
linhas cuja janela 3×W não tem espalhadores.

## 3. Versões paralelas

**Divisão:** faixas contíguas de linhas, tamanhos diferindo em ≤ 1 linha
(`dividir_linhas`). Todas as versões chamam o mesmo
`kernel(src, dst, W, C, r0, r1, ctx, g)`, que lê só `src` e escreve só as
linhas `[r0, r1)` de `dst`.

**Threads (`paralelo_threads.py`):** buffer duplo compartilhado, faixas
disjuntas em `dst` (sem condição de corrida), `threading.Barrier` ao fim de
cada geração (impede que alguém sobrescreva o buffer ainda lido), contagens em
posições exclusivas e decisão de parada replicada após a barreira.

**Processos (`paralelo_processos.py`):** mesma lógica com
`multiprocessing.shared_memory` (dois buffers), `multiprocessing.Barrier` e
`RawArray` para as contagens. Versão final: cada processo copia sua faixa + 2
linhas de halo para um `bytearray` local, calcula e grava de volta só suas
linhas (ver E7).

## 4. Versão distribuída (`distribuido.py`)

* Coordenador cria a grade, envia a cada trabalhador sua faixa **com 2
  linhas de halo**, os parâmetros (JSON) e o endereço dos vizinhos.
* Protocolo próprio sobre TCP: `[tamanho uint32][tipo 'J'|'B'][dados]`; nada de
  pickle na rede; `TCP_NODELAY` ativo.
* **p2p:** bordas trocadas direto entre vizinhos. As linhas de borda são
  calculadas primeiro e enviadas antes do miolo (sobreposição de cálculo e
  comunicação). Contagens (24 bytes) vão ao coordenador, que faz a redução e
  responde CONTINUA/PARA; sem parada automática, nem há resposta.
* **estrela:** bordas sobem ao coordenador, que as redistribui (comparação).
* Sem deadlock: cada trabalhador conecta ao vizinho de baixo (que já escuta)
  e depois aceita o de cima.
* Execução em várias máquinas: `coordenador --porta P` + `trabalhador --host IP`.

## 5. Validação

`tests/test_equivalencia.py` (8 testes, todos passando) compara grade final e
histórico de contagens de threads, processos (com e sem cópia local) e
distribuída (p2p e estrela) com a sequencial — e esta com o `FakeNews.py`
original. Inclui o modelo estendido probabilístico. Nos benchmarks, as 330
execuções gravaram o SHA-256 da grade: idêntico entre versões em todos os 17
cenários.

## 6. Configuração experimental

| Item | Valor |
|---|---|
| Processador | Intel Xeon E5-2620 v3 @ 2,40 GHz |
| Núcleos | 6 físicos / 12 lógicos |
| RAM | 16 GB (15,8 GB utilizáveis) |
| SO | Windows 10 Home 22H2 (10.0.19045), 64 bits |
| Linguagem | Python (CPython 3.11.5, MSC v.1936, 64 bits, com GIL) |
| Ambiente | uma máquina; distribuída por TCP loopback, 1 processo por trabalhador |

Metodologia: 3 repetições intercaladas, mediana; `--sem-parada` (carga fixa);
limiar 2; semente 42; 5% de espalhadores (exceto E4). **T computação** = laço
de gerações (inclui barreiras e comunicação); **T total** = inclui criação do
estado, processos, conexões e distribuição inicial.

## 7. Resultados

### E1 — Escalabilidade forte (1000², 20 gerações; T_seq = 16,27 s)

| Versão | p=2 | p=4 | p=6 | p=8 | p=12 |
|---|---|---|---|---|---|
| Threads (S) | 0,77 | 0,74 | 0,74 | 0,76 | — |
| Multiprocessing (S / E) | 1,84 / 92% | 3,08 / 77% | 3,73 / 62% | 4,62 / 58% | 5,32 / 44% |
| Distribuída p2p (S / E) | 1,87 / 93% | 3,17 / 79% | 4,22 / 70% | 4,85 / 61% | **6,01** / 50% |
| Distribuída estrela (S / E) | 1,73 / 86% | 3,07 / 77% | 4,12 / 69% | 4,61 / 58% | 5,75 / 48% |

Fração serial de Karp-Flatt entre 0,07 e 0,16 e sem tendência de crescimento com p: a perda de
eficiência não vem de uma parte serial que cresce, mas de custos fixos por
geração (barreira, cópias) e da saturação do hardware — a partir de 6
processos os núcleos lógicos (Hyper-Threading) dividem as unidades de execução.

### Comunicação (E1, distribuída)

| p | p2p: % do tempo em comunicação/espera | estrela |
|---|---|---|
| 2 | 0,0% | 6,1% |
| 6 | 1,7% | 13,0% |
| 12 | 0,8% | 7,0% |

Cada fronteira troca 1 linha (C+2 = 1002 bytes) por geração e sentido: o
volume cresce com o perímetro, o cálculo com a área. Na estrela o coordenador
recebe e reenvia 2N bordas por geração, sequencialmente — vira gargalo.

### E2 — Tamanho (10 gerações, p=6)

Speedup de computação 2,7–3,5× em 250² até 4,3× (processos) / 4,2× (p2p) em
2000². No tempo total, 250² fica **mais lento** que o sequencial (0,65×) porque
criar 6 processos no Windows (spawn) custa ≈ 0,5 s; em 2000² chega a 3,9×.
Problemas maiores escalam melhor (Gustafson, 1988).

### E3 — Gerações (1000², p=6)

Speedup total: multiprocessing 3,2× (5 ger.) → 4,0× (40 ger.); p2p 3,6× → 4,3×.
O custo fixo de inicialização é amortizado.

### E4 — Percentual inicial (1000², 10 gerações)

Sequencial: 12,6 s (1%) → 10,6 s (5%) → 3,9 s (20%) → 2,6 s (50%). Só células
ignorantes contam vizinhos; com muitos espalhadores a população fica inativa
rápido. O speedup se mantém (3,9–4,4× processos; 3,9–4,7× p2p).

### E5 — Otimizações do kernel

Original 14,85 s; refatorado 4,24 s (3,5×); otimizado 1,99 s (7,5×). Kernel
otimizado + multiprocessing (1000², 20 ger.): 2,18× (p=2, eficiência 109%,
superlinear por efeito de cache), 5,11× (p=6), 5,67× (p=8). Combinando as
duas coisas, o tempo por célula fica ≈ 42× menor que o do código original.

### E6 — Modelo estendido

O kernel estendido custa 1,75× o base (3,86 s vs 2,20 s, 500², 10 ger.), mas
escala melhor: 4,52× (processos, p=6) e 4,53× (p2p) contra 3,65× / 3,80× do
base — mais cálculo por byte comunicado/sincronizado.

### E7 — Gargalo corrigido (memória compartilhada)

| p | acesso direto à shm (s) | cópia local faixa+halo (s) | ganho |
|---|---|---|---|
| 1 | 19,40 | 16,07 | 1,21× |
| 2 | 10,01 | 8,82 | 1,14× |
| 6 | 4,66 | 4,36 | 1,07× |
| 12 | 3,19 | 3,06 | 1,04× |

Indexar célula a célula um `memoryview` de memória compartilhada é mais lento
que um `bytearray` privado; copiar a faixa (O(h·W)) uma vez por geração resolve.

## 8. Comportamento do modelo e extensões

200², 3% inicial, limiar 2 (`experimentos/cenarios_modelo.py`):

| Cenário | Alcance (semente 42) | Média 10 sementes ± desvio |
|---|---|---|
| Original determinístico | 32,1% | — |
| Probabilístico p=0,85 | 24,2% | 23,6% ± 2,5 |
| + 1% influenciadores (peso 3) | 46,3% | 43,5% ± 3,7 |
| + 0,2% bots | 36,5% | 35,0% ± 2,8 |
| + 30% céticos (+2 no limiar) | 6,4% | 6,1% ± 0,2 |
| Combinado | 8,8% | 8,4% ± 0,3 |

* Probabilidade P(k) = 1 − (1 − p)^k: cada contato com espalhador é uma
  tentativa independente; o sorteio usa um gerador baseado em contador
  (SplitMix64; Salmon et al., 2011), por isso o resultado não depende da
  divisão da matriz.
* 1% de influenciadores quase dobra o alcance (Cha et al., 2010).
* Bots mantêm a propagação ativa indefinidamente (Shao et al., 2018).
* 30% de céticos reduzem o alcance para ~6%; a resistência domina mesmo com
  influenciadores e bots (Lewandowsky et al., 2012; van der Linden et al., 2017).

## 9. Gargalos e limitações

1. **GIL**: threads ficam 0,74× (mais lentas) no CPython 3.11.
2. **Hardware**: 6 núcleos físicos; Hyper-Threading rende pouco além disso.
3. **Custo fixo** de spawn/conexões (≈ 0,4–0,6 s) domina grades pequenas.
4. **Barreira global** por geração: o processo mais lento dita o ritmo. A
   distribuída p2p sem parada automática só sincroniza com vizinhos e por isso
   supera o multiprocessing nesta máquina.
5. **Rede real não medida**: experimentos em loopback; em LAN a latência
   (~0,1–1 ms por mensagem) somaria ~2 mensagens por geração — ainda pequena
   perto de ~180 ms de cálculo por geração por trabalhador (1000², p=6).
6. **Balanceamento estático**: adequado ao kernel de referência (carga
   uniforme); com o kernel otimizado a carga depende dos dados.
7. Python puro ≈ 1 milhão de células/s por núcleo.

## 10. Melhorias implementadas

1. Modelo probabilístico com gerador de contador (determinístico em qualquer partição).
2. Influenciadores digitais.
3. Bots automatizados.
4. Resistência à propagação (céticos).
5. Otimizações computacionais do núcleo (3,5× e 7,5×).
6. Redução de comunicação: topologia p2p + sobreposição cálculo/comunicação + TCP_NODELAY + mensagens binárias.
7. Cópia local faixa+halo no multiprocessing (gargalo medido e corrigido).
8. Visualização gráfica (GIF, mosaicos) e estatísticas adicionais (pico, geração do pico, alcance, taxa de crescimento, Monte Carlo com 10 sementes).
9. Testes automatizados de equivalência e métricas de Karp-Flatt.
