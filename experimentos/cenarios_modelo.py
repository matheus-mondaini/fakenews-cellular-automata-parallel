"""
cenarios_modelo.py — Análise do COMPORTAMENTO do modelo (não de desempenho).

Compara o modelo original com as extensões propostas (probabilidade de
convencimento, influenciadores, bots, céticos) e gera:
  * figuras/modelo_espalhadores.png  — espalhadores por geração
  * figuras/modelo_alcance.png       — % da população atingida por cenário
  * figuras/mosaico_base.png / mosaico_estendido.png — snapshots da grade
  * figuras/animacao.gif             — animação do cenário estendido
  * resultados/cenarios_modelo.md    — tabela com estatísticas adicionais

Inclui também uma análise probabilística simples: o cenário probabilístico é
repetido com 10 sementes e reportamos média e desvio-padrão do alcance.

    python experimentos/cenarios_modelo.py
"""

import os
import statistics
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from fakenews import sequencial, visualizacao, modelo  # noqa: E402
from fakenews.modelo import Config  # noqa: E402

FIG = os.path.join(RAIZ, "experimentos", "figuras")
RES = os.path.join(RAIZ, "experimentos", "resultados")
L = 200
BASE = dict(linhas=L, colunas=L, geracoes=80, percentual_espalhadores=0.03, limiar_convencimento=2,
            kernel="otimizado", parar_sem_espalhadores=True)

CENARIOS = [  # (nome, cor da paleta validada, parâmetros extras)
    ("Original (determinístico)", "#52514e", {}),
    ("Probabilístico p=0,85", "#2a78d6", dict(prob_convencimento=0.85)),
    ("+ 1% influenciadores (peso 3)", "#eb6834", dict(prob_convencimento=0.85, frac_influenciadores=0.01)),
    ("+ 0,2% bots", "#1baf7a", dict(prob_convencimento=0.85, frac_bots=0.002)),
    ("+ 30% céticos (+2 limiar)", "#eda100", dict(prob_convencimento=0.85, frac_ceticos=0.30)),
    ("Combinado (infl.+bots+céticos)", "#e87ba4", dict(prob_convencimento=0.85, frac_influenciadores=0.01,
                                                       frac_bots=0.002, frac_ceticos=0.30)),
]


def main():
    os.makedirs(FIG, exist_ok=True)
    total = L * L
    linhas_md = ["# Comportamento do modelo — cenários (grade 200x200, 3% inicial, limiar 2)\n",
                 "| Cenário | Pico de espalhadores | Geração do pico | Alcance final | Gerações | Taxa média de crescimento |",
                 "|---|---|---|---|---|---|"]
    fig, ax = plt.subplots(figsize=(8, 4.4))
    alcances = []
    for nome, cor, extra in CENARIOS:
        cfg = Config(**BASE, **extra)
        r = sequencial.executar(cfg, verbose=False)
        est = modelo.estatisticas(r.historico, total)
        alcances.append((nome, cor, est["alcance_final_%"]))
        esp = [h[1] for h in r.historico]
        ax.plot(range(len(esp)), [e / total * 100 for e in esp], color=cor, label=nome)
        linhas_md.append(f"| {nome} | {est['pico_espalhadores']:,} | {est['geracao_pico']} | "
                         f"{est['alcance_final_%']:.1f}% | {est['geracoes_executadas']} | "
                         f"{est['taxa_crescimento_media']:.2f} |")
        print(nome, est, flush=True)
    ax.set(xlabel="geração", ylabel="espalhadores (% da população)",
           title="Espalhadores ativos por geração — modelo original x extensões")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "modelo_espalhadores.png"), dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 3.8))
    nomes = [a[0] for a in alcances][::-1]
    ax.barh(nomes, [a[2] for a in alcances][::-1], color=[a[1] for a in alcances][::-1], height=0.55)
    for i, a in enumerate(alcances[::-1]):
        ax.text(a[2], i, f"  {a[2]:.1f}%", va="center", fontsize=9)
    ax.set(xlabel="alcance final (% que recebeu a fake news)", xlim=(0, 115),
           title="Alcance final por cenário")
    ax.grid(axis="y", visible=False)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "modelo_alcance.png"), dpi=150); plt.close(fig)

    # --- análise probabilística: 10 sementes ---
    linhas_md.append("\n## Análise probabilística (10 sementes)\n")
    linhas_md.append("| Cenário | Alcance médio | Desvio-padrão | Mín | Máx |")
    linhas_md.append("|---|---|---|---|---|")
    for nome, _, extra in CENARIOS[1:]:
        vals = []
        for s in range(10):
            cfg = Config(**{**BASE, "semente": 100 + s}, **extra)
            r = sequencial.executar(cfg, verbose=False)
            vals.append(modelo.estatisticas(r.historico, total)["alcance_final_%"])
        linhas_md.append(f"| {nome} | {statistics.mean(vals):.1f}% | {statistics.pstdev(vals):.1f} | "
                         f"{min(vals):.1f}% | {max(vals):.1f}% |")
        print(nome, "alcance médio", round(statistics.mean(vals), 1), flush=True)

    # --- visualizações da grade ---
    base = Config(**BASE)
    visualizacao.salvar_mosaico(base, os.path.join(FIG, "mosaico_base.png"),
                                (0, 3, 8, 15, 25, 40), "Modelo original — 200x200, 3% inicial, limiar 2")
    est = Config(**BASE, **CENARIOS[-1][2])
    visualizacao.salvar_mosaico(est, os.path.join(FIG, "mosaico_estendido.png"),
                                (0, 3, 8, 15, 25, 40), "Modelo estendido combinado (p=0,85, influenciadores, bots, céticos)")
    n = visualizacao.salvar_gif(est, os.path.join(FIG, "animacao.gif"), escala=2)
    print("GIF:", n, "quadros")
    with open(os.path.join(RES, "cenarios_modelo.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(linhas_md) + "\n")


if __name__ == "__main__":
    main()
