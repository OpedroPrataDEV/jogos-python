# ⛏️ Rumo ao Núcleo

Projeto final de **Laboratório de Programação de Jogos** (UFF) — Python + **PPlay** + Pygame.
Um Breakout de mineração: a broca é a "bolinha", os blocos são camadas de terra, pedra, prata, ouro e diamante,
e o chão é lava. Cinco fases, chefe final, loja de melhorias, ranking e muito efeito visual.

## Como rodar (PyCharm)

1. Abra a pasta `RumoAoNucleo` como projeto no PyCharm (a pasta que contém o `main.py`).
2. Garanta que o **PPlay** esteja instalado/visível no projeto (a pasta `PPlay` ao lado do `main.py`, como nas aulas,
   ou instalada no interpretador). O jogo aceita `PPlay` e `pplay`.
3. Instale o Pygame se ainda não tiver: `pip install pygame`
4. Execute o **`main.py`**.

> Não é preciso instalar mais nada para jogar. `numpy` e `Pillow` só são usados por quem quiser **regenerar**
> as imagens e os sons (pasta `ferramentas/`).

## Controles

| Tecla | Ação |
|---|---|
| ← → ou A D | mover a vagoneta (plataforma) |
| ESPAÇO / ENTER | lançar a broca / confirmar |
| P ou ESC | pausar |
| M | ligar/desligar o som |
| ↑ ↓ ← → | navegar nos menus |

## O que tem no jogo

- **5 fases**: Poço de Terra → Galeria de Prata → Caverna Cega (escura) → Gruta de Cristal (gêiseres de lava) → **O Núcleo** (chefe em 3 fases).
- **Mineração de verdade na jogabilidade**
  - Blocos com resistência crescente (terra 1, pedra 2, prata 3, ouro 4, diamante 5) que racham a cada golpe.
  - **Minério cai dos blocos** e vira dinheiro: pegue com a vagoneta antes que caia na lava.
  - **Oficina**: gaste o minério em 5 melhorias permanentes (tungstênio, vagoneta, capacete, ímã, isolamento térmico).
  - **Calor**: acertar blocos esquenta a broca; no máximo ela entra em **superaquecimento** e perfura tudo.
  - **TNT** explode em cadeia; **granito** só quebra com explosão.
  - **Estalactites** se soltam dos blocos; **gêiseres de lava** com aviso no chão; fase **escura** em que ouro e diamante brilham.
  - O fundo "desce" conforme você escava e o HUD mostra a **profundidade** em metros.
  - 6 power-ups: viga de aço, multibroca, picareta x2, dinamite, capacete (+vida), lanterna.
  - Combo até x5, golpes críticos, câmera tremendo, câmera lenta na morte do chefe, partículas, lava animada.
- **Menus**: título animado, selecionar fase (com bloqueio), oficina, ranking top-10 (salvo em arquivo),
  como jogar (3 páginas), créditos, tela de nome para o recorde, pausa.
- **Progresso salvo** em `dados/progresso.json` e **ranking** em `dados/ranking.json` (apague os arquivos para zerar).

## Sobre o código (para a defesa com o professor)

- **Nada de `if bola.x <= 0`**: paredes e teto usam *clamp* com `min/max` (`util.clamp`) e o sinal da velocidade é
  invertido por aritmética (`vx *= 1 - 2*int(bateu_x)`). Veja `Partida._paredes`.
- **Sem a classe/método de colisão do PPlay**: toda colisão é feita à mão em `util.py`
  (`colidiu` — retângulo × retângulo; `circulo_retangulo` — broca × bloco, com normal de rebote).
- **PPlay**: `Window` (janela e laço), `Sprite` com *spritesheet* (frames de rachadura dos blocos, giro da broca),
  `set_position`, `set_curr_frame`, `draw`. Efeitos extras (partículas, lava, escuridão, chefe) são desenhados com Pygame.
- **Entrada de teclado** lida com `pygame.key.get_pressed()` e detecção de "apertou agora" própria (`util.Entrada`).

### Estrutura

```
main.py          ← execute este
config.py        ← constantes e opções (DEBUG, DESBLOQUEAR_TODAS_FASES...)
jogo.py          ← janela, laço principal, transições de tela
partida.py       ← toda a jogabilidade, HUD, pausa, fim de fase
entidades.py     ← Bloco, Broca, Plataforma, itens que caem, perigos
chefe.py         ← o chefe "O Núcleo"
fases.py         ← layout das 5 fases
menus.py         ← título, seleção, oficina, ranking, ajuda, créditos, nome
util.py          ← colisão, entrada, texto, partículas, áudio
dados.py         ← salvar/ler progresso e ranking
assets/          ← imagens e sons
ferramentas/     ← scripts que geram as imagens e os sons
```

### Opções úteis

Em `config.py` (ou pela linha de comando `python main.py --debug --todas`):

- `DEBUG = True` → `N` pula a fase, `L` +1 vida, `H` esquenta a broca, `K` +100 de minério.
- `DESBLOQUEAR_TODAS_FASES = True` → libera todas as fases no menu.
- `AUTOR = "Seu Nome"` → aparece nos créditos.
- Link Teaser: https://www.youtube.com/watch?v=9ACkjCx5Ki0
- Link do jogo no ITCH.IO: https://opedroprata.itch.io/rumo-ao-nucleo

Bom jogo! ⛏️🔥
