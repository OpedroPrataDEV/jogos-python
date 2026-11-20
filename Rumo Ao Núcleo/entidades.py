"""Objetos de jogo: blocos, broca, plataforma, minérios, power-ups e perigos (usam Sprite do PPlay)."""
import math
import random

import pygame

import config as C
import util
from pplay_compat import Sprite, Window


class Caixa:
    """Retângulo simples (x, y, width, height) usado nas colisões feitas à mão (util.colidiu)."""

    def __init__(self, x=0, y=0, w=0, h=0):
        self.x, self.y, self.width, self.height = x, y, w, h


# =============================================================== BLOCOS
ATRIB_BLOCO = {
    #            hp  pontos  minério   chance  cor dos estilhaços
    "terra":    (1, 10, "cobre", 0.35, (134, 94, 62)),
    "pedra":    (2, 20, "cobre", 0.65, (122, 122, 134)),
    "prata":    (3, 40, "prata", 1.00, (205, 214, 232)),
    "ouro":     (4, 80, "ouro", 1.00, (255, 204, 64)),
    "diamante": (5, 150, "diamante", 1.00, (120, 232, 255)),
    "gema":     (3, 100, "gema", 1.00, (224, 96, 255)),
    "granito":  (3, 50, None, 0.0, (74, 74, 88)),
    "tnt":      (1, 30, None, 0.0, (232, 64, 52)),
}
FRAMES_BLOCO = {"granito": 1, "tnt": 2}

VALOR_MINERIO = {"cobre": 1, "prata": 3, "ouro": 6, "diamante": 15, "gema": 25}
COR_MINERIO = {"cobre": (230, 140, 80), "prata": (210, 225, 245), "ouro": (255, 215, 80),
               "diamante": (120, 235, 255), "gema": (235, 120, 255)}


class Bloco:
    def __init__(self, tipo, col, lin, x, y):
        self.tipo = tipo
        self.col, self.lin = col, lin
        self.hp_max, self.pontos, self.minerio, self.chance, self.cor = ATRIB_BLOCO[tipo]
        self.hp = self.hp_max
        self.vivo = True
        self.tremor = 0.0
        self.flash = 0.0
        self.cd = 0.0            # recarga do dano por perfuração
        self.fuse = None         # pavio do TNT (explosão em cadeia)
        self.solta = 0.0         # estalactite prestes a cair
        self.x, self.y = float(x), float(y)
        self.atraso = random.uniform(0, 0.55) + lin * 0.07   # animação de entrada
        frames = FRAMES_BLOCO.get(tipo, 4)
        if tipo in ("granito", "tnt", "gema"):
            arq = f"bloco_{tipo}.png"
        else:
            arq = f"bloco_{tipo}_{'ab'[(col + lin) % 2]}.png"
        self.frames = frames
        self.spr = Sprite(f"{C.IMG}/{arq}", frames)
        self.spr.set_position(self.x, self.y)

    @property
    def width(self):
        return C.BLOCO_L

    @property
    def height(self):
        return C.BLOCO_A

    @property
    def cx(self):
        return self.x + C.BLOCO_L / 2

    @property
    def cy(self):
        return self.y + C.BLOCO_A / 2

    @property
    def indestrutivel(self):
        return self.tipo == "granito"

    @property
    def obrigatorio(self):
        return self.tipo != "granito"

    def desenhar(self, t, entrada=1.0):
        """entrada: 0..1 (animação de queda inicial)."""
        off = (1 - util.ease_back(entrada)) * -260 if entrada < 1 else 0
        ox = math.sin(self.tremor * 70) * self.tremor * 14 if self.tremor > 0 else 0
        if self.tipo == "tnt":
            quadro = int(t * (4 + 10 * (self.fuse is not None))) % 2
        elif self.frames == 1:
            quadro = 0
        else:
            quadro = min(self.frames - 1, int((1 - self.hp / self.hp_max) * self.frames))
        self.spr.set_curr_frame(quadro)
        self.spr.set_position(self.x + ox, self.y + off)
        self.spr.draw()


# =============================================================== BROCA (a "bolinha")
class Broca:
    def __init__(self, x, y, vel):
        self.x, self.y = float(x), float(y)
        self.vx = self.vy = 0.0
        self.vel = vel
        self.presa = True        # presa na plataforma antes do lançamento
        self.quente = 0.0        # segundos restantes de superaquecimento
        self.anim = random.uniform(0, 8)
        self.trilha = []
        self.pierce_cd = 0.0
        self.spr_f = Sprite(f"{C.IMG}/broca.png", 8)
        self.spr_q = Sprite(f"{C.IMG}/broca_quente.png", 8)

    def caixa(self):
        r = C.RAIO_BROCA - 1
        return Caixa(self.x - r, self.y - r, 2 * r, 2 * r)

    def direcao(self, ang_graus):
        """ang_graus: 0 = para cima; positivo = para a direita."""
        a = math.radians(ang_graus)
        self.vx = math.sin(a) * self.vel
        self.vy = -math.cos(a) * self.vel

    def acertar_velocidade(self):
        """Mantém a velocidade escalar e evita trajetórias quase horizontais (sem if de posição)."""
        v = math.hypot(self.vx, self.vy) or 1.0
        vy_min = 0.30 * self.vel
        vy = math.copysign(max(abs(self.vy), vy_min), self.vy or -1.0)
        vx = self.vx
        n = math.hypot(vx, vy) or 1.0
        self.vx, self.vy = vx / n * self.vel, vy / n * self.vel

    def desenhar(self, t):
        spr = self.spr_q if self.quente > 0 else self.spr_f
        spr.set_curr_frame(int((t + self.anim) * (26 if self.quente > 0 else 16)) % 8)
        spr.set_position(self.x - 20, self.y - 20)
        spr.draw()


