"""
distribuido.py — Versão DISTRIBUÍDA com sockets TCP.

Arquitetura
-----------
                     +-------------------+
                     |   COORDENADOR     |  cria a grade, divide em faixas,
                     |  (porta TCP P)    |  agrega contagens, decide parada,
                     +-------------------+  junta a grade final
                      /        |        \
             +----------+ +----------+ +----------+
             | trab. 0  |-| trab. 1  |-| trab. 2  |   (faixas de linhas)
             +----------+ +----------+ +----------+
                 troca de BORDAS (halo) entre vizinhos

Cada trabalhador recebe uma faixa de linhas [inicio, fim) MAIS duas linhas
extras ("halo"/linhas fantasmas): a última linha da faixa de cima e a
primeira da faixa de baixo. Para calcular a geração g+1 ele só precisa da
sua faixa e dessas 2 linhas. Depois de cada geração as linhas de borda
recém-calculadas são enviadas aos vizinhos (sincronização de fronteiras).

Duas topologias de comunicação (comparadas nos experimentos):
  * "estrela": cada trabalhador envia [contagens + 2 bordas] ao coordenador,
    que redistribui as bordas aos vizinhos e responde CONTINUA/PARA.
    Simples, mas o coordenador vira gargalo (2N mensagens por geração
    passando por um único nó).
  * "p2p" (padrão): as bordas vão DIRETAMENTE de vizinho para vizinho;
    o coordenador só recebe 3 inteiros (contagens) por trabalhador.
    Otimização adicional: as linhas de borda são calculadas PRIMEIRO e
    enviadas antes do miolo da faixa ser calculado -> a transmissão se
    sobrepõe ao cálculo (ocultação de latência). Se a parada automática
    estiver desligada, o trabalhador nem espera a resposta do coordenador.

Consistência: um trabalhador só inicia a geração g+1 depois de receber as
bordas da geração g de ambos os vizinhos (recv bloqueante) — isso equivale
a uma barreira local entre vizinhos. A decisão de parada é global (vem do
coordenador), então todos param na mesma geração.

Protocolo (sobre TCP): cada mensagem = 4 bytes de tamanho + 1 byte de tipo
('J' = JSON de controle, 'B' = bytes brutos de linhas da grade). Não usamos
pickle na rede (inseguro com máquinas não confiáveis).

Uso em várias máquinas:
    # máquina A (coordenador):
    python -m fakenews.distribuido coordenador --porta 5000 --trabalhadores 3 --linhas 1000 --colunas 1000
    # máquinas B, C, D (um por trabalhador):
    python -m fakenews.distribuido trabalhador --host IP_DA_MAQUINA_A --porta 5000

Uso local (coordenador + N trabalhadores como processos nesta máquina):
    python -m fakenews.distribuido local --trabalhadores 4 --linhas 500 --colunas 500
"""

import argparse
import json
import os
import socket
import struct
import subprocess
import sys
import time

from . import modelo
from .modelo import Config, Contexto, Resultado

_CAB = struct.Struct("!IB")      # tamanho (uint32) + tipo (uint8)
_CONT = struct.Struct("!qqq")    # contagens (ign, esp, ina)
J, B = ord("J"), ord("B")


# ---------------------------------------------------------------------------
# Funções de rede (enquadramento de mensagens sobre TCP)
# ---------------------------------------------------------------------------
def enviar(sock, tipo: int, dados: bytes) -> None:
    sock.sendall(_CAB.pack(len(dados), tipo) + dados)


def enviar_json(sock, obj) -> None:
    enviar(sock, J, json.dumps(obj).encode())


def receber_exato(sock, n: int) -> bytes:
    buf = bytearray(n)
    mv = memoryview(buf)
    lido = 0
    while lido < n:
        k = sock.recv_into(mv[lido:], n - lido)
        if k == 0:
            raise ConnectionError("conexão encerrada pelo par")
        lido += k
    return bytes(buf)


def receber(sock):
    tam, tipo = _CAB.unpack(receber_exato(sock, _CAB.size))
    dados = receber_exato(sock, tam)
    return (json.loads(dados) if tipo == J else dados), tipo


