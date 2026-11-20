"""
RUMO AO NÚCLEO — projeto final de Laboratório de Programação de Jogos (Python + PPlay + Pygame).

Execute este arquivo (main.py) para jogar.
Opções de linha de comando (úteis para testes):
    --debug    N pula a fase | L +1 vida | H esquenta a broca | K +100 de minério
    --todas    libera todas as fases na tela "Selecionar fase"
"""
import sys

import config as C

if "--debug" in sys.argv:
    C.DEBUG = True
if "--todas" in sys.argv:
    C.DESBLOQUEAR_TODAS_FASES = True

from jogo import Jogo  # noqa: E402  (importa depois das opções, para a config valer)


def main():
    Jogo().rodar()


if __name__ == "__main__":
    main()
