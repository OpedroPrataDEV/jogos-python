"""Telas de menu: título, seleção de fase, oficina (loja), ranking, como jogar, créditos e nome do recorde."""
import math
import random

import pygame

import config as C
import dados
import util
from entidades import COR_MINERIO, Plataforma
from fases import FASES
from pplay_compat import Sprite

# ------------------------------------------------------------------ melhorias da Oficina
UPGRADES = [
    dict(id="tungstenio", nome="Broca de Tungstênio", max=4, custos=[40, 90, 170, 300], icone="pu_picareta.png",
         desc="Cada impacto tem chance de ser CRÍTICO e causar +1 de dano nos blocos.",
         efeito=lambda n: "sem críticos" if n == 0 else f"{12 * n}% de chance de crítico"),
    dict(id="plataforma", nome="Vagoneta Reforçada", max=4, custos=[30, 70, 140, 250], icone="pu_viga.png",
         desc="Plataforma mais larga: fica mais fácil rebater a broca e apanhar o minério.",
         efeito=lambda n: f"largura de {Plataforma.LARGS[3 + n]} px"),
    dict(id="capacete", nome="Capacete de Segurança", max=3, custos=[80, 180, 350], icone="pu_capacete.png",
         desc="Você começa cada escavação com brocas reserva (vidas) extras.",
         efeito=lambda n: f"{C.VIDAS_BASE + n} vidas iniciais"),
    dict(id="ima", nome="Ímã de Minério", max=4, custos=[50, 110, 200, 340], icone=None,
         desc="Atrai o minério que cai na direção da plataforma antes de ele cair na lava.",
         efeito=lambda n: "desligado" if n == 0 else f"alcance de {70 + 55 * n} px"),
    dict(id="isolamento", nome="Isolamento Térmico", max=4, custos=[60, 130, 230, 380], icone=None,
         desc="A broca esquenta mais rápido e o SUPERAQUECIMENTO (perfura tudo!) dura mais.",
         efeito=lambda n: f"superaquecimento de {4 + 0.9 * n:.1f} s"),
]


def icone_ima(tela, cx, cy, escala=1.0):
    e = escala
    pygame.draw.circle(tela, (225, 50, 55), (cx, int(cy + 4 * e)), int(15 * e), int(8 * e), draw_bottom_left=True, draw_bottom_right=True)
    for sx in (-1, 1):
        x = cx + sx * 11 * e
        pygame.draw.rect(tela, (225, 50, 55), (x - 4 * e, cy - 12 * e, 8 * e, 17 * e))
        pygame.draw.rect(tela, (225, 232, 245), (x - 4 * e, cy - 14 * e, 8 * e, 7 * e))
    pygame.draw.circle(tela, (255, 200, 80), (cx, int(cy - 20 * e)), max(1, int(2 * e)))


def icone_calor(tela, cx, cy, escala=1.0):
    e = escala
    ext = [(0, -18), (8, -6), (12, 4), (8, 14), (0, 18), (-8, 14), (-12, 4), (-7, -4), (-3, -9)]
    pygame.draw.polygon(tela, (255, 110, 40), [(cx + x * e, cy + y * e) for x, y in ext])
    inte = [(0, -4), (5, 5), (3, 13), (0, 15), (-3, 13), (-5, 5)]
    pygame.draw.polygon(tela, (255, 220, 100), [(cx + x * e, cy + y * e) for x, y in inte])


def desenhar_icone(tela, up, cx, cy, escala=1.0):
    if up["icone"]:
        im = util.img(up["icone"])
        if escala != 1.0:
            im = pygame.transform.smoothscale(im, (int(im.get_width() * escala), int(im.get_height() * escala)))
        tela.blit(im, im.get_rect(center=(cx, cy)))
    elif up["id"] == "ima":
        icone_ima(tela, cx, cy, escala)
    else:
        icone_calor(tela, cx, cy, escala)


