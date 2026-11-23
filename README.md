# Propagação de Fake News — Sequencial, Paralela e Distribuída

**Grupo 05** — Carlos Haruhiko Iwata Junior (1632752) · Leonardo Freitas dos Santos (2465302) · Matheus Mondaini Alegre de Miranda (2504219) · Vinicius Henrique de Oliveira Silva (2525925)

Trabalho prático de EC48A (Sistemas Distribuídos / Desenvolvimento Paralelo e
Distribuído) — UTFPR. Simulação, por autômato celular com vizinhança de Moore,
da propagação de uma fake news numa população representada por uma matriz.

Estados: `0 = Ignorante`, `1 = Espalhador`, `2 = Inativo`.
Regra base (igual ao código fornecido): ignorante com ≥ *limiar* vizinhos
espalhadores vira espalhador; espalhador vira inativo; inativo continua inativo.

## Estrutura

```
fake_news/
├── FakeNews.py                  # código sequencial ORIGINAL (preservado, usado nos testes)
├── fakenews/                    # pacote com todas as versões
│   ├── modelo.py                # núcleo comum: grade, kernels, extensões, estatísticas
│   ├── sequencial.py            # versão sequencial refatorada
│   ├── paralelo_threads.py      # paralela: threading.Thread + Barrier
│   ├── paralelo_processos.py    # paralela: multiprocessing + shared_memory + Barrier
│   ├── distribuido.py           # distribuída: sockets TCP (coordenador/trabalhadores)
│   └── visualizacao.py          # GIF/mosaicos da grade
├── tests/test_equivalencia.py   # prova que todas as versões dão o MESMO resultado
├── experimentos/
│   ├── benchmark.py             # roda os experimentos -> resultados/resultados.csv
│   ├── graficos.py              # mediana, speedup, eficiência, Karp-Flatt -> figuras/ + tabelas.md
│   ├── cenarios_modelo.py       # comportamento do modelo e das extensões
│   ├── resultados/              # CSV, tabelas.md, ambiente.json, logs
│   └── figuras/                 # gráficos PNG e animação GIF
├── docs/
│   ├── apresentacao.html / .pdf # slides
│   ├── RELATORIO.md             # análise completa dos resultados
│   ├── ROTEIRO_VIDEO.md         # roteiro do vídeo (10–15 min)
│   └── REFERENCIAS.md           # referências bibliográficas
└── README.md
```

## Requisitos

* Python ≥ 3.9 (testado em CPython 3.11.5, Windows 10).
* **Nenhuma dependência para a simulação** (só biblioteca padrão).
* `matplotlib` e `Pillow` apenas para gráficos/GIF (`pip install matplotlib pillow`).

Todos os comandos abaixo são executados **na pasta `fake_news/`**.

## Como executar

### Sequencial
```powershell
python -m fakenews.sequencial --linhas 100 --colunas 100 --geracoes 50 --percentual 0.05 --limiar 3
```
(`python FakeNews.py` continua rodando o código original.)

### Paralela — threads
```powershell
python -m fakenews.paralelo_threads --threads 4 --linhas 500 --colunas 500 --geracoes 20 --limiar 2 --sem-parada
```

### Paralela — processos (paralelismo real)
```powershell
python -m fakenews.paralelo_processos --processos 6 --linhas 1000 --colunas 1000 --geracoes 20 --limiar 2 --sem-parada --quieto
```

### Distribuída — sockets
Tudo na mesma máquina (o coordenador lança os trabalhadores como processos):
```powershell
python -m fakenews.distribuido local --trabalhadores 4 --topologia p2p --linhas 1000 --colunas 1000 --geracoes 20 --limiar 2 --sem-parada --quieto
```
Em várias máquinas (mesma rede; liberar a porta no firewall):
```powershell
# máquina do coordenador
python -m fakenews.distribuido coordenador --porta 5000 --trabalhadores 3 --linhas 1000 --colunas 1000 --geracoes 20 --limiar 2
# em cada máquina trabalhadora
python -m fakenews.distribuido trabalhador --host IP_DO_COORDENADOR --porta 5000
```
`--topologia estrela` faz as bordas passarem pelo coordenador (para comparação).

### Opções comuns
| Opção | Significado | Padrão |
|---|---|---|
| `--linhas`, `--colunas` | tamanho da matriz | 100 |
| `--geracoes` | máximo de gerações | 50 |
| `--percentual` | fração inicial de espalhadores | 0.05 |
| `--limiar` | vizinhos espalhadores necessários | 3 |
| `--semente` | semente aleatória | 42 |
| `--kernel referencia\|otimizado` | núcleo de cálculo do modelo base | referencia |
| `--sem-parada` | não para quando zera espalhadores (carga fixa) | — |
| `--quieto` | não imprime cada geração | — |
| `--prob P` | **extensão:** prob. de convencimento por contato | 1.0 |
| `--influenciadores F --peso-influenciador K` | **extensão:** fração de influenciadores e seu peso | 0 / 3 |
| `--bots F` | **extensão:** fração de bots (espalham sempre) | 0 |
| `--ceticos F --resistencia R` | **extensão:** fração de céticos e limiar extra | 0 / 2 |

Exemplo do modelo estendido (funciona igual em todas as versões):
```powershell
python -m fakenews.distribuido local --trabalhadores 3 --linhas 200 --colunas 200 --geracoes 60 --percentual 0.01 --limiar 2 --prob 0.6 --influenciadores 0.01 --bots 0.002 --ceticos 0.3
```

### Visualização
```powershell
python -m fakenews.visualizacao --linhas 200 --colunas 200 --geracoes 60 --percentual 0.01 --limiar 2 --saida experimentos/figuras/minha_animacao.gif
```

## Testes de equivalência
```powershell
python -m unittest discover -s tests -v
```
Verificam que: a grade inicial é igual à do `FakeNews.py`; a versão sequencial
(kernel de referência e otimizado) reproduz o `FakeNews.py`; threads,
processos e distribuída (p2p e estrela, 1..N trabalhadores, inclusive mais
trabalhadores que linhas) produzem **grade final e histórico idênticos** ao
sequencial — também no modelo estendido probabilístico.

## Reproduzir os experimentos
```powershell
python experimentos/benchmark.py --reps 3
python experimentos/graficos.py
python experimentos/cenarios_modelo.py
```
(`--rapido --reps 1` gera uma versão curta em ~3 min.)

## Uso de IA generativa
Este projeto utilizou o assistente Claude (Anthropic) como apoio na
estruturação do código, nos scripts de experimento e na redação da
documentação, conforme permitido no enunciado. Ver `docs/REFERENCIAS.md`.
