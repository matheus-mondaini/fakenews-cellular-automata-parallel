"""
Pacote `fakenews` — Simulação de Propagação de Fake News
=========================================================

Versões disponíveis (todas usam o MESMO núcleo de cálculo de `modelo.py`,
o que garante que produzem exatamente a mesma grade final):

    sequencial.py         -> versão sequencial refatorada
    paralelo_threads.py   -> versão paralela com threading.Thread + Barrier
    paralelo_processos.py -> versão paralela com multiprocessing.Process +
                             memória compartilhada (paralelismo real, sem GIL)
    distribuido.py        -> versão distribuída com sockets TCP
                             (coordenador + trabalhadores, troca de bordas/halo)
    visualizacao.py       -> geração de imagens/GIF e gráficos de evolução

O código sequencial original fornecido pelo professor está preservado em
`FakeNews.py` (raiz do projeto) e é usado como referência nos testes.
"""
