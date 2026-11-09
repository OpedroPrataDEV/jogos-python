import config

# Tela de seleção de dificuldade
def tela_dificuldade():
    largura_botao, altura_botao = 190, 60
    espaco = 25
    total_largura = 3 * largura_botao + 2 * espaco
    x_inicial = config.largura_janela // 2 - total_largura // 2
    y_botao = 260

    # Criação dos botões de dificuldade
    botao_facil = config.Botao(x_inicial, y_botao, largura_botao, altura_botao, "FACIL", config.cor_jogar)
    botao_medio = config.Botao(x_inicial + (largura_botao + espaco), y_botao, largura_botao, altura_botao, "MEDIO", config.cor_dificuldade)
    botao_dificil = config.Botao(x_inicial + 2 * (largura_botao + espaco), y_botao, largura_botao, altura_botao, "DIFICIL", config.cor_sair)

    while True:
        config.window.set_background_color(config.cor_fundo_dificuldade)
        pos_mouse = config.mouse.get_position()

        config.desenhar_titulo("DIFICULDADE", 100)
        config.window.draw_text("Selecione o nivel de desafio:", config.largura_janela // 2 - 120, 190, size=20, color=(230, 230, 230))

        # Desenha os botões indicando o selecionado atual
        botao_facil.desenhar(selecionado=(config.dificuldade_atual == "Facil"))
        botao_medio.desenhar(selecionado=(config.dificuldade_atual == "Medio"))
        botao_dificil.desenhar(selecionado=(config.dificuldade_atual == "Dificil"))

        clicou = config.clique_unico()

        # Atualiza a dificuldade conforme o clique
        if clicou and botao_facil.esta_sobre(pos_mouse):
            config.dificuldade_atual = "Facil"
        elif clicou and botao_medio.esta_sobre(pos_mouse):
            config.dificuldade_atual = "Medio"
        elif clicou and botao_dificil.esta_sobre(pos_mouse):
            config.dificuldade_atual = "Dificil"

        config.window.update()

        # Retorna ao menu ao pressionar ESC
        if config.keyboard.key_pressed("esc"):
            return "MENU"