# Tabelas de resultados (mediana das repetições)

**Consistência:** 17 cenários; todas as versões produziram a mesma assinatura SHA-256 em 17 deles.


## E1 — Escalabilidade forte (1000x1000, 20 gerações, 5%, limiar 2)

Sequencial: computação 16.27 s | total 16.35 s

| Versão | p | T comp (s) | T total (s) | Speedup comp | Eficiência | Speedup total | Karp-Flatt e |
|---|---|---|---|---|---|---|---|
| Paralela (threads/GIL) | 1 | 17.30 | 17.44 | 0.94 | 94% | 0.94 | nan |
| Paralela (threads/GIL) | 2 | 21.23 | 21.35 | 0.77 | 38% | 0.77 | 1.610 |
| Paralela (threads/GIL) | 4 | 22.02 | 22.16 | 0.74 | 18% | 0.74 | 1.472 |
| Paralela (threads/GIL) | 6 | 21.93 | 22.07 | 0.74 | 12% | 0.74 | 1.418 |
| Paralela (threads/GIL) | 8 | 21.29 | 21.39 | 0.76 | 10% | 0.76 | 1.353 |
| Paralela (multiproc., acesso direto shm) | 1 | 19.40 | 19.89 | 0.84 | 84% | 0.82 | nan |
| Paralela (multiproc., acesso direto shm) | 2 | 10.01 | 10.61 | 1.62 | 81% | 1.54 | 0.231 |
| Paralela (multiproc., acesso direto shm) | 4 | 5.83 | 6.48 | 2.79 | 70% | 2.52 | 0.144 |
| Paralela (multiproc., acesso direto shm) | 6 | 4.66 | 5.36 | 3.49 | 58% | 3.05 | 0.144 |
| Paralela (multiproc., acesso direto shm) | 8 | 3.99 | 4.88 | 4.07 | 51% | 3.35 | 0.138 |
| Paralela (multiproc., acesso direto shm) | 12 | 3.19 | 4.18 | 5.09 | 42% | 3.91 | 0.123 |
| Paralela (multiprocessing) | 1 | 16.07 | 16.64 | 1.01 | 101% | 0.98 | nan |
| Paralela (multiprocessing) | 2 | 8.82 | 9.44 | 1.84 | 92% | 1.73 | 0.085 |
| Paralela (multiprocessing) | 4 | 5.28 | 5.85 | 3.08 | 77% | 2.79 | 0.099 |
| Paralela (multiprocessing) | 6 | 4.36 | 5.02 | 3.73 | 62% | 3.26 | 0.121 |
| Paralela (multiprocessing) | 8 | 3.52 | 4.35 | 4.62 | 58% | 3.76 | 0.104 |
| Paralela (multiprocessing) | 12 | 3.06 | 4.15 | 5.32 | 44% | 3.94 | 0.114 |
| Distribuída p2p (sockets) | 1 | 16.37 | 16.86 | 0.99 | 99% | 0.97 | nan |
| Distribuída p2p (sockets) | 2 | 8.70 | 9.15 | 1.87 | 93% | 1.79 | 0.070 |
| Distribuída p2p (sockets) | 4 | 5.13 | 5.57 | 3.17 | 79% | 2.94 | 0.087 |
| Distribuída p2p (sockets) | 6 | 3.85 | 4.36 | 4.22 | 70% | 3.75 | 0.084 |
| Distribuída p2p (sockets) | 8 | 3.36 | 3.90 | 4.85 | 61% | 4.19 | 0.093 |
| Distribuída p2p (sockets) | 12 | 2.70 | 3.44 | 6.01 | 50% | 4.76 | 0.090 |
| Distribuída estrela (sockets) | 1 | 16.41 | 16.90 | 0.99 | 99% | 0.97 | nan |
| Distribuída estrela (sockets) | 2 | 9.41 | 9.89 | 1.73 | 86% | 1.65 | 0.157 |
| Distribuída estrela (sockets) | 4 | 5.29 | 5.72 | 3.07 | 77% | 2.86 | 0.101 |
| Distribuída estrela (sockets) | 6 | 3.94 | 4.47 | 4.12 | 69% | 3.65 | 0.091 |
| Distribuída estrela (sockets) | 8 | 3.53 | 4.14 | 4.61 | 58% | 3.95 | 0.105 |
| Distribuída estrela (sockets) | 12 | 2.83 | 3.54 | 5.75 | 48% | 4.62 | 0.099 |

### E1 — Cálculo x comunicação/espera por trabalhador (distribuída)

