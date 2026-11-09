import pygame
import config

# Classe responsável pelos tiros disparados pelo jogador
class Tiro:
    def __init__(self, x, y, velocidade_tiro):
        self.largura = 4
        self.altura = 12
        self.y = float(y)
        self.x = float(x - self.largura // 2)
        self.rect = pygame.Rect(int(self.x), int(self.y), self.largura, self.altura)
        self.velocidade = velocidade_tiro

    def atualizar(self, dt):
        self.y -= self.velocidade * dt
        self.rect.y = int(self.y)

    def desenhar(self):
        pygame.draw.rect(config.tela, (0, 229, 255), self.rect)

# Classe principal do jogador (nave)
class Jogador:
    def __init__(self):
        self.largura = 50
        self.altura = 25
        self.resetar_posicao()
        self.velocidade_base = 350
        self.tiros = []
        self.cooldown_tiro = 0
        self.vidas = 3
        self.tempo_invencivel = 0
        self.visivel = True
        self.tempo_piscando = 0

    def resetar_posicao(self):
        self.x = float((config.largura_janela // 2) - (self.largura // 2))
        self.y = float(config.altura_janela - 50)
        self.rect = pygame.Rect(int(self.x), int(self.y), self.largura, self.altura)

    def tomar_dano(self):
        if self.tempo_invencivel <= 0:
            self.vidas -= 1
            self.resetar_posicao()
            self.tempo_invencivel = 2.0
            return self.vidas <= 0
        return False

    def ajustar_dificuldade(self):
        if config.dificuldade_atual == "Facil":
            self.velocidade = self.velocidade_base * 1.2
            self.tempo_recarga = 0.27
            self.velocidade_tiro = 400
        elif config.dificuldade_atual == "Medio":
            self.velocidade = self.velocidade_base
            self.tempo_recarga = 0.27
            self.velocidade_tiro = 400
        elif config.dificuldade_atual == "Dificil":
            self.velocidade = self.velocidade_base * 0.85
            self.tempo_recarga = 0.27
            self.velocidade_tiro = 400

    def atirar(self):
        if self.cooldown_tiro <= 0:
            novo_tiro = Tiro(self.rect.centerx, self.rect.top, self.velocidade_tiro)
            self.tiros.append(novo_tiro)
            self.cooldown_tiro = self.tempo_recarga

    def atualizar(self, dt):
        self.ajustar_dificuldade()

        # Controla o tempo de invencibilidade e efeito visual de piscar
        if self.tempo_invencivel > 0:
            self.tempo_invencivel -= dt
            self.tempo_piscando += dt
            if self.tempo_piscando >= 0.1:
                self.visivel = not self.visivel
                self.tempo_piscando = 0
        else:
            self.visivel = True

        if self.cooldown_tiro > 0:
            self.cooldown_tiro -= dt

        # Movimentação lateral com as setas do teclado
        if config.keyboard.key_pressed("LEFT"):
            self.x -= self.velocidade * dt
        elif config.keyboard.key_pressed("RIGHT"):
            self.x += self.velocidade * dt

        self.rect.x = int(self.x)

        # Limita a nave dentro dos limites da janela
        if self.rect.left < 0:
            self.rect.left = 0
            self.x = 0.0
        if self.rect.right > config.largura_janela:
            self.rect.right = config.largura_janela
            self.x = float(config.largura_janela - self.largura)

        if config.keyboard.key_pressed("SPACE"):
            self.atirar()

        for tiro in self.tiros[:]:
            tiro.atualizar(dt)
            if tiro.rect.bottom < 0:
                self.tiros.remove(tiro)

    def desenhar(self):
        if not self.visivel:
            return

        p1 = (self.rect.centerx, self.rect.top)
        p2 = (self.rect.right, self.rect.bottom)
        p3 = (self.rect.centerx, self.rect.bottom - 6)
        p4 = (self.rect.left, self.rect.bottom)

        pygame.draw.polygon(config.tela, config.cor_jogar, [p1, p2, p3, p4])
        pygame.draw.polygon(config.tela, (255, 255, 255), [p1, p2, p3, p4], width=2)

        for tiro in self.tiros:
            tiro.desenhar()