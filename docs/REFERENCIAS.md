# Referências bibliográficas

## Modelo (propagação de rumores / fake news, autômatos celulares)

1. DALEY, D. J.; KENDALL, D. G. Epidemics and rumours. **Nature**, v. 204, p. 1118, 1964. DOI: 10.1038/2041118a0. — modelo clássico ignorante/espalhador/inativo (*ignorant–spreader–stifler*), base dos três estados.
2. MAKI, D. P.; THOMPSON, M. **Mathematical Models and Applications**. Englewood Cliffs: Prentice-Hall, 1973. — variante Maki–Thompson do modelo de rumores.
3. KERMACK, W. O.; McKENDRICK, A. G. A contribution to the mathematical theory of epidemics. **Proc. Royal Society A**, v. 115, n. 772, p. 700–721, 1927. — modelo SIR, análogo epidemiológico.
4. MORENO, Y.; NEKOVEE, M.; PACHECO, A. F. Dynamics of rumor spreading in complex networks. **Physical Review E**, v. 69, 066130, 2004. DOI: 10.1103/PhysRevE.69.066130.
5. WOLFRAM, S. Statistical mechanics of cellular automata. **Reviews of Modern Physics**, v. 55, n. 3, p. 601–644, 1983. — autômatos celulares, vizinhança e atualização síncrona.
6. GRANOVETTER, M. Threshold models of collective behavior. **American Journal of Sociology**, v. 83, n. 6, p. 1420–1443, 1978. — fundamenta o *limiar de convencimento*.
7. WATTS, D. J. A simple model of global cascades on random networks. **PNAS**, v. 99, n. 9, p. 5766–5771, 2002. — cascatas com limiar.
8. VOSOUGHI, S.; ROY, D.; ARAL, S. The spread of true and false news online. **Science**, v. 359, n. 6380, p. 1146–1151, 2018. — evidência empírica da difusão de notícias falsas.
9. LAZER, D. M. J. et al. The science of fake news. **Science**, v. 359, n. 6380, p. 1094–1096, 2018.
10. SHAO, C. et al. The spread of low-credibility content by social bots. **Nature Communications**, v. 9, 4787, 2018. — justifica a extensão *bots*.
11. FERRARA, E. et al. The rise of social bots. **Communications of the ACM**, v. 59, n. 7, p. 96–104, 2016.
12. CHA, M. et al. Measuring user influence in Twitter: the million follower fallacy. In: **ICWSM**, 2010. — justifica a extensão *influenciadores* (peso maior).
13. LEWANDOWSKY, S. et al. Misinformation and its correction: continued influence and successful debiasing. **Psychological Science in the Public Interest**, v. 13, n. 3, p. 106–131, 2012. — justifica a extensão *céticos/resistência*.
14. VAN DER LINDEN, S. et al. Inoculating the public against misinformation about climate change. **Global Challenges**, v. 1, n. 2, 1600008, 2017.

## Computação paralela e distribuída

15. FOSTER, I. **Designing and Building Parallel Programs**. Addison-Wesley, 1995. — metodologia PCAM, decomposição de domínio e troca de bordas (*halo/ghost cells*).
16. GRAMA, A.; GUPTA, A.; KARYPIS, G.; KUMAR, V. **Introduction to Parallel Computing**. 2. ed. Addison-Wesley, 2003. — speedup, eficiência, decomposição por blocos.
17. PACHECO, P. **An Introduction to Parallel Programming**. Morgan Kaufmann, 2011. — barreiras, condições de corrida, métricas.
18. AMDAHL, G. M. Validity of the single processor approach to achieving large scale computing capabilities. In: **AFIPS Spring Joint Computer Conference**, 1967, p. 483–485.
19. GUSTAFSON, J. L. Reevaluating Amdahl's law. **Communications of the ACM**, v. 31, n. 5, p. 532–533, 1988.
20. KARP, A. H.; FLATT, H. P. Measuring parallel processor performance. **Communications of the ACM**, v. 33, n. 5, p. 539–543, 1990. — fração serial experimental usada na análise.
21. TANENBAUM, A. S.; VAN STEEN, M. **Distributed Systems: Principles and Paradigms**. 2. ed. Pearson, 2007. — comunicação por sockets, arquiteturas cliente-servidor e P2P.
22. COULOURIS, G. et al. **Distributed Systems: Concepts and Design**. 5. ed. Addison-Wesley, 2011.
23. SALMON, J. K. et al. Parallel random numbers: as easy as 1, 2, 3. In: **SC'11**, ACM, 2011. DOI: 10.1145/2063384.2063405. — geradores baseados em contador (usado para o modelo probabilístico ser independente da partição).
24. STEELE, G. L.; LEA, D.; FLOOD, C. H. Fast splittable pseudorandom number generators. In: **OOPSLA 2014**, ACM. — função de mistura SplitMix64.
25. BEAZLEY, D. Understanding the Python GIL. **PyCon 2010**. — limitação de threads em CPython.
26. GROSS, S. **PEP 703 – Making the Global Interpreter Lock Optional in CPython**, 2023. https://peps.python.org/pep-0703/
27. NAGLE, J. **RFC 896 – Congestion Control in IP/TCP Internetworks**, 1984. — algoritmo de Nagle (desligado com TCP_NODELAY).

## Documentação técnica

28. Python Software Foundation. `threading`, `multiprocessing`, `multiprocessing.shared_memory`, `socket`, `struct` — Python 3.11 Documentation. https://docs.python.org/3.11/library/
29. Matplotlib 3.10 e Pillow 12 — usados exclusivamente para gráficos e GIF.

## Uso de IA generativa

30. ANTHROPIC. **Claude** (assistente de IA generativa, modelo Claude Opus), 2026. Utilizado como apoio na estruturação e revisão do código, na elaboração dos scripts de experimentos e na redação da documentação/slides. Todo o conteúdo foi revisado, executado e validado pelo grupo (ver testes automatizados).