| Topologia | p | t cálculo médio (s) | t comunicação+espera médio (s) | % comunicação | bytes de borda enviados |
|---|---|---|---|---|---|
| p2p | 2 | 8.667 | 0.004 | 0.0% | 40,080 |
| p2p | 4 | 4.921 | 0.020 | 0.4% | 120,240 |
| p2p | 6 | 3.602 | 0.064 | 1.7% | 200,400 |
| p2p | 8 | 3.225 | 0.028 | 0.9% | 280,560 |
| p2p | 12 | 2.586 | 0.021 | 0.8% | 440,880 |
| estrela | 2 | 8.830 | 0.572 | 6.1% | 80,160 |
| estrela | 4 | 4.800 | 0.438 | 8.4% | 160,320 |
| estrela | 6 | 3.450 | 0.513 | 13.0% | 240,480 |
| estrela | 8 | 3.165 | 0.362 | 10.3% | 320,640 |
| estrela | 12 | 2.556 | 0.194 | 7.0% | 480,960 |

## E7 — Gargalo corrigido: kernel direto na shared_memory x cópia local (faixa + halo)

| p | Direto T comp (s) | Cópia local T comp (s) | Ganho | Speedup direto | Speedup cópia local |
|---|---|---|---|---|---|
| 1 | 19.40 | 16.07 | 1.21x | 0.84 | 1.01 |
| 2 | 10.01 | 8.82 | 1.14x | 1.62 | 1.84 |
| 4 | 5.83 | 5.28 | 1.10x | 2.79 | 3.08 |
| 6 | 4.66 | 4.36 | 1.07x | 3.49 | 3.73 |
| 8 | 3.99 | 3.52 | 1.13x | 4.07 | 4.62 |
| 12 | 3.19 | 3.06 | 1.04x | 5.09 | 5.32 |

## E2 — Variação do tamanho da matriz (10 gerações)

| N x N | Versão | p | T comp (s) | T total (s) | Speedup comp | Speedup total | Eficiência |
|---|---|---|---|---|---|---|---|
| 250 | Paralela (threads/GIL) | 4 | 0.786 | 0.790 | 0.64 | 0.64 | 16% |
| 500 | Paralela (threads/GIL) | 4 | 3.275 | 3.298 | 0.71 | 0.71 | 18% |
| 1000 | Paralela (threads/GIL) | 4 | 12.128 | 12.291 | 0.80 | 0.80 | 20% |
| 2000 | Paralela (threads/GIL) | 4 | 46.909 | 47.353 | 0.82 | 0.82 | 20% |
| 250 | Paralela (multiprocessing) | 6 | 0.187 | 0.778 | 2.67 | 0.65 | 44% |
| 500 | Paralela (multiprocessing) | 6 | 0.602 | 1.197 | 3.87 | 1.97 | 64% |
| 1000 | Paralela (multiprocessing) | 6 | 2.294 | 2.967 | 4.22 | 3.30 | 70% |
| 2000 | Paralela (multiprocessing) | 6 | 9.010 | 10.000 | 4.26 | 3.88 | 71% |
| 250 | Distribuída p2p (sockets) | 6 | 0.145 | 0.527 | 3.44 | 0.96 | 57% |
| 500 | Distribuída p2p (sockets) | 6 | 0.593 | 1.056 | 3.93 | 2.23 | 65% |
| 1000 | Distribuída p2p (sockets) | 6 | 2.480 | 3.004 | 3.91 | 3.26 | 65% |
| 2000 | Distribuída p2p (sockets) | 6 | 9.111 | 9.861 | 4.21 | 3.93 | 70% |
| 250 | Distribuída estrela (sockets) | 6 | 0.144 | 0.514 | 3.46 | 0.98 | 58% |
| 500 | Distribuída estrela (sockets) | 6 | 0.621 | 1.059 | 3.75 | 2.23 | 62% |
| 1000 | Distribuída estrela (sockets) | 6 | 2.617 | 3.146 | 3.70 | 3.11 | 62% |
| 2000 | Distribuída estrela (sockets) | 6 | 9.304 | 10.192 | 4.13 | 3.81 | 69% |
| 250 | Sequencial | 1 | 0.499 | 0.504 | 1.00 | 1.00 | 100% |
| 500 | Sequencial | 1 | 2.328 | 2.357 | 1.00 | 1.00 | 100% |
| 1000 | Sequencial | 1 | 9.687 | 9.794 | 1.00 | 1.00 | 100% |
| 2000 | Sequencial | 1 | 38.387 | 38.792 | 1.00 | 1.00 | 100% |

## E3 — Variação do número de gerações

