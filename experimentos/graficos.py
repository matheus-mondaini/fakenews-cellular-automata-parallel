"""
graficos.py — Lê resultados.csv, calcula mediana, speedup, eficiência e
fração serial (Karp-Flatt), gera tabelas (Markdown) e gráficos (PNG).

    python experimentos/graficos.py [--csv experimentos/resultados/resultados.csv]

Definições:
    S(p) = T_seq / T_p                 (speedup)
    E(p) = S(p) / p                    (eficiência)
    e(p) = (1/S - 1/p) / (1 - 1/p)     (fração serial experimental, Karp & Flatt 1990)
T = mediana das repetições. "computação" = só o laço de gerações (inclui
sincronização e comunicação, exclui criação de processos/conexões);
"total" = inclui criação do estado, processos, conexões e distribuição.
"""

import argparse
import csv
import os
import statistics
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(RAIZ, "experimentos", "figuras")
RES = os.path.join(RAIZ, "experimentos", "resultados")

# Paleta categórica validada (ordem fixa; cor acompanha a versão, nunca o rank)
COR = {"processos": "#2a78d6", "p2p": "#eb6834", "estrela": "#1baf7a", "threads": "#eda100",
       "sequencial": "#52514e", "original": "#9a988f", "processos_direto": "#6250d6"}
NOME = {"processos": "Paralela (multiprocessing)", "p2p": "Distribuída p2p (sockets)",
        "estrela": "Distribuída estrela (sockets)", "threads": "Paralela (threads/GIL)",
        "sequencial": "Sequencial", "original": "Original (FakeNews.py)",
        "processos_direto": "Paralela (multiproc., acesso direto shm)"}
MARC = {"processos": "o", "p2p": "s", "estrela": "^", "threads": "D", "processos_direto": "v"}

plt.rcParams.update({
    "font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#8a8984", "axes.labelcolor": "#0b0b0b", "xtick.color": "#52514e",
    "ytick.color": "#52514e", "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": 0.8,
    "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "legend.frameon": False,
    "lines.linewidth": 2, "lines.markersize": 7, "savefig.facecolor": "#fcfcfb",
})


def carregar(caminho):
    grupos = defaultdict(list)
    assin = defaultdict(set)
    with open(caminho, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            k = (r["experimento"], r["versao"], int(r["trabalhadores"]), int(r["linhas"]),
                 int(r["geracoes"]), float(r["percentual"]), r["kernel"])
            grupos[k].append(r)
            assin[(r["experimento"], int(r["linhas"]), int(r["geracoes"]), float(r["percentual"]),
                   r["kernel"] if r["kernel"] == "estendido" else "base")].add(r["assinatura"])
    med = {}
    for k, rs in grupos.items():
        med[k] = {c: statistics.median(float(r[c]) for r in rs)
                  for c in ("tempo_total", "tempo_computacao", "t_calc_medio", "t_com_medio",
                            "t_calc_max", "bytes_bordas")}
        med[k]["reps"] = len(rs)
        med[k]["desvio"] = statistics.pstdev(float(r["tempo_computacao"]) for r in rs)
    return med, assin


def salvar(fig, nome):
    os.makedirs(FIG, exist_ok=True)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, nome), dpi=150)
    plt.close(fig)


def sel(med, exp, versao=None, **filtro):
    out = []
    for k, v in med.items():
        e, ver, n, L, G, pct, ker = k
        if e != exp or (versao and ver != versao):
            continue
        d = dict(versao=ver, n=n, L=L, G=G, pct=pct, kernel=ker, **v)
        if all(d[a] == b for a, b in filtro.items()):
            out.append(d)
    return sorted(out, key=lambda d: (d["n"], d["L"], d["G"], d["pct"]))


