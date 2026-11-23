"""
benchmark.py — Executa os experimentos de desempenho e grava CSV.

Para cada cenário as versões sequencial, threads, processos e distribuída
(p2p e estrela) são executadas `--reps` vezes; cada linha do CSV é UMA
execução. A análise (mediana, speedup, eficiência) é feita em graficos.py.

Todos os experimentos de desempenho usam `parar_sem_espalhadores=False`
para que TODAS as gerações sejam calculadas (carga de trabalho fixa e
comparável). Cada execução também grava a assinatura SHA-256 da grade final,
o que permite conferir que todas as versões chegaram ao mesmo resultado.

Uso (na raiz do projeto):
    python experimentos/benchmark.py --reps 3            # completo (~40 min)
    python experimentos/benchmark.py --rapido --reps 1   # versão curta (~3 min)
"""

import argparse
import csv
import json
import os
import platform
import subprocess
import sys
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import FakeNews as original  # noqa: E402
from fakenews import sequencial, paralelo_threads, paralelo_processos, distribuido  # noqa: E402
from fakenews.modelo import Config, Resultado  # noqa: E402

RES_DIR = os.path.join(RAIZ, "experimentos", "resultados")
CAMPOS = ["experimento", "versao", "trabalhadores", "linhas", "colunas", "geracoes", "percentual",
          "limiar", "kernel", "rep", "tempo_total", "tempo_computacao", "t_calc_medio", "t_com_medio",
          "t_calc_max", "bytes_bordas", "assinatura"]


def rodar(versao: str, cfg: Config, n: int) -> Resultado:
    if versao == "sequencial":
        return sequencial.executar(cfg, verbose=False)
    if versao == "threads":
        return paralelo_threads.executar(cfg, n, verbose=False)
    if versao == "processos":            # versão final: cópia local da faixa + halo
        return paralelo_processos.executar(cfg, n, verbose=False)
    if versao == "processos_direto":     # versão inicial: kernel direto na shared_memory
        return paralelo_processos.executar(cfg, n, verbose=False, copia_local=False)
    if versao in ("p2p", "estrela"):
        return distribuido.executar_local(cfg, n, versao, verbose=False)
    if versao == "original":                     # FakeNews.py (deepcopy, lista de listas)
        t0 = time.perf_counter()
        g = original.criar_grade(cfg.linhas, cfg.colunas, cfg.percentual_espalhadores, cfg.semente)
        t1 = time.perf_counter()
        for _ in range(cfg.geracoes):
            g = original.proxima_geracao(g, cfg.limiar_convencimento)
            original.contar_estados(g)
        t2 = time.perf_counter()
        return Resultado("original", [], bytes(v for row in g for v in row), t2 - t0, t2 - t1)
    raise ValueError(versao)


class Gravador:
    def __init__(self, caminho):
        novo = not os.path.exists(caminho)
        self.f = open(caminho, "a", newline="", encoding="utf-8")
        self.w = csv.DictWriter(self.f, fieldnames=CAMPOS)
        if novo:
            self.w.writeheader()

    def gravar(self, exp, versao, n, cfg, rep, r: Resultado):
        e = r.extras
        self.w.writerow({
            "experimento": exp, "versao": versao, "trabalhadores": n, "linhas": cfg.linhas,
            "colunas": cfg.colunas, "geracoes": cfg.geracoes, "percentual": cfg.percentual_espalhadores,
            "limiar": cfg.limiar_convencimento, "kernel": "estendido" if cfg.estendido else cfg.kernel,
            "rep": rep, "tempo_total": f"{r.tempo_total:.5f}", "tempo_computacao": f"{r.tempo_computacao:.5f}",
            "t_calc_medio": f"{e.get('t_calc_medio_s', 0):.5f}", "t_com_medio": f"{e.get('t_com_medio_s', 0):.5f}",
            "t_calc_max": f"{e.get('t_calc_max_s', 0):.5f}", "bytes_bordas": e.get("bytes_bordas_enviados", 0),
            "assinatura": r.assinatura})
        self.f.flush()


def base(**kw) -> Config:
    d = dict(linhas=1000, colunas=1000, geracoes=20, percentual_espalhadores=0.05,
             limiar_convencimento=2, parar_sem_espalhadores=False, kernel="referencia")
    d.update(kw)
    return Config(**d)


def plano(rapido: bool):
    """Lista de (experimento, versao, n, cfg)."""
    P = []
    if rapido:
        tam, ns, tams = 400, [1, 2, 4], [150, 300, 400]
    else:
        tam, ns, tams = 1000, [1, 2, 4, 6, 8, 12], [250, 500, 1000, 2000]
    G = 20 if not rapido else 10
    # E1 — escalabilidade forte: tamanho fixo, varia nº de threads/processos/hosts
    c = base(linhas=tam, colunas=tam, geracoes=G)
    P.append(("E1_escalabilidade", "sequencial", 1, c))
    for n in ns:
        if n <= 8:
            P.append(("E1_escalabilidade", "threads", n, c))
        for v in ("processos", "p2p", "estrela"):
            P.append(("E1_escalabilidade", v, n, c))
    # E2 — tamanho da matriz
    nmax = 6 if not rapido else 4
    for t in tams:
        c = base(linhas=t, colunas=t, geracoes=10)
        P.append(("E2_tamanho", "sequencial", 1, c))
        P.append(("E2_tamanho", "threads", 4, c))
        for v in ("processos", "p2p", "estrela"):
            P.append(("E2_tamanho", v, nmax, c))
    # E3 — número de gerações
    for g in ([5, 10, 20, 40] if not rapido else [5, 10, 20]):
        c = base(linhas=tam, colunas=tam, geracoes=g)
        for v, n in (("sequencial", 1), ("processos", nmax), ("p2p", nmax), ("estrela", nmax)):
            P.append(("E3_geracoes", v, n, c))
    # E4 — percentual inicial de espalhadores
    for pct in (0.01, 0.05, 0.20, 0.50):
        c = base(linhas=tam, colunas=tam, geracoes=10, percentual_espalhadores=pct)
        for v, n in (("sequencial", 1), ("processos", nmax), ("p2p", nmax)):
            P.append(("E4_percentual", v, n, c))
    # E5 — otimizações do kernel (original x referência x otimizado)
    t5 = 500 if not rapido else 200
    c = base(linhas=t5, colunas=t5, geracoes=20)
    P.append(("E5_kernel", "original", 1, c))
    P.append(("E5_kernel", "sequencial", 1, c))
    P.append(("E5_kernel", "sequencial", 1, base(linhas=t5, colunas=t5, geracoes=20, kernel="otimizado")))
    co = base(linhas=tam, colunas=tam, geracoes=G, kernel="otimizado")
    P.append(("E5_kernel_otim_escala", "sequencial", 1, co))
    for n in ns[1:]:
        if n <= 8:
            P.append(("E5_kernel_otim_escala", "processos", n, co))
    # E6 — custo do modelo estendido
    ce = base(linhas=t5, colunas=t5, geracoes=10, prob_convencimento=0.5, frac_influenciadores=0.01,
              frac_bots=0.002, frac_ceticos=0.2)
    cb = base(linhas=t5, colunas=t5, geracoes=10)
    for v, n in (("sequencial", 1), ("processos", nmax), ("p2p", nmax)):
        P.append(("E6_estendido", v, n, cb))
        P.append(("E6_estendido", v, n, ce))
    return P


def ambiente() -> dict:
    info = {"python": sys.version, "implementacao": platform.python_implementation(),
            "so": platform.platform(), "processador": platform.processor(),
            "nucleos_logicos": os.cpu_count()}
    if sys.platform == "win32":
        try:
            ps = ("$p=Get-CimInstance Win32_Processor; $c=Get-CimInstance Win32_ComputerSystem; "
                  "$o=Get-CimInstance Win32_OperatingSystem; "
                  "\"$($p.Name)|$($p.NumberOfCores)|$($p.NumberOfLogicalProcessors)|$($p.MaxClockSpeed)|"
                  "$([math]::Round($c.TotalPhysicalMemory/1GB,1))|$($o.Caption) $($o.Version)\"")
            s = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True,
                               text=True, timeout=60).stdout.strip().split("|")
            info.update({"cpu": s[0], "nucleos_fisicos": int(s[1]), "nucleos_logicos": int(s[2]),
                         "clock_mhz": int(s[3]), "ram_gb": float(s[4]), "so": s[5]})
        except Exception as e:  # pragma: no cover
            info["erro_coleta"] = str(e)
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--rapido", action="store_true")
    ap.add_argument("--saida", default=None)
    ap.add_argument("--somente", default=None, help="prefixo de experimento (ex.: E1)")
    ap.add_argument("--versoes", default=None, help="lista separada por vírgula (ex.: processos)")
    a = ap.parse_args()
    os.makedirs(RES_DIR, exist_ok=True)
    saida = a.saida or os.path.join(RES_DIR, "resultados_rapido.csv" if a.rapido else "resultados.csv")
    with open(os.path.join(RES_DIR, "ambiente.json"), "w", encoding="utf-8") as f:
        json.dump(ambiente(), f, indent=2, ensure_ascii=False)

    P = [p for p in plano(a.rapido) if not a.somente or p[0].startswith(a.somente)]
    if a.versoes:
        P = [p for p in P if p[1] in a.versoes.split(",")]
    g = Gravador(saida)
    t0 = time.time()
    # Repetições intercaladas (rep 0 de tudo, depois rep 1...) para diluir
    # efeitos de aquecimento/térmicos entre versões.
    for rep in range(a.reps):
        for i, (exp, v, n, cfg) in enumerate(P):
            r = rodar(v, cfg, n)
            g.gravar(exp, v, n, cfg, rep, r)
            print(f"[{time.time() - t0:7.1f}s] rep {rep} {i + 1}/{len(P)} {exp:22s} {v:10s} n={n:<2d} "
                  f"{cfg.linhas}x{cfg.colunas} g={cfg.geracoes} p={cfg.percentual_espalhadores} "
                  f"-> {r.tempo_computacao:8.3f}s (total {r.tempo_total:.3f}s) {r.assinatura}", flush=True)
    print("concluído em", round(time.time() - t0, 1), "s ->", saida)


if __name__ == "__main__":
    main()