# ------------------------------------------------------------------ fundo animado compartilhado
class FundoMenu:
    def __init__(self):
        bruto = util.img("fundo_menu.png")
        self.bg = pygame.transform.smoothscale(bruto, (864, 648))
        self.t = 0.0
        self.part = util.Particulas()
        self.brocas = [Sprite(f"{C.IMG}/broca.png", 8)]
        self.bx, self.by = 380.0, 330.0
        self.bvx, self.bvy = 170.0, -140.0
        self.trilha = []
        self.estrelas = [(random.uniform(0, 800), random.uniform(0, 400), random.uniform(0, 6)) for _ in range(40)]
        self.grad = self._criar_grad()

    def _criar_grad(self):
        s = pygame.Surface((C.LARGURA, C.ALTURA), pygame.SRCALPHA)
        for y in range(C.ALTURA):
            f = y / C.ALTURA
            a = int(60 + 150 * max(0, f - 0.35) / 0.65)
            pygame.draw.line(s, (6, 4, 14, a), (0, y), (C.LARGURA, y))
        return s

    def atualizar(self, dt):
        self.t += dt
        self.part.atualizar(dt)
        if random.random() < dt * 14:
            self.part.brasas(random.uniform(0, 800), C.ALTURA - 5, 1, random.choice([(255, 150, 60), (255, 100, 200), (120, 220, 255)]), 40)
        # broca decorativa quicando pela tela (clamp, como no jogo)
        self.bx += self.bvx * dt
        self.by += self.bvy * dt
        xn, yn = util.clamp(self.bx, 20, 780), util.clamp(self.by, 20, 560)
        self.bvx *= 1 - 2 * int(xn != self.bx)
        self.bvy *= 1 - 2 * int(yn != self.by)
        self.bx, self.by = xn, yn
        self.trilha.append((self.bx, self.by))
        self.trilha = self.trilha[-14:]

    def desenhar(self, tela, escurecer=0, com_broca=True):
        ox = -32 + math.sin(self.t * 0.25) * 22
        oy = -24 + math.cos(self.t * 0.19) * 14
        tela.blit(self.bg, (ox, oy))
        for x, y, f in self.estrelas:
            a = 0.5 + 0.5 * math.sin(self.t * 2 + f)
            c = int(90 + 140 * a)
            pygame.draw.circle(tela, (c, c, 255), (int(x), int(y)), 1 + (a > 0.9))
        tela.blit(self.grad, (0, 0))
        if com_broca:
            n = len(self.trilha)
            for i, (x, y) in enumerate(self.trilha):
                k = (i + 1) / n
                util.brilho(tela, int(x), int(y), int(18 * k + 3), (255, 170, 80), 0.35 * k)
            spr = self.brocas[0]
            spr.set_curr_frame(int(self.t * 16) % 8)
            spr.set_position(self.bx - 20, self.by - 20)
            # (desenha direto na tela atual)
            tela.blit(spr.image, (self.bx - 20, self.by - 20), area=pygame.Rect(spr.curr_frame * spr.width, 0, spr.width, spr.height))
            util.brilho(tela, int(self.bx), int(self.by), 36, (255, 190, 100), 0.45)
        self.part.desenhar(tela)
        if escurecer:
            s = pygame.Surface((C.LARGURA, C.ALTURA), pygame.SRCALPHA)
            s.fill((6, 4, 14, escurecer))
            tela.blit(s, (0, 0))


