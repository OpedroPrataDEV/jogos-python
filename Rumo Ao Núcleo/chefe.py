"""O Núcleo: chefe final desenhado por código (esfera de magma, olho, placas de rocha)."""
import math
import random

import pygame

import util

R_NUCLEO = 46


def _esfera(raio, cores):
    """Esfera com gradiente radial: cores = (borda, meio, centro)."""
    s = pygame.Surface((raio * 2 + 2, raio * 2 + 2), pygame.SRCALPHA)
    c = (raio + 1, raio + 1)
    for i in range(raio, 0, -1):
        t = 1 - i / raio
        if t < 0.5:
            col = util.misturar(cores[0], cores[1], t / 0.5)
        else:
            col = util.misturar(cores[1], cores[2], (t - 0.5) / 0.5)
        pygame.draw.circle(s, col, c, i)
    # realce de luz
    brilho = pygame.Surface(s.get_size(), pygame.SRCALPHA)
    pygame.draw.circle(brilho, (255, 255, 255, 70), (c[0] - raio // 3, c[1] - raio // 3), raio // 2)
    s.blit(brilho, (0, 0))
    return s


class Chefe:
    HP_MAX = 36

    def __init__(self):
        self.x, self.y = 400.0, 138.0
        self.t = 0.0
        self.hp = self.HP_MAX
        self.fase = 1
        self.inv = 0.0
        self.flash = 0.0
        self.transicao = 0.0
        self.morrendo = 0.0
        self.morto = False
        self.aviso = 0.0            # telegrafa o ataque (olho brilha)
        self.t_tiro = 2.2
        self.t_geiser = 4.5
        self.ataque_pend = None
        self.olhar = (0.0, 1.0)
        self.spr_nucleo = [
            _esfera(R_NUCLEO, ((110, 18, 10), (235, 80, 20), (255, 215, 120))),
            _esfera(R_NUCLEO, ((120, 10, 20), (255, 60, 20), (255, 235, 150))),
            _esfera(R_NUCLEO, ((140, 20, 20), (255, 140, 40), (255, 255, 230))),
        ]
        self.rachaduras = [(random.uniform(0, math.tau), random.uniform(14, 32)) for _ in range(9)]
        self.placas = []

    # ------------------------------------------------------------ regras
    @property
    def raio(self):
        return R_NUCLEO

    def fase_por_hp(self):
        return 1 if self.hp > 24 else (2 if self.hp > 12 else 3)

    def dano(self, n):
        """Retorna True se o dano foi aplicado."""
        if self.inv > 0 or self.transicao > 0 or self.morrendo > 0:
            return False
        self.hp = max(0, self.hp - n)
        self.inv = 0.30
        self.flash = 1.0
        return True

    # ------------------------------------------------------------ lógica
    def atualizar(self, dt, alvo):
        """alvo = (x, y) da plataforma. Retorna lista de eventos para a partida."""
        ev = []
        self.t += dt
        self.inv = max(0.0, self.inv - dt)
        self.flash = max(0.0, self.flash - dt * 4)
        self.aviso = max(0.0, self.aviso - dt)
        amp, vel = {1: (170, 0.85), 2: (215, 1.15), 3: (235, 1.55)}[self.fase]
        self.x = 400 + amp * math.sin(self.t * vel)
        self.y = 138 + 9 * math.sin(self.t * 2.1)
        dx, dy = alvo[0] - self.x, alvo[1] - self.y
        n = math.hypot(dx, dy) or 1
        self.olhar = (self.olhar[0] + (dx / n - self.olhar[0]) * min(1, dt * 6),
                      self.olhar[1] + (dy / n - self.olhar[1]) * min(1, dt * 6))

        if self.morrendo > 0:
            self.morrendo -= dt
            self.morto = self.morrendo <= 0
            return ev

        if self.transicao > 0:
            self.transicao -= dt
            return ev

        nova = self.fase_por_hp()
        if nova != self.fase and self.hp > 0:
            self.fase = nova
            self.transicao = 1.8
            self.t_tiro = 2.6
            self.t_geiser = 4.0
            ev.append(("fase", nova))
            return ev
        if self.hp <= 0:
            self.morrendo = 3.4
            ev.append(("morreu", None))
            return ev

        # ---- tiros
        self.t_tiro -= dt
        if self.t_tiro <= 0.55 and self.ataque_pend is None:
            self.aviso = 0.55
            self.ataque_pend = "tiro"
        if self.t_tiro <= 0:
            self.t_tiro = {1: 2.4, 2: 2.1, 3: 1.7}[self.fase]
            self.ataque_pend = None
            base = math.atan2(alvo[0] - self.x, alvo[1] - self.y)  # 0 = para baixo
            qtd = {1: 1, 2: 3, 3: 5}[self.fase]
            passo = math.radians({1: 0, 2: 17, 3: 15}[self.fase])
            vel_t = {1: 285, 2: 300, 3: 325}[self.fase]
            tiros = []
            for i in range(qtd):
                a = base + (i - (qtd - 1) / 2) * passo
                tiros.append((self.x, self.y + 36, math.sin(a) * vel_t, math.cos(a) * vel_t))
            ev.append(("tiro", tiros))

        # ---- gêiseres
        if self.fase >= 2:
            self.t_geiser -= dt
            if self.t_geiser <= 0:
                self.t_geiser = {2: 5.6, 3: 3.9}[self.fase]
                xs = [alvo[0]] + [random.uniform(80, 720) for _ in range(self.fase - 1)]
                ev.append(("geiser", xs))
        return ev

    # ------------------------------------------------------------ desenho
    def desenhar(self, tela, t):
        x, y = int(self.x), int(self.y)
        quente = {1: (255, 110, 40), 2: (255, 70, 30), 3: (255, 190, 120)}[self.fase]
        pulso = 1 + 0.08 * math.sin(t * 5)
        util.brilho(tela, x, y, int(150 * pulso), quente, 0.95)
        # placas de rocha ao redor (somem a cada fase)
        n_placas = {1: 6, 2: 3, 3: 0}[self.fase]
        if self.transicao > 0:
            n_placas = {1: 6, 2: 3, 3: 0}[self.fase] + int(self.transicao * 3)  # as placas voam ao mudar de fase
        for i in range(n_placas):
            a = t * 0.55 + i * math.tau / max(1, n_placas)
            self._placa(tela, x, y, a, 30 if self.morrendo <= 0 else 60)
        # núcleo
        surf = self.spr_nucleo[self.fase - 1]
        esc = pulso * (1 + 0.05 * math.sin(t * 40) * (self.transicao > 0))
        if abs(esc - 1) > 0.01:
            w = int(surf.get_width() * esc)
            surf = pygame.transform.smoothscale(surf, (w, w))
        tela.blit(surf, surf.get_rect(center=(x, y)))
        # rachaduras incandescentes
        for i, (a, comp) in enumerate(self.rachaduras[: 3 + self.fase * 2]):
            aa = a + 0.2 * math.sin(t + i)
            p1 = (x + math.cos(aa) * 8, y + math.sin(aa) * 8)
            p2 = (x + math.cos(aa) * comp, y + math.sin(aa) * comp)
            pygame.draw.line(tela, (255, 245, 200), p1, p2, 2)
        self._olho(tela, x, y, t)
        if self.flash > 0:
            util.brilho(tela, x, y, 90, (255, 255, 255), self.flash * 1.4)

    def _placa(self, tela, x, y, ang, folga):
        pts = []
        r1, r2 = R_NUCLEO - 2, R_NUCLEO + 18
        a0, a1 = ang - 0.42, ang + 0.42
        for k in range(6):
            a = a0 + (a1 - a0) * k / 5
            pts.append((x + math.cos(a) * r2, y + math.sin(a) * r2))
        for k in range(5, -1, -1):
            a = a0 + (a1 - a0) * k / 5
            pts.append((x + math.cos(a) * r1, y + math.sin(a) * r1))
        pygame.draw.polygon(tela, (52, 46, 54), pts)
        pygame.draw.polygon(tela, (120, 104, 112), pts, 2)
        pygame.draw.line(tela, (255, 110, 50), pts[2], pts[3], 1)

    def _olho(self, tela, x, y, t):
        ex, ey = x, y + 2
        brilho_aviso = self.aviso > 0
        cor_olho = (255, 255, 235) if not brilho_aviso else (255, 120, 90)
        pygame.draw.ellipse(tela, cor_olho, (ex - 27, ey - 17, 54, 34))
        pygame.draw.ellipse(tela, (70, 10, 5), (ex - 27, ey - 17, 54, 34), 3)
        px = ex + self.olhar[0] * 10
        py = ey + self.olhar[1] * 6
        pygame.draw.ellipse(tela, (30, 0, 0), (px - 6, py - 15, 12, 30))
        pygame.draw.ellipse(tela, (255, 90, 30), (px - 2, py - 8, 4, 8))
        # sobrancelhas de raiva
        inc = 6 + self.fase * 3
        pygame.draw.line(tela, (50, 8, 6), (ex - 34, ey - 22 - inc * 0.2), (ex - 3, ey - 9), 8)
        pygame.draw.line(tela, (50, 8, 6), (ex + 34, ey - 22 - inc * 0.2), (ex + 3, ey - 9), 8)
        if brilho_aviso:
            util.brilho(tela, int(ex), int(ey), 46, (255, 80, 40), 1.2)
