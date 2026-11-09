# Jogos em Python

Jogos que desenvolvi em Python com as bibliotecas **Pygame** e **PPlay**.

## Jogos

| Jogo | Pasta | Descrição |
|------|-------|-----------|
| Pong | `pong/` | Pong contra uma IA, com placar, pausa após o gol e bolinha que acelera a cada rebatida. |

## Dependências

- Python 3
- [Pygame](https://www.pygame.org/): `pip install pygame`
- PPlay, na versão [Power-PPlay 2.0](https://github.com/Kronohdev) (Kronohdev, licença MIT). Ela não está incluída neste repositório: baixe e coloque a pasta `PPlay/` ao lado do arquivo do jogo (por exemplo, `pong/PPlay/`).

## Como executar

```bash
cd pong
python PongCompleto.py
```

Controles do Pong: setas `↑` e `↓` movem a raquete da esquerda e `Espaço` continua o jogo depois de um gol.