def _configurar(sock) -> None:
    # Desliga o algoritmo de Nagle: mensagens pequenas (bordas, contagens)
    # saem imediatamente, reduzindo a latência por geração.
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)


# ===========================================================================
# TRABALHADOR
# ===========================================================================
def trabalhador(host: str, porta: int, verbose: bool = False) -> None:
    # 1) Socket de escuta para o vizinho de cima se conectar (p2p).
    escuta = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    escuta.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    escuta.bind(("0.0.0.0", 0))
    escuta.listen(1)
    porta_p2p = escuta.getsockname()[1]

    # 2) Registro no coordenador.
    coord = socket.create_connection((host, porta))
    _configurar(coord)
    enviar_json(coord, {"porta_p2p": porta_p2p})

    # 3) Recebe tarefa: configuração, faixa, vizinhos e as linhas iniciais.
    tarefa, _ = receber(coord)
    cfg = Config.de_dict(tarefa["cfg"])
    rank, inicio, fim = tarefa["rank"], tarefa["inicio"], tarefa["fim"]
    topologia = tarefa["topologia"]
    W, C = cfg.largura, cfg.colunas
    h = fim - inicio                                   # linhas reais da faixa
    faixa, _ = receber(coord)                          # (h+2)*W bytes: halo+faixa+halo
    tipos = receber(coord)[0] if cfg.estendido else None
    atual, proximo = bytearray(faixa), bytearray(len(faixa))
    ctx = Contexto(cfg, tipos, deslocamento_linha=inicio)
    if verbose:
        print(f"[trab {rank}] linhas {inicio}..{fim - 1} ({h} linhas), topologia {topologia}")

    # 4) Conexões ponto a ponto com os vizinhos (somente p2p).
    #    Regra anti-deadlock: primeiro CONECTA ao vizinho de baixo (que já
    #    está escutando desde o passo 1) e depois ACEITA o de cima.
    cima = baixo = None
    if topologia == "p2p":
        if tarefa["baixo"]:
            baixo = socket.create_connection(tuple(tarefa["baixo"]))
            _configurar(baixo)
        if tarefa["cima"]:
            cima, _ = escuta.accept()
            _configurar(cima)
    escuta.close()
    enviar_json(coord, {"pronto": True})
    receber(coord)                                     # sinal de início (barreira global)

    t_calc = t_com = 0.0
    bytes_env = 0
    geracoes = 0
    k = ctx.kernel
    ultima = h * W                                     # offset da linha h (última real)
    for g in range(cfg.geracoes):
        t = time.perf_counter()
        if topologia == "p2p":
            # (a) calcula primeiro as bordas...
            c1 = k(atual, proximo, W, C, 1, 2, ctx, g)
            c2 = k(atual, proximo, W, C, h, h + 1, ctx, g) if h > 1 else (0, 0, 0)
            t2 = time.perf_counter(); t_calc += t2 - t
            # (b) ...envia aos vizinhos (vai pela rede enquanto calculamos o miolo)
            if cima:
                enviar(cima, B, bytes(proximo[W:2 * W])); bytes_env += W
            if baixo:
                enviar(baixo, B, bytes(proximo[ultima:ultima + W])); bytes_env += W
            t3 = time.perf_counter(); t_com += t3 - t2
            # (c) calcula o miolo da faixa
            c3 = k(atual, proximo, W, C, 2, h, ctx, g) if h > 2 else (0, 0, 0)
            t4 = time.perf_counter(); t_calc += t4 - t3
            # (d) recebe as bordas dos vizinhos -> linhas de halo da nova geração
            if cima:
                proximo[0:W] = receber(cima)[0]
            if baixo:
                proximo[ultima + W:ultima + 2 * W] = receber(baixo)[0]
            cont = tuple(a + b + c for a, b, c in zip(c1, c2, c3))
            enviar(coord, B, _CONT.pack(*cont))
            continua = True
            if cfg.parar_sem_espalhadores:              # espera decisão global
                continua = receber(coord)[0] == b"C"
            t_com += time.perf_counter() - t4
        else:  # ------------------------------ estrela ------------------------
            cont = k(atual, proximo, W, C, 1, h + 1, ctx, g)
            t2 = time.perf_counter(); t_calc += t2 - t
            enviar(coord, B, _CONT.pack(*cont) + bytes(proximo[W:2 * W])
                   + bytes(proximo[ultima:ultima + W]))
            bytes_env += 2 * W
            resp = receber(coord)[0]                    # flag + halo cima + halo baixo
            proximo[0:W] = resp[1:1 + W]
            proximo[ultima + W:ultima + 2 * W] = resp[1 + W:1 + 2 * W]
            continua = resp[0:1] == b"C"
            t_com += time.perf_counter() - t2
        atual, proximo = proximo, atual
        geracoes += 1
        if not continua:
            break

    # 5) Devolve a faixa final (sem halo) + métricas.
    enviar(coord, B, bytes(atual[W:(h + 1) * W]))
    enviar_json(coord, {"t_calc": t_calc, "t_com": t_com, "bytes_enviados": bytes_env,
                        "geracoes": geracoes})
    for s in (cima, baixo, coord):
        if s:
            s.close()


