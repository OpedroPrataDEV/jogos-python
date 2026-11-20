"""Constantes globais do jogo Rumo ao Núcleo."""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(BASE, "assets", "img")
SOM = os.path.join(BASE, "assets", "sons")
DADOS = os.path.join(BASE, "dados")

LARGURA, ALTURA = 800, 600
FPS = 60

# ---- opções de teste / professor -------------------------------------------
DEBUG = False                    # True: N = pula fase | L = +1 vida | H = esquenta a broca | K = +100 minério
DESBLOQUEAR_TODAS_FASES = False  # True: libera todas as fases na tela "Selecionar fase"
AUTOPLAY = False                 # True: a plataforma joga sozinha (usado nos testes automáticos)

VOLUME_MUSICA = 0.38
VOLUME_SFX = 0.75

# ---- grade de blocos --------------------------------------------------------
BLOCO_L, BLOCO_A, ESPACO = 60, 24, 4
COLUNAS = 11
GRADE_X0 = (LARGURA - (COLUNAS * (BLOCO_L + ESPACO) - ESPACO)) // 2
GRADE_Y0 = 96

# ---- layout da tela ---------------------------------------------------------
HUD_ALTURA = 50
PLAT_Y = ALTURA - 76
LAVA_Y = ALTURA - 32
RAIO_BROCA = 13

VIDAS_BASE = 3
VIDAS_MAX = 7

AUTOR = "Seu Nome Aqui"          # aparece na tela de créditos
TITULO_JANELA = "Rumo ao Núcleo"
