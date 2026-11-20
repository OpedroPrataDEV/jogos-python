"""Classe Jogo: janela, laço principal, troca de telas com transição de 'furo de broca'."""
import sys

import pygame

import config as C
import dados
import menus
import util
from partida import Partida
from pplay_compat import Window


class Jogo:
    def __init__(self):
        self.janela = Window(C.LARGURA, C.ALTURA)
        self.janela.set_title(C.TITULO_JANELA)
        self.real = Window.get_screen()
        # Tudo é desenhado numa tela "canvas" (permite tremor de câmera e transições);
        # os Sprites do PPlay desenham em Window.screen, então apontamos para o canvas.
        self.canvas = pygame.Surface((C.LARGURA, C.ALTURA)).convert()
        Window.screen = self.canvas
        self.audio = util.Audio()
        self.ent = util.Entrada()
        self.ent_vazia = util.Entrada()
        self.progresso = dados.carregar_progresso()
        self.fundo = menus.FundoMenu()
        self.telas = {
            "menu": menus.TelaMenu(self),
            "selecao": menus.TelaSelecao(self),
            "oficina": menus.TelaOficina(self),
            "ranking": menus.TelaRanking(self),
            "ajuda": menus.TelaAjuda(self),
            "creditos": menus.TelaCreditos(self),
            "nome": menus.TelaNome(self),
        }
        self.atual = None
        self.partida = None
        self.trans = None
        self.rodando = True
        self.relogio = pygame.time.Clock()
        self.iris = pygame.Surface((C.LARGURA, C.ALTURA), pygame.SRCALPHA)
        self._trocar("menu", {})

    # ------------------------------------------------------------ utilidades
    def salvar(self):
        dados.salvar_progresso(self.progresso)

    def fase_max(self):
        return 5 if C.DESBLOQUEAR_TODAS_FASES else int(self.progresso["fase_max"])

    # ------------------------------------------------------------ troca de telas
    def _transicao(self, destino, dur=0.38):
        if self.trans is None:
            self.trans = {"fase": "fecha", "t": 0.0, "dur": dur, "destino": destino}

    def _trocar(self, nome, kw):
        self.partida = None
        self.atual = self.telas[nome]
        self.atual.entrar(**kw)

    def ir(self, nome, **kw):
        self._transicao(lambda: self._trocar(nome, kw))

    def jogar(self, fase):
        def comecar():
            self.partida = Partida(self, fase)
            self.atual = None
        self._transicao(comecar)

    def iris_fase(self, partida):
        self._transicao(partida.iniciar_fase)

    def _tratar(self, acao):
        if not acao:
            return
        if acao[0] == "tela":
            self.ir(acao[1], **(acao[2] if len(acao) > 2 else {}))
        elif acao[0] == "jogar":
            self.jogar(acao[1])
        elif acao[0] == "sair":
            self.rodando = False

    def _fim_partida(self):
        p = self.partida
        r = p.resultado
        p.resultado = None
        if r == "menu":
            self.ir("menu")
            return
        pontos, fase = p.pontos, (5 if r == "vitoria" else p.fase["id"])
        if dados.qualifica(pontos):
            self.ir("nome", pontos=pontos, fase=fase, vitoria=(r == "vitoria"))
        else:
            self.ir("ranking")

    # ------------------------------------------------------------ laço
    def _atualizar(self, dt):
        ent = self.ent if self.trans is None else self.ent_vazia
        if self.partida is not None:
            self.partida.atualizar(dt, ent)
            if self.partida.resultado and self.trans is None:
                self._fim_partida()
        else:
            self._tratar(self.atual.atualizar(dt, ent))
        if self.trans is not None:
            tr = self.trans
            tr["t"] += dt
            if tr["t"] >= tr["dur"]:
                if tr["fase"] == "fecha":
                    tr["destino"]()
                    tr["fase"], tr["t"] = "abre", 0.0
                else:
                    self.trans = None

    def _desenhar_iris(self):
        tr = self.trans
        f = util.suave(tr["t"] / tr["dur"])
        raio = 520 * (1 - f if tr["fase"] == "fecha" else f)
        self.iris.fill((0, 0, 0, 255))
        centro = (C.LARGURA // 2, C.ALTURA // 2)
        if raio >= 1:
            pygame.draw.circle(self.iris, (0, 0, 0, 0), centro, int(raio))
        self.canvas.blit(self.iris, (0, 0))
        if raio > 6:
            pygame.draw.circle(self.canvas, (255, 170, 60), centro, int(raio), 5)
            pygame.draw.circle(self.canvas, (255, 235, 170), centro, int(raio) + 5, 2)

    def _desenhar(self):
        if self.partida is not None:
            self.partida.desenhar(self.canvas)
            dx, dy = self.partida.deslocamento()
        else:
            self.atual.desenhar(self.canvas)
            dx, dy = 0, 0
        if self.trans is not None:
            self._desenhar_iris()
        if dx or dy:
            self.real.fill((0, 0, 0))
        self.real.blit(self.canvas, (int(dx), int(dy)))
        self.janela.update()      # atualiza a tela e trata o botão de fechar da janela (PPlay)

    def rodar(self, max_quadros=None, dt_fixo=None):
        n = 0
        while self.rodando:
            dt = dt_fixo if dt_fixo else self.relogio.tick(C.FPS) / 1000.0
            self.ent.atualizar()
            if self.ent.tocou(pygame.K_m):
                self.audio.alternar_mudo()
            self._atualizar(dt)
            self._desenhar()
            n += 1
            if max_quadros and n >= max_quadros:
                break
        self.salvar()