# ===========================================================================
# COORDENADOR
# ===========================================================================
def coordenador(cfg: Config, n: int, porta: int = 5000, topologia: str = "p2p",
                verbose: bool = True, servidor=None, ao_escutar=None) -> Resultado:
    t0 = time.perf_counter()
    if servidor is None:
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind(("0.0.0.0", porta))
        servidor.listen(n)
    if ao_escutar:
        ao_escutar()
    n = min(n, cfg.linhas)
    if verbose:
        print(f"[coord] aguardando {n} trabalhador(es) na porta {servidor.getsockname()[1]}...")

    # 1) Registro dos trabalhadores (rank = ordem de chegada).
    conns, enderecos = [], []
    for _ in range(n):
        s, addr = servidor.accept()
        _configurar(s)
        info, _ = receber(s)
        conns.append(s)
        enderecos.append([addr[0], info["porta_p2p"]])
        if verbose:
            print(f"[coord] trabalhador {len(conns) - 1} conectado de {addr[0]}")
    servidor.close()

    # 2) Cria o estado inicial e distribui as faixas (com halo).
    grade, tipos = modelo.criar_estado(cfg)
    contagem_inicial = modelo.contar(modelo.remover_moldura(grade, cfg))
    W = cfg.largura
    faixas = modelo.dividir_linhas(cfg.linhas, n)
    t_dist = time.perf_counter()
    for r, (ini, fim) in enumerate(faixas):
        enviar_json(conns[r], {
            "cfg": cfg.para_dict(), "rank": r, "inicio": ini, "fim": fim,
            "topologia": topologia,
            "cima": enderecos[r - 1] if r > 0 else None,
            "baixo": enderecos[r + 1] if r < n - 1 else None})
        # linhas com moldura ini .. fim+1  (= halo de cima, faixa, halo de baixo)
        enviar(conns[r], B, bytes(grade[ini * W:(fim + 2) * W]))
        if tipos:
            enviar(conns[r], B, bytes(tipos[ini * W:(fim + 2) * W]))
    for s in conns:
        receber(s)                                      # "pronto"
    t_dist = time.perf_counter() - t_dist

    # 3) Laço de gerações (o coordenador só agrega e decide).
    t1 = time.perf_counter()
    for s in conns:
        enviar_json(s, {"inicio": True})
    historico = [contagem_inicial]
    zero = bytes(W)
    for g in range(cfg.geracoes):
        if topologia == "p2p":
            parc = [_CONT.unpack(receber(s)[0]) for s in conns]
            cont = tuple(sum(p[i] for p in parc) for i in range(3))
            continua = not (cfg.parar_sem_espalhadores and cont[1] == 0)
            if cfg.parar_sem_espalhadores:
                for s in conns:
                    enviar(s, B, b"C" if continua else b"P")
        else:  # estrela: recebe bordas de todos e devolve os halos
            msgs = [receber(s)[0] for s in conns]
            parc = [_CONT.unpack(m[:_CONT.size]) for m in msgs]
            cont = tuple(sum(p[i] for p in parc) for i in range(3))
            continua = not (cfg.parar_sem_espalhadores and cont[1] == 0)
            flag = b"C" if continua else b"P"
            o = _CONT.size
            for r, s in enumerate(conns):
                halo_cima = msgs[r - 1][o + W:o + 2 * W] if r > 0 else zero   # última linha de r-1
                halo_baixo = msgs[r + 1][o:o + W] if r < n - 1 else zero      # 1ª linha de r+1
                enviar(s, B, flag + halo_cima + halo_baixo)
        historico.append(cont)
        if verbose:
            modelo.imprimir_geracao(g + 1, cont)
        if not continua:
            if verbose:
                print("\nA propagação terminou: não há mais espalhadores.")
            break

    # 4) Junta a grade final e as métricas.
    partes, metricas = [], []
    for s in conns:
        partes.append(receber(s)[0])
        metricas.append(receber(s)[0])
        s.close()
    t2 = time.perf_counter()
    final = modelo.remover_moldura(b"".join([bytes(W)] + partes + [bytes(W)]), cfg)
    extras = {
        "topologia": topologia,
        "t_distribuicao_inicial_s": t_dist,
        "t_calc_medio_s": sum(m["t_calc"] for m in metricas) / n,
        "t_com_medio_s": sum(m["t_com"] for m in metricas) / n,
        "t_calc_max_s": max(m["t_calc"] for m in metricas),
        "bytes_bordas_enviados": sum(m["bytes_enviados"] for m in metricas),
    }
    return Resultado(f"distribuido-{topologia}", historico, final, tempo_total=t2 - t0,
                     tempo_computacao=t2 - t1, trabalhadores=n, extras=extras)


# ===========================================================================
# Execução local: coordenador + N trabalhadores (processos) na mesma máquina
# ===========================================================================
def executar_local(cfg: Config, n: int = 4, topologia: str = "p2p",
                   verbose: bool = True) -> Resultado:
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.bind(("127.0.0.1", 0))                   # porta livre qualquer
    servidor.listen(n)
    porta = servidor.getsockname()[1]
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    procs = []

    def lancar():
        for _ in range(min(n, cfg.linhas)):
            procs.append(subprocess.Popen(
                [sys.executable, "-m", "fakenews.distribuido", "trabalhador",
                 "--host", "127.0.0.1", "--porta", str(porta)], cwd=raiz))
    try:
        res = coordenador(cfg, n, topologia=topologia, verbose=verbose,
                          servidor=servidor, ao_escutar=lancar)
    finally:
        for p in procs:
            try:
                p.wait(timeout=30)
            except subprocess.TimeoutExpired:
                p.kill()
    return res


def main():
    p = argparse.ArgumentParser(description="Simulação DISTRIBUÍDA (sockets) de fake news")
    sub = p.add_subparsers(dest="modo", required=True)

    pc = sub.add_parser("coordenador", help="inicia o coordenador")
    modelo.adicionar_argumentos(pc)
    pc.add_argument("--porta", type=int, default=5000)
    pc.add_argument("--trabalhadores", type=int, default=2)
    pc.add_argument("--topologia", choices=["p2p", "estrela"], default="p2p")

    pt = sub.add_parser("trabalhador", help="inicia um trabalhador")
    pt.add_argument("--host", default="127.0.0.1")
    pt.add_argument("--porta", type=int, default=5000)
    pt.add_argument("--verbose", action="store_true")

    pl = sub.add_parser("local", help="coordenador + N trabalhadores nesta máquina")
    modelo.adicionar_argumentos(pl)
    pl.add_argument("--trabalhadores", type=int, default=4)
    pl.add_argument("--topologia", choices=["p2p", "estrela"], default="p2p")

    a = p.parse_args()
    if a.modo == "trabalhador":
        trabalhador(a.host, a.porta, a.verbose)
        return
    cfg = modelo.config_de_args(a)
    modelo.imprimir_cabecalho(f"SIMULAÇÃO DISTRIBUÍDA (SOCKETS, {a.topologia.upper()})", cfg,
                              a.trabalhadores)
    if a.modo == "coordenador":
        res = coordenador(cfg, a.trabalhadores, a.porta, a.topologia, verbose=not a.quieto)
    else:
        res = executar_local(cfg, a.trabalhadores, a.topologia, verbose=not a.quieto)
    modelo.imprimir_resumo(res, cfg)


if __name__ == "__main__":
    main()
