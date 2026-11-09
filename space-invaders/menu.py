import os
import config

# Tela de exibição do ranking com os 5 melhores jogadores ordenados
def tela_ranking():
    while True:
        config.window.set_background_color(config.cor_fundo_menu)
        config.desenhar_titulo("RANKING", 70)

        linhas_ranking = []
        if os.path.exists("ranking.txt"):
            with open("ranking.txt", "r", encoding="utf-8") as f:
                linhas_ranking = f.readlines()

        dados = []
        for linha in linhas_ranking:
            partes = linha.strip().split(";")
            if len(partes) == 3:
                nome, score, data = partes[0], int(partes[1]), partes[2]
                dados.append((nome, score, data))

        # Ordena do maior para o menor score e seleciona estritamente os top 5
        dados.sort(key=lambda x: x[1], reverse=True)
        top_5 = dados[:5]

        y_inicial = 180
        if not top_5:
            config.window.draw_text("Nenhum recorde registrado ainda!", config.largura_janela // 2 - 160, y_inicial, size=20, color=(200, 200, 200))
        else:
            config.window.draw_text("POS   NOME                   PONTOS      DATA", config.largura_janela // 2 - 220, y_inicial, size=18, color=(255, 193, 7))
            pygame_y = y_inicial + 35
            for i, (nome, score, data) in enumerate(top_5):
                texto_linha = f"{i+1}º    {nome[:15]:<15}      {score:<8}    {data}"
                config.window.draw_text(texto_linha, config.largura_janela // 2 - 220, pygame_y, size=18, color=(255, 255, 255))
                pygame_y += 35

        config.window.draw_text("Pressione [ESC] para voltar ao Menu", config.largura_janela // 2 - 140, config.altura_janela - 70, size=16, color=(150, 150, 150))
        config.window.update()

        if config.keyboard.key_pressed("esc"):
            return "MENU"

# Tela principal do menu do jogo
def tela_menu(navegar_para):
    largura_botao, altura_botao = 260, 52
    x_botao = config.largura_janela // 2 - largura_botao // 2
    espaco = 18

    botao_jogar = config.Botao(x_botao, 190, largura_botao, altura_botao, "JOGAR", config.cor_jogar)
    botao_dificuldade = config.Botao(x_botao, 190 + (altura_botao + espaco), largura_botao, altura_botao, "DIFICULDADE", config.cor_dificuldade)
    botao_ranking = config.Botao(x_botao, 190 + 2 * (altura_botao + espaco), largura_botao, altura_botao, "RANKING", config.cor_ranking)
    botao_sair = config.Botao(x_botao, 190 + 3 * (altura_botao + espaco), largura_botao, altura_botao, "SAIR", config.cor_sair)

    while True:
        config.window.set_background_color(config.cor_fundo_menu)
        pos_mouse = config.mouse.get_position()

        config.desenhar_titulo("SPACE INVADERS", 95)
        botao_jogar.desenhar()
        botao_dificuldade.desenhar()
        botao_ranking.desenhar()
        botao_sair.desenhar()

        clicou = config.clique_unico()

        if clicou and botao_jogar.esta_sobre(pos_mouse):
            config.window.update()
            return "JOGO"
        elif clicou and botao_dificuldade.esta_sobre(pos_mouse):
            config.window.update()
            return "DIFICULDADE"
        elif clicou and botao_ranking.esta_sobre(pos_mouse):
            config.window.update()
            return "RANKING"
        elif clicou and botao_sair.esta_sobre(pos_mouse):
            config.window.close()

        config.window.update()