"""
sequencial.py — Versão sequencial REFATORADA.

Fluxo (igual ao original):
    criar grade -> para cada geração: calcular próxima geração (lendo só a
    grade atual) -> contar estados -> imprimir -> parar se não houver
    espalhadores -> resultado final.

Diferenças em relação a FakeNews.py (mesmo resultado, ver testes):
    * grade achatada com moldura (sem testes de limite);
    * buffer duplo em vez de deepcopy a cada geração;
    * contagem de estados feita junto com o cálculo;
    * suporte às extensões do modelo e ao kernel otimizado.

Uso:
    python -m fakenews.sequencial --linhas 100 --colunas 100 --geracoes 50
"""

import argparse
import time

from . import modelo
from .modelo import Config, Contexto, Resultado


def executar(cfg: Config, verbose: bool = True) -> Resultado:
    t0 = time.perf_counter()
    grade, tipos = modelo.criar_estado(cfg)
    ctx = Contexto(cfg, tipos)
    W, C, L = cfg.largura, cfg.colunas, cfg.linhas

    # Buffer duplo: atual (leitura) e proximo (escrita). A moldura de ambos
    # permanece 0 para sempre, porque o kernel nunca a escreve.
    atual, proximo = grade, bytearray(len(grade))
    historico = [modelo.contar(modelo.remover_moldura(atual, cfg))]

    t1 = time.perf_counter()
    for g in range(cfg.geracoes):
        # A geração inteira é UMA faixa: linhas 1..L (com moldura).
        contagem = ctx.kernel(atual, proximo, W, C, 1, L + 1, ctx, g)
        atual, proximo = proximo, atual                 # troca de buffers O(1)
        historico.append(contagem)
        if verbose:
            modelo.imprimir_geracao(g + 1, contagem)
        if cfg.parar_sem_espalhadores and contagem[1] == 0:
            if verbose:
                print("\nA propagação terminou: não há mais espalhadores.")
            break
    t2 = time.perf_counter()

    return Resultado("sequencial", historico, modelo.remover_moldura(atual, cfg),
                     tempo_total=t2 - t0, tempo_computacao=t2 - t1)


def main():
    p = argparse.ArgumentParser(description="Simulação SEQUENCIAL de propagação de fake news")
    modelo.adicionar_argumentos(p)
    a = p.parse_args()
    cfg = modelo.config_de_args(a)
    modelo.imprimir_cabecalho("SIMULAÇÃO SEQUENCIAL DE PROPAGAÇÃO DE FAKE NEWS", cfg)
    res = executar(cfg, verbose=not a.quieto)
    modelo.imprimir_resumo(res, cfg)


if __name__ == "__main__":
    main()
