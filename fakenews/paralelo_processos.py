"""
paralelo_processos.py — Versão PARALELA com multiprocessing (paralelismo real).

Por que processos? No CPython 3.11 o GIL impede que threads executem código
Python simultaneamente. Cada processo tem seu próprio interpretador (e seu
próprio GIL), então N processos usam N núcleos de verdade. O enunciado
permite explicitamente o uso de `multiprocessing` no lugar de `threading`.

Divisão e sincronização (mesma lógica da versão com threads):
  * a matriz (com moldura) fica em MEMÓRIA COMPARTILHADA
    (multiprocessing.shared_memory) — dois buffers: geração par / ímpar;
  * o processo p calcula apenas as linhas [inicio, fim) da sua faixa;
  * multiprocessing.Barrier sincroniza o fim de cada geração;
  * as contagens parciais vão para um vetor compartilhado (RawArray) em
    posições exclusivas de cada processo -> sem locks;
  * todos os processos lêem a soma após a barreira e decidem igualmente se
    param (não há um "mestre" que precise avisar os demais).

Nenhuma cópia da matriz é trocada entre processos: a vizinhança de fronteira
é lida diretamente na memória compartilhada (custo de comunicação ~ zero;
o custo de sincronização é 1 barreira por geração).

Uso:
    python -m fakenews.paralelo_processos --processos 6 --linhas 1000 --colunas 1000
"""

import argparse
import multiprocessing as mp
import time
from multiprocessing import shared_memory

from . import modelo
from .modelo import Config, Contexto, Resultado


def _trabalhador(p, inicio, fim, n, cfg_dict, nomes, tam, barreira, contagens, tempos,
                 copia_local=True):
    """Código executado por CADA processo filho."""
    cfg = Config.de_dict(cfg_dict)
    shms = [shared_memory.SharedMemory(name=nome) for nome in nomes]
    buffers = [shms[0].buf[:tam], shms[1].buf[:tam]]   # memoryviews compartilhadas
    W, C = cfg.largura, cfg.colunas
    h = fim - inicio
    if copia_local:
        # OTIMIZAÇÃO (gargalo medido no experimento E1): acessar célula a
        # célula um memoryview de memória compartilhada é ~20% mais lento que
        # um bytearray local. Então, a cada geração, o processo copia SUA
        # faixa + 2 linhas de halo para um bytearray local (O(h·W), barato),
        # calcula localmente e grava de volta só as suas linhas.
        # É exatamente o mesmo esquema de halo da versão distribuída.
        lo, hi = inicio * W, (fim + 2) * W           # linhas com moldura inicio..fim+1
        tipos = bytes(shms[2].buf[lo:hi]) if cfg.estendido else None
        ctx = Contexto(cfg, tipos, deslocamento_linha=inicio)
        dst_local = bytearray(hi - lo)
        r0, r1 = 1, h + 1
    else:
        tipos = bytes(shms[2].buf[:tam]) if cfg.estendido else None  # só leitura
        ctx = Contexto(cfg, tipos)
        r0, r1 = inicio + 1, fim + 1
    src = dst = None
    try:
        barreira.wait()                       # todos prontos: começa a medição
        tempos[2 * p] = time.perf_counter()
        for g in range(cfg.geracoes):
            src, dst = buffers[g % 2], buffers[(g + 1) % 2]
            if copia_local:
                local = bytearray(src[lo:hi])                     # faixa + halo
                c = ctx.kernel(local, dst_local, W, C, r0, r1, ctx, g)
                dst[lo + W:hi - W] = dst_local[W:-W]              # só as minhas linhas
            else:
                c = ctx.kernel(src, dst, W, C, r0, r1, ctx, g)
            base = ((g + 1) * n + p) * 3      # posição exclusiva deste processo
            contagens[base], contagens[base + 1], contagens[base + 2] = c
            barreira.wait()                   # fim da geração g (sincronização global)
            if cfg.parar_sem_espalhadores:
                esp = sum(contagens[((g + 1) * n + q) * 3 + 1] for q in range(n))
                if esp == 0:
                    break
        tempos[2 * p + 1] = time.perf_counter()
    finally:
        del src, dst
        buffers.clear()                        # libera memoryviews antes de fechar
        for s in shms:
            s.close()


