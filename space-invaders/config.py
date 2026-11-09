import pygame
from pplay.window import Window

# Dimensões da janela do jogo
largura_janela = 800
altura_janela = 600

# Cores de fundo para cada estado do jogo
cor_fundo_menu = [12, 10, 20]
cor_fundo_jogo = [5, 5, 10]
cor_fundo_dificuldade = [15, 12, 25]

# Cores dos botões do menu
cor_jogar = (0, 230, 118)
cor_dificuldade = (255, 193, 7)
cor_ranking = (255, 87, 34)
cor_sair = (236, 64, 122)

# Cores gerais de texto e títulos
cor_texto_botao = (255, 255, 255)
cor_titulo = (0, 229, 255)

# Configurações da matriz de monstros
linhas_monstros = 4
colunas_monstros = 6

# Inicialização da janela e dispositivos de entrada
window = Window(largura_janela, altura_janela)
window.set_title("Space Invaders")
keyboard = window.get_keyboard()
mouse = window.get_mouse()
tela = window.get_screen()

# Inicialização das fontes do sistema
pygame.font.init()
fonte_titulo = pygame.font.SysFont("Impact", 52)
fonte_botao = pygame.font.SysFont("Impact", 24)

dificuldade_atual = "Medio"
_mouse_pressionado_frame_anterior = False

# Função para garantir clique único do mouse
def clique_unico():
    global _mouse_pressionado_frame_anterior
    pressionado_agora = mouse.is_button_pressed(1)
    houve_clique = pressionado_agora and not _mouse_pressionado_frame_anterior
    _mouse_pressionado_frame_anterior = pressionado_agora
    return houve_clique

# Classe padrão para criação de botões chanfrados
class Botao:
    def __init__(self, x, y, largura, altura, texto, cor_base):
        self.rect = pygame.Rect(x, y, largura, altura)
        self.texto = texto
        self.cor_base = cor_base

    def esta_sobre(self, pos_mouse):
        return self.rect.collidepoint(pos_mouse)

    def desenhar(self, selecionado=False):
        x, y, w, h = self.rect.x, self.rect.y, self.rect.width, self.rect.height
        corte = 12
        pontos = [
            (x + corte, y), (x + w - corte, y),
            (x + w, y + corte), (x + w, y + h - corte),
            (x + w - corte, y + h), (x + corte, y + h),
            (x, y + h - corte), (x, y + corte)
        ]
        pontos_sombra = [(px + 4, py + 4) for px, py in pontos]
        pygame.draw.polygon(tela, (5, 5, 12), pontos_sombra)
        pygame.draw.polygon(tela, self.cor_base, pontos)
        cor_borda = (255, 255, 255) if selecionado else (20, 20, 30)
        pygame.draw.polygon(tela, cor_borda, pontos, width=3)
        superficie_texto = fonte_botao.render(self.texto, True, cor_texto_botao)
        rect_texto = superficie_texto.get_rect(center=self.rect.center)
        tela.blit(superficie_texto, rect_texto)

# Função auxiliar para desenhar o título centralizado
def desenhar_titulo(texto, y):
    superficie = fonte_titulo.render(texto, True, cor_titulo)
    rect = superficie.get_rect(center=(largura_janela // 2, y))
    tela.blit(superficie, rect)