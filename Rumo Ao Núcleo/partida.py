"""Partida: toda a jogabilidade (blocos, broca, calor, TNT, power-ups, perigos, chefe, HUD, fim de fase)."""
import math
import random

import pygame

import config as C
import util
from chefe import Chefe
from entidades import (ATRIB_BLOCO, COR_MINERIO, VALOR_MINERIO, Bloco, Broca, Caindo, Caixa, Estalactite,
                       Estilhaco, Geiser, Plataforma)
from fases import FASES, NOMES_BLOCO
from pplay_compat import Window

# durações dos power-ups (segundos)
DUR_VIGA, DUR_PICARETA, DUR_LANTERNA = 14.0, 10.0, 14.0
CARGAS_DINAMITE = 3
PESOS_PU = {"viga": 22, "cristal": 16, "picareta": 18, "dinamite": 14, "capacete": 6, "lanterna": 10}
NOMES_PU = {"viga": "VIGA DE AÇO", "cristal": "MULTIBROCA", "picareta": "PICARETA x2", "dinamite": "DINAMITE",
            "capacete": "+1 VIDA", "lanterna": "LANTERNA"}
COR_PU = {"viga": (170, 190, 255), "cristal": (150, 255, 255), "picareta": (255, 200, 90), "dinamite": (255, 90, 70),
          "capacete": (255, 230, 90), "lanterna": (255, 240, 150)}
CUSTOS_PADRAO = None  # (as melhorias são lidas de jogo.UPGRADES)


class Partida:
    def __init__(self, jogo, fase_inicial=1):
        self.jogo = jogo
        self.audio = jogo.audio
        self.prog = jogo.progresso
        mel = self.prog["melhorias"]
        self.mel = mel
        self.pontos = 0
        self.vidas = min(C.VIDAS_MAX, C.VIDAS_BASE + mel["capacete"])
        self.minerio_run = 0
        self.minerio_banco = 0          # já depositado no cofre neste run
        self.fase_idx = fase_inicial - 1
        self.fase_inicial = fase_inicial
        self.part = util.Particulas()
        self.t = 0.0
        self.escala_tempo = 1.0
        self.escala_alvo = 1.0
        self.resultado = None            # None | "menu" | "game_over" | "vitoria"
        self.tremor = 0.0
        self.flash = 0.0
        self.flash_cor = (255, 255, 255)
        self.bg_off = 0.0
        self.sel_pausa = 0
        self.sel_fim = 0
        self.escuridao = pygame.Surface((C.LARGURA, C.ALTURA), pygame.SRCALPHA)
        self.vinheta = self._criar_vinheta()
        self.vinheta_verm = self._criar_vinheta_vermelha()
        self.poeira = [[random.uniform(0, C.LARGURA), random.uniform(0, C.ALTURA), random.uniform(0.2, 1.0)] for _ in range(46)]
        self.estatisticas_totais = {"blocos": 0, "tempo": 0.0, "melhor_combo": 0}
        self.iniciar_fase()

    # ============================================================ criação de fase
    def iniciar_fase(self):
        self.fase = FASES[self.fase_idx]
        self.eh_chefe = bool(self.fase.get("chefe"))
        self.bg = util.img(self.fase["fundo"])
        self.blocos = []
        self.criar_blocos(self.fase["layout"], animar=True)
        vel = self.fase["vel"]
        self.vel_base = vel
        self.vel_max = self.fase["vel_max"]
        self.largura_base = Plataforma.LARGS[min(7, 3 + self.mel["plataforma"])]
        self.plat = Plataforma(self.largura_base)
        self.brocas = [Broca(self.plat.cx, self.plat.y - C.RAIO_BROCA, vel)]
        self.itens = []
        self.estalactites = []
        self.estilhacos = []
        self.geiseres = []
        self.explosoes = []              # (tempo, x, y, raio, dano)
        self.chefe = Chefe() if self.eh_chefe else None
        self.combo = 0
        self.calor = 0.0
        self.t_viga = self.t_picareta = self.t_lanterna = 0.0
        self.cargas_dinamite = 0
        self.t_estal = (self.fase["estalactites"] or 0) * 0.8
        self.t_geiser = (self.fase["geysers"] or 0) * 0.8
        self.estado = "intro"
        self.t_estado = 0.0
        self.t_fase = 0.0
        self.st = {"blocos": 0, "minerio": 0, "vidas_perdidas": 0, "melhor_combo": 0, "pontos_ini": self.pontos}
        self.total_obrig = max(1, sum(1 for b in self.blocos if b.obrigatorio))
        self.bg_off = 0.0
        self.aviso_dica = 0.0
        self.audio.musica(self.fase["musica"])

    def criar_blocos(self, layout, animar=False, y0=None):
        y0 = self.fase["grade_y0"] if y0 is None else y0
        novos = []
        ocupado = {(b.col, b.lin) for b in self.blocos if b.vivo}
        for lin, linha in enumerate(layout):
            for col, ch in enumerate(linha):
                if ch == "." or (col, lin) in ocupado:
                    continue
                x = C.GRADE_X0 + col * (C.BLOCO_L + C.ESPACO)
                y = y0 + lin * (C.BLOCO_A + C.ESPACO)
                b = Bloco(NOMES_BLOCO[ch], col, lin, x, y)
                b.t_nasc = self.t if animar else None
                novos.append(b)
        self.blocos += novos
        return novos

    # ============================================================ utilidades
    @property
    def mult(self):
        return min(5, 1 + self.combo // 5)

    @property
    def vivos_obrig(self):
        return sum(1 for b in self.blocos if b.vivo and b.obrigatorio)

    def progresso_fase(self):
        if self.eh_chefe:
            return 1 - self.chefe.hp / Chefe.HP_MAX
        return 1 - self.vivos_obrig / self.total_obrig

    def profundidade(self):
        a, b = self.fase["prof"]
        return int(a + (b - a) * self.progresso_fase())

    def raio_luz(self):
        return 118 * (1.7 if self.t_lanterna > 0 else 1.0)

    def somar_pontos(self, n, x=None, y=None, cor=(255, 255, 255), tam=18):
        n = int(n)
        self.pontos += n
        if x is not None:
            self.part.texto(x, y, f"+{n}", cor, tam)

    def tremer(self, v):
        self.tremor = max(self.tremor, v)

    def deslocamento(self):
        a = min(14, self.tremor * 16)
        return (random.uniform(-a, a), random.uniform(-a, a)) if a > 0.3 else (0, 0)

    def _criar_vinheta(self):
        grad = pygame.Surface((C.LARGURA // 8, C.ALTURA // 8), pygame.SRCALPHA)
        w, h = grad.get_size()
        for y in range(h):
            for x in range(w):
                dx, dy = (x / w - 0.5) * 2, (y / h - 0.5) * 2
                d = min(1.0, math.sqrt(dx * dx * 0.8 + dy * dy))
                grad.set_at((x, y), (0, 0, 0, int(max(0, d - 0.55) / 0.45 * 150)))
        return pygame.transform.smoothscale(grad, (C.LARGURA, C.ALTURA))

    def _criar_vinheta_vermelha(self):
        s = self.vinheta.copy()
        s.fill((255, 40, 20, 0), special_flags=pygame.BLEND_RGBA_ADD)
        return s

    # ============================================================ laço principal
    def atualizar(self, dt, ent):
        dt = min(dt, 1 / 30)
        self.t_estado += dt
        if self.estado == "pausa":
            self._atualizar_pausa(ent)
            return
        # tempo relativo (câmera lenta dramática)
        self.escala_tempo += (self.escala_alvo - self.escala_tempo) * min(1, dt * 6)
        dt *= self.escala_tempo
        self.t += dt
        self.tremor = max(0.0, self.tremor - dt * 1.8)
        self.flash = max(0.0, self.flash - dt * 2.2)
        self.part.atualizar(dt)
        self._ambiente(dt)
        for b in self.blocos:
            b.tremor = max(0.0, b.tremor - dt)
            b.cd = max(0.0, b.cd - dt)

        if C.DEBUG:
            self._debug(ent)

        if self.estado in ("pronto", "jogando") and ent.t_pausa():
            self.estado_antes = self.estado
            self.estado = "pausa"
            self.sel_pausa = 0
            self.audio.tocar("menu_ok")
            return

        getattr(self, "_est_" + self.estado)(dt, ent)

        # fundo desce conforme a escavação avança (a câmera "mergulha")
        alvo = self.progresso_fase() * (self.bg.get_height() - C.ALTURA)
        self.bg_off += (alvo - self.bg_off) * min(1, dt * 2.5)

    def _ambiente(self, dt):
        for p in self.poeira:
            p[1] -= 12 * p[2] * dt
            p[0] += math.sin(self.t * 0.7 + p[2] * 9) * 6 * dt
            p[1] = p[1] % C.ALTURA
        # bolhas/brasas da lava
        if random.random() < dt * (3 + 5 * self.fase["lava"]):
            self.part.brasas(random.uniform(10, C.LARGURA - 10), C.LAVA_Y + 8, 1, (255, 150, 60), 40)

    # ------------------------------------------------------------ estados
    def _est_intro(self, dt, ent):
        # blocos "caem" na tela; depois a plataforma aparece
        if self.t_estado > 2.6:
            self.estado = "pronto"
            self.t_estado = 0
        if ent.t_ok() and self.t_estado > 0.8:
            self.t_estado = 99

    def _est_pronto(self, dt, ent):
        self._mover_plataforma(dt, ent)
        for b in self.brocas:
            b.x = self.plat.cx
            b.y = self.plat.y - C.RAIO_BROCA - 1
            b.anim += dt
        lancar = ent.t_ok() or (C.AUTOPLAY and self.t_estado > 0.6)
        if lancar:
            self.audio.tocar("lancar")
            for b in self.brocas:
                b.presa = False
                b.direcao(random.uniform(-22, 22))
            self.estado = "jogando"
            self.t_estado = 0
            self.part.faiscas(self.plat.cx, self.plat.y, 10, (255, 220, 140), 260, 0.4, -math.pi / 2, 1.5)

    def _est_jogando(self, dt, ent):
        self.t_fase += dt
        self.estatisticas_totais["tempo"] += dt
        self._mover_plataforma(dt, ent)
        self._timers_powerup(dt)
        self._calor(dt)
        for b in list(self.brocas):
            self._mover_broca(b, dt)
        self._itens(dt)
        self._explosoes(dt)
        self._perigos(dt)
        for b in self.blocos:
            if b.fuse is not None:
                b.fuse -= dt
                if b.fuse <= 0 and b.vivo:
                    self._quebrar_bloco(b, forcar=True)
        self.blocos = [b for b in self.blocos if b.vivo]
        if self.chefe:
            self._chefe(dt)
        # --- sem brocas -> perde vida
        if not self.brocas and self.estado == "jogando":
            self._perder_vida()
        # --- fase completa?
        if not self.eh_chefe and self.vivos_obrig == 0 and self.estado == "jogando":
            self._concluir_fase()

    def _est_morte(self, dt, ent):
        self._mover_plataforma(dt, None)
        if self.t_estado > 1.3:
            if self.vidas <= 0:
                self._fim_de_jogo()
            else:
                self.brocas = [Broca(self.plat.cx, self.plat.y - C.RAIO_BROCA, self.vel_base)]
                self.itens = [i for i in self.itens if i.categoria == "minerio"]
                self.estilhacos, self.estalactites, self.geiseres = [], [], []
                self.combo = 0
                self.estado = "pronto"
                self.t_estado = 0

    def _est_fase_ok(self, dt, ent):
        self._itens(dt, coletar_so=True)
        self._mover_plataforma(dt, None)
        if self.t_estado > 1.2 and ent.t_ok():
            self.audio.tocar("menu_ok")
            self._proxima_fase()
        if self.t_estado < 3 and random.random() < dt * 5:
            self.part.confete(random.uniform(120, 680), random.uniform(60, 200), 8)

    def _est_game_over(self, dt, ent):
        if self.t_estado > 1.0 and ent.t_ok():
            self.audio.tocar("menu_ok")
            self.resultado = "game_over"

    def _est_vitoria(self, dt, ent):
        if random.random() < dt * 9:
            self.part.confete(random.uniform(100, 700), random.uniform(40, 300), 10)
        if self.t_estado > 2.0 and ent.t_ok():
            self.audio.tocar("menu_ok")
            self.resultado = "vitoria"

    # ------------------------------------------------------------ pausa
    def _atualizar_pausa(self, ent):
        opcoes = 3
        if ent.t_cima():
            self.sel_pausa = (self.sel_pausa - 1) % opcoes
            self.audio.tocar("menu_mover")
        if ent.t_baixo():
            self.sel_pausa = (self.sel_pausa + 1) % opcoes
            self.audio.tocar("menu_mover")
        if ent.t_pausa():
            self.estado = self.estado_antes
            self.audio.tocar("menu_ok")
            return
        if ent.t_ok():
            self.audio.tocar("menu_ok")
            if self.sel_pausa == 0:
                self.estado = self.estado_antes
            elif self.sel_pausa == 1:
                self._depositar_minerio()
                self.pontos = self.st["pontos_ini"]
                self.iniciar_fase()
            else:
                self._depositar_minerio()
                self.resultado = "menu"

    # ============================================================ plataforma
    def _mover_plataforma(self, dt, ent):
        direcao = 0
        if ent is not None:
            direcao = int(ent.direita()) - int(ent.esquerda())
            if C.AUTOPLAY:
                direcao = self._ia_direcao()
        self.plat.alvo = self.largura_base * (1.5 if self.t_viga > 0 else 1.0)
        antes = self.plat.x
        self.plat.mover(dt, direcao, 560)
        if abs(self.plat.vx) > 120 and random.random() < dt * 25:
            self.part.faiscas(self.plat.cx - math.copysign(self.plat.largura / 2 - 8, self.plat.vx), self.plat.y + 24,
                              1, (255, 210, 130), 90, 0.3, math.pi / 2, 1.2, 100)
        if self.plat.atordoada > 0 and random.random() < dt * 40:
            self.part.faiscas(self.plat.x + random.uniform(0, self.plat.largura), self.plat.y + 4, 1, (140, 220, 255), 160, 0.25)

    def _ia_direcao(self):
        alvo = None
        if self.estado == "pronto" or not self.brocas:
            alvo = 400
        else:
            descendo = [b for b in self.brocas if b.vy > 0] or self.brocas
            b = max(descendo, key=lambda k: k.y)
            alvo = b.x
            # tenta pegar minério e desviar de perigos
            for it in self.itens:
                if it.categoria == "powerup" and abs(it.y - self.plat.y) < 200:
                    alvo = it.x
            for p in self.estalactites + self.estilhacos:
                if abs(p.x - self.plat.cx) < self.plat.largura / 2 + 28 and p.y > 300:
                    alvo = p.x + (140 if p.x < 400 else -140)
        alvo += math.sin(self.t * 1.7) * self.plat.largura * 0.28
        d = alvo - self.plat.cx
        return 0 if abs(d) < 8 else (1 if d > 0 else -1)

    # ============================================================ calor / power-ups
    def _timers_powerup(self, dt):
        self.t_viga = max(0.0, self.t_viga - dt)
        self.t_picareta = max(0.0, self.t_picareta - dt)
        self.t_lanterna = max(0.0, self.t_lanterna - dt)

    def _calor(self, dt):
        quentes = [b for b in self.brocas if b.quente > 0]
        for b in self.brocas:
            b.quente = max(0.0, b.quente - dt)
        if quentes:
            self.calor = max(b.quente for b in self.brocas) / self.duracao_calor()
            if random.random() < dt * 40:
                for b in quentes:
                    self.part.brasas(b.x, b.y, 1, (255, 170, 60), 40)
        else:
            self.calor = max(0.0, self.calor - dt * 0.035)

    def duracao_calor(self):
        return 4.0 + 0.9 * self.mel["isolamento"]

    def _acumular_calor(self, n=1):
        if any(b.quente > 0 for b in self.brocas):
            return
        self.calor += 0.085 * (1 + 0.22 * self.mel["isolamento"]) * n
        if self.calor >= 1.0:
            for b in self.brocas:
                b.quente = self.duracao_calor()
            self.calor = 1.0
            self.audio.tocar("calor")
            self.flash = 0.35
            self.flash_cor = (255, 150, 60)
            self.tremer(0.3)
            self.part.texto(self.brocas[0].x, self.brocas[0].y - 26, "SUPERAQUECIMENTO!", (255, 170, 60), 22, 1.4)

    def _aplicar_powerup(self, tipo, x, y):
        self.audio.tocar("powerup")
        cor = COR_PU[tipo]
        self.part.anel(x, y, 60, cor, 0.5, 5)
        self.part.faiscas(x, y, 16, cor, 320, 0.6)
        self.part.texto(x, y - 24, NOMES_PU[tipo], cor, 20, 1.3)
        if tipo == "viga":
            self.t_viga = DUR_VIGA
        elif tipo == "picareta":
            self.t_picareta = DUR_PICARETA
        elif tipo == "dinamite":
            self.cargas_dinamite = CARGAS_DINAMITE
        elif tipo == "lanterna":
            self.t_lanterna = DUR_LANTERNA
        elif tipo == "capacete":
            if self.vidas < C.VIDAS_MAX:
                self.vidas += 1
                self.audio.tocar("vida_extra")
            else:
                self.somar_pontos(500, x, y - 40, (255, 230, 90))
        elif tipo == "cristal":
            novos = []
            for b in self.brocas:
                if b.presa:
                    continue
                for ang in (-26, 26):
                    if len(self.brocas) + len(novos) >= 7:
                        break
                    n = Broca(b.x, b.y, b.vel)
                    n.presa = False
                    n.quente = b.quente
                    a = math.atan2(b.vx, -b.vy) + math.radians(ang)
                    n.vx, n.vy = math.sin(a) * n.vel, -math.cos(a) * n.vel
                    novos.append(n)
            self.brocas += novos

    def _sortear_powerup(self):
        pesos = dict(PESOS_PU)
        if self.fase["escuro"]:
            pesos["lanterna"] = 26
        tipos = list(pesos)
        return random.choices(tipos, [pesos[k] for k in tipos])[0]

    # ============================================================ broca: movimento e colisões
    def _mover_broca(self, b, dt):
        b.anim += dt
        b.pierce_cd = max(0.0, b.pierce_cd - dt)
        b.trilha.append((b.x, b.y))
        b.trilha = b.trilha[-9:]
        vel_real = math.hypot(b.vx, b.vy)
        passos = int(vel_real * dt / 4.5) + 1
        sdt = dt / passos
        for _ in range(passos):
            b.x += b.vx * sdt
            b.y += b.vy * sdt
            self._paredes(b)
            self._plataforma(b)
            self._blocos(b)
            if self.chefe:
                self._colisao_chefe(b)
            self._estalactite_x_broca(b)
            if b not in self.brocas:
                return
        # caiu na lava?
        if b.y > C.LAVA_Y + 6:
            self._broca_na_lava(b)

    def _paredes(self, b):
        """Paredes e teto por clamp (min/max) — sem a cadeia de if bola.x <= 0."""
        r = C.RAIO_BROCA
        xn = util.clamp(b.x, r, C.LARGURA - r)
        yn = max(b.y, C.HUD_ALTURA + r)
        bateu_x, bateu_y = xn != b.x, yn != b.y
        b.x, b.y = xn, yn
        b.vx *= 1 - 2 * int(bateu_x)
        b.vy *= 1 - 2 * int(bateu_y)
        if bateu_x or bateu_y:
            self.audio.tocar("parede", 0.6)
            self.part.faiscas(b.x, b.y, 4, (255, 220, 160), 160, 0.25)

    def _plataforma(self, b):
        p = self.plat
        if b.vy <= 0 or not util.colidiu(b.caixa(), p.caixa()) or b.y > p.y + 14:
            return
        rel = util.clamp((b.x - p.cx) / (p.largura / 2), -1.0, 1.0)
        b.vel = min(self.vel_max, b.vel + 3.2)
        b.direcao(rel * 63 + random.uniform(-4.5, 4.5))   # leve aleatoriedade evita laços infinitos
        b.y = p.y - C.RAIO_BROCA - 0.5
        p.mola = 1.0
        self.combo = 0
        self.audio.tocar("rebater")
        self.part.faiscas(b.x, b.y + 10, 8, (255, 230, 170), 230, 0.35, -math.pi / 2, 2.2)
        self.part.anel(b.x, p.y + 4, 26, (255, 220, 150), 0.25, 3)

    def _dano_broca(self, b, bloco):
        d = 1
        if self.t_picareta > 0:
            d *= 2
        if b.quente > 0:
            d += 1
        crit = random.random() < 0.12 * self.mel["tungstenio"]
        if crit:
            d += 1
        return d, crit

    def _blocos(self, b):
        r = C.RAIO_BROCA
        melhor, pen_max = None, 0.0
        for bl in self.blocos:
            if not bl.vivo:
                continue
            if abs(bl.cx - b.x) > 48 or abs(bl.cy - b.y) > 28:
                continue
            res = util.circulo_retangulo(b.x, b.y, r, bl.x, bl.y, C.BLOCO_L, C.BLOCO_A)
            if res and res[2] > pen_max:
                melhor, pen_max = (bl, res), res[2]
        if not melhor:
            return
        bl, (nx, ny, pen) = melhor
        perfura = b.quente > 0 and not bl.indestrutivel
        if not perfura:
            dot = b.vx * nx + b.vy * ny
            if dot < 0:
                b.vx -= 2 * dot * nx
                b.vy -= 2 * dot * ny
            b.x += nx * (pen + 0.3)
            b.y += ny * (pen + 0.3)
            b.acertar_velocidade()
        if bl.indestrutivel:
            self.audio.tocar("impacto", 0.7)
            self.part.faiscas(b.x - nx * r, b.y - ny * r, 6, (200, 200, 220), 200, 0.3)
            bl.tremor = 0.12
            return
        if perfura and b.pierce_cd > 0 and bl.cd > 0:
            return
        bl.cd = 0.1
        dano, crit = self._dano_broca(b, bl)
        self.combo += 1
        self.st["melhor_combo"] = max(self.st["melhor_combo"], self.combo)
        self.estatisticas_totais["melhor_combo"] = max(self.estatisticas_totais["melhor_combo"], self.combo)
        if self.combo and self.combo % 5 == 0:
            self.audio.tocar("combo")
            self.part.texto(b.x, b.y - 28, f"COMBO x{self.mult}!", (255, 235, 120), 22, 1.0)
        self._acumular_calor()
        if crit:
            self.part.texto(bl.cx, bl.y - 10, "CRÍTICO!", (255, 120, 90), 17, 0.8)
            self.part.faiscas(bl.cx, bl.cy, 12, (255, 120, 90), 320, 0.45)
        self._acertar_bloco(bl, dano)
        # dinamite: cada bloco atingido detona
        if self.cargas_dinamite > 0:
            self.cargas_dinamite -= 1
            self._explodir(bl.cx, bl.cy, 78, 2)

    def _acertar_bloco(self, bl, dano):
        bl.hp -= dano
        bl.tremor = 0.22
        if bl.hp <= 0:
            self._quebrar_bloco(bl)
        else:
            self.audio.tocar("bloco")
            self.somar_pontos(5 * self.mult)
            self.part.detritos(bl.cx, bl.cy, 4, bl.cor, 150)
            if bl.tipo in ("prata", "ouro", "diamante", "gema"):
                self.part.brilho_estrela(bl.cx + random.uniform(-20, 20), bl.cy + random.uniform(-6, 6), bl.cor, 6)

    def _quebrar_bloco(self, bl, forcar=False):
        if not bl.vivo:
            return
        bl.vivo = False
        bl.hp = 0
        self.st["blocos"] += 1
        self.estatisticas_totais["blocos"] += 1
        self.audio.tocar("quebra")
        self.part.detritos(bl.cx, bl.cy, 12, bl.cor, 260)
        self.part.fumaca(bl.cx, bl.cy, 2, (90, 84, 82), 7)
        self.somar_pontos(bl.pontos * self.mult, bl.cx, bl.cy - 6, ATRIB_BLOCO[bl.tipo][4], 16 + self.mult)
        if bl.tipo == "tnt":
            self._explodir(bl.cx, bl.cy, 100, 3)
            return
        if bl.tipo == "granito":
            return
        self.tremer(0.12)
        # minério
        if bl.minerio and random.random() < bl.chance:
            n = 1 + (1 if bl.tipo in ("ouro", "diamante") and random.random() < 0.35 else 0)
            for _ in range(n):
                self.itens.append(Caindo("minerio", bl.minerio, bl.cx + random.uniform(-10, 10), bl.cy))
        # power-up
        if bl.tipo == "gema" or random.random() < 0.10:
            self.itens.append(Caindo("powerup", self._sortear_powerup(), bl.cx, bl.cy))
        if bl.tipo in ("ouro", "diamante", "gema", "prata"):
            for _ in range(3):
                self.part.brilho_estrela(bl.cx + random.uniform(-26, 26), bl.cy + random.uniform(-10, 10), bl.cor, 8, 0.7)

    def _explodir(self, cx, cy, raio, dano):
        self.explosoes.append((0.0, cx, cy, raio, dano))

    def _explosoes(self, dt):
        pend = []
        for tempo, cx, cy, raio, dano in self.explosoes:
            tempo -= dt
            if tempo > 0:
                pend.append((tempo, cx, cy, raio, dano))
                continue
            self.audio.tocar("explosao")
            self.part.explosao(cx, cy, raio)
            self.tremer(0.6 if raio > 90 else 0.35)
            self.flash = max(self.flash, 0.25 if raio > 90 else 0.12)
            self.flash_cor = (255, 220, 150)
            for bl in self.blocos:
                if not bl.vivo:
                    continue
                dx, dy = (bl.cx - cx) / (raio * 0.95), (bl.cy - cy) / (raio * 0.62)
                if dx * dx + dy * dy < 1.15:
                    if bl.tipo == "tnt":
                        if bl.fuse is None:
                            bl.fuse = 0.14
                    else:
                        bl.hp -= dano
                        bl.tremor = 0.3
                        if bl.hp <= 0:
                            self._quebrar_bloco(bl)
            for e in self.estalactites:
                if math.hypot(e.x - cx, e.y - cy) < raio:
                    e.vivo = False
            if self.chefe and math.hypot(self.chefe.x - cx, self.chefe.y - cy) < raio + self.chefe.raio:
                self._ferir_chefe(2, cx, cy)
        self.explosoes = pend

    # ============================================================ itens que caem
    def _itens(self, dt, coletar_so=False):
        plat = self.plat
        ima = 0
        if self.mel["ima"] > 0:
            ima = 70 + 55 * self.mel["ima"]
        if self.t_lanterna > 0:
            ima = max(ima, 230)
        cx_p, cy_p = plat.cx, plat.y + 6
        for it in self.itens:
            it.vy = min(330.0, it.vy + 420 * dt)
            it.x += it.vx * dt
            it.vx *= max(0.0, 1 - 2.5 * dt)
            it.y += it.vy * dt
            it.x = util.clamp(it.x, 14, C.LARGURA - 14)
            if ima and it.categoria == "minerio" and not coletar_so:
                dx, dy = cx_p - it.x, cy_p - it.y
                d = math.hypot(dx, dy)
                if d < ima and it.y > 150:
                    f = (1 - d / ima) * 640 * dt
                    it.x += dx / (d or 1) * f
                    it.y += dy / (d or 1) * f * 0.6
            if coletar_so and it.categoria == "powerup":
                it.vivo = False
                continue
            if util.colidiu(it.caixa(), plat.caixa()):
                self._coletar(it)
            elif it.y > C.LAVA_Y:
                it.vivo = False
                self.part.fumaca(it.x, C.LAVA_Y, 2, (255, 120, 60), 6)
                self.part.faiscas(it.x, C.LAVA_Y, 4, (255, 160, 60), 120, 0.35, -math.pi / 2, 1.4)
        self.itens = [i for i in self.itens if i.vivo]

    def _coletar(self, it):
        it.vivo = False
        if it.categoria == "powerup":
            self._aplicar_powerup(it.tipo, it.x, it.y)
            return
        val = VALOR_MINERIO[it.tipo]
        self.minerio_run += val
        self.st["minerio"] += val
        self.somar_pontos(val * 6, it.x, it.y - 14, COR_MINERIO[it.tipo], 15)
        self.audio.tocar({"cobre": "minerio", "prata": "minerio", "ouro": "ouro", "diamante": "diamante", "gema": "gema"}[it.tipo])
        self.part.faiscas(it.x, it.y, 6, COR_MINERIO[it.tipo], 200, 0.4)
        self.part.brilho_estrela(it.x, it.y, COR_MINERIO[it.tipo], 8)

    # ============================================================ perigos
    def _perigos(self, dt):
        plat = self.plat
        # ---- estalactites: soltam de um bloco, avisam e caem
        intervalo = self.fase["estalactites"]
        if intervalo and not self.chefe:
            self.t_estal -= dt
            if self.t_estal <= 0:
                self.t_estal = intervalo * random.uniform(0.75, 1.25)
                colunas = {}
                for bl in self.blocos:
                    if bl.vivo and bl.solta <= 0:
                        if bl.col not in colunas or bl.y > colunas[bl.col].y:
                            colunas[bl.col] = bl
                if colunas:
                    escolhido = random.choice(list(colunas.values()))
                    escolhido.solta = 1.1
                    self.audio.tocar("aviso", 0.7)
        for bl in self.blocos:
            if bl.solta > 0:
                bl.solta -= dt
                bl.tremor = max(bl.tremor, 0.05)
                if random.random() < dt * 30:
                    self.part.detritos(bl.cx + random.uniform(-20, 20), bl.y + C.BLOCO_A, 1, bl.cor, 40)
                if bl.solta <= 0 and bl.vivo:
                    self.estalactites.append(Estalactite(bl.cx, bl.y + C.BLOCO_A - 2))
        for e in self.estalactites:
            e.vy = min(520.0, e.vy + 620 * dt)
            e.y += e.vy * dt
            if util.colidiu(e.caixa(), plat.caixa()):
                e.vivo = False
                self._atordoar(e.x, e.y + 40, 1.3)
            elif e.y > C.LAVA_Y:
                e.vivo = False
                self.part.fumaca(e.x, C.LAVA_Y, 3, (255, 120, 60), 8)
        self.estalactites = [e for e in self.estalactites if e.vivo]

        # ---- gêiseres de lava (fase 4 e chefe)
        intervalo = self.fase["geysers"]
        if intervalo and not self.chefe:
            self.t_geiser -= dt
            if self.t_geiser <= 0:
                self.t_geiser = intervalo * random.uniform(0.8, 1.2)
                self._novo_geiser([plat.cx + random.uniform(-70, 70), random.uniform(60, 740)])
        for g in self.geiseres:
            g.t += dt
            if g.t < g.AVISO and random.random() < dt * 40:
                self.part.faiscas(g.x + random.uniform(-24, 24), C.LAVA_Y, 1, (255, 90, 40), 160, 0.5, -math.pi / 2, 0.8, 40)
            if g.ativo:
                if random.random() < dt * 90:
                    self.part.brasas(g.x + random.uniform(-20, 20), C.LAVA_Y - random.uniform(0, 380), 1, (255, 170, 70), 50)
                if util.colidiu(g.caixa(), plat.caixa()) and plat.atordoada <= 0:
                    self._atordoar(plat.cx, plat.y, 1.6)
                for b in self.brocas:
                    if abs(b.x - g.x) < 30 and b.quente <= 0 and self.calor < 0.9:
                        self._acumular_calor(0.15 * dt * 60 / 10)
            if g.t > g.AVISO + g.ERUPCAO:
                g.vivo = False
        self.geiseres = [g for g in self.geiseres if g.vivo]

        # ---- estilhaços do chefe
        for s in self.estilhacos:
            s.x += s.vx * dt
            s.y += s.vy * dt
            if util.colidiu(s.caixa(), plat.caixa()):
                s.vivo = False
                self._atordoar(s.x, s.y, 1.2)
            elif s.y > C.LAVA_Y or s.x < -20 or s.x > C.LARGURA + 20:
                s.vivo = False
        self.estilhacos = [s for s in self.estilhacos if s.vivo]

    def _novo_geiser(self, xs):
        for x in xs:
            self.geiseres.append(Geiser(util.clamp(x, 40, C.LARGURA - 40)))
        self.audio.tocar("aviso")

    def _atordoar(self, x, y, seg):
        if self.plat.atordoada > 0.4:
            return
        self.plat.atordoada = seg
        self.audio.tocar("impacto")
        self.tremer(0.5)
        self.part.faiscas(x, y, 14, (150, 225, 255), 300, 0.5)
        self.part.texto(self.plat.cx, self.plat.y - 18, "ATORDOADA!", (150, 225, 255), 18, 1.0)

    def _estalactite_x_broca(self, b):
        cb = b.caixa()
        for e in self.estalactites:
            if e.vivo and util.colidiu(cb, e.caixa()):
                e.vivo = False
                self.audio.tocar("quebra", 0.8)
                self.part.detritos(e.x, e.y + 20, 10, (120, 110, 120), 240)
                self.somar_pontos(25 * self.mult, e.x, e.y, (200, 200, 220), 15)
        for s in self.estilhacos:
            if s.vivo and util.colidiu(cb, s.caixa()):
                s.vivo = False
                self.part.faiscas(s.x, s.y, 8, (255, 140, 60), 220, 0.4)
                self.somar_pontos(15 * self.mult, s.x, s.y, (255, 170, 90), 14)

    # ============================================================ chefe
    def _colisao_chefe(self, b):
        ch = self.chefe
        if ch.morrendo > 0 or ch.morto:
            return
        dx, dy = b.x - ch.x, b.y - ch.y
        d = math.hypot(dx, dy)
        lim = ch.raio + C.RAIO_BROCA
        if d >= lim:
            return
        nx, ny = (dx / d, dy / d) if d > 1e-6 else (0.0, 1.0)
        dot = b.vx * nx + b.vy * ny
        if dot < 0:
            b.vx -= 2 * dot * nx
            b.vy -= 2 * dot * ny
        b.x = ch.x + nx * (lim + 0.5)
        b.y = ch.y + ny * (lim + 0.5)
        b.acertar_velocidade()
        dano, crit = self._dano_broca(b, None)
        if self.cargas_dinamite > 0:
            self.cargas_dinamite -= 1
            self._explodir(b.x, b.y, 80, 2)
        self._ferir_chefe(dano, b.x, b.y)

    def _ferir_chefe(self, dano, x, y):
        ch = self.chefe
        if ch.dano(dano):
            self.combo += 1
            self.audio.tocar("chefe_hit")
            self.tremer(0.55)
            self.somar_pontos(120 * self.mult, ch.x, ch.y - 70, (255, 200, 120), 22)
            self.part.faiscas(x, y, 16, (255, 190, 90), 380, 0.6)
            self.part.anel(x, y, 50, (255, 230, 180), 0.35, 4)
            self._acumular_calor(2)
            # o Núcleo derrama minério
            self.itens.append(Caindo("minerio", random.choice(["ouro", "diamante", "prata"]), ch.x + random.uniform(-30, 30), ch.y + 40))

    def _chefe(self, dt):
        ch = self.chefe
        eventos = ch.atualizar(dt, (self.plat.cx, self.plat.y))
        for nome, dados in eventos:
            if nome == "tiro":
                self.audio.tocar("lancar", 0.7)
                for (x, y, vx, vy) in dados:
                    self.estilhacos.append(Estilhaco(x, y, vx, vy))
            elif nome == "geiser":
                self._novo_geiser(dados)
            elif nome == "fase":
                self.audio.tocar("chefe_morre", 0.6)
                self.tremer(1.0)
                self.flash, self.flash_cor = 0.9, (255, 255, 255)
                self.part.explosao(ch.x, ch.y, 120)
                self.estilhacos.clear()
                self.part.texto(ch.x, ch.y + 90, f"FASE {dados} DA LUTA!", (255, 210, 120), 26, 1.8)
                # novos blocos para gerar minério e power-ups
                novos = self.criar_blocos(self.fase["reabastece"], animar=True)
            elif nome == "morreu":
                self.audio.tocar("chefe_morre")
                self.escala_alvo = 0.35
                self.estilhacos.clear()
                self.geiseres.clear()
        if ch.morrendo > 0:
            if ch.morrendo < 2.9:
                self.escala_alvo = 1.0
            if random.random() < dt * 9:
                self.part.explosao(ch.x + random.uniform(-45, 45), ch.y + random.uniform(-40, 40), random.uniform(40, 80))
                self.audio.tocar("explosao", 0.6)
                self.tremer(0.5)
        if ch.morto and self.estado == "jogando":
            self._vitoria()

    # ============================================================ vida / fim de fase
    def _broca_na_lava(self, b):
        self.part.explosao(b.x, C.LAVA_Y, 40)
        self.part.fumaca(b.x, C.LAVA_Y, 6, (255, 140, 70), 10)
        self.part.faiscas(b.x, C.LAVA_Y, 16, (255, 150, 50), 350, 0.7, -math.pi / 2, 1.3)
        self.audio.tocar("parede", 0.5)
        if b in self.brocas:
            self.brocas.remove(b)

    def _perder_vida(self):
        self.vidas -= 1
        self.st["vidas_perdidas"] += 1
        self.combo = 0
        self.calor = 0.0
        self.cargas_dinamite = 0
        self.audio.tocar("vida_perdida")
        self.tremer(0.9)
        self.flash, self.flash_cor = 0.5, (255, 80, 40)
        self.estado = "morte"
        self.t_estado = 0.0

    def _fim_de_jogo(self):
        self._depositar_minerio()
        self.prog["partidas"] += 1
        self.prog["recorde"] = max(self.prog["recorde"], self.pontos)
        self.jogo.salvar()
        self.audio.parar_musica(400)
        self.audio.tocar("game_over")
        self.estado = "game_over"
        self.t_estado = 0

    def _concluir_fase(self):
        bonus_vidas = self.vidas * 150
        perdidas = self.st["vidas_perdidas"]
        self.estrelas = 3 if perdidas == 0 else (2 if perdidas == 1 else 1)
        self.bonus = bonus_vidas + self.estrelas * 200
        self.pontos += self.bonus
        self._depositar_minerio()
        self.prog["fase_max"] = max(self.prog["fase_max"], min(5, self.fase_idx + 2))
        self.prog["recorde"] = max(self.prog["recorde"], self.pontos)
        self.jogo.salvar()
        self.audio.tocar("fase_ok")
        self.audio.tocar("vitoria", 0.6)
        self.flash, self.flash_cor = 0.4, (255, 240, 180)
        self.part.confete(400, 200, 70)
        self.estado = "fase_ok"
        self.t_estado = 0.0
        self.brocas = []

    def _proxima_fase(self):
        self.fase_idx += 1
        self.jogo.iris_fase(self)

    def _vitoria(self):
        self.prog["zerado"] = True
        self.prog["fase_max"] = 5
        self.pontos += 1000 + self.vidas * 300
        self.prog["partidas"] += 1
        self.prog["recorde"] = max(self.prog["recorde"], self.pontos)
        self._depositar_minerio()
        self.jogo.salvar()
        self.audio.tocar("vitoria")
        self.flash, self.flash_cor = 1.0, (255, 255, 255)
        self.part.confete(400, 250, 120)
        self.estado = "vitoria"
        self.t_estado = 0.0
        self.escala_alvo = 1.0

    def _depositar_minerio(self):
        novo = self.minerio_run - self.minerio_banco
        if novo > 0:
            self.prog["minerio"] += novo
            self.minerio_banco = self.minerio_run
            self.jogo.salvar()

    def _debug(self, ent):
        if ent.tocou(pygame.K_n):
            for b in self.blocos:
                if b.obrigatorio:
                    b.vivo = False
            if self.chefe:
                self.chefe.hp = 1
        if ent.tocou(pygame.K_l):
            self.vidas = min(C.VIDAS_MAX, self.vidas + 1)
        if ent.tocou(pygame.K_h):
            for b in self.brocas:
                b.quente = self.duracao_calor()
        if ent.tocou(pygame.K_k):
            self.minerio_run += 100

    # ============================================================ DESENHO
    def desenhar(self, tela):
        self._desenhar_fundo(tela)
        t = self.t
        # blocos (animação de entrada)
        for b in self.blocos:
            ent = 1.0 if b.t_nasc is None else util.clamp((self.t - b.t_nasc - 0.1 - b.atraso) / 0.55, 0.0, 1.0)
            b.desenhar(t, ent)
            self._efeitos_bloco(tela, b, ent)
        # chefe
        if self.chefe and not self.chefe.morto:
            self.chefe.desenhar(tela, t)
            self._barra_chefe(tela)
        # lava (atrás da plataforma)
        self._desenhar_lava(tela)
        self._desenhar_geiseres(tela)
        for e in self.estalactites:
            e.desenhar(t)
        for s in self.estilhacos:
            s.desenhar(t)
            util.brilho(tela, int(s.x), int(s.y), 26, (255, 110, 40), 0.7)
        for it in self.itens:
            it.desenhar(t)
            cor = COR_MINERIO[it.tipo] if it.categoria == "minerio" else COR_PU[it.tipo]
            util.brilho(tela, int(it.x), int(it.y), 20 if it.categoria == "minerio" else 34, cor, 0.55)
        # plataforma e brocas
        if self.estado != "intro" or self.t_estado > 0.6:
            self.plat.desenhar(t)
            if self.plat.atordoada > 0:
                for i in range(4):
                    x = self.plat.x + (i + 0.5) * self.plat.largura / 4 + random.uniform(-8, 8)
                    pygame.draw.line(tela, (170, 235, 255), (x, self.plat.y), (x + random.uniform(-10, 10), self.plat.y - random.uniform(6, 16)), 2)
            for b in self.brocas:
                self._desenhar_broca(tela, b)
        self.part.desenhar(tela)
        for x, y, z in self.poeira:
            c = int(70 + 120 * z)
            pygame.draw.circle(tela, (c, c, int(c * 0.9)), (int(x), int(y)), 1)
        # escuridão (fase 3)
        if self.fase["escuro"]:
            self._desenhar_escuridao(tela)
        tela.blit(self.vinheta, (0, 0))
        if self.vidas == 1 and self.estado in ("jogando", "pronto"):
            self.vinheta_verm.set_alpha(int(110 + 90 * math.sin(self.t * 5)))
            tela.blit(self.vinheta_verm, (0, 0))
        if self.flash > 0:
            s = pygame.Surface((C.LARGURA, C.ALTURA))
            s.fill(tuple(int(c * self.flash) for c in self.flash_cor))
            tela.blit(s, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        self._desenhar_hud(tela)
        self._desenhar_estado(tela)

    def _desenhar_fundo(self, tela):
        tela.blit(self.bg, (0, -int(self.bg_off)))
        # brilho quente que sobe da lava
        util.brilho(tela, 400, C.ALTURA + 40, 380, (255, 90, 30), 0.35 * self.fase["lava"] * (0.9 + 0.1 * math.sin(self.t * 3)))

    def _efeitos_bloco(self, tela, b, ent):
        if ent < 1:
            return
        if b.tipo in ("ouro", "diamante", "gema", "prata") and random.random() < 0.004:
            self.part.brilho_estrela(b.x + random.uniform(4, C.BLOCO_L - 4), b.y + random.uniform(3, C.BLOCO_A - 3), b.cor, 6, 0.6)
        if b.tipo == "tnt" and b.fuse is not None:
            util.brilho(tela, int(b.cx), int(b.cy), 40, (255, 200, 80), 1.0)
        if b.tremor > 0.15:
            util.brilho(tela, int(b.cx), int(b.cy), 34, (255, 255, 255), 0.6)

    def _desenhar_broca(self, tela, b):
        # rastro
        n = len(b.trilha)
        for i, (x, y) in enumerate(b.trilha):
            k = (i + 1) / (n + 1)
            if b.quente > 0:
                util.brilho(tela, int(x), int(y), int(16 * k + 4), (255, 120, 30), 0.55 * k)
            else:
                util.brilho(tela, int(x), int(y), int(10 * k + 2), (255, 190, 110), 0.28 * k)
        if b.quente > 0:
            util.brilho(tela, int(b.x), int(b.y), 52 + int(6 * math.sin(self.t * 25)), (255, 110, 30), 0.9)
        else:
            util.brilho(tela, int(b.x), int(b.y), 30, (255, 190, 100), 0.42)
        b.desenhar(self.t)
        if self.cargas_dinamite > 0:
            pygame.draw.circle(tela, (255, 70, 60), (int(b.x), int(b.y)), 20, 2)
            util.texto(tela, str(self.cargas_dinamite), int(b.x), int(b.y - 28), 14, (255, 120, 100))

    def _desenhar_lava(self, tela):
        t = self.t
        topo = C.LAVA_Y
        k = self.fase["lava"]
        pts = [(0, C.ALTURA), (0, topo)]
        for x in range(0, C.LARGURA + 20, 16):
            y = topo + math.sin(x * 0.03 + t * 2.4) * 3.5 + math.sin(x * 0.013 - t * 1.6) * 3
            pts.append((x, y))
        pts += [(C.LARGURA, C.ALTURA)]
        # brilho aditivo acima da superfície
        util.brilho(tela, 400, topo + 6, 340, (255, 110, 30), 0.35 * k)
        cor_b = util.misturar((200, 50, 10), (255, 90, 20), min(1, k / 1.3))
        pygame.draw.polygon(tela, cor_b, pts)
        pts2 = [(0, C.ALTURA)]
        for x in range(0, C.LARGURA + 20, 16):
            y = topo + 9 + math.sin(x * 0.045 - t * 2.9) * 3
            pts2.append((x, y))
        pts2.append((C.LARGURA, C.ALTURA))
        pygame.draw.polygon(tela, (255, 140, 40), pts2)
        pts3 = [(0, C.ALTURA)]
        for x in range(0, C.LARGURA + 20, 16):
            y = topo + 17 + math.sin(x * 0.06 + t * 3.3) * 2
            pts3.append((x, y))
        pts3.append((C.LARGURA, C.ALTURA))
        pygame.draw.polygon(tela, (255, 205, 80), pts3)
        # linha de brilho na crista
        for x in range(0, C.LARGURA, 16):
            y1 = topo + math.sin(x * 0.03 + t * 2.4) * 3.5 + math.sin(x * 0.013 - t * 1.6) * 3
            y2 = topo + math.sin((x + 16) * 0.03 + t * 2.4) * 3.5 + math.sin((x + 16) * 0.013 - t * 1.6) * 3
            pygame.draw.line(tela, (255, 235, 150), (x, y1), (x + 16, y2), 2)

    def _desenhar_geiseres(self, tela):
        for g in self.geiseres:
            if g.t < g.AVISO:
                a = 0.4 + 0.6 * abs(math.sin(g.t * 14))
                util.brilho(tela, int(g.x), C.LAVA_Y, 70, (255, 40, 20), a)
                s = pygame.Surface((56, 22), pygame.SRCALPHA)
                pygame.draw.rect(s, (255, 60, 30, int(90 * a)), s.get_rect(), border_radius=6)
                tela.blit(s, (g.x - 28, C.LAVA_Y - 22))
                util.texto(tela, "!", int(g.x), C.LAVA_Y - 44, 26, (255, 90, 60), alfa=int(255 * a))
            elif g.ativo:
                prog = (g.t - g.AVISO) / g.ERUPCAO
                larg = 52 * (0.8 + 0.2 * math.sin(g.t * 40)) * min(1, prog * 6) * (1 - max(0, prog - 0.8) * 4)
                alt = (C.LAVA_Y - 150)
                col = pygame.Surface((int(larg) + 2, alt), pygame.SRCALPHA)
                for y in range(0, alt, 6):
                    f = y / alt
                    c = util.misturar((255, 240, 150), (255, 90, 25), f)
                    w = int(larg * (0.65 + 0.35 * f) * (0.9 + 0.1 * math.sin(y * 0.2 + self.t * 30)))
                    pygame.draw.rect(col, c, ((col.get_width() - w) // 2, y, w, 7))
                tela.blit(col, (g.x - col.get_width() / 2, 150))
                util.brilho(tela, int(g.x), 300, 150, (255, 110, 30), 0.7)

    def _desenhar_escuridao(self, tela):
        esc = self.escuridao
        esc.fill((4, 3, 12, 230))
        luzes = [(b.x, b.y, self.raio_luz()) for b in self.brocas]
        luzes.append((self.plat.cx, self.plat.y, 92 * (1.5 if self.t_lanterna > 0 else 1)))
        for it in self.itens:
            luzes.append((it.x, it.y, 42))
        for g in self.geiseres:
            luzes.append((g.x, C.LAVA_Y - 120, 120))
        for e in self.estalactites:
            luzes.append((e.x, e.y, 38))
        luzes.append((400, C.LAVA_Y + 20, 330))   # a lava ilumina o chão (luz fraca)
        for x, y, r in luzes:
            self._luz(esc, x, y, int(r), 0.42 if r > 300 else 1.0)
        tela.blit(esc, (0, 0))
        # o brilho dos minérios atravessa a escuridão
        for b in self.blocos:
            if b.tipo in ("ouro", "diamante", "gema", "prata", "tnt"):
                util.brilho(tela, int(b.cx), int(b.cy), 26, b.cor, 0.32 + 0.12 * math.sin(self.t * 3 + b.col))
        for b in self.brocas:
            util.brilho(tela, int(b.x), int(b.y), int(self.raio_luz() * 0.7), (255, 150, 60), 0.30)

    _luzes = {}

    def _luz(self, esc, x, y, r, forca=1.0):
        chave = (r, forca)
        s = Partida._luzes.get(chave)
        if s is None:
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            for i in range(r, 0, -2):
                t = min(1.0, (1 - i / r) * 1.15)
                a = int(255 * forca * t * t * (3 - 2 * t))
                pygame.draw.circle(s, (255, 255, 255, a), (r, r), i)
            if len(Partida._luzes) > 60:
                Partida._luzes.clear()
            Partida._luzes[chave] = s
        esc.blit(s, (int(x - r), int(y - r)), special_flags=pygame.BLEND_RGBA_SUB)

    # ------------------------------------------------------------ HUD
    def _desenhar_hud(self, tela):
        util.painel(tela, (0, 0, C.LARGURA, C.HUD_ALTURA), (10, 8, 18, 235), None, 0)
        pygame.draw.line(tela, self.fase["cor"], (0, C.HUD_ALTURA), (C.LARGURA, C.HUD_ALTURA), 2)
        cap = util.img("pu_capacete.png", (22, 22))
        for i in range(self.vidas):
            tela.blit(cap, (10 + i * 25, 6))
        # barra de calor
        util.texto(tela, "CALOR", 12, 38, 11, (255, 175, 90), "e", contorno=None)
        quente = any(b.quente > 0 for b in self.brocas)
        util.barra(tela, 56, 33, 118, 10, self.calor, (255, 190, 70), (255, 60, 30) if not quente else (255, 255, 200))
        if quente:
            util.brilho(tela, 115, 38, 60, (255, 120, 40), 0.5)
        # pontos
        util.texto(tela, f"{self.pontos:07d}", 300, 17, 24, (255, 240, 200), "c", titulo=True)
        util.texto(tela, "PONTOS", 300, 38, 11, (200, 190, 170), "c", contorno=None)
        # combo
        if self.combo >= 2:
            pulso = 1 + 0.1 * math.sin(self.t * 12)
            util.texto(tela, f"x{self.mult}", 395, 22, int(26 * pulso), (255, 215, 90) if self.mult > 1 else (230, 230, 230), "c", titulo=True)
            util.texto(tela, f"{self.combo} HITS", 395, 40, 10, (255, 215, 150), "c", contorno=None)
        # fase / profundidade
        util.texto(tela, f"FASE {self.fase['id']}  {self.fase['nome'].upper()}", 520, 15, 13, self.fase["cor"], "c", contorno=None)
        util.texto(tela, f"PROF. {self.profundidade()} m", 520, 36, 13, (190, 200, 220), "c", contorno=None)
        # minério
        tela.blit(util.img("min_ouro.png"), (640, 6))
        util.texto(tela, f"{self.minerio_run}", 668, 17, 18, (255, 225, 110), "e", contorno=(30, 20, 5))
        # power-ups ativos
        x = 640
        ativos = []
        if self.t_viga > 0:
            ativos.append(("viga", self.t_viga / DUR_VIGA))
        if self.t_picareta > 0:
            ativos.append(("picareta", self.t_picareta / DUR_PICARETA))
        if self.t_lanterna > 0:
            ativos.append(("lanterna", self.t_lanterna / DUR_LANTERNA))
        if self.cargas_dinamite > 0:
            ativos.append(("dinamite", 1.0))
        for tipo, f in ativos:
            tela.blit(util.img(f"pu_{tipo}.png", (22, 22)), (x, 26))
            pygame.draw.rect(tela, (30, 28, 40), (x, 47, 22, 3))
            pygame.draw.rect(tela, COR_PU[tipo], (x, 47, int(22 * f), 3))
            x += 27
        if self.mel["ima"] > 0 or self.t_lanterna > 0:
            pass

    def _barra_chefe(self, tela):
        ch = self.chefe
        x, y, w = 150, 74, 500
        util.painel(tela, (x - 10, y - 6, w + 20, 24), (14, 10, 18, 190), (255, 90, 60), 8, 2)
        util.barra(tela, x, y, w, 12, ch.hp / Chefe.HP_MAX, (255, 200, 70), (255, 60, 40), borda=None)
        for f in (1 / 3, 2 / 3):
            pygame.draw.line(tela, (20, 10, 10), (x + int(w * f), y), (x + int(w * f), y + 11), 2)
        util.texto(tela, "O NÚCLEO", 400, y - 15, 11, (255, 180, 120), "c", contorno=None)

    # ------------------------------------------------------------ camadas de estado
    def _desenhar_estado(self, tela):
        e = self.estado
        cx = C.LARGURA // 2
        if e == "intro":
            tt = self.t_estado
            a = util.clamp(1 - (tt - 1.9) / 0.6, 0, 1)
            ent = util.ease_out(tt / 0.7)
            faixa = pygame.Surface((C.LARGURA, 130), pygame.SRCALPHA)
            faixa.fill((6, 4, 12, int(210 * a)))
            tela.blit(faixa, (0, 230))
            pygame.draw.line(tela, self.fase["cor"], (0, 230), (C.LARGURA, 230), 3)
            pygame.draw.line(tela, self.fase["cor"], (0, 359), (C.LARGURA, 359), 3)
            util.texto(tela, f"FASE {self.fase['id']}", int(-200 + (cx + 200) * ent), 268, 40, self.fase["cor"], titulo=True, alfa=int(255 * a))
            util.texto(tela, self.fase["nome"].upper(), int(C.LARGURA + 200 - (200 + cx) * ent), 312, 30, (255, 245, 225), titulo=True, alfa=int(255 * a))
            util.texto(tela, self.fase["sub"], cx, 345, 14, (200, 195, 215), alfa=int(255 * a), contorno=None)
        elif e == "pronto":
            util.texto(tela, "ESPAÇO  para lançar a broca", cx, 470, 18, (255, 240, 200), alfa=int(170 + 85 * math.sin(self.t * 5)))
            if self.t_estado < 7:
                util.texto(tela, self.fase["dica"], cx, 436, 14, (255, 215, 140), contorno=(20, 10, 5), alfa=int(255 * util.clamp(7 - self.t_estado, 0, 1)))
            # seta de mira
            b = self.brocas[0]
            for i in range(1, 5):
                pygame.draw.circle(tela, (255, 230, 170), (int(b.x), int(b.y - 22 - i * 14)), 3 if i < 4 else 2)
        elif e == "morte":
            util.texto(tela, "A broca derreteu!", cx, 300, 26, (255, 130, 80), titulo=True, alfa=int(255 * util.clamp(self.t_estado * 3, 0, 1)))
        elif e == "pausa":
            self._desenhar_pausa(tela)
        elif e == "fase_ok":
            self._desenhar_fim_fase(tela)
        elif e == "game_over":
            self._desenhar_game_over(tela)
        elif e == "vitoria":
            self._desenhar_vitoria(tela)

    def _cobertura(self, tela, alfa):
        s = pygame.Surface((C.LARGURA, C.ALTURA), pygame.SRCALPHA)
        s.fill((4, 3, 10, alfa))
        tela.blit(s, (0, 0))

    def _desenhar_pausa(self, tela):
        self._cobertura(tela, 170)
        cx = C.LARGURA // 2
        util.painel(tela, (cx - 190, 170, 380, 270), (14, 12, 26, 235), self.fase["cor"], 16, 3)
        util.texto(tela, "PAUSA", cx, 215, 44, (255, 235, 190), titulo=True)
        for i, nome in enumerate(["CONTINUAR", "REINICIAR FASE", "SAIR PARA O MENU"]):
            sel = i == self.sel_pausa
            cor = (255, 215, 90) if sel else (190, 185, 200)
            if sel:
                util.painel(tela, (cx - 150, 262 + i * 52, 300, 40), (60, 40, 20, 200), (255, 190, 80), 10, 2)
            util.texto(tela, nome, cx, 282 + i * 52, 22 if sel else 20, cor)
        util.texto(tela, "↑ ↓ escolher    ENTER confirmar    P voltar", cx, 424, 12, (160, 155, 180), contorno=None)

    def _desenhar_fim_fase(self, tela):
        tt = self.t_estado
        self._cobertura(tela, int(150 * util.clamp(tt * 2, 0, 1)))
        cx = C.LARGURA // 2
        ent = util.ease_back(tt / 0.6)
        y = int(-300 + (150 + 300) * util.clamp(ent, 0, 1.05))
        util.painel(tela, (cx - 230, y, 460, 300), (14, 12, 26, 240), (255, 205, 90), 18, 3)
        util.texto(tela, "FASE COMPLETA!", cx, y + 38, 38, (255, 220, 110), titulo=True)
        util.texto(tela, self.fase["nome"], cx, y + 70, 16, (200, 195, 220), contorno=None)
        # estrelas
        for i in range(3):
            surge = util.clamp((tt - 0.5 - i * 0.25) / 0.3, 0, 1)
            cor = (255, 215, 70) if i < self.estrelas else (60, 56, 72)
            self._estrela(tela, cx - 56 + i * 56, y + 112, 22 * util.ease_back(surge) if surge else 0, cor)
        linhas = [
            ("Blocos minerados", f"{self.st['blocos']}"),
            ("Minério coletado", f"{self.st['minerio']}"),
            ("Melhor combo", f"{self.st['melhor_combo']} hits"),
            ("Bônus (vidas + estrelas)", f"+{self.bonus}"),
        ]
        for i, (a, b) in enumerate(linhas):
            vis = util.clamp((tt - 1.0 - i * 0.18) / 0.2, 0, 1)
            if vis > 0:
                util.texto(tela, a, cx - 190, y + 160 + i * 28, 16, (210, 205, 225), "e", alfa=int(255 * vis), contorno=None)
                util.texto(tela, b, cx + 190, y + 160 + i * 28, 17, (255, 235, 150), "d", alfa=int(255 * vis), contorno=None)
        if tt > 2.0:
            proximo = "PRÓXIMA FASE" if self.fase_idx < 4 else "CONTINUAR"
            util.texto(tela, f"ENTER  ›  {proximo}", cx, y + 276, 17, (255, 240, 200), alfa=int(170 + 85 * math.sin(self.t * 5)))

    def _estrela(self, tela, x, y, r, cor):
        if r <= 1:
            return
        pts = []
        for i in range(10):
            a = -math.pi / 2 + i * math.pi / 5
            rr = r if i % 2 == 0 else r * 0.45
            pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
        pygame.draw.polygon(tela, cor, pts)
        pygame.draw.polygon(tela, (30, 20, 5), pts, 2)

    def _desenhar_game_over(self, tela):
        tt = self.t_estado
        self._cobertura(tela, int(200 * util.clamp(tt * 1.5, 0, 1)))
        cx = C.LARGURA // 2
        util.texto(tela, "FIM DA ESCAVAÇÃO", cx, 190, 52, (255, 100, 70), titulo=True, alfa=int(255 * util.clamp(tt * 2, 0, 1)))
        util.texto(tela, "A lava engoliu as suas brocas...", cx, 236, 18, (220, 200, 210), alfa=int(255 * util.clamp(tt * 2 - 0.4, 0, 1)), contorno=None)
        util.painel(tela, (cx - 190, 270, 380, 150), (14, 12, 26, 230), (255, 120, 80), 14, 2)
        util.texto(tela, "PONTOS", cx - 150, 298, 15, (200, 195, 220), "e", contorno=None)
        util.texto(tela, f"{self.pontos}", cx + 150, 298, 22, (255, 235, 150), "d", titulo=True)
        util.texto(tela, "CHEGOU À FASE", cx - 150, 330, 15, (200, 195, 220), "e", contorno=None)
        util.texto(tela, f"{self.fase['id']}  ({self.profundidade()} m)", cx + 150, 330, 17, (255, 235, 150), "d", contorno=None)
        util.texto(tela, "MINÉRIO GUARDADO NO COFRE", cx - 150, 362, 15, (200, 195, 220), "e", contorno=None)
        util.texto(tela, f"+{self.minerio_run}", cx + 150, 362, 17, (255, 225, 110), "d", contorno=None)
        util.texto(tela, "Gaste o minério na OFICINA para ficar mais forte!", cx, 400, 13, (170, 210, 255), contorno=None)
        if tt > 1.0:
            util.texto(tela, "ENTER  ›  continuar", cx, 460, 20, (255, 240, 200), alfa=int(170 + 85 * math.sin(self.t * 5)))

    def _desenhar_vitoria(self, tela):
        tt = self.t_estado
        self._cobertura(tela, int(130 * util.clamp(tt, 0, 1)))
        cx = C.LARGURA // 2
        util.brilho(tela, cx, 190, 260, (255, 200, 90), 0.5 + 0.2 * math.sin(self.t * 3))
        util.texto(tela, "VOCÊ CHEGOU AO NÚCLEO!", cx, 160, 46, (255, 225, 110), titulo=True, alfa=int(255 * util.clamp(tt * 2, 0, 1)))
        util.texto(tela, "O coração do planeta é seu. Lenda da mineração!", cx, 210, 18, (255, 245, 220), alfa=int(255 * util.clamp(tt * 2 - 0.5, 0, 1)), contorno=None)
        util.painel(tela, (cx - 190, 250, 380, 130), (14, 12, 26, 230), (255, 205, 90), 14, 2)
        util.texto(tela, "PONTOS FINAIS", cx - 150, 282, 15, (200, 195, 220), "e", contorno=None)
        util.texto(tela, f"{self.pontos}", cx + 150, 282, 26, (255, 235, 150), "d", titulo=True)
        util.texto(tela, "BLOCOS MINERADOS", cx - 150, 320, 15, (200, 195, 220), "e", contorno=None)
        util.texto(tela, f"{self.estatisticas_totais['blocos']}", cx + 150, 320, 17, (255, 235, 150), "d", contorno=None)
        util.texto(tela, "MINÉRIO NO COFRE", cx - 150, 352, 15, (200, 195, 220), "e", contorno=None)
        util.texto(tela, f"{self.minerio_run}", cx + 150, 352, 17, (255, 225, 110), "d", contorno=None)
        if tt > 2.0:
            util.texto(tela, "ENTER  ›  continuar", cx, 440, 20, (255, 240, 200), alfa=int(170 + 85 * math.sin(self.t * 5)))
