import random
import pygame
import config

# Classe para gerenciar os tiros disparados pelos monstros
class TiroMonstro:
    def __init__(self, x, y):
        self.largura = 5
        self.altura = 12
        self.x = float(x)
        self.y = float(y)
        self.rect = pygame.Rect(int(self.x), int(self.y), self.largura, self.altura)
        self.velocidade = 220

    def atualizar(self, dt):
        self.y += self.velocidade * dt
        self.rect.y = int(self.y)

    def desenhar(self):
        pygame.draw.rect(config.tela, (255, 87, 34), self.rect)

# Classe individual de cada monstro da horda
class Monstro:
    def __init__(self, x, y):
        self.largura = 36
        self.altura = 26
        self.x = float(x)
        self.y = float(y)
        self.rect = pygame.Rect(int(self.x), int(self.y), self.largura, self.altura)
        self.cor = (255, 87, 34)

    def desenhar(self):
        pygame.draw.rect(config.tela, self.cor, self.rect, border_radius=4)
        olho_esq = pygame.Rect(self.rect.x + 7, self.rect.y + 6, 6, 6)
        olho_dir = pygame.Rect(self.rect.right - 13, self.rect.y + 6, 6, 6)
        pygame.draw.rect(config.tela, (255, 255, 255), olho_esq)
        pygame.draw.rect(config.tela, (255, 255, 255), olho_dir)

# Classe que gerencia a matriz de monstros (horda)
class HordaMonstros:
    def __init__(self, linhas, colunas, fase=1):
        self.linhas = linhas
        self.colunas = colunas
        self.fase = fase
        self.monstros = []
        self.tiros = []
        self.direcao = 1
        self.velocidade_base = 120 + (fase - 1) * 25
        self.deslocamento_vertical = 18
        self.tempo_recarga_tiro = max(0.5, 1.2 - (fase - 1) * 0.2)
        self.cooldown_tiro = self.obter_novo_cooldown()
        self.criar_horda()

    def obter_novo_cooldown(self):
        return self.tempo_recarga_tiro + random.uniform(-0.2, 0.2)

    def criar_horda(self):
        self.monstros = []
        largura_m = 36
        altura_m = 26
        espaco_x = largura_m // 2
        espaco_y = altura_m // 2
        largura_total = self.colunas * largura_m + (self.colunas - 1) * espaco_x
        margin_x = (config.largura_janela - largura_total) // 2
        margin_y = 60

        for l in range(self.linhas):
            linha_monstros = []
            for c in range(self.colunas):
                pos_x = margin_x + c * (largura_m + espaco_x)
                pos_y = margin_y + l * (altura_m + espaco_y)
                monstro = Monstro(pos_x, pos_y)
                linha_monstros.append(monstro)
            self.monstros.append(linha_monstros)

    def ajustar_dificuldade(self):
        base_vel = self.velocidade_base
        if config.dificuldade_atual == "Facil":
            self.velocidade = base_vel * 0.8
        elif config.dificuldade_atual == "Medio":
            self.velocidade = base_vel
        elif config.dificuldade_atual == "Dificil":
            self.velocidade = base_vel * 1.35

    def atirar_aleatorio(self):
        monstros_vivos = [m for linha in self.monstros for m in linha]
        if monstros_vivos:
            atirador = random.choice(monstros_vivos)
            novo_tiro = TiroMonstro(atirador.rect.centerx, atirador.rect.bottom)
            self.tiros.append(novo_tiro)

    def obter_bounding_box(self):
        monstros_vivos = [m for linha in self.monstros for m in linha]
        if not monstros_vivos:
            return None
        min_x = min(m.rect.left for m in monstros_vivos)
        max_x = max(m.rect.right for m in monstros_vivos)
        min_y = min(m.rect.top for m in monstros_vivos)
        max_y = max(m.rect.bottom for m in monstros_vivos)
        return pygame.Rect(min_x, min_y, max_x - min_x, max_y - min_y)

    def esta_vazia(self):
        for linha in self.monstros:
            if len(linha) > 0:
                return False
        return True

    def checar_colisoes(self, player):
        pontos_ganhos = 0
        caixa_horda = self.obter_bounding_box()

        # Verifica colisão dos tiros do jogador com os monstros (otimizado via Bounding Box)
        for tiro in player.tiros[:]:
            if caixa_horda and not tiro.rect.colliderect(caixa_horda):
                continue
            tiro_atingiu = False
            for linha in self.monstros:
                for monstro in linha[:]:
                    if tiro.rect.colliderect(monstro.rect):
                        linha.remove(monstro)
                        tiro_atingiu = True
                        pontos_ganhos += 10
                        break
                if tiro_atingiu:
                    player.tiros.remove(tiro)
                    break

        # Verifica colisão dos tiros dos monstros com o jogador
        game_over = False
        for tiro in self.tiros[:]:
            if tiro.rect.colliderect(player.rect):
                self.tiros.remove(tiro)
                game_over = player.tomar_dano()
                if game_over:
                    return True, pontos_ganhos

        return False, pontos_ganhos

    def atualizar(self, dt, player):
        self.ajustar_dificuldade()

        self.cooldown_tiro -= dt
        if self.cooldown_tiro <= 0:
            self.atirar_aleatorio()
            self.cooldown_tiro = self.obter_novo_cooldown()

        for tiro in self.tiros[:]:
            tiro.atualizar(dt)
            if tiro.rect.top > config.altura_janela:
                self.tiros.remove(tiro)

        muda_direcao = False
        for linha in self.monstros:
            for monstro in linha:
                monstro.x += self.velocidade * self.direcao * dt
                monstro.rect.x = int(monstro.x)
                if monstro.rect.right >= config.largura_janela and self.direcao > 0:
                    muda_direcao = True
                elif monstro.rect.left <= 0 and self.direcao < 0:
                    muda_direcao = True

        if muda_direcao:
            self.direcao *= -1
            for linha in self.monstros:
                for monstro in linha:
                    monstro.y += self.deslocamento_vertical
                    monstro.rect.y = int(monstro.y)

        for linha in self.monstros:
            for monstro in linha:
                if monstro.rect.bottom >= player.rect.top:
                    return True

        return False

    def desenhar(self):
        for linha in self.monstros:
            for monstro in linha:
                monstro.desenhar()
        for tiro in self.tiros:
            tiro.desenhar()