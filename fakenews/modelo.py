"""
modelo.py — Núcleo compartilhado por TODAS as versões (sequencial, paralela
e distribuída).

Ideia central do projeto
------------------------
Para que as versões paralela e distribuída "preservem o comportamento lógico
da versão sequencial", todas chamam exatamente as mesmas funções de cálculo
(os *kernels* deste arquivo). A única diferença entre as versões é QUEM
executa cada faixa de linhas e COMO as faixas se sincronizam.

Representação da grade (otimização em relação ao original)
-----------------------------------------------------------
O código original usa lista de listas + `deepcopy` a cada geração e testa os
limites da matriz para cada vizinho. Aqui usamos:

  * um único `bytearray` "achatado" (1 byte por pessoa), com
  * uma moldura de células-fantasma (ghost cells) sempre IGNORANTES ao redor
    da matriz. Assim os 8 vizinhos de qualquer célula real existem e o teste
    `0 <= ni < linhas` desaparece do laço interno;
  * buffer duplo (origem/destino) — a geração g é lida de um buffer e escrita
    no outro, eliminando o `deepcopy` e a atualização "ao vivo";
  * contagem de estados feita DENTRO do kernel (evita uma 2ª varredura).

Layout com moldura: a grade real L x C vira (L+2) x (C+2) = (L+2) x W.
A célula real (i, j) (0-based) fica no índice  (i+1)*W + (j+1).

Essa mesma moldura é o que, nas versões distribuídas, vira a "linha de halo"
(fronteira) recebida dos vizinhos.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, asdict, field

# ---------------------------------------------------------------------------
# Estados (iguais ao código original)
# ---------------------------------------------------------------------------
IGNORANTE = 0
ESPALHADOR = 1
INATIVO = 2

# ---------------------------------------------------------------------------
# Tipos de indivíduo (EXTENSÃO do modelo — ver README/slides)
# ---------------------------------------------------------------------------
NORMAL = 0
INFLUENCIADOR = 1   # seu compartilhamento "pesa" mais (peso_influenciador)
BOT = 2             # conta automatizada: espalha SEMPRE, nunca fica inativa
CETICO = 3          # resistente: precisa de mais vizinhos para ser convencido

# Tabelas de tradução de bytes (operação nativa, sequencial, de bytes):
#   _T_ESP : 1 -> 1, demais -> 0      (indicador "é espalhador?")
#   _T_ENV : 1 -> 2, demais iguais    (espalhador envelhece para inativo)
_T_ESP = bytes(1 if b == ESPALHADOR else 0 for b in range(256))
_T_ENV = bytes(INATIVO if b == ESPALHADOR else b for b in range(256))

_MASK64 = (1 << 64) - 1


# ---------------------------------------------------------------------------
# Configuração da simulação
# ---------------------------------------------------------------------------
@dataclass
class Config:
    """Todos os parâmetros de uma execução (serializável em JSON para a
    versão distribuída)."""

    linhas: int = 100
    colunas: int = 100
    geracoes: int = 50
    percentual_espalhadores: float = 0.02
    limiar_convencimento: int = 2
    semente: int = 42
    # 'referencia' = laço célula a célula fiel ao original
    # 'otimizado'  = somas por coluna + pulo de linhas sem espalhadores
    kernel: str = "referencia"
    # Igual ao original: para quando não há mais espalhadores.
    # Nos experimentos de desempenho usamos False para fixar a carga.
    parar_sem_espalhadores: bool = True

    # ---------------- Extensões do modelo (desligadas por padrão) ----------
    prob_convencimento: float = 1.0      # p por vizinho espalhador
    frac_influenciadores: float = 0.0
    peso_influenciador: int = 3
    frac_bots: float = 0.0
    frac_ceticos: float = 0.0
    resistencia_cetico: int = 2          # limiar extra dos céticos

    @property
    def estendido(self) -> bool:
        """True se alguma extensão estiver ativa (usa o kernel estendido)."""
        return (self.prob_convencimento < 1.0 or self.frac_influenciadores > 0
                or self.frac_bots > 0 or self.frac_ceticos > 0)

    @property
    def largura(self) -> int:
        """Largura W da linha com moldura (C + 2)."""
        return self.colunas + 2

    def para_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def de_dict(d: dict) -> "Config":
        return Config(**d)


# ---------------------------------------------------------------------------
# Resultado de uma execução
# ---------------------------------------------------------------------------
@dataclass
class Resultado:
    versao: str
    historico: list                   # [(ign, esp, ina)] por geração (g=0 inicial)
    grade_final: bytes                # grade SEM moldura (L*C bytes)
    tempo_total: float                # inclui criação de threads/processos/rede
    tempo_computacao: float           # só o laço de gerações
    trabalhadores: int = 1
    extras: dict = field(default_factory=dict)  # tempos de comunicação etc.

    @property
    def geracoes_executadas(self) -> int:
        return len(self.historico) - 1

    @property
    def assinatura(self) -> str:
        """SHA-256 da grade final: usada para provar equivalência entre versões."""
        return hashlib.sha256(self.grade_final).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Criação do estado inicial
# ---------------------------------------------------------------------------
def criar_estado(cfg: Config):
    """
    Cria a grade inicial COM moldura e (se houver extensões) o vetor de tipos.

    Os espalhadores iniciais são sorteados exatamente como no código original
    (random.seed(semente) + randint(i), randint(j)), de modo que a grade
    inicial é idêntica à de `FakeNews.criar_grade`.
    """
    L, C, W = cfg.linhas, cfg.colunas, cfg.largura
    grade = bytearray((L + 2) * W)          # tudo IGNORANTE (0), inclusive moldura

    rng = random.Random(cfg.semente)        # mesma sequência de random.seed()
    total_esp = int(L * C * cfg.percentual_espalhadores)
    for _ in range(total_esp):
        i = rng.randint(0, L - 1)
        j = rng.randint(0, C - 1)
        grade[(i + 1) * W + (j + 1)] = ESPALHADOR

    tipos = None
    if cfg.estendido:
        # Gerador separado: não altera a grade base (comparabilidade).
        rng2 = random.Random(cfg.semente + 1)
        tipos = bytearray((L + 2) * W)
        for tipo, frac in ((CETICO, cfg.frac_ceticos),
                           (INFLUENCIADOR, cfg.frac_influenciadores),
                           (BOT, cfg.frac_bots)):
            for _ in range(int(L * C * frac)):
                x = (rng2.randint(0, L - 1) + 1) * W + rng2.randint(0, C - 1) + 1
                tipos[x] = tipo
        # Bots já começam espalhando.
        for x in range(len(tipos)):
            if tipos[x] == BOT:
                grade[x] = ESPALHADOR
    return grade, tipos


def remover_moldura(grade, cfg: Config, linhas: int | None = None) -> bytes:
    """Devolve só as células reais (sem moldura), linha a linha."""
    W, C = cfg.largura, cfg.colunas
    L = cfg.linhas if linhas is None else linhas
    return b"".join(bytes(grade[(r * W) + 1:(r * W) + 1 + C]) for r in range(1, L + 1))


def contar(grade_sem_moldura: bytes):
    """Conta (ignorantes, espalhadores, inativos) numa grade sem moldura."""
    esp = grade_sem_moldura.count(ESPALHADOR)
    ina = grade_sem_moldura.count(INATIVO)
    return (len(grade_sem_moldura) - esp - ina, esp, ina)


def dividir_linhas(total: int, partes: int):
    """
    Decomposição em faixas horizontais (block row decomposition).
    Retorna [(inicio, fim)] em linhas REAIS 0-based, fim exclusivo; as faixas
    diferem em no máximo 1 linha (balanceamento estático de carga).
    """
    partes = max(1, min(partes, total))
    base, resto = divmod(total, partes)
    faixas, ini = [], 0
    for p in range(partes):
        tam = base + (1 if p < resto else 0)
        faixas.append((ini, ini + tam))
        ini += tam
    return faixas


# ---------------------------------------------------------------------------
# Gerador pseudoaleatório baseado em contador (para o modelo probabilístico)
# ---------------------------------------------------------------------------
def uniforme(semente: int, geracao: int, indice_global: int) -> float:
    """
    Número em [0,1) que depende SÓ de (semente, geração, célula).

    Por que não usar random.random()? Porque a sequência de um gerador comum
    depende da ORDEM em que as células são visitadas — e essa ordem muda
    conforme a matriz é dividida entre threads/processos. Com um gerador
    baseado em contador (estilo SplitMix64 / Salmon et al., SC'11) o
    resultado é idêntico em qualquer particionamento.
    """
    z = (semente * 0x9E3779B97F4A7C15 + geracao * 0xBF58476D1CE4E5B9
         + indice_global * 0x94D049BB133111EB + 0x632BE59BD9B4E019) & _MASK64
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _MASK64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _MASK64
    z ^= z >> 31
    return z / 18446744073709551616.0


class Contexto:
    """Dados auxiliares que o kernel precisa (somente leitura)."""

    def __init__(self, cfg: Config, tipos=None, deslocamento_linha: int = 0):
        self.cfg = cfg
        self.limiar = cfg.limiar_convencimento
        self.tipos = tipos
        # linha global da linha local r (com moldura) = r - 1 + deslocamento
        self.desloc = deslocamento_linha
        if cfg.estendido:
            if tipos is None:
                raise ValueError("modelo estendido requer vetor de tipos")
            # peso de cada célula quando ela é espalhadora
            pi = cfg.peso_influenciador
            self.peso = bytes(pi if t == INFLUENCIADOR else 1 for t in tipos)
            # probabilidade de convencer dada a "pressão" k (k vizinhos pesados):
            #   P(k) = 1 - (1 - p)^k   (cada contato é uma tentativa independente)
            p = cfg.prob_convencimento
            kmax = 8 * max(1, pi) + 1
            self.prob = [1.0 - (1.0 - p) ** k for k in range(kmax + 1)]
        self.kernel = escolher_kernel(cfg)


# ---------------------------------------------------------------------------
# KERNELS: calculam a próxima geração das linhas [r0, r1) (índices com moldura)
# Lêem `src`, escrevem `dst` e devolvem (ign, esp, ina) dessas linhas.
# Não escrevem fora de [r0, r1): por isso faixas disjuntas podem ser
# processadas simultaneamente sem condição de corrida.
# ---------------------------------------------------------------------------
def passo_referencia(src, dst, W, C, r0, r1, ctx: Contexto, geracao: int):
    """
    Kernel de referência — mesma regra do código original, célula a célula:
      - Ignorante com >= limiar vizinhos espalhadores -> Espalhador
      - Espalhador -> Inativo
      - Inativo -> Inativo
    """
    limiar = ctx.limiar
    ign = esp = ina = 0
    for r in range(r0, r1):
        base = r * W
        for x in range(base + 1, base + C + 1):
            if src[x] == IGNORANTE:
                a = x - W
                b = x + W
                k = ((src[a - 1] == 1) + (src[a] == 1) + (src[a + 1] == 1)
                     + (src[x - 1] == 1) + (src[x + 1] == 1)
                     + (src[b - 1] == 1) + (src[b] == 1) + (src[b + 1] == 1))
                if k >= limiar:
                    dst[x] = ESPALHADOR
                    esp += 1
                else:
                    dst[x] = IGNORANTE
                    ign += 1
            else:  # espalhador ou inativo -> inativo
                dst[x] = INATIVO
                ina += 1
    return ign, esp, ina


def passo_otimizado(src, dst, W, C, r0, r1, ctx: Contexto, geracao: int):
    """
    Kernel otimizado (mesmo resultado do de referência), três ideias:
      1. Indicador de espalhador obtido de uma vez por `bytes.translate`.
      2. Soma vertical por coluna: col[j] = cima[j] + meio[j] + baixo[j];
         para uma célula IGNORANTE (não espalhadora) o número de vizinhos é
         col[j-1] + col[j] + col[j+1]  -> 3 somas em vez de 8 comparações.
      3. Se nenhuma coluna da janela 3xW tem espalhador, a linha apenas
         "envelhece" (1->2) e não precisa do laço célula a célula.
    """
    limiar = ctx.limiar
    ini = (r0 - 1) * W
    esp_ind = bytes(src[ini:(r1 + 1) * W]).translate(_T_ESP)  # indicadores 0/1
    esp = ina = 0
    for r in range(r0, r1):
        o = (r - r0) * W                                    # offset em esp_ind
        cima = esp_ind[o:o + W]
        meio_ind = esp_ind[o + W:o + 2 * W]
        baixo = esp_ind[o + 2 * W:o + 3 * W]
        base = r * W
        meio = bytes(src[base:base + W])
        novo = bytearray(meio.translate(_T_ENV))            # 1 -> 2
        if (cima.count(1) or meio_ind.count(1) or baixo.count(1)) and meio.count(0) > 2:
            col = [p + q + s for p, q, s in zip(cima, meio_ind, baixo)]
            for j in range(1, C + 1):
                if meio[j] == IGNORANTE and col[j - 1] + col[j] + col[j + 1] >= limiar:
                    novo[j] = ESPALHADOR
        novo[0] = novo[W - 1] = 0                           # moldura sempre 0
        dst[base:base + W] = novo
        esp += novo.count(ESPALHADOR)
        ina += novo.count(INATIVO)
    return (r1 - r0) * C - esp - ina, esp, ina


def passo_estendido(src, dst, W, C, r0, r1, ctx: Contexto, geracao: int):
    """
    Kernel do MODELO ESTENDIDO (melhorias propostas pelo grupo):
      * Probabilidade de convencimento: ignorante com pressão k >= limiar é
        convencido com prob. P(k) = 1-(1-p)^k (sorteio por gerador de contador).
      * Influenciadores: quando espalham, contam `peso_influenciador` vizinhos.
      * Bots: espalham em TODAS as gerações (nunca ficam inativos).
      * Céticos: limiar efetivo = limiar + resistencia_cetico.
    """
    cfg = ctx.cfg
    tipos, peso, prob = ctx.tipos, ctx.peso, ctx.prob
    limiar = ctx.limiar
    lim_cet = limiar + cfg.resistencia_cetico
    p_um = cfg.prob_convencimento >= 1.0
    semente = cfg.semente
    ign = esp = ina = 0
    for r in range(r0, r1):
        base = r * W
        linha_global = r - 1 + ctx.desloc
        for x in range(base + 1, base + C + 1):
            t = tipos[x]
            if t == BOT:
                dst[x] = ESPALHADOR
                esp += 1
            elif src[x] == IGNORANTE:
                k = 0
                for v in (x - W - 1, x - W, x - W + 1, x - 1, x + 1,
                          x + W - 1, x + W, x + W + 1):
                    if src[v] == ESPALHADOR:
                        k += peso[v]
                lim = lim_cet if t == CETICO else limiar
                if k >= lim and (p_um or uniforme(
                        semente, geracao, linha_global * C + (x - base - 1)) < prob[min(k, len(prob) - 1)]):
                    dst[x] = ESPALHADOR
                    esp += 1
                else:
                    dst[x] = IGNORANTE
                    ign += 1
            else:
                dst[x] = INATIVO
                ina += 1
    return ign, esp, ina


def escolher_kernel(cfg: Config):
    if cfg.estendido:
        return passo_estendido
    if cfg.kernel == "otimizado":
        return passo_otimizado
    if cfg.kernel == "referencia":
        return passo_referencia
    raise ValueError(f"kernel desconhecido: {cfg.kernel}")


# ---------------------------------------------------------------------------
# Estatísticas adicionais (extensão)
# ---------------------------------------------------------------------------
def estatisticas(historico, total: int) -> dict:
    """Indicadores derivados da série temporal (ign, esp, ina)."""
    esp = [h[1] for h in historico]
    pico = max(esp)
    g_pico = esp.index(pico)
    ign_final = historico[-1][0]
    # taxa de crescimento média nas gerações em que os espalhadores aumentaram
    taxas = [esp[g + 1] / esp[g] for g in range(len(esp) - 1) if esp[g] > 0 and esp[g + 1] > esp[g]]
    return {
        "pico_espalhadores": pico,
        "geracao_pico": g_pico,
        "alcance_final_%": 100.0 * (total - ign_final) / total,
        "ignorantes_final_%": 100.0 * ign_final / total,
        "geracoes_executadas": len(historico) - 1,
        "taxa_crescimento_media": (sum(taxas) / len(taxas)) if taxas else 0.0,
    }


def imprimir_geracao(g: int, c) -> None:
    print(f"Geração {g:03d} | Ignorantes: {c[0]:>10,} | "
          f"Espalhadores: {c[1]:>10,} | Inativos: {c[2]:>10,}")


def imprimir_resumo(res: Resultado, cfg: Config) -> None:
    total = cfg.linhas * cfg.colunas
    ign, esp, ina = res.historico[-1]
    print()
    print(f"=== RESULTADO FINAL ({res.versao}, {res.trabalhadores} trabalhador(es)) ===")
    print(f"Tempo total: {res.tempo_total:.4f} s | tempo de computação: {res.tempo_computacao:.4f} s")
    print(f"Ignorantes finais:   {ign:,} ({ign / total * 100:.2f}%)")
    print(f"Espalhadores finais: {esp:,} ({esp / total * 100:.2f}%)")
    print(f"Inativos finais:     {ina:,} ({ina / total * 100:.2f}%)")
    for k, v in estatisticas(res.historico, total).items():
        print(f"  {k}: {v:.3f}" if isinstance(v, float) else f"  {k}: {v}")
    for k, v in res.extras.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")
    print(f"Assinatura (SHA-256) da grade final: {res.assinatura}")


def adicionar_argumentos(parser) -> None:
    """Argumentos de linha de comando comuns a todas as versões."""
    d = Config()
    parser.add_argument("--linhas", type=int, default=d.linhas)
    parser.add_argument("--colunas", type=int, default=d.colunas)
    parser.add_argument("--geracoes", type=int, default=d.geracoes)
    parser.add_argument("--percentual", type=float, default=0.05,
                        help="fração inicial de espalhadores (0.05 = 5%%)")
    parser.add_argument("--limiar", type=int, default=3)
    parser.add_argument("--semente", type=int, default=d.semente)
    parser.add_argument("--kernel", choices=["referencia", "otimizado"], default=d.kernel)
    parser.add_argument("--sem-parada", action="store_true",
                        help="executa todas as gerações mesmo sem espalhadores")
    parser.add_argument("--prob", type=float, default=1.0, help="prob. de convencimento por contato")
    parser.add_argument("--influenciadores", type=float, default=0.0)
    parser.add_argument("--peso-influenciador", type=int, default=3)
    parser.add_argument("--bots", type=float, default=0.0)
    parser.add_argument("--ceticos", type=float, default=0.0)
    parser.add_argument("--resistencia", type=int, default=2)
    parser.add_argument("--quieto", action="store_true", help="não imprime cada geração")


def config_de_args(a) -> Config:
    return Config(linhas=a.linhas, colunas=a.colunas, geracoes=a.geracoes,
                  percentual_espalhadores=a.percentual, limiar_convencimento=a.limiar,
                  semente=a.semente, kernel=a.kernel, parar_sem_espalhadores=not a.sem_parada,
                  prob_convencimento=a.prob, frac_influenciadores=a.influenciadores,
                  peso_influenciador=a.peso_influenciador, frac_bots=a.bots,
                  frac_ceticos=a.ceticos, resistencia_cetico=a.resistencia)


def imprimir_cabecalho(titulo: str, cfg: Config, trabalhadores: int = 1) -> None:
    print(f"=== {titulo} ===")
    print(f"Grade: {cfg.linhas} x {cfg.colunas} ({cfg.linhas * cfg.colunas:,} pessoas) | "
          f"gerações: {cfg.geracoes} | espalhadores iniciais: {cfg.percentual_espalhadores * 100:.2f}% | "
          f"limiar: {cfg.limiar_convencimento} | kernel: {'estendido' if cfg.estendido else cfg.kernel} | "
          f"trabalhadores: {trabalhadores}")
    if cfg.estendido:
        print(f"Extensões: p={cfg.prob_convencimento}, influenciadores={cfg.frac_influenciadores} "
              f"(peso {cfg.peso_influenciador}), bots={cfg.frac_bots}, céticos={cfg.frac_ceticos} "
              f"(+{cfg.resistencia_cetico})")
    print()
