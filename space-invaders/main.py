from datetime import datetime
import config
import dificuldade
import menu
from jogador import Jogador
from monstro import HordaMonstros

# Salva o ranking do jogador no arquivo de texto ao fim do jogo
def salvar_ranking(pontos):
    print("\n" + "=" * 40)
    print(" FIM DE JOGO! VOCÊ PERDEU TODAS AS VIDAS ")
    print(f" Pontuação final: {pontos} pontos")
    print("=" * 40)
    nome = input("Digite seu nome para o Ranking: ").strip()
    if not nome:
        nome = "Jogador Anônimo"

    data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")

    with open("ranking.txt", "a", encoding="utf-8") as f:
        f.write(f"{nome};{pontos};{data_atual}\n")
    print("Pontuação salva com sucesso no ranking!\n")

# Loop principal da partida do jogo
def tela_jogo():
    player = Jogador()
    fase = 1
    pontos = 0
    tempo_fase = 0.0  # Cronômetro para calcular o bônus de velocidade
    horda = HordaMonstros(config.linhas_monstros, config.colunas_monstros, fase)

    while True:
        dt = config.window.delta_time()
        tempo_fase += dt  # Incrementa o tempo gasto na fase atual
        config.window.set_background_color(config.cor_fundo_jogo)

        # Atualiza posições do player e horda
        player.atualizar(dt)
        game_over_invasao = horda.atualizar(dt, player)
        game_over_tiro, pontos_novos = horda.checar_colisoes(player)
        pontos += pontos_novos

        # Se todos os monstros forem destruídos, avança para a próxima fase com bônus de velocidade
        if horda.esta_vazia():
            # Concede pontuação ligeiramente maior para quem limpou a fase mais rápido
            bonus_velocidade = max(50, int(300 - tempo_fase * 5))
            pontos += bonus_velocidade

            fase += 1
            tempo_fase = 0.0  # Reseta o cronômetro para a nova fase
            horda = HordaMonstros(config.linhas_monstros, config.colunas_monstros, fase)
            player.resetar_posicao()

        # Desenha os elementos na tela
        player.desenhar()
        horda.desenhar()

        # Exibe informações na interface (HUD)
        fps = int(1.0 / dt) if dt > 0 else 0
        config.window.draw_text(f"FAS: {fase}", 10, 10, size=18, color=(255, 235, 59))
        config.window.draw_text(f"PONTOS: {pontos}", 10, 32, size=18, color=(0, 229, 255))
        config.window.draw_text(f"VIDAS: {player.vidas}", 10, 54, size=18, color=(255, 87, 34))

        config.window.draw_text(f"Dificuldade: {config.dificuldade_atual.upper()}", config.largura_janela - 180, 10, size=14, color=(180, 180, 180))
        config.window.draw_text(f"FPS: {fps}", config.largura_janela - 80, 30, size=16, color=(0, 230, 118))

        config.window.update()

        # Trata o fim de jogo
        if game_over_invasao or game_over_tiro:
            salvar_ranking(pontos)
            return "MENU"

        # Atalho para voltar ao menu
        if config.keyboard.key_pressed("esc"):
            return "MENU"

# Gerencia a troca de estados do jogo (Menu, Jogo, Dificuldade, Ranking)
def main():
    estado_atual = "MENU"

    while True:
        if estado_atual == "MENU":
            estado_atual = menu.tela_menu(estado_atual)
        elif estado_atual == "JOGO":
            estado_atual = tela_jogo()
        elif estado_atual == "DIFICULDADE":
            estado_atual = dificuldade.tela_dificuldade()
        elif estado_atual == "RANKING":
            estado_atual = menu.tela_ranking()

if __name__ == "__main__":
    main()