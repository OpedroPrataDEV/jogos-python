from PPlay.window import Window
from PPlay.sprite import Sprite

#Criação da Janela
janela=Window(800,600)
janela.set_title("Pong Completo")

donobola=None

#Criação dos Sprites, Bolinha e Pads
bolinha=Sprite("pixil-frame-0.png")
pad_esquerdo=Sprite("pad.png")
pad_direito=Sprite("pad.png")

#Tornando o Teclado Utilizável
teclado=janela.get_keyboard()

#Variáveis do placar
placar_jogador=0
placar_ia=0

#Pausa do jogo após o gol
em_espera=False

#Função que mantém a bolinha no meio
def reseta_bolinha():
    #Nós dividimos por 2 e subtraímos metade da largura da bolinha pois se isso não fosse feito
    #O sprite COMEÇARIA a ser desenhado no meio da janela, deixando a bolinha levemente
    #Inclinada para a direita
    bolinha.x=((janela.width/2)-(bolinha.width/2))
    bolinha.y=((janela.height/2)-(bolinha.height/2))
reseta_bolinha()

#Posicionamento dos pads
pad_esquerdo.x=5
pad_esquerdo.y=((janela.height/2)-(pad_esquerdo.height/2)) #Mesma lógica da bolinha
pad_direito.x=janela.width-pad_direito.width-5 #ele COMEÇA a ser desenhado no fim da janela, depois fica
#na borda e DEPOIS o -5 para ficar a 5 pixeis de distância da borda
pad_direito.y=((janela.height/2)-(pad_direito.height/2))

#Velocidade âncora
vel_x_inicial=200
vel_y_inicial=200

#Velociade da Bolinha
vel_x=200
vel_y=200
#Velocidade Pad
vel_pad=300
#Fator de Aceleração a cada rebatida
fator_aceleracao=1.05

tempo_acumulado=0

#O While True mantém a janela na tela, em cada ciclo ele
#Lê as Entradas, Atualiza a lógica, Desenha na tela
while True:
    janela.set_background_color((0,0,0))
    #Captura o tempo decorrido desde o último quadro
    dt=janela.delta_time()
    tempo_acumulado+=dt
    #Atualiza a posição da bolinha baseado no cálculo do tempo


    #Lógica da pontuação
    if not em_espera:
        bolinha.x += vel_x * dt
        bolinha.y += vel_y * dt

        #Lógica/Verificação de Colisão
            #Chão/Teto
        if bolinha.y<=0:
            bolinha.y=0
            vel_y*=-1
        elif bolinha.y+bolinha.height>=janela.height:
            bolinha.y=janela.height-bolinha.height
            vel_y*=-1

        #Movimento Teclado Jogador
        if teclado.key_pressed("UP") and pad_esquerdo.y>0:
            #Respeitando o teto (>0)
            pad_esquerdo.y-=vel_pad*dt
        if teclado.key_pressed("DOWN") and pad_esquerdo.y+pad_esquerdo.height<janela.height:
            #Respeitando o chão(<0)
            pad_esquerdo.y+=vel_pad*dt

        #Movimento da IA
        centro_ia=pad_direito.y+(pad_direito.height/2) #Pega exatamente o centro
        centro_bolinha=bolinha.y+(bolinha.height/2)
        #Logica de movimento baseada no alinhamento do meio do pad da IA e da bolinha
        if centro_ia>centro_bolinha and pad_direito.y>0:
            pad_direito.y-=vel_pad*dt
        elif centro_ia<centro_bolinha and pad_direito.y+pad_direito.height<janela.height:
            pad_direito.y+=vel_pad*dt

        #Colisão com os Pads
        if bolinha.collided(pad_direito):
            bolinha.x=pad_direito.x-bolinha.width #Descola da bolinha do pad
            vel_x*=-1
            vel_x*=fator_aceleracao
            vel_y*=fator_aceleracao
        elif bolinha.collided(pad_esquerdo):
            bolinha.x=pad_esquerdo.x+pad_esquerdo.width
            vel_x*=-1
            vel_x*=fator_aceleracao
            vel_y*=fator_aceleracao

        #Lógica dos gols/Pontuação
        if bolinha.x<=0:
            placar_ia+=1
            reseta_bolinha()
            vel_x=vel_x_inicial
            vel_y=vel_y_inicial
            donobola='ia'
            em_espera=True #Ativa a Pausa
        elif bolinha.x+bolinha.width>=janela.width:
            placar_jogador+=1
            reseta_bolinha()
            vel_x=vel_x_inicial
            vel_y=vel_y_inicial
            donobola='jogador'
            em_espera=True
    else:
        tempo_acumulado+=dt
        # Movimento Teclado Jogador
        if teclado.key_pressed("UP") and pad_esquerdo.y > 0:
            # Respeitando o teto (>0)
            pad_esquerdo.y -= vel_pad * dt
        if teclado.key_pressed("DOWN") and pad_esquerdo.y + pad_esquerdo.height < janela.height:
            # Respeitando o chão(<0)
            pad_esquerdo.y += vel_pad * dt


        if donobola=='jogador':
            bolinha.x=pad_esquerdo.x+pad_esquerdo.width
            bolinha.y=(
                pad_esquerdo.y
                + (pad_esquerdo.height/2)
                - (bolinha.height/2)
            )
        elif donobola=='ia':
            bolinha.x=pad_direito.x-bolinha.width
            bolinha.y=(
                pad_direito.y+(pad_direito.height/2)-(bolinha.height/2)
            )

        if teclado.key_pressed("SPACE"):
            em_espera=False



    janela.draw_text(f"{placar_jogador}", janela.width/4,20,size=36,color=(255,255,255))
    janela.draw_text(f"{placar_ia}", (3*janela.width) / 4, 20, size=36, color=(255, 255, 255))
    if em_espera:
        janela.draw_text("Aperte Espaço para Continuar ",janela.width/2 -180, janela.height/2 +50,size=20,color=(255,255,255))


    #Renderização
    bolinha.draw()
    pad_direito.draw()
    pad_esquerdo.draw()
    janela.update()