def executar(cfg: Config, n_proc: int = 4, verbose: bool = True,
             copia_local: bool = True) -> Resultado:
    """copia_local=False acessa a memória compartilhada diretamente no kernel
    (versão inicial, mantida para o experimento E7)."""
    t0 = time.perf_counter()
    grade, tipos = modelo.criar_estado(cfg)
    tam = len(grade)
    contagem_inicial = modelo.contar(modelo.remover_moldura(grade, cfg))

    # --- memória compartilhada: buffer A, buffer B e tipos -----------------
    shms = [shared_memory.SharedMemory(create=True, size=tam) for _ in range(3 if tipos else 2)]
    shms[0].buf[:tam] = grade
    shms[1].buf[:tam] = bytes(tam)
    if tipos:
        shms[2].buf[:tam] = tipos
    nomes = [s.name for s in shms]

    faixas = modelo.dividir_linhas(cfg.linhas, n_proc)
    n = len(faixas)
    ctxmp = mp.get_context("spawn")            # igual em Windows e Linux
    barreira = ctxmp.Barrier(n)
    contagens = ctxmp.RawArray("q", (cfg.geracoes + 1) * n * 3)
    tempos = ctxmp.RawArray("d", 2 * n)

    procs = [ctxmp.Process(target=_trabalhador, name=f"faixa-{p}",
                           args=(p, ini, fim, n, cfg.para_dict(), nomes, tam,
                                 barreira, contagens, tempos, copia_local))
             for p, (ini, fim) in enumerate(faixas)]
    try:
        for pr in procs:
            pr.start()
        for pr in procs:
            pr.join()
        if any(pr.exitcode != 0 for pr in procs):
            raise RuntimeError("um processo trabalhador falhou")
        t2 = time.perf_counter()

        # --- redução das contagens e montagem do histórico ------------------
        historico = [contagem_inicial]
        for g in range(1, cfg.geracoes + 1):
            c = tuple(sum(contagens[(g * n + q) * 3 + i] for q in range(n)) for i in range(3))
            historico.append(c)
            if verbose:
                modelo.imprimir_geracao(g, c)
            if cfg.parar_sem_espalhadores and c[1] == 0:
                if verbose:
                    print("\nA propagação terminou: não há mais espalhadores.")
                break
        feitas = len(historico) - 1
        final = modelo.remover_moldura(bytes(shms[feitas % 2].buf[:tam]), cfg)
    finally:
        for s in shms:
            s.close()
            s.unlink()

    inicio = min(tempos[2 * p] for p in range(n))
    fim = max(tempos[2 * p + 1] for p in range(n))
    return Resultado("processos", historico, final, tempo_total=t2 - t0,
                     tempo_computacao=fim - inicio, trabalhadores=n,
                     extras={"overhead_criacao_processos_s": (t2 - t0) - (fim - inicio)})


def main():
    p = argparse.ArgumentParser(description="Simulação PARALELA (multiprocessing) de fake news")
    modelo.adicionar_argumentos(p)
    p.add_argument("--processos", type=int, default=mp.cpu_count() // 2 or 1)
    p.add_argument("--sem-copia-local", action="store_true",
                   help="kernel lê/escreve direto na memória compartilhada (versão inicial)")
    a = p.parse_args()
    cfg = modelo.config_de_args(a)
    modelo.imprimir_cabecalho("SIMULAÇÃO PARALELA (MULTIPROCESSING)", cfg, a.processos)
    res = executar(cfg, a.processos, verbose=not a.quieto, copia_local=not a.sem_copia_local)
    modelo.imprimir_resumo(res, cfg)


if __name__ == "__main__":
    main()