| Gerações | Versão | p | T comp (s) | T total (s) | Speedup comp | Speedup total |
|---|---|---|---|---|---|---|
| 5 | Paralela (multiprocessing) | 6 | 1.27 | 1.94 | 4.84 | 3.23 |
| 10 | Paralela (multiprocessing) | 6 | 2.30 | 2.98 | 4.54 | 3.54 |
| 20 | Paralela (multiprocessing) | 6 | 4.14 | 4.77 | 4.20 | 3.67 |
| 40 | Paralela (multiprocessing) | 6 | 7.31 | 7.98 | 4.38 | 4.02 |
| 5 | Distribuída p2p (sockets) | 6 | 1.24 | 1.74 | 4.93 | 3.60 |
| 10 | Distribuída p2p (sockets) | 6 | 2.33 | 2.80 | 4.47 | 3.78 |
| 20 | Distribuída p2p (sockets) | 6 | 3.82 | 4.31 | 4.55 | 4.06 |
| 40 | Distribuída p2p (sockets) | 6 | 6.99 | 7.49 | 4.57 | 4.28 |
| 5 | Distribuída estrela (sockets) | 6 | 1.49 | 1.99 | 4.11 | 3.14 |
| 10 | Distribuída estrela (sockets) | 6 | 2.33 | 2.82 | 4.49 | 3.75 |
| 20 | Distribuída estrela (sockets) | 6 | 4.23 | 4.77 | 4.11 | 3.67 |
| 40 | Distribuída estrela (sockets) | 6 | 6.98 | 7.46 | 4.58 | 4.30 |
| 5 | Sequencial | 1 | 6.14 | 6.26 | 1.00 | 1.00 |
| 10 | Sequencial | 1 | 10.44 | 10.56 | 1.00 | 1.00 |
| 20 | Sequencial | 1 | 17.38 | 17.48 | 1.00 | 1.00 |
| 40 | Sequencial | 1 | 31.97 | 32.08 | 1.00 | 1.00 |

## E4 — Variação do percentual inicial de espalhadores (10 gerações)

| % inicial | Versão | p | T comp (s) | Speedup comp |
|---|---|---|---|---|
| 1% | Sequencial | 1 | 12.59 | 1.00 |
| 5% | Sequencial | 1 | 10.62 | 1.00 |
| 20% | Sequencial | 1 | 3.88 | 1.00 |
| 50% | Sequencial | 1 | 2.57 | 1.00 |
| 1% | Paralela (multiprocessing) | 6 | 2.98 | 4.23 |
| 5% | Paralela (multiprocessing) | 6 | 2.44 | 4.35 |
| 20% | Paralela (multiprocessing) | 6 | 0.88 | 4.39 |
| 50% | Paralela (multiprocessing) | 6 | 0.65 | 3.92 |
| 1% | Distribuída p2p (sockets) | 6 | 2.89 | 4.36 |
| 5% | Distribuída p2p (sockets) | 6 | 2.27 | 4.67 |
| 20% | Distribuída p2p (sockets) | 6 | 0.91 | 4.29 |
| 50% | Distribuída p2p (sockets) | 6 | 0.66 | 3.90 |

## E5 — Otimizações do núcleo sequencial

| Implementação | T comp (s) | Ganho sobre o original |
|---|---|---|
| Original (listas + deepcopy) | 14.85 | 1.0x |
| Refatorado (bytearray + moldura + buffer duplo) | 4.24 | 3.5x |
| Otimizado (somas por coluna + pulo de linhas) | 1.99 | 7.5x |

### E5b — Kernel otimizado + multiprocessing

| p | T comp (s) | Speedup | Eficiência |
|---|---|---|---|
| 1 | 7.914 | 1.00 | 100% |
| 2 | 3.633 | 2.18 | 109% |
| 4 | 2.024 | 3.91 | 98% |
| 6 | 1.548 | 5.11 | 85% |
| 8 | 1.395 | 5.67 | 71% |

## E6 — Custo do modelo estendido (probabilidade, influenciadores, bots, céticos)

| Modelo | Versão | p | T comp (s) | Speedup |
|---|---|---|---|---|
| base | Sequencial | 1 | 2.20 | 1.00 |
| base | Paralela (multiproc., acesso direto shm) | 6 | 0.72 | 3.08 |
| base | Distribuída p2p (sockets) | 6 | 0.58 | 3.80 |
| base | Paralela (multiprocessing) | 6 | 0.60 | 3.65 |
| estendido | Sequencial | 1 | 3.86 | 1.00 |
| estendido | Paralela (multiproc., acesso direto shm) | 6 | 0.97 | 3.98 |
| estendido | Distribuída p2p (sockets) | 6 | 0.85 | 4.53 |
| estendido | Paralela (multiprocessing) | 6 | 0.85 | 4.52 |
