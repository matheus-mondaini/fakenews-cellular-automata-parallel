"""
paralelo_threads.py — Versão PARALELA com threads (threading.Thread).

Divisão do trabalho
-------------------
A matriz é dividida em N faixas horizontais contíguas (decomposição por
blocos de linhas). A thread t calcula SOMENTE as linhas da sua faixa.

Consistência entre gerações / ausência de condições de corrida
--------------------------------------------------------------
  * Buffer duplo compartilhado: na geração g todas as threads LÊEM o buffer
    g%2 e ESCREVEM no buffer (g+1)%2. Como cada thread escreve apenas nas
    suas linhas (faixas disjuntas), não há escrita concorrente na mesma
    posição. Leituras das linhas vizinhas (fronteira) são feitas no buffer
    de leitura, que ninguém altera durante a geração.
  * Uma barreira (threading.Barrier) ao final de cada geração garante que
    ninguém começa a geração g+1 (que vai SOBRESCREVER o buffer lido em g)
    antes de todas terminarem a geração g.
  * Cada thread grava suas contagens numa posição exclusiva do histórico
    (historico[g][t]); após a barreira todas lêem a soma — e todas tomam a
    MESMA decisão de parada, sem precisar de lock.

Limitação esperada (CPython 3.11): o GIL (Global Interpreter Lock) só permite
que uma thread execute bytecode Python por vez. Esta versão é correta e
demonstra a sincronização, mas NÃO acelera um laço CPU-bound em CPython com
GIL. Para paralelismo real usamos paralelo_processos.py (multiprocessing),
permitido no enunciado. Em Python 3.13t (free-threaded, PEP 703) este mesmo
código passa a escalar.

Uso:
    python -m fakenews.paralelo_threads --threads 4 --linhas 500 --colunas 500
"""

import argparse
import threading
import time

from . import modelo
from .modelo import Config, Contexto, Resultado


def executar(cfg: Config, n_threads: int = 4, verbose: bool = True) -> Resultado:
    t0 = time.perf_counter()
    grade, tipos = modelo.criar_estado(cfg)
    ctx = Contexto(cfg, tipos)
    W, C, L = cfg.largura, cfg.colunas, cfg.linhas

    contagem_inicial = modelo.contar(modelo.remover_moldura(grade, cfg))
    buffers = [grade, bytearray(len(grade))]           # buffer duplo compartilhado
    faixas = modelo.dividir_linhas(L, n_threads)
    n = len(faixas)
    # parciais[g][t] = (ign, esp, ina) da thread t na geração g (posição exclusiva)
    parciais = [[None] * n for _ in range(cfg.geracoes + 1)]
    barreira = threading.Barrier(n)
    geracoes_feitas = [0] * n
    erros = []

    def trabalhador(t: int, inicio: int, fim: int):
        try:
            r0, r1 = inicio + 1, fim + 1                # linhas com moldura
            for g in range(cfg.geracoes):
                src, dst = buffers[g % 2], buffers[(g + 1) % 2]
                parciais[g + 1][t] = ctx.kernel(src, dst, W, C, r0, r1, ctx, g)
                barreira.wait()                         # fim da geração g
                geracoes_feitas[t] = g + 1
                if cfg.parar_sem_espalhadores and sum(p[1] for p in parciais[g + 1]) == 0:
                    break                                # decisão idêntica em todas
        except Exception as e:                           # pragma: no cover
            erros.append(e)
            barreira.abort()

    threads = [threading.Thread(target=trabalhador, args=(t, ini, fim), name=f"faixa-{t}")
               for t, (ini, fim) in enumerate(faixas)]
    t1 = time.perf_counter()
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    t2 = time.perf_counter()
    if erros:
        raise erros[0]

    # Redução das contagens parciais (feita depois, fora da região crítica)
    feitas = geracoes_feitas[0]
    historico = [contagem_inicial]
    for g in range(1, feitas + 1):
        historico.append(tuple(sum(p[i] for p in parciais[g]) for i in range(3)))
        if verbose:
            modelo.imprimir_geracao(g, historico[-1])
    if verbose and cfg.parar_sem_espalhadores and historico[-1][1] == 0:
        print("\nA propagação terminou: não há mais espalhadores.")

    final = buffers[feitas % 2]
    return Resultado("threads", historico, modelo.remover_moldura(final, cfg),
                     tempo_total=t2 - t0, tempo_computacao=t2 - t1, trabalhadores=n)


def main():
    p = argparse.ArgumentParser(description="Simulação PARALELA (threads) de fake news")
    modelo.adicionar_argumentos(p)
    p.add_argument("--threads", type=int, default=4)
    a = p.parse_args()
    cfg = modelo.config_de_args(a)
    modelo.imprimir_cabecalho("SIMULAÇÃO PARALELA (THREADS)", cfg, a.threads)
    res = executar(cfg, a.threads, verbose=not a.quieto)
    modelo.imprimir_resumo(res, cfg)


if __name__ == "__main__":
    main()