def kf(S, p):
    return (1 / S - 1 / p) / (1 - 1 / p) if p > 1 and S > 0 else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=os.path.join(RES, "resultados.csv"))
    a = ap.parse_args()
    med, assin = carregar(a.csv)
    md = ["# Tabelas de resultados (mediana das repetições)\n"]

    # ---------------- consistência ----------------
    inconsist = {k: v for k, v in assin.items() if len(v) > 1 and k[0] != "E5_kernel"}
    md.append(f"**Consistência:** {len(assin)} cenários; todas as versões produziram a mesma "
              f"assinatura SHA-256 em {len(assin) - len(inconsist)} deles"
              + ("." if not inconsist else f" — DIVERGÊNCIAS: {inconsist}") + "\n")

    # ---------------- E1 escalabilidade forte ----------------
    seq = sel(med, "E1_escalabilidade", "sequencial")
    if seq:
        Ts, Tst = seq[0]["tempo_computacao"], seq[0]["tempo_total"]
        L, G = seq[0]["L"], seq[0]["G"]
        md.append(f"\n## E1 — Escalabilidade forte ({L}x{L}, {G} gerações, 5%, limiar 2)\n")
        md.append(f"Sequencial: computação {Ts:.2f} s | total {Tst:.2f} s\n")
        md.append("| Versão | p | T comp (s) | T total (s) | Speedup comp | Eficiência | Speedup total | Karp-Flatt e |")
        md.append("|---|---|---|---|---|---|---|---|")
        fig1, ax1 = plt.subplots(figsize=(7.2, 4.4))
        fig2, ax2 = plt.subplots(figsize=(7.2, 4.4))
        fig3, ax3 = plt.subplots(figsize=(7.2, 4.4))
        nmax = 1
        for v in ("threads", "processos_direto", "processos", "p2p", "estrela"):
            d = sel(med, "E1_escalabilidade", v)
            if not d:
                continue
            ns = [x["n"] for x in d]
            nmax = max(nmax, max(ns))
            T = [x["tempo_computacao"] for x in d]
            S = [Ts / t for t in T]
            E = [s / n for s, n in zip(S, ns)]
            for x, s, e in zip(d, S, E):
                md.append(f"| {NOME[v]} | {x['n']} | {x['tempo_computacao']:.2f} | {x['tempo_total']:.2f} | "
                          f"{s:.2f} | {e * 100:.0f}% | {Tst / x['tempo_total']:.2f} | {kf(s, x['n']):.3f} |")
            kw = dict(color=COR[v], marker=MARC[v], label=NOME[v])
            ax1.plot(ns, T, **kw)
            ax2.plot(ns, S, **kw)
            ax3.plot(ns, [e * 100 for e in E], **kw)
            if v != "processos_direto":
                ax2.annotate(f"{S[-1]:.1f}x", (ns[-1], S[-1]), textcoords="offset points", xytext=(6, -3),
                             fontsize=9, color="#0b0b0b")
        ax1.axhline(Ts, color=COR["sequencial"], ls="--", lw=1.5, label="Sequencial")
        ax1.set(xlabel="threads / processos / trabalhadores (p)", ylabel="tempo de computação (s)",
                title=f"Tempo x paralelismo — {L}x{L}, {G} gerações")
        ax1.set_yscale("log")
        ax2.plot([1, nmax], [1, nmax], color="#b5b3ab", ls=":", lw=1.5, label="Ideal (linear)")
        ax2.axvline(6, color="#d3d1c8", lw=1)
        ax2.text(6.1, 0.3, "6 núcleos físicos", fontsize=8, color="#52514e")
        ax2.set(xlabel="p", ylabel="speedup  T_seq / T_p", title="Speedup (computação)")
        ax3.axhline(100, color="#b5b3ab", ls=":", lw=1.5)
        ax3.set(xlabel="p", ylabel="eficiência (%)", title="Eficiência  S(p) / p", ylim=(0, 110))
        for ax in (ax1, ax2, ax3):
            ax.legend(fontsize=9)
        salvar(fig1, "e1_tempo.png"); salvar(fig2, "e1_speedup.png"); salvar(fig3, "e1_eficiencia.png")

        # comunicação x cálculo (distribuída)
        fig, ax = plt.subplots(figsize=(7.6, 4.2))
        largura = 0.38
        md.append("\n### E1 — Cálculo x comunicação/espera por trabalhador (distribuída)\n")
        md.append("| Topologia | p | t cálculo médio (s) | t comunicação+espera médio (s) | % comunicação | bytes de borda enviados |")
        md.append("|---|---|---|---|---|---|")
        for i, v in enumerate(("p2p", "estrela")):
            d = [x for x in sel(med, "E1_escalabilidade", v) if x["n"] > 1]
            if not d:
                continue
            xs = [j + (i - 0.5) * largura for j in range(len(d))]
            calc = [x["t_calc_medio"] for x in d]
            com = [x["t_com_medio"] for x in d]
            ax.bar(xs, calc, largura * 0.92, color=COR[v], label=f"{v}: cálculo")
            ax.bar(xs, com, largura * 0.92, bottom=calc, color=COR[v], alpha=0.35, hatch="//",
                   edgecolor="#fcfcfb", label=f"{v}: comunicação + espera")
            for x in d:
                md.append(f"| {v} | {x['n']} | {x['t_calc_medio']:.3f} | {x['t_com_medio']:.3f} | "
                          f"{100 * x['t_com_medio'] / (x['t_calc_medio'] + x['t_com_medio']):.1f}% | "
                          f"{int(x['bytes_bordas']):,} |")
            ax.set_xticks(range(len(d)), [str(x["n"]) for x in d])
        ax.set(xlabel="trabalhadores", ylabel="tempo por trabalhador (s)",
               title="Distribuída: cálculo x comunicação (média por trabalhador)")
        ax.legend(fontsize=8, ncol=2)
        salvar(fig, "e1_comunicacao.png")

    # ---------------- E7 gargalo: memoryview compartilhado x cópia local ----------
    dd = {x["n"]: x for x in sel(med, "E1_escalabilidade", "processos_direto")}
    dl = {x["n"]: x for x in sel(med, "E1_escalabilidade", "processos")}
    if dd and dl and seq:
        md.append("\n## E7 — Gargalo corrigido: kernel direto na shared_memory x cópia local (faixa + halo)\n")
        md.append("| p | Direto T comp (s) | Cópia local T comp (s) | Ganho | Speedup direto | Speedup cópia local |")
        md.append("|---|---|---|---|---|---|")
        for n in sorted(set(dd) & set(dl)):
            a_, b_ = dd[n]["tempo_computacao"], dl[n]["tempo_computacao"]
            md.append(f"| {n} | {a_:.2f} | {b_:.2f} | {a_ / b_:.2f}x | {Ts / a_:.2f} | {Ts / b_:.2f} |")

    # ---------------- E2 tamanho ----------------
    d2 = sel(med, "E2_tamanho")
    if d2:
        md.append("\n## E2 — Variação do tamanho da matriz (10 gerações)\n")
        md.append("| N x N | Versão | p | T comp (s) | T total (s) | Speedup comp | Speedup total | Eficiência |")
        md.append("|---|---|---|---|---|---|---|---|")
        seqs = {x["L"]: x for x in sel(med, "E2_tamanho", "sequencial")}
        fig, (axa, axb) = plt.subplots(1, 2, figsize=(11, 4.2))
        for v in ("threads", "processos", "p2p", "estrela"):
            d = sel(med, "E2_tamanho", v)
            if not d:
                continue
            Ls = [x["L"] for x in d]
            S = [seqs[x["L"]]["tempo_computacao"] / x["tempo_computacao"] for x in d]
            St = [seqs[x["L"]]["tempo_total"] / x["tempo_total"] for x in d]
            for x, s, st in zip(d, S, St):
                md.append(f"| {x['L']} | {NOME[v]} | {x['n']} | {x['tempo_computacao']:.3f} | "
                          f"{x['tempo_total']:.3f} | {s:.2f} | {st:.2f} | {s / x['n'] * 100:.0f}% |")
            axa.plot(Ls, S, color=COR[v], marker=MARC[v], label=f"{NOME[v]} (p={d[0]['n']})")
            axb.plot(Ls, St, color=COR[v], marker=MARC[v], label=f"{NOME[v]} (p={d[0]['n']})")
        for L, x in sorted(seqs.items()):
            md.append(f"| {L} | Sequencial | 1 | {x['tempo_computacao']:.3f} | {x['tempo_total']:.3f} | 1.00 | 1.00 | 100% |")
        axa.set(xlabel="lado da matriz N (N x N)", ylabel="speedup", title="Speedup (só computação)")
        axb.set(xlabel="lado da matriz N (N x N)", ylabel="speedup",
                title="Speedup (total: inclui criação de processos/conexões)")
        for ax in (axa, axb):
            ax.set_xscale("log"); ax.minorticks_off(); ax.set_xticks(sorted(seqs), [str(s) for s in sorted(seqs)])
            ax.axhline(1, color="#b5b3ab", ls=":")
        axa.legend(fontsize=8)
        salvar(fig, "e2_tamanho.png")

    # ---------------- E3 gerações ----------------
    d3 = sel(med, "E3_geracoes")
    if d3:
        md.append("\n## E3 — Variação do número de gerações\n")
        md.append("| Gerações | Versão | p | T comp (s) | T total (s) | Speedup comp | Speedup total |")
        md.append("|---|---|---|---|---|---|---|")
        seqs = {x["G"]: x for x in sel(med, "E3_geracoes", "sequencial")}
        fig, ax = plt.subplots(figsize=(7.2, 4.2))
        for v in ("processos", "p2p", "estrela"):
            d = sel(med, "E3_geracoes", v)
            Gs = [x["G"] for x in d]
            S = [seqs[x["G"]]["tempo_computacao"] / x["tempo_computacao"] for x in d]
            St = [seqs[x["G"]]["tempo_total"] / x["tempo_total"] for x in d]
            for x, s, st in zip(d, S, St):
                md.append(f"| {x['G']} | {NOME[v]} | {x['n']} | {x['tempo_computacao']:.2f} | "
                          f"{x['tempo_total']:.2f} | {s:.2f} | {st:.2f} |")
            ax.plot(Gs, St, color=COR[v], marker=MARC[v], label=f"{NOME[v]} — total")
            ax.plot(Gs, S, color=COR[v], marker=MARC[v], ls="--", alpha=0.55, label=f"{NOME[v]} — computação")
        for G, x in sorted(seqs.items()):
            md.append(f"| {G} | Sequencial | 1 | {x['tempo_computacao']:.2f} | {x['tempo_total']:.2f} | 1.00 | 1.00 |")
        ax.set(xlabel="número de gerações", ylabel="speedup",
               title="Amortização do custo fixo (processos/conexões)")
        ax.legend(fontsize=8)
        salvar(fig, "e3_geracoes.png")

    # ---------------- E4 percentual ----------------
    d4 = sel(med, "E4_percentual")
    if d4:
        md.append("\n## E4 — Variação do percentual inicial de espalhadores (10 gerações)\n")
        md.append("| % inicial | Versão | p | T comp (s) | Speedup comp |")
        md.append("|---|---|---|---|---|")
        seqs = {x["pct"]: x for x in sel(med, "E4_percentual", "sequencial")}
        fig, (axa, axb) = plt.subplots(1, 2, figsize=(11, 4.2))
        ps = sorted(seqs)
        axa.bar([f"{p * 100:.0f}%" for p in ps], [seqs[p]["tempo_computacao"] for p in ps],
                color=COR["sequencial"], width=0.55)
        axa.set(xlabel="espalhadores iniciais", ylabel="tempo sequencial (s)",
                title="Custo sequencial x densidade inicial")
        for p in ps:
            md.append(f"| {p * 100:.0f}% | Sequencial | 1 | {seqs[p]['tempo_computacao']:.2f} | 1.00 |")
        for v in ("processos", "p2p"):
            d = sel(med, "E4_percentual", v)
            S = [seqs[x["pct"]]["tempo_computacao"] / x["tempo_computacao"] for x in d]
            for x, s in zip(d, S):
                md.append(f"| {x['pct'] * 100:.0f}% | {NOME[v]} | {x['n']} | {x['tempo_computacao']:.2f} | {s:.2f} |")
            axb.plot([f"{x['pct'] * 100:.0f}%" for x in d], S, color=COR[v], marker=MARC[v],
                     label=f"{NOME[v]} (p={d[0]['n']})")
        axb.set(xlabel="espalhadores iniciais", ylabel="speedup", title="Speedup x densidade inicial",
                ylim=(0, None))
        axb.legend(fontsize=8)
        salvar(fig, "e4_percentual.png")

    # ---------------- E5 kernel ----------------
    d5 = sel(med, "E5_kernel")
    if d5:
        md.append("\n## E5 — Otimizações do núcleo sequencial\n")
        md.append("| Implementação | T comp (s) | Ganho sobre o original |")
        md.append("|---|---|---|")
        orig = [x for x in d5 if x["versao"] == "original"][0]["tempo_computacao"]
        rot = {"original": "Original (listas + deepcopy)", "referencia": "Refatorado (bytearray + moldura + buffer duplo)",
               "otimizado": "Otimizado (somas por coluna + pulo de linhas)"}
        itens = [("original", orig)] + [(x["kernel"], x["tempo_computacao"]) for x in d5 if x["versao"] == "sequencial"]
        for k, t in itens:
            md.append(f"| {rot[k]} | {t:.2f} | {orig / t:.1f}x |")
        fig, ax = plt.subplots(figsize=(7.6, 3.6))
        cores = ["#9a988f", "#52514e", "#2a78d6"]
        ax.barh([rot[k] for k, _ in itens][::-1], [t for _, t in itens][::-1], color=cores[:len(itens)][::-1], height=0.5)
        for i, (k, t) in enumerate(itens[::-1]):
            ax.text(t, i, f"  {t:.1f} s ({orig / t:.1f}x)", va="center", fontsize=9)
        ax.set(xlabel="tempo (s)", title=f"Núcleo sequencial — {d5[0]['L']}x{d5[0]['L']}, {d5[0]['G']} gerações")
        ax.set_xlim(0, orig * 1.3)
        ax.grid(axis="y", visible=False)
        salvar(fig, "e5_kernel.png")
    d5b = sel(med, "E5_kernel_otim_escala")
    if d5b:
        Ts = [x for x in d5b if x["versao"] == "sequencial"][0]["tempo_computacao"]
        md.append("\n### E5b — Kernel otimizado + multiprocessing\n")
        md.append("| p | T comp (s) | Speedup | Eficiência |")
        md.append("|---|---|---|---|")
        for x in [x for x in d5b if x["versao"] != "processos_direto"]:
            md.append(f"| {x['n']} | {x['tempo_computacao']:.3f} | {Ts / x['tempo_computacao']:.2f} | "
                      f"{Ts / x['tempo_computacao'] / x['n'] * 100:.0f}% |")

    # ---------------- E6 estendido ----------------
    d6 = sel(med, "E6_estendido")
    if d6:
        md.append("\n## E6 — Custo do modelo estendido (probabilidade, influenciadores, bots, céticos)\n")
        md.append("| Modelo | Versão | p | T comp (s) | Speedup |")
        md.append("|---|---|---|---|---|")
        for ker in ("referencia", "estendido"):
            Ts = [x for x in d6 if x["kernel"] == ker and x["versao"] == "sequencial"][0]["tempo_computacao"]
            for x in [x for x in d6 if x["kernel"] == ker]:
                md.append(f"| {'base' if ker == 'referencia' else 'estendido'} | {NOME[x['versao']]} | {x['n']} | "
                          f"{x['tempo_computacao']:.2f} | {Ts / x['tempo_computacao']:.2f} |")

    with open(os.path.join(RES, "tabelas.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