# =============================================================== PLATAFORMA (carrinho com mola)
class Plataforma:
    LARGS = [112, 126, 140, 154, 168, 188, 208, 230]
    _cache = {}

    def __init__(self, largura):
        self.largura = float(largura)
        self.alvo = float(largura)
        self.base = float(largura)
        self.x = (C.LARGURA - largura) / 2
        self.y = C.PLAT_Y
        self.vx = 0.0
        self.mola = 0.0          # compressão ao rebater
        self.atordoada = 0.0
        self.spr = Sprite(f"{C.IMG}/plataforma_168.png", 1)
        self._ultima = None
        self._ajustar_imagem()

    @property
    def cx(self):
        return self.x + self.largura / 2

    @property
    def altura(self):
        return 28

    def caixa(self):
        return Caixa(self.x, self.y + 2, self.largura, 26)

    def _ajustar_imagem(self):
        w = max(80, int(round(self.largura)))
        if w == self._ultima:
            return
        self._ultima = w
        if w not in Plataforma._cache:
            base = min(self.LARGS, key=lambda L: abs(L - w))
            im = util.img(f"plataforma_{base}.png")
            Plataforma._cache[w] = im if base == w else pygame.transform.smoothscale(im, (w, 28))
        self.spr.image = Plataforma._cache[w]
        self.spr.width = w
        self.spr.height = 28

    def mover(self, dt, direcao, velocidade):
        """direcao: -1, 0 ou 1. Movimento com leve inércia; os limites usam min/max (clamp)."""
        alvo_v = direcao * velocidade * (0.35 if self.atordoada > 0 else 1.0)
        self.vx += (alvo_v - self.vx) * min(1.0, 16 * dt)
        self.largura += (self.alvo - self.largura) * min(1.0, 7 * dt)
        self.x = util.clamp(self.x + self.vx * dt, 0, C.LARGURA - self.largura)
        # se a plataforma está encostada na parede, a inércia zera
        self.vx *= 0 if self.x in (0, C.LARGURA - self.largura) else 1
        self.mola = max(0.0, self.mola - dt * 5)
        self.atordoada = max(0.0, self.atordoada - dt)
        self._ajustar_imagem()

    def desenhar(self, t):
        sq = math.sin(self.mola * math.pi) * 5
        self.spr.set_position(self.x, self.y + sq)
        self.spr.draw()


# =============================================================== ITENS QUE CAEM
class Caindo:
    """Minério ou power-up descendo em direção à plataforma (e à lava!)."""

    def __init__(self, categoria, tipo, x, y):
        self.categoria = categoria      # "minerio" | "powerup"
        self.tipo = tipo
        arq = f"min_{tipo}.png" if categoria == "minerio" else f"pu_{tipo}.png"
        self.spr = Sprite(f"{C.IMG}/{arq}", 1)
        self.x, self.y = float(x), float(y)
        self.vy = -random.uniform(40, 120) if categoria == "minerio" else -90
        self.vx = random.uniform(-40, 40) if categoria == "minerio" else 0.0
        self.t = random.uniform(0, 6)
        self.vivo = True

    @property
    def width(self):
        return self.spr.width

    @property
    def height(self):
        return self.spr.height

    def caixa(self):
        return Caixa(self.x - self.spr.width / 2, self.y - self.spr.height / 2, self.spr.width, self.spr.height)

    def desenhar(self, t):
        bal = math.sin((t + self.t) * 4) * (3 if self.categoria == "powerup" else 0)
        self.spr.set_position(self.x - self.spr.width / 2, self.y - self.spr.height / 2 + bal)
        self.spr.draw()


# =============================================================== PERIGOS
class Estalactite:
    """Pedra que se solta de um bloco e cai sobre a plataforma. A broca pode destruí-la."""

    def __init__(self, x, y):
        self.spr = Sprite(f"{C.IMG}/estalactite.png", 1)
        self.x, self.y = float(x), float(y)   # centro do topo
        self.vy = 40.0
        self.vivo = True

    def caixa(self):
        return Caixa(self.x - 9, self.y, 18, self.spr.height - 4)

    def desenhar(self, t):
        self.spr.set_position(self.x - self.spr.width / 2, self.y)
        self.spr.draw()


class Estilhaco:
    """Projétil do chefe (cristal de magma)."""
    _rot = {}

    def __init__(self, x, y, vx, vy):
        self.spr = Sprite(f"{C.IMG}/estilhaco.png", 1)
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = vx, vy
        self.vivo = True
        self.ang = math.degrees(math.atan2(vx, vy))     # 0 = apontando pra baixo

    def caixa(self):
        return Caixa(self.x - 8, self.y - 14, 16, 28)

    def desenhar(self, t):
        chave = int(round(self.ang / 6.0))
        im = Estilhaco._rot.get(chave)
        if im is None:
            im = pygame.transform.rotate(self.spr.image, chave * 6.0)
            Estilhaco._rot[chave] = im
        Window.get_screen().blit(im, im.get_rect(center=(self.x, self.y)))


class Geiser:
    """Coluna de lava: aviso no chão (vermelho) e depois erupção."""
    AVISO = 1.15
    ERUPCAO = 0.95

    def __init__(self, x):
        self.x = float(x)
        self.t = 0.0
        self.vivo = True

    @property
    def ativo(self):
        return self.AVISO <= self.t < self.AVISO + self.ERUPCAO

    def caixa(self):
        return Caixa(self.x - 26, 150, 52, C.LAVA_Y - 150)