def moldura_titulo(tela, texto, sub=None, tam=40):
    util.texto(tela, texto, C.LARGURA // 2, 44, tam, (255, 215, 110), titulo=True, esp=3)
    if sub:
        util.texto(tela, sub, C.LARGURA // 2, 80, 14, (190, 190, 220), contorno=None)
    pygame.draw.line(tela, (255, 176, 64), (180, 100), (620, 100), 2)


def rodape(tela, s):
    util.texto(tela, s, C.LARGURA // 2, 578, 13, (170, 168, 195), contorno=None)


# ================================================================== TÍTULO
class TelaMenu:
    ITENS = ["JOGAR", "SELECIONAR FASE", "OFICINA", "RANKING", "COMO JOGAR", "CRÉDITOS", "SAIR"]

    def __init__(self, jogo):
        self.jogo = jogo
        self.sel = 0
        self.y_barra = 0.0
        self.t = 0.0

    def entrar(self, **kw):
        self.t = 0.0
        self.jogo.audio.musica("menu")

    def atualizar(self, dt, ent):
        self.t += dt
        self.jogo.fundo.atualizar(dt)
        if ent.t_cima():
            self.sel = (self.sel - 1) % len(self.ITENS)
            self.jogo.audio.tocar("menu_mover")
        if ent.t_baixo():
            self.sel = (self.sel + 1) % len(self.ITENS)
            self.jogo.audio.tocar("menu_mover")
        self.y_barra += (self.sel - self.y_barra) * min(1, dt * 14)
        if ent.t_ok():
            self.jogo.audio.tocar("menu_ok")
            return {0: ("jogar", 1), 1: ("tela", "selecao"), 2: ("tela", "oficina"), 3: ("tela", "ranking"),
                    4: ("tela", "ajuda"), 5: ("tela", "creditos"), 6: ("sair",)}[self.sel]
        return None

    def desenhar(self, tela):
        self.jogo.fundo.desenhar(tela)
        cx = C.LARGURA // 2
        t = self.t
        # título caindo com quique
        queda = util.clamp(t / 0.9, 0, 1)
        y_off = (1 - util.ease_back(queda)) * -220
        pulso = 0.5 + 0.5 * math.sin(t * 2.2)
        util.brilho(tela, cx, 150, 250, (255, 140, 40), 0.30 + 0.12 * pulso)
        util.texto(tela, "R U M O   A O", cx, int(70 + y_off), 30, (255, 238, 200), titulo=True, esp=3)
        util.texto(tela, "NÚCLEO", cx, int(138 + y_off * 1.1), 92, (255, 190, 60), titulo=True, esp=5)
        util.texto(tela, "NÚCLEO", cx, int(135 + y_off * 1.1), 92, (255, 235, 140), titulo=True, contorno=None, alfa=150)
        util.texto(tela, "uma aventura de mineração", cx, int(198 + y_off * 0.6), 17, (200, 205, 255), contorno=(10, 8, 30), alfa=int(255 * queda))
        # estrelinhas no título
        if random.random() < 0.15:
            self.jogo.fundo.part.brilho_estrela(random.uniform(220, 580), random.uniform(105, 170), (255, 245, 200), 9, 0.5)
        # lista
        y0, passo = 256, 40
        yb = y0 + self.y_barra * passo
        util.painel(tela, (cx - 170, yb - 18, 340, 36), (90, 50, 14, 205), (255, 190, 80), 10, 2)
        util.brilho(tela, cx, int(yb), 120, (255, 150, 50), 0.22)
        for i, nome in enumerate(self.ITENS):
            sel = i == self.sel
            cor = (255, 240, 190) if sel else (205, 200, 225)
            ap = util.clamp((t - 0.5 - i * 0.07) / 0.25, 0, 1)
            x = cx + (1 - util.ease_out(ap)) * (300 if i % 2 else -300)
            util.texto(tela, nome, int(x), y0 + i * passo, 25 if sel else 22, cor, alfa=int(255 * ap))
            if sel:
                util.texto(tela, "‹", int(x - 150 - 3 * math.sin(t * 8)), y0 + i * passo - 2, 26, (255, 200, 80))
                util.texto(tela, "›", int(x + 150 + 3 * math.sin(t * 8)), y0 + i * passo - 2, 26, (255, 200, 80))
        p = self.jogo.progresso
        util.texto(tela, f"RECORDE {p['recorde']:,}".replace(",", "."), 20, 580, 14, (255, 225, 150), "e", contorno=None)
        tela.blit(util.img("min_ouro.png"), (610, 570))
        util.texto(tela, f"{p['minerio']} no cofre", 636, 580, 14, (255, 225, 150), "e", contorno=None)
        util.texto(tela, "M: " + ("SOM OFF" if self.jogo.audio.mudo else "SOM ON"), 420, 580, 13, (170, 168, 195), "c", contorno=None)


# ================================================================== SELEÇÃO DE FASE
class TelaSelecao:
    def __init__(self, jogo):
        self.jogo = jogo
        self.sel = 0
        self.t = 0.0
        self.mini = {}
        self.tipos_blocos = {}

    def entrar(self, **kw):
        self.t = 0.0
        fm = self.jogo.fase_max()
        self.sel = min(self.sel, fm - 1)
        self.jogo.audio.musica("menu")
        if not self.mini:
            for f in FASES:
                bg = util.img(f["fundo"])
                self.mini[f["id"]] = pygame.transform.smoothscale(bg.subsurface((100, 120, 600, 780)).copy(), (146, 190))

    def atualizar(self, dt, ent):
        self.t += dt
        self.jogo.fundo.atualizar(dt)
        if ent.t_esq():
            self.sel = (self.sel - 1) % 5
            self.jogo.audio.tocar("menu_mover")
        if ent.t_dir():
            self.sel = (self.sel + 1) % 5
            self.jogo.audio.tocar("menu_mover")
        if ent.t_voltar():
            self.jogo.audio.tocar("menu_ok")
            return ("tela", "menu")
        if ent.t_ok():
            if self.sel + 1 <= self.jogo.fase_max():
                self.jogo.audio.tocar("menu_ok")
                return ("jogar", self.sel + 1)
            self.jogo.audio.tocar("erro")
        return None

    def desenhar(self, tela):
        self.jogo.fundo.desenhar(tela, 120)
        moldura_titulo(tela, "SELECIONAR FASE", "Termine uma fase para liberar a seguinte")
        fm = self.jogo.fase_max()
        for i, f in enumerate(FASES):
            sel = i == self.sel
            livre = i + 1 <= fm
            ap = util.clamp((self.t - i * 0.06) / 0.3, 0, 1)
            x = 28 + i * 152
            y = 130 - (14 if sel else 0) + (1 - util.ease_out(ap)) * 60
            painel_cor = f["cor"] if sel else (90, 88, 110)
            util.painel(tela, (x - 3, y - 3, 152, 242), (16, 14, 28, 235), painel_cor, 12, 3 if sel else 2)
            im = self.mini[f["id"]]
            tela.blit(im, (x, y))
            if not livre:
                s = pygame.Surface((146, 190), pygame.SRCALPHA)
                s.fill((5, 4, 10, 200))
                tela.blit(s, (x, y))
                self._cadeado(tela, x + 73, y + 95)
            else:
                util.brilho(tela, x + 73, y + 190, 80, f["cor"], 0.25 + 0.15 * sel)
            util.texto(tela, f"FASE {f['id']}", x + 73, y + 205, 15, f["cor"] if livre else (130, 128, 150), contorno=None)
            util.texto(tela, f["nome"] if livre else "???", x + 73, y + 224, 11, (235, 230, 245) if livre else (120, 118, 140), contorno=None)
        f = FASES[self.sel]
        livre = self.sel + 1 <= fm
        util.painel(tela, (28, 388, 744, 164), (14, 12, 26, 235), f["cor"], 14, 2)
        if livre:
            util.texto(tela, f["nome"].upper(), 50, 414, 26, f["cor"], "e", titulo=True)
            util.texto(tela, f["sub"], 50, 444, 15, (215, 210, 235), "e", contorno=None)
            tags = []
            if f.get("chefe"):
                tags.append(("CHEFE FINAL", (255, 90, 70)))
            if f["escuro"]:
                tags.append(("ESCURIDÃO", (150, 150, 255)))
            if f["estalactites"]:
                tags.append(("ESTALACTITES", (200, 190, 170)))
            if f["geysers"]:
                tags.append(("GÊISERES DE LAVA", (255, 130, 60)))
            if not tags:
                tags.append(("FASE CALMA", (140, 230, 150)))
            x = 50
            for nome, cor in tags:
                w = util.largura_texto(nome, 12) + 22
                util.painel(tela, (x, 468, w, 24), (30, 26, 44, 230), cor, 8, 2)
                util.texto(tela, nome, x + w // 2, 480, 12, cor, contorno=None)
                x += w + 8
            util.texto(tela, f"Profundidade: {f['prof'][0]} m  ›  {f['prof'][1]} m", 50, 516, 14, (190, 200, 225), "e", contorno=None)
            tipos = []
            for linha in f["layout"]:
                for ch in linha:
                    if ch != "." and ch not in tipos:
                        tipos.append(ch)
            util.texto(tela, "Blocos desta fase:", 520, 414, 14, (200, 195, 220), "e", contorno=None)
            nomes = {"t": "terra", "p": "pedra", "s": "prata", "o": "ouro", "d": "diamante", "g": "gema", "x": "tnt", "G": "granito"}
            for k, ch in enumerate(tipos[:6]):
                nm = nomes[ch]
                arq = f"bloco_{nm}_a.png" if nm not in ("gema", "tnt", "granito") else f"bloco_{nm}.png"
                quad = util.img(arq).subsurface((0, 0, 60, 24))
                tela.blit(pygame.transform.smoothscale(quad, (66, 26)), (520 + (k % 3) * 80, 436 + (k // 3) * 36))
        else:
            self._cadeado(tela, 70, 440, 0.8)
            util.texto(tela, "FASE TRANCADA", 110, 424, 24, (180, 176, 200), "e", titulo=True)
            util.texto(tela, f"Termine a fase {self.sel} para liberar.", 110, 458, 16, (190, 188, 215), "e", contorno=None)
        util.texto(tela, "‹ ›  escolher     ENTER  jogar     ESC  voltar", C.LARGURA // 2, 572, 13, (170, 168, 195), contorno=None)

    def _cadeado(self, tela, cx, cy, e=1.0):
        pygame.draw.rect(tela, (200, 190, 120), (cx - 20 * e, cy - 4 * e, 40 * e, 32 * e), border_radius=int(6 * e))
        pygame.draw.rect(tela, (120, 100, 50), (cx - 20 * e, cy - 4 * e, 40 * e, 32 * e), 3, border_radius=int(6 * e))
        pygame.draw.arc(tela, (190, 190, 205), (cx - 13 * e, cy - 26 * e, 26 * e, 34 * e), 0, math.pi, max(2, int(5 * e)))
        pygame.draw.circle(tela, (60, 40, 20), (int(cx), int(cy + 10 * e)), max(2, int(4 * e)))


# ================================================================== OFICINA
class TelaOficina:
    def __init__(self, jogo):
        self.jogo = jogo
        self.sel = 0
        self.t = 0.0
        self.erro = 0.0
        self.compra = 0.0
        self.part = util.Particulas()

    def entrar(self, **kw):
        self.t = 0.0
        self.jogo.audio.musica("menu")

    def nivel(self, up):
        return self.jogo.progresso["melhorias"][up["id"]]

    def custo(self, up):
        n = self.nivel(up)
        return None if n >= up["max"] else up["custos"][n]

    def atualizar(self, dt, ent):
        self.t += dt
        self.erro = max(0.0, self.erro - dt)
        self.compra = max(0.0, self.compra - dt)
        self.jogo.fundo.atualizar(dt)
        self.part.atualizar(dt)
        if ent.t_cima():
            self.sel = (self.sel - 1) % len(UPGRADES)
            self.jogo.audio.tocar("menu_mover")
        if ent.t_baixo():
            self.sel = (self.sel + 1) % len(UPGRADES)
            self.jogo.audio.tocar("menu_mover")
        if ent.t_voltar():
            self.jogo.audio.tocar("menu_ok")
            return ("tela", "menu")
        if ent.t_ok():
            up = UPGRADES[self.sel]
            c = self.custo(up)
            p = self.jogo.progresso
            if c is None or p["minerio"] < c:
                self.jogo.audio.tocar("erro")
                self.erro = 0.35
            else:
                p["minerio"] -= c
                p["melhorias"][up["id"]] += 1
                self.jogo.salvar()
                self.jogo.audio.tocar("comprar")
                self.compra = 0.6
                y = 150 + self.sel * 74
                self.part.faiscas(330, y + 30, 22, (255, 220, 110), 340, 0.7)
                self.part.anel(70, y + 30, 50, (255, 220, 110), 0.5, 4)
                self.part.confete(330, y + 30, 12)
        return None

    def desenhar(self, tela):
        self.jogo.fundo.desenhar(tela, 140, com_broca=False)
        moldura_titulo(tela, "OFICINA DO MINEIRO", "Troque o minério por melhorias permanentes", 34)
        p = self.jogo.progresso
        util.painel(tela, (650, 22, 130, 40), (30, 24, 8, 230), (255, 205, 90), 12, 2)
        tela.blit(util.img("min_ouro.png"), (662, 32))
        util.texto(tela, f"{p['minerio']}", 770, 42, 22, (255, 225, 110), "d", titulo=True)
        for i, up in enumerate(UPGRADES):
            sel = i == self.sel
            n = self.nivel(up)
            ap = util.clamp((self.t - i * 0.06) / 0.25, 0, 1)
            x, y = 24 - (1 - util.ease_out(ap)) * 200, 118 + i * 74
            if sel and self.erro > 0:
                x += math.sin(self.erro * 70) * 6
            borda = (255, 190, 80) if sel else (80, 78, 105)
            util.painel(tela, (x, y, 430, 66), (30, 22, 14, 235) if sel else (16, 14, 28, 225), borda, 12, 3 if sel else 2)
            util.painel(tela, (x + 8, y + 8, 50, 50), (8, 6, 16, 240), (110, 100, 130), 10, 2)
            desenhar_icone(tela, up, int(x + 33), int(y + 33))
            util.texto(tela, up["nome"], int(x + 70), int(y + 20), 17, (255, 240, 200) if sel else (210, 205, 225), "e", contorno=None)
            for k in range(up["max"]):
                cx = int(x + 78 + k * 22)
                cor = (255, 190, 60) if k < n else (50, 46, 68)
                pygame.draw.polygon(tela, cor, [(cx, y + 40), (cx + 8, y + 46), (cx, y + 56), (cx - 8, y + 46)])
                pygame.draw.polygon(tela, (20, 14, 8), [(cx, y + 40), (cx + 8, y + 46), (cx, y + 56), (cx - 8, y + 46)], 1)
            c = self.custo(up)
            if c is None:
                util.texto(tela, "MÁXIMO", int(x + 415), int(y + 33), 17, (130, 235, 150), "d", titulo=True)
            else:
                pode = p["minerio"] >= c
                tela.blit(util.img("min_ouro.png"), (int(x + 342), int(y + 22)))
                util.texto(tela, f"{c}", int(x + 418), int(y + 33), 22, (255, 225, 110) if pode else (225, 110, 100), "d", titulo=True)
        # painel de detalhes
        up = UPGRADES[self.sel]
        n = self.nivel(up)
        util.painel(tela, (470, 118, 306, 360), (14, 12, 26, 238), (255, 190, 80), 16, 2)
        util.painel(tela, (595, 138, 56, 56), (8, 6, 16, 245), (255, 190, 80), 12, 2)
        desenhar_icone(tela, up, 623, 166, 1.2)
        util.texto(tela, up["nome"].upper(), 623, 216, 16, (255, 220, 120), "c", contorno=None)
        self._paragrafo(tela, up["desc"], 486, 240, 274, 14, (215, 210, 235))
        util.texto(tela, "AGORA", 486, 336, 12, (160, 160, 190), "e", contorno=None)
        util.texto(tela, up["efeito"](n), 486, 356, 16, (255, 240, 200), "e", contorno=None)
        if n < up["max"]:
            util.texto(tela, "PRÓXIMO NÍVEL", 486, 390, 12, (130, 230, 150), "e", contorno=None)
            util.texto(tela, up["efeito"](n + 1), 486, 410, 17, (150, 255, 170), "e", contorno=None)
            pode = p["minerio"] >= self.custo(up)
            util.texto(tela, "ENTER  ›  COMPRAR" if pode else "minério insuficiente", 623, 454, 16, (255, 240, 200) if pode else (225, 120, 110), "c", contorno=None)
        else:
            util.texto(tela, "Melhoria no nível máximo!", 486, 410, 16, (150, 255, 170), "e", contorno=None)
        if self.compra > 0:
            util.brilho(tela, 623, 166, 110, (255, 220, 110), self.compra * 1.3)
        self.part.desenhar(tela)
        rodape(tela, "↑ ↓ escolher     ENTER comprar     ESC voltar")

    def _paragrafo(self, tela, s, x, y, larg, tam, cor):
        palavras, linha, yy = s.split(), "", y
        for w in palavras:
            teste = (linha + " " + w).strip()
            if util.largura_texto(teste, tam) > larg:
                util.texto(tela, linha, x, yy, tam, cor, "e", contorno=None)
                linha, yy = w, yy + tam + 6
            else:
                linha = teste
        if linha:
            util.texto(tela, linha, x, yy, tam, cor, "e", contorno=None)


# ================================================================== RANKING
class TelaRanking:
    def __init__(self, jogo):
        self.jogo = jogo
        self.t = 0.0
        self.destaque = -1
        self.dados = []

    def entrar(self, destaque=-1, **kw):
        self.t = 0.0
        self.destaque = destaque
        self.dados = dados.carregar_ranking()
        self.jogo.audio.musica("menu")

    def atualizar(self, dt, ent):
        self.t += dt
        self.jogo.fundo.atualizar(dt)
        if ent.t_voltar() or ent.t_ok():
            self.jogo.audio.tocar("menu_ok")
            return ("tela", "menu")
        return None

    def desenhar(self, tela):
        self.jogo.fundo.desenhar(tela, 130, com_broca=False)
        moldura_titulo(tela, "RANKING DOS MINEIROS", "Os melhores escavadores de todos os tempos")
        cab = 128
        util.texto(tela, "#", 90, cab, 13, (160, 160, 190), "c", contorno=None)
        util.texto(tela, "NOME", 150, cab, 13, (160, 160, 190), "e", contorno=None)
        util.texto(tela, "PONTOS", 520, cab, 13, (160, 160, 190), "d", contorno=None)
        util.texto(tela, "FASE", 590, cab, 13, (160, 160, 190), "c", contorno=None)
        util.texto(tela, "DATA", 690, cab, 13, (160, 160, 190), "c", contorno=None)
        medalhas = [(255, 215, 80), (215, 222, 235), (215, 140, 80)]
        for i, e in enumerate(self.dados):
            ap = util.clamp((self.t - i * 0.07) / 0.3, 0, 1)
            x_off = (1 - util.ease_out(ap)) * 500
            y = 160 + i * 38
            dest = i == self.destaque
            cor_fundo = (60, 40, 10, 230) if dest else (18, 16, 30, 215)
            borda = medalhas[i] if i < 3 else ((255, 220, 90) if dest else (70, 68, 95))
            util.painel(tela, (int(70 + x_off), y - 16, 660, 32), cor_fundo, borda, 10, 2)
            cor = medalhas[i] if i < 3 else (225, 220, 240)
            if dest:
                cor = (255, 245, 150) if int(self.t * 4) % 2 == 0 else (255, 200, 80)
            if i < 3:
                pygame.draw.circle(tela, medalhas[i], (int(90 + x_off), y), 11)
                pygame.draw.circle(tela, (30, 20, 8), (int(90 + x_off), y), 11, 2)
                util.texto(tela, str(i + 1), int(90 + x_off), y, 14, (30, 20, 8), "c", contorno=None)
            else:
                util.texto(tela, str(i + 1), int(90 + x_off), y, 16, cor, "c", contorno=None)
            util.texto(tela, e["nome"], int(150 + x_off), y, 19, cor, "e", contorno=None)
            util.texto(tela, f"{int(e['pontos']):,}".replace(",", "."), int(520 + x_off), y, 19, cor, "d", contorno=None)
            util.texto(tela, str(e["fase"]), int(590 + x_off), y, 17, cor, "c", contorno=None)
            util.texto(tela, str(e["data"]), int(690 + x_off), y, 15, (170, 168, 195), "c", contorno=None)
        rodape(tela, "ENTER ou ESC para voltar")


# ================================================================== COMO JOGAR
class TelaAjuda:
    def __init__(self, jogo):
        self.jogo = jogo
        self.pagina = 0
        self.t = 0.0

    def entrar(self, **kw):
        self.pagina = 0
        self.t = 0.0
        self.jogo.audio.musica("menu")

    def atualizar(self, dt, ent):
        self.t += dt
        self.jogo.fundo.atualizar(dt)
        if ent.t_dir() or ent.t_ok():
            if self.pagina < 2:
                self.pagina += 1
                self.jogo.audio.tocar("menu_mover")
            else:
                self.jogo.audio.tocar("menu_ok")
                return ("tela", "menu")
        if ent.t_esq() and self.pagina > 0:
            self.pagina -= 1
            self.jogo.audio.tocar("menu_mover")
        if ent.t_voltar():
            self.jogo.audio.tocar("menu_ok")
            return ("tela", "menu")
        return None

    def desenhar(self, tela):
        self.jogo.fundo.desenhar(tela, 150, com_broca=False)
        moldura_titulo(tela, "COMO JOGAR", f"página {self.pagina + 1} de 3")
        [self._p1, self._p2, self._p3][self.pagina](tela)
        rodape(tela, "‹ › trocar de página     ESC voltar" if self.pagina < 2 else "‹ › trocar de página     ENTER voltar ao menu")

    def _linha(self, tela, y, icone, titulo, desc, cor=(255, 225, 130)):
        util.painel(tela, (50, y - 22, 700, 46), (16, 14, 28, 225), (70, 68, 95), 10, 2)
        icone(tela, 84, y)
        util.texto(tela, titulo, 130, y - 8, 16, cor, "e", contorno=None)
        util.texto(tela, desc, 130, y + 12, 13, (205, 200, 225), "e", contorno=None)

    def _p1(self, tela):
        itens = [
            ("← →  ou  A D", "Move a vagoneta (plataforma).", lambda t, x, y: self._tecla(t, x, y, "◄ ►")),
            ("ESPAÇO / ENTER", "Lança a broca. Em qualquer momento também confirma menus.", lambda t, x, y: self._tecla(t, x, y, "␣")),
            ("P  ou  ESC", "Pausa o jogo.", lambda t, x, y: self._tecla(t, x, y, "P")),
            ("M", "Liga e desliga o som.", lambda t, x, y: self._tecla(t, x, y, "M")),
        ]
        for i, (a, b, ic) in enumerate(itens):
            self._linha(tela, 150 + i * 56, ic, a, b)
        util.texto(tela, "OBJETIVO", 400, 396, 18, (255, 190, 80), contorno=None)
        txt = ["Escave todos os blocos para descer até o Núcleo da Terra.",
               "Rebata a broca na vagoneta: se ela cair na LAVA, você perde uma vida.",
               "Apanhe o minério que cai: ele vira dinheiro para a OFICINA!"]
        for i, s in enumerate(txt):
            util.texto(tela, s, 400, 430 + i * 28, 15, (225, 220, 240), contorno=None)

    def _tecla(self, tela, x, y, s):
        util.painel(tela, (x - 18, y - 16, 36, 32), (40, 36, 60, 255), (200, 190, 230), 7, 2)
        util.texto(tela, s, x, y, 14, (255, 240, 200), contorno=None)

    def _p2(self, tela):
        util.texto(tela, "BLOCOS E MINÉRIOS", 400, 124, 17, (255, 190, 80), contorno=None)
        dados_b = [("terra", "Terra", "1 golpe", "cobre"), ("pedra", "Pedra", "2 golpes", "cobre"), ("prata", "Prata", "3 golpes", "prata ◆3"),
                   ("ouro", "Ouro", "4 golpes", "ouro ◆6"), ("diamante", "Diamante", "5 golpes", "diamante ◆15")]
        for i, (k, nome, hp, mi) in enumerate(dados_b):
            y = 160 + i * 40
            util.painel(tela, (50, y - 16, 340, 34), (16, 14, 28, 225), (70, 68, 95), 10, 2)
            sheet = util.img(f"bloco_{k}_a.png")
            tela.blit(sheet.subsurface((0, 0, 60, 24)), (60, y - 12))
            util.texto(tela, nome, 135, y, 15, (255, 235, 190), "e", contorno=None)
            util.texto(tela, hp, 225, y, 13, (200, 200, 225), "e", contorno=None)
            util.texto(tela, mi, 310, y, 13, COR_MINERIO.get(mi.split()[0], (255, 225, 110)), "e", contorno=None)
        especiais = [("bloco_gema.png", 4, "Gema", "Sempre solta um power-up!"),
                     ("bloco_granito.png", 1, "Granito", "Indestrutível — só a explosão quebra."),
                     ("bloco_tnt.png", 2, "TNT", "Explode e leva os vizinhos junto (em cadeia!).")]
        for i, (arq, fr, nome, desc) in enumerate(especiais):
            y = 160 + i * 52
            util.painel(tela, (410, y - 20, 340, 44), (16, 14, 28, 225), (70, 68, 95), 10, 2)
            sheet = util.img(arq)
            w = sheet.get_width() // fr
            tela.blit(sheet.subsurface((0, 0, w, 24)), (420, y - 12))
            util.texto(tela, nome, 490, y - 7, 14, (255, 235, 190), "e", contorno=None)
            util.texto(tela, desc, 490, y + 11, 11, (205, 200, 225), "e", contorno=None)
        util.texto(tela, "SISTEMAS DA MINA", 400, 380, 17, (255, 190, 80), contorno=None)
        regras = [("COMBO", "Cada bloco seguido sem tocar na vagoneta aumenta o multiplicador (até x5)."),
                  ("CALOR", "Acertar blocos esquenta a broca. No máximo: SUPERAQUECIMENTO — ela perfura tudo!"),
                  ("LAVA", "O chão é lava. Minério que cai nela se perde para sempre."),
                  ("COFRE", "O minério coletado fica salvo, mesmo se você perder. Gaste na OFICINA.")]
        for i, (a, b) in enumerate(regras):
            util.texto(tela, a, 60, 414 + i * 34, 15, (255, 215, 110), "e", contorno=None)
            util.texto(tela, b, 150, 414 + i * 34, 13, (215, 210, 235), "e", contorno=None)

    def _p3(self, tela):
        util.texto(tela, "POWER-UPS (caem dos blocos)", 400, 124, 17, (255, 190, 80), contorno=None)
        pus = [("viga", "Viga de Aço", "Plataforma 50% maior por 14 s."), ("cristal", "Multibroca", "Cada broca se divide em três!"),
               ("picareta", "Picareta x2", "Dano dobrado por 10 s."), ("dinamite", "Dinamite", "Os próximos 3 impactos explodem."),
               ("capacete", "Capacete", "+1 vida extra."), ("lanterna", "Lanterna", "Ilumina a escuridão e atrai minério.")]
        for i, (k, nome, desc) in enumerate(pus):
            col, lin = i % 2, i // 2
            x, y = 40 + col * 370, 160 + lin * 62
            util.painel(tela, (x, y - 24, 360, 52), (16, 14, 28, 225), (70, 68, 95), 10, 2)
            tela.blit(util.img(f"pu_{k}.png"), (x + 10, y - 17))
            util.texto(tela, nome, x + 56, y - 8, 15, (255, 235, 190), "e", contorno=None)
            util.texto(tela, desc, x + 56, y + 12, 12, (205, 200, 225), "e", contorno=None)
        util.texto(tela, "PERIGOS", 400, 372, 17, (255, 190, 80), contorno=None)
        per = ["Estalactites: blocos tremem e soltam pedras. Quebre-as com a broca ou desvie!",
               "Gêiseres de lava (fase 4): fuja da faixa vermelha no chão.",
               "Atordoada, a vagoneta fica lenta — fique de olho na broca.",
               "Fase 3 é escura: ouro e diamante brilham mesmo no escuro."]
        for i, s in enumerate(per):
            util.texto(tela, "• " + s, 70, 406 + i * 30, 14, (225, 220, 240), "e", contorno=None)


# ================================================================== CRÉDITOS
class TelaCreditos:
    def __init__(self, jogo):
        self.jogo = jogo
        self.t = 0.0

    def entrar(self, **kw):
        self.t = 0.0
        self.jogo.audio.musica("menu")

    def atualizar(self, dt, ent):
        self.t += dt
        self.jogo.fundo.atualizar(dt)
        if ent.t_voltar() or (ent.t_ok() and self.t > 0.6):
            self.jogo.audio.tocar("menu_ok")
            return ("tela", "menu")
        return None

    def desenhar(self, tela):
        self.jogo.fundo.desenhar(tela, 110)
        linhas = [
            ("RUMO AO NÚCLEO", 44, (255, 200, 80)),
            ("um jogo de mineração estilo Breakout", 16, (200, 205, 255)),
            ("", 20, None),
            ("PROJETO FINAL", 16, (255, 190, 80)),
            ("Laboratório de Programação de Jogos", 20, (255, 245, 225)),
            ("Ciência da Computação — UFF", 18, (230, 225, 245)),
            ("", 20, None),
            ("DESENVOLVIMENTO", 16, (255, 190, 80)),
            (C.AUTOR, 24, (255, 245, 225)),
            ("", 20, None),
            ("TECNOLOGIA", 16, (255, 190, 80)),
            ("Python  •  PPlay  •  Pygame", 20, (255, 245, 225)),
            ("Gráficos e sons gerados por código", 16, (230, 225, 245)),
            ("", 20, None),
            ("OBRIGADO POR JOGAR!", 28, (255, 215, 110)),
        ]
        total = len(linhas) * 38
        y = C.ALTURA + 20 - (self.t * 42) % (total + C.ALTURA + 40)
        for s, tam, cor in linhas:
            if s:
                util.texto(tela, s, C.LARGURA // 2, int(y), tam, cor, titulo=tam >= 28)
            y += 38
        rodape(tela, "ESC voltar")


# ================================================================== NOME NO RANKING
class TelaNome:
    def __init__(self, jogo):
        self.jogo = jogo
        self.nome = ""
        self.t = 0.0
        self.pontos = 0
        self.fase = 1
        self.vitoria = False
        self.part = util.Particulas()

    def entrar(self, pontos=0, fase=1, vitoria=False, **kw):
        self.nome = ""
        self.t = 0.0
        self.pontos, self.fase, self.vitoria = pontos, fase, vitoria
        self.jogo.audio.musica("menu")
        self.part.confete(400, 200, 50)

    def atualizar(self, dt, ent):
        self.t += dt
        self.jogo.fundo.atualizar(dt)
        self.part.atualizar(dt)
        for c in ent.digitado():
            if len(self.nome) < 8 and (c != " " or self.nome):
                self.nome += c
                self.jogo.audio.tocar("menu_mover")
        if ent.tocou(pygame.K_BACKSPACE) and self.nome:
            self.nome = self.nome[:-1]
        if ent.tocou(pygame.K_RETURN, pygame.K_KP_ENTER):
            self.jogo.audio.tocar("comprar")
            idx = dados.inserir_ranking(self.nome or "MINEIRO", self.pontos, self.fase)
            return ("tela", "ranking", {"destaque": idx})
        return None

    def desenhar(self, tela):
        self.jogo.fundo.desenhar(tela, 150, com_broca=False)
        cx = C.LARGURA // 2
        util.brilho(tela, cx, 150, 240, (255, 200, 80), 0.3 + 0.1 * math.sin(self.t * 3))
        util.texto(tela, "NOVO RECORDE!", cx, 110, 58, (255, 220, 100), titulo=True, esp=3)
        util.texto(tela, f"{self.pontos:,}".replace(",", ".") + " pontos", cx, 170, 28, (255, 245, 225), titulo=True)
        util.painel(tela, (cx - 230, 230, 460, 190), (14, 12, 26, 240), (255, 190, 80), 16, 3)
        util.texto(tela, "DIGITE SEU NOME", cx, 262, 18, (200, 195, 225), contorno=None)
        util.painel(tela, (cx - 170, 292, 340, 62), (6, 4, 12, 255), (255, 200, 90), 10, 2)
        cursor = "_" if int(self.t * 2.5) % 2 == 0 else " "
        util.texto(tela, self.nome + cursor, cx, 324, 38, (255, 235, 160), titulo=True)
        util.texto(tela, "letras e números  •  máx. 8  •  BACKSPACE apaga", cx, 378, 13, (170, 168, 195), contorno=None)
        util.texto(tela, "ENTER  ›  confirmar", cx, 402, 16, (255, 240, 200), alfa=int(170 + 85 * math.sin(self.t * 5)), contorno=None)
        self.part.desenhar(tela)
