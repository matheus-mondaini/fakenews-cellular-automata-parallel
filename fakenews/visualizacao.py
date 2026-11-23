"""
visualizacao.py — Visualização gráfica (EXTENSÃO).

  * GIF animado da grade ao longo das gerações (Pillow);
  * mosaico PNG com algumas gerações;
  * gráfico da evolução de ignorantes/espalhadores/inativos (matplotlib).

matplotlib/Pillow são usados SÓ para desenhar; nenhum cálculo da simulação
passa por eles (requisito do trabalho).

Uso:
    python -m fakenews.visualizacao --linhas 200 --colunas 200 --geracoes 40 \
        --percentual 0.01 --limiar 2 --saida figuras/animacao.gif
"""

import argparse
import os

from . import modelo
from .modelo import Config, Contexto

# cores (R, G, B): ignorante, espalhador, inativo
CORES = {modelo.IGNORANTE: (235, 235, 228), modelo.ESPALHADOR: (214, 39, 40),
         modelo.INATIVO: (31, 78, 140)}


def quadros(cfg: Config):
    """Gera (geração, grade_sem_moldura) da geração 0 até o fim."""
    grade, tipos = modelo.criar_estado(cfg)
    ctx = Contexto(cfg, tipos)
    atual, prox = grade, bytearray(len(grade))
    yield 0, modelo.remover_moldura(atual, cfg)
    for g in range(cfg.geracoes):
        c = ctx.kernel(atual, prox, cfg.largura, cfg.colunas, 1, cfg.linhas + 1, ctx, g)
        atual, prox = prox, atual
        yield g + 1, modelo.remover_moldura(atual, cfg)
        if cfg.parar_sem_espalhadores and c[1] == 0:
            break


def para_imagem(grade: bytes, cfg: Config, escala: int = 3):
    from PIL import Image
    pal = bytearray(b"\x00" * 768)
    for est, (r, g, b) in CORES.items():
        pal[est * 3:est * 3 + 3] = bytes((r, g, b))
    img = Image.frombytes("P", (cfg.colunas, cfg.linhas), grade)
    img.putpalette(bytes(pal))
    return img.resize((cfg.colunas * escala, cfg.linhas * escala), Image.NEAREST)


def salvar_gif(cfg: Config, saida: str, escala: int = 3, ms: int = 120):
    imgs = [para_imagem(g, cfg, escala).convert("RGB") for _, g in quadros(cfg)]
    os.makedirs(os.path.dirname(os.path.abspath(saida)), exist_ok=True)
    imgs[0].save(saida, save_all=True, append_images=imgs[1:], duration=ms, loop=0)
    return len(imgs)


def salvar_mosaico(cfg: Config, saida: str, geracoes=(0, 2, 5, 10, 20, 40), titulo=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    cmap = ListedColormap([tuple(c / 255 for c in CORES[e]) for e in range(3)])
    alvo = set(geracoes)
    sel = [(g, q) for g, q in quadros(cfg) if g in alvo]
    fig, axs = plt.subplots(1, len(sel), figsize=(2.6 * len(sel), 2.9))
    for ax, (g, q) in zip(axs, sel):
        linhas = [list(q[i * cfg.colunas:(i + 1) * cfg.colunas]) for i in range(cfg.linhas)]
        ax.imshow(linhas, cmap=cmap, vmin=0, vmax=2, interpolation="nearest")
        ax.set_title(f"Geração {g}", fontsize=10)
        ax.axis("off")
    if titulo:
        fig.suptitle(titulo, fontsize=11)
    fig.tight_layout()
    fig.savefig(saida, dpi=130)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser(description="Gera GIF animado da propagação")
    modelo.adicionar_argumentos(p)
    p.add_argument("--saida", default="figuras/animacao.gif")
    p.add_argument("--escala", type=int, default=3)
    a = p.parse_args()
    cfg = modelo.config_de_args(a)
    n = salvar_gif(cfg, a.saida, a.escala)
    print(f"GIF com {n} quadros salvo em {a.saida}")


if __name__ == "__main__":
    main()
