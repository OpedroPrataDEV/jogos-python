# Jogos em Python

Jogos que desenvolvi em Python com as bibliotecas **Pygame** e **PPlay**.

## Jogos

| Jogo | Pasta | Descrição |
|------|-------|-----------|
| Pong | `pong/` | Pong contra uma IA, com placar, pausa após o gol e bolinha que acelera a cada rebatida. |
| Space Invaders | `space-invaders/` | Nave contra hordas de monstros, com menu, três dificuldades, fases, vidas e ranking dos 5 melhores. |

## Dependências

- Python 3
- [Pygame](https://www.pygame.org/): `pip install pygame`
- PPlay, na versão [Power-PPlay 2.0](https://github.com/Kronohdev) (Kronohdev, licença MIT). Ela não está incluída neste repositório: baixe e coloque a pasta `PPlay/` ao lado do arquivo do jogo (por exemplo, `pong/PPlay/`).

## Como executar

Cada jogo fica na sua pasta e deve ser executado de dentro dela, porque lê imagens e arquivos pelo caminho relativo.

### Pong

```bash
cd pong
python PongCompleto.py
```

Setas `↑` e `↓` movem a raquete da esquerda e `Espaço` continua o jogo depois de um gol.

### Space Invaders

```bash
cd space-invaders
python main.py
```

O menu é controlado com o mouse. No jogo, setas `←` e `→` movem a nave, `Espaço` atira e `Esc` volta ao menu. Ao perder todas as vidas, o nome para o ranking é digitado no terminal. O arquivo `ranking.txt` é criado ao jogar e não é versionado.
