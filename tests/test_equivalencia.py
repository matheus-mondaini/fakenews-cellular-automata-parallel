"""
Testes automatizados: provam que TODAS as versões produzem exatamente a mesma
grade final e o mesmo histórico de contagens que a versão sequencial — e que
a versão sequencial refatorada reproduz o código original (FakeNews.py).

Executar (na raiz do projeto):
    python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import FakeNews as original  # noqa: E402  (código fornecido pelo professor)
from fakenews import modelo, sequencial, paralelo_threads, paralelo_processos, distribuido  # noqa: E402
from fakenews.modelo import Config  # noqa: E402

CENARIOS = [
    # (descrição, Config)
    ("base limiar 2 sem parada", Config(linhas=45, colunas=61, geracoes=25, percentual_espalhadores=0.05,
                                        limiar_convencimento=2, parar_sem_espalhadores=False)),
    ("base limiar 3 com parada", Config(linhas=50, colunas=50, geracoes=30, percentual_espalhadores=0.05,
                                        limiar_convencimento=3)),
    ("densa 20%", Config(linhas=33, colunas=40, geracoes=12, percentual_espalhadores=0.2,
                         limiar_convencimento=2, parar_sem_espalhadores=False)),
    ("estendido completo", Config(linhas=40, colunas=37, geracoes=15, percentual_espalhadores=0.03,
                                  limiar_convencimento=2, prob_convencimento=0.4,
                                  frac_influenciadores=0.02, frac_bots=0.005, frac_ceticos=0.2)),
]


def rodar_original(cfg: Config) -> bytes:
    """Executa o código ORIGINAL com a mesma regra de parada."""
    g = original.criar_grade(cfg.linhas, cfg.colunas, cfg.percentual_espalhadores, cfg.semente)
    for _ in range(cfg.geracoes):
        g = original.proxima_geracao(g, cfg.limiar_convencimento)
        if cfg.parar_sem_espalhadores and original.contar_estados(g)[original.ESPALHADOR] == 0:
            break
    return bytes(v for linha in g for v in linha)


class TestModelo(unittest.TestCase):
    def test_divisao_de_linhas(self):
        for total in (1, 7, 100, 1001):
            for partes in (1, 2, 3, 6, 12, 2000):
                f = modelo.dividir_linhas(total, partes)
                self.assertEqual(f[0][0], 0)
                self.assertEqual(f[-1][1], total)
                for (a, b), (c, _) in zip(f, f[1:]):
                    self.assertEqual(b, c)                   # contíguas, sem buraco
                tams = [b - a for a, b in f]
                self.assertLessEqual(max(tams) - min(tams), 1)  # balanceadas

    def test_uniforme(self):
        vals = [modelo.uniforme(42, g, i) for g in range(5) for i in range(2000)]
        self.assertTrue(all(0.0 <= v < 1.0 for v in vals))
        self.assertAlmostEqual(sum(vals) / len(vals), 0.5, delta=0.02)
        self.assertEqual(modelo.uniforme(1, 2, 3), modelo.uniforme(1, 2, 3))

    def test_grade_inicial_igual_original(self):
        cfg = Config(linhas=70, colunas=90, percentual_espalhadores=0.05)
        g = original.criar_grade(70, 90, 0.05, 42)
        esperado = bytes(v for linha in g for v in linha)
        grade, _ = modelo.criar_estado(cfg)
        self.assertEqual(modelo.remover_moldura(grade, cfg), esperado)


class TestEquivalencia(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ref = {nome: sequencial.executar(cfg, verbose=False) for nome, cfg in CENARIOS}

    def comparar(self, nome, res):
        ref = self.ref[nome]
        self.assertEqual(res.grade_final, ref.grade_final, f"{res.versao}/{nome}: grade difere")
        self.assertEqual(list(map(tuple, res.historico)), list(map(tuple, ref.historico)),
                         f"{res.versao}/{nome}: histórico difere")

    def test_sequencial_igual_original(self):
        for nome, cfg in CENARIOS:
            if cfg.estendido:
                continue
            for kernel in ("referencia", "otimizado"):
                cfg.kernel = kernel
                with self.subTest(nome=nome, kernel=kernel):
                    self.assertEqual(sequencial.executar(cfg, verbose=False).grade_final,
                                     rodar_original(cfg))
            cfg.kernel = "referencia"

    def test_threads(self):
        for nome, cfg in CENARIOS:
            for n in (1, 2, 5):
                with self.subTest(nome=nome, n=n):
                    self.comparar(nome, paralelo_threads.executar(cfg, n, verbose=False))

    def test_processos(self):
        for nome, cfg in CENARIOS:
            for n in (2, 4):
                for copia in (True, False):
                    with self.subTest(nome=nome, n=n, copia_local=copia):
                        self.comparar(nome, paralelo_processos.executar(cfg, n, verbose=False,
                                                                        copia_local=copia))

    def test_distribuido(self):
        for nome, cfg in CENARIOS:
            for n in (1, 3):
                for topo in ("p2p", "estrela"):
                    with self.subTest(nome=nome, n=n, topologia=topo):
                        self.comparar(nome, distribuido.executar_local(cfg, n, topo, verbose=False))

    def test_mais_trabalhadores_que_linhas(self):
        cfg = Config(linhas=4, colunas=30, geracoes=6, percentual_espalhadores=0.3,
                     limiar_convencimento=2, parar_sem_espalhadores=False)
        ref = sequencial.executar(cfg, verbose=False).grade_final
        self.assertEqual(paralelo_threads.executar(cfg, 8, verbose=False).grade_final, ref)
        self.assertEqual(distribuido.executar_local(cfg, 8, "p2p", verbose=False).grade_final, ref)


if __name__ == "__main__":
    unittest.main(verbosity=2)
