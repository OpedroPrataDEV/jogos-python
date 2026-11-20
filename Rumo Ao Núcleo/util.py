"""Utilidades: matemática, colisão, entrada, texto, brilho, partículas e áudio."""
import math
import os
import random

import pygame

import config as C


# =============================================================== matemática
def clamp(v, a, b):
    return a if v < a else (b if v > b else v)


def lerp(a, b, t):
    return a + (b - a) * t


def suave(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def ease_out(t):
    t = clamp(t, 0.0, 1.0)
    return 1 - (1 - t) ** 3


def ease_back(t):
    t = clamp(t, 0.0, 1.0)
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def misturar(c1, c2, t):
    t = clamp(t, 0.0, 1.0)
    return (int(c1[0] + (c2[0] - c1[0]) * t), int(c1[1] + (c2[1] - c1[1]) * t), int(c1[2] + (c2[2] - c1[2]) * t))


# =============================================================== colisão (feita à mão, sem usar o collided do PPlay)
def colidiu(a, b):
    """Sobreposição de dois retângulos (objetos com x, y, width, height)."""
    return (a.x < b.x + b.width and a.x + a.width > b.x and
            a.y < b.y + b.height and a.y + a.height > b.y)


def circulo_retangulo(cx, cy, r, rx, ry, rw, rh):
    """Círculo x retângulo. Retorna None ou (normal_x, normal_y, penetração)."""
    px = rx if cx < rx else (rx + rw if cx > rx + rw else cx)
    py = ry if cy < ry else (ry + rh if cy > ry + rh else cy)
    dx, dy = cx - px, cy - py
    d2 = dx * dx + dy * dy
    if d2 >= r * r:
        return None
    if d2 > 1e-8:
        d = math.sqrt(d2)
        return dx / d, dy / d, r - d
    esq, dir_, topo, base = cx - rx, rx + rw - cx, cy - ry, ry + rh - cy
    m = min(esq, dir_, topo, base)
    if m == topo:
        return 0.0, -1.0, r + topo
    if m == base:
        return 0.0, 1.0, r + base
    if m == esq:
        return -1.0, 0.0, r + esq
    return 1.0, 0.0, r + dir_


# =============================================================== imagens
_cache_img = {}


def img(nome, escala=None):
    chave = (nome, escala)
    if chave not in _cache_img:
        s = pygame.image.load(os.path.join(C.IMG, nome)).convert_alpha()
        if escala:
            s = pygame.transform.smoothscale(s, escala)
        _cache_img[chave] = s
    return _cache_img[chave]


# =============================================================== entrada de teclado
def _montar_teclas():
    ks = [pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN, pygame.K_SPACE, pygame.K_RETURN,
          pygame.K_KP_ENTER, pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_TAB, pygame.K_MINUS]
    ks += [getattr(pygame, "K_" + c) for c in "abcdefghijklmnopqrstuvwxyz"]
    ks += [getattr(pygame, "K_" + str(n)) for n in range(10)]
    return ks


class Entrada:
    """Lê o teclado direto do pygame (funciona junto com a Window do PPlay)."""
    TECLAS = _montar_teclas()
    fonte = None  # usado nos testes automáticos para injetar teclas

    def __init__(self):
        self.agora = set()
        self.antes = set()

    def atualizar(self):
        self.antes = self.agora
        if Entrada.fonte is not None:
            self.agora = set(Entrada.fonte())
            return
        pygame.event.pump()
        ks = pygame.key.get_pressed()
        self.agora = {k for k in self.TECLAS if ks[k]}

    def segurando(self, *teclas):
        return any(k in self.agora for k in teclas)

    def tocou(self, *teclas):
        return any(k in self.agora and k not in self.antes for k in teclas)

    # ações compostas
    def esquerda(self):
        return self.segurando(pygame.K_LEFT, pygame.K_a)

    def direita(self):
        return self.segurando(pygame.K_RIGHT, pygame.K_d)

    def t_cima(self):
        return self.tocou(pygame.K_UP, pygame.K_w)

    def t_baixo(self):
        return self.tocou(pygame.K_DOWN, pygame.K_s)

    def t_esq(self):
        return self.tocou(pygame.K_LEFT, pygame.K_a)

    def t_dir(self):
        return self.tocou(pygame.K_RIGHT, pygame.K_d)

    def t_ok(self):
        return self.tocou(pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)

    def t_voltar(self):
        return self.tocou(pygame.K_ESCAPE, pygame.K_BACKSPACE)

    def t_pausa(self):
        return self.tocou(pygame.K_p, pygame.K_ESCAPE)

    def digitado(self):
        """Caracteres (A-Z, 0-9) pressionados neste frame, para digitar o nome."""
        s = ""
        for c in "abcdefghijklmnopqrstuvwxyz0123456789":
            k = getattr(pygame, "K_" + c)
            if self.tocou(k):
                s += c.upper()
        if self.tocou(pygame.K_SPACE):
            s += " "
        if self.tocou(pygame.K_MINUS):
            s += "-"
        return s


# =============================================================== texto
_fontes = {}
_cache_txt = {}
_NOMES_TEXTO = "arial,segoeui,verdana,tahoma,dejavusans,liberationsans"
_NOMES_TITULO = "impact,arialblack,franklingothicheavy,arial,segoeui,dejavusans"


def fonte(tam, titulo=False):
    chave = (tam, titulo)
    if chave not in _fontes:
        _fontes[chave] = pygame.font.SysFont(_NOMES_TITULO if titulo else _NOMES_TEXTO, tam, bold=not titulo)
    return _fontes[chave]


def _texto_surf(s, tam, cor, titulo, contorno, esp):
    chave = (s, tam, cor, titulo, contorno, esp)
    surf = _cache_txt.get(chave)
    if surf is None:
        if len(_cache_txt) > 900:
            _cache_txt.clear()
        base = fonte(tam, titulo).render(s, True, cor)
        if contorno:
            w, h = base.get_size()
            surf = pygame.Surface((w + 2 * esp, h + 2 * esp), pygame.SRCALPHA)
            sombra = fonte(tam, titulo).render(s, True, contorno)
            for dx in range(-esp, esp + 1):
                for dy in range(-esp, esp + 1):
                    if dx or dy:
                        surf.blit(sombra, (esp + dx, esp + dy))
            surf.blit(base, (esp, esp))
        else:
            surf = base
        _cache_txt[chave] = surf
    return surf


def texto(tela, s, x, y, tam=20, cor=(255, 255, 255), ancora="c", titulo=False, contorno=(8, 6, 14), esp=2, alfa=255):
    surf = _texto_surf(str(s), tam, cor, titulo, contorno, esp)
    r = surf.get_rect()
    if ancora == "c":
        r.center = (x, y)
    elif ancora == "e":
        r.midleft = (x, y)
    else:
        r.midright = (x, y)
    if alfa < 255:
        surf.set_alpha(alfa)
        tela.blit(surf, r)
        surf.set_alpha(255)
    else:
        tela.blit(surf, r)
    return r


def largura_texto(s, tam, titulo=False):
    return fonte(tam, titulo).size(str(s))[0]


# =============================================================== painéis / barras
_cache_painel = {}


def painel(tela, rect, fundo=(14, 12, 24, 215), borda=(255, 176, 64), raio=12, largura_borda=2):
    r = pygame.Rect(rect)
    chave = (r.w, r.h, fundo, borda, raio, largura_borda)
    s = _cache_painel.get(chave)
    if s is None:
        if len(_cache_painel) > 120:
            _cache_painel.clear()
        s = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        pygame.draw.rect(s, fundo, s.get_rect(), border_radius=raio)
        if borda and largura_borda:
            pygame.draw.rect(s, borda, s.get_rect(), largura_borda, border_radius=raio)
        _cache_painel[chave] = s
    tela.blit(s, r.topleft)


def barra(tela, x, y, w, h, frac, cor_a, cor_b, fundo=(20, 18, 28), borda=(255, 255, 255)):
    frac = clamp(frac, 0.0, 1.0)
    pygame.draw.rect(tela, fundo, (x, y, w, h), border_radius=h // 2)
    pw = int((w - 2) * frac)
    if pw > 1:
        for i in range(pw):
            t = i / max(1, w - 3)
            pygame.draw.line(tela, misturar(cor_a, cor_b, t), (x + 1 + i, y + 1), (x + 1 + i, y + h - 2))
    if borda:
        pygame.draw.rect(tela, borda, (x, y, w, h), 1, border_radius=h // 2)


# =============================================================== brilho aditivo
_cache_brilho = {}


def _surf_brilho(raio, cor, intens):
    chave = (raio, cor, round(intens, 2))
    s = _cache_brilho.get(chave)
    if s is None:
        if len(_cache_brilho) > 260:
            _cache_brilho.clear()
        s = pygame.Surface((raio * 2, raio * 2))
        s.fill((0, 0, 0))
        passo = 1 if raio < 40 else 2
        for i in range(raio, 0, -passo):
            a = (1 - i / raio) ** 2 * intens
            pygame.draw.circle(s, (min(255, int(cor[0] * a)), min(255, int(cor[1] * a)), min(255, int(cor[2] * a))), (raio, raio), i)
        _cache_brilho[chave] = s
    return s


def brilho(tela, x, y, raio, cor=(255, 160, 60), intens=1.0):
    raio = int(raio)
    if raio < 2:
        return
    tela.blit(_surf_brilho(raio, cor, intens), (x - raio, y - raio), special_flags=pygame.BLEND_RGB_ADD)


# =============================================================== partículas
class Particulas:
    MAX = 520

    def __init__(self):
        self.p = []

    def _add(self, **kw):
        if len(self.p) >= self.MAX:
            self.p.pop(0)
        kw.setdefault("grav", 0.0)
        kw.setdefault("arrasto", 0.0)
        kw.setdefault("rot", 0.0)
        kw.setdefault("vrot", 0.0)
        kw["vida0"] = kw["vida"]
        self.p.append(kw)

    # ---- emissores
    def faiscas(self, x, y, n=8, cor=(255, 200, 110), vel=300, vida=0.45, ang=None, abertura=math.tau, grav=300):
        for _ in range(n):
            a = (ang if ang is not None else 0) + random.uniform(-abertura / 2, abertura / 2)
            v = random.uniform(vel * 0.4, vel)
            self._add(tipo="faisca", x=x, y=y, vx=math.cos(a) * v, vy=math.sin(a) * v, vida=vida * random.uniform(0.6, 1.1),
                      cor=cor, tam=2, grav=grav, arrasto=1.2)

    def detritos(self, x, y, n=8, cor=(150, 108, 68), vel=230):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            v = random.uniform(vel * 0.3, vel)
            c = tuple(int(clamp(k * random.uniform(0.7, 1.2), 0, 255)) for k in cor)
            self._add(tipo="detrito", x=x, y=y, vx=math.cos(a) * v, vy=math.sin(a) * v - 90, vida=random.uniform(0.5, 0.95),
                      cor=c, tam=random.uniform(2, 4.6), grav=720, rot=random.uniform(0, 6), vrot=random.uniform(-9, 9))

    def fumaca(self, x, y, n=3, cor=(88, 84, 82), tam=8):
        for _ in range(n):
            self._add(tipo="fumaca", x=x + random.uniform(-6, 6), y=y + random.uniform(-4, 4), vx=random.uniform(-20, 20),
                      vy=random.uniform(-60, -20), vida=random.uniform(0.6, 1.1), cor=cor, tam=tam * random.uniform(0.7, 1.3))

    def brasas(self, x, y, n=3, cor=(255, 140, 50), vel=60):
        for _ in range(n):
            self._add(tipo="brasa", x=x + random.uniform(-8, 8), y=y, vx=random.uniform(-vel, vel), vy=random.uniform(-vel * 2, -vel * 0.6),
                      vida=random.uniform(0.7, 1.4), cor=cor, tam=random.uniform(3, 6), arrasto=0.3)

    def brilho_estrela(self, x, y, cor=(255, 255, 255), tam=5, vida=0.5):
        self._add(tipo="estrela", x=x, y=y, vx=0, vy=0, vida=vida, cor=cor, tam=tam)

    def texto(self, x, y, s, cor=(255, 255, 255), tam=18, vida=0.9, vy=-48):
        self._add(tipo="texto", x=x, y=y, vx=0, vy=vy, vida=vida, cor=cor, tam=tam, s=s, arrasto=1.2)

    def anel(self, x, y, raio, cor=(255, 200, 120), vida=0.45, largura=4):
        self._add(tipo="anel", x=x, y=y, vx=0, vy=0, vida=vida, cor=cor, tam=raio, largura=largura)

    def confete(self, x, y, n=30, cores=((255, 210, 70), (120, 220, 255), (255, 120, 190), (140, 255, 170))):
        for _ in range(n):
            a = random.uniform(-math.pi, 0)
            v = random.uniform(160, 520)
            self._add(tipo="confete", x=x, y=y, vx=math.cos(a) * v, vy=math.sin(a) * v, vida=random.uniform(1.4, 2.6),
                      cor=random.choice(cores), tam=random.uniform(3, 6), grav=420, arrasto=0.8, rot=random.uniform(0, 6), vrot=random.uniform(-12, 12))

    def explosao(self, x, y, raio=90):
        self.anel(x, y, raio * 1.25, (255, 230, 150), 0.38, 6)
        self.anel(x, y, raio * 0.8, (255, 120, 40), 0.5, 4)
        self.faiscas(x, y, int(raio * 0.35), (255, 210, 110), 520, 0.7)
        self.detritos(x, y, int(raio * 0.18), (120, 100, 90), 380)
        self.fumaca(x, y, int(raio * 0.12), (70, 66, 64), 16)
        self.brasas(x, y, 10, (255, 150, 50), 120)

    # ---- atualização / desenho
    def atualizar(self, dt):
        vivos = []
        for p in self.p:
            p["vida"] -= dt
            if p["vida"] <= 0:
                continue
            if p["arrasto"]:
                f = max(0.0, 1 - p["arrasto"] * dt)
                p["vx"] *= f
                p["vy"] *= f
            p["vy"] += p["grav"] * dt
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["rot"] += p["vrot"] * dt
            vivos.append(p)
        self.p = vivos

    def desenhar(self, tela):
        for p in self.p:
            t = p["vida"] / p["vida0"]
            tipo = p["tipo"]
            x, y = p["x"], p["y"]
            if tipo == "faisca":
                c = (int(p["cor"][0] * t), int(p["cor"][1] * t), int(p["cor"][2] * t))
                pygame.draw.line(tela, c, (x, y), (x - p["vx"] * 0.035, y - p["vy"] * 0.035), 2)
            elif tipo in ("detrito", "confete"):
                r = p["tam"] * (1 if tipo == "confete" else (0.5 + 0.5 * t))
                ca, sa = math.cos(p["rot"]) * r, math.sin(p["rot"]) * r
                pts = [(x - ca - sa * 0.6, y - sa + ca * 0.6), (x + ca - sa * 0.6, y + sa + ca * 0.6),
                       (x + ca + sa * 0.6, y + sa - ca * 0.6), (x - ca + sa * 0.6, y - sa - ca * 0.6)]
                pygame.draw.polygon(tela, p["cor"], pts)
            elif tipo == "fumaca":
                r = int(p["tam"] * (1.6 - t * 0.6))
                if r > 1:
                    s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                    pygame.draw.circle(s, p["cor"] + (int(110 * t),), (r, r), r)
                    tela.blit(s, (x - r, y - r))
            elif tipo == "brasa":
                brilho(tela, int(x), int(y), int(p["tam"] * 2.4 * (0.4 + 0.6 * t)), p["cor"], 1.1 * t + 0.2)
            elif tipo == "estrela":
                r = p["tam"] * (0.3 + 0.7 * math.sin(t * math.pi))
                c = (int(p["cor"][0] * t), int(p["cor"][1] * t), int(p["cor"][2] * t))
                pygame.draw.line(tela, c, (x - r, y), (x + r, y), 1)
                pygame.draw.line(tela, c, (x, y - r), (x, y + r), 1)
                pygame.draw.circle(tela, c, (int(x), int(y)), max(1, int(r * 0.25)))
            elif tipo == "texto":
                texto(tela, p["s"], int(x), int(y), p["tam"], p["cor"], alfa=int(255 * clamp(t * 2.2, 0, 1)))
            elif tipo == "anel":
                prog = 1 - t
                r = int(p["tam"] * (0.25 + 0.75 * ease_out(prog)))
                larg = max(1, int(p["largura"] * t))
                c = (int(p["cor"][0] * t), int(p["cor"][1] * t), int(p["cor"][2] * t))
                if r > 2:
                    s = pygame.Surface((r * 2 + 4, r * 2 + 4))
                    s.fill((0, 0, 0))
                    pygame.draw.circle(s, c, (r + 2, r + 2), r, larg)
                    tela.blit(s, (x - r - 2, y - r - 2), special_flags=pygame.BLEND_RGB_ADD)


# =============================================================== áudio
class Audio:
    def __init__(self):
        self.ok = False
        self.mudo = False
        self.sons = {}
        self.musica_atual = None
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            pygame.mixer.set_num_channels(24)
            self.ok = True
        except Exception:
            self.ok = False
        if self.ok:
            for arq in sorted(os.listdir(C.SOM)):
                if arq.endswith(".wav") and not arq.startswith("musica_"):
                    try:
                        self.sons[arq[:-4]] = pygame.mixer.Sound(os.path.join(C.SOM, arq))
                    except Exception:
                        pass

    def tocar(self, nome, vol=1.0):
        if self.ok and not self.mudo and nome in self.sons:
            s = self.sons[nome]
            s.set_volume(clamp(C.VOLUME_SFX * vol, 0, 1))
            s.play()

    def musica(self, nome, fade=700):
        if not self.ok or nome == self.musica_atual:
            return
        self.musica_atual = nome
        try:
            pygame.mixer.music.load(os.path.join(C.SOM, f"musica_{nome}.wav"))
            pygame.mixer.music.set_volume(0 if self.mudo else C.VOLUME_MUSICA)
            pygame.mixer.music.play(-1, fade_ms=fade)
        except Exception:
            pass

    def parar_musica(self, fade=500):
        if self.ok:
            try:
                pygame.mixer.music.fadeout(fade)
            except Exception:
                pass
        self.musica_atual = None

    def alternar_mudo(self):
        self.mudo = not self.mudo
        if self.ok:
            try:
                pygame.mixer.music.set_volume(0 if self.mudo else C.VOLUME_MUSICA)
            except Exception:
                pass
