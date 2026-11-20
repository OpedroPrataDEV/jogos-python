"""Definição das 5 fases (layout da grade, regras especiais, tema)."""
import config as C

# Legenda do layout:  . vazio | t terra | p pedra | s prata | o ouro | d diamante
#                     g gema (sempre solta um power-up) | G granito (só TNT quebra) | x TNT
FASES = [
    dict(
        id=1, nome="Poço de Terra", sub="Todo grande mineiro começa cavando devagar",
        fundo="fundo_fase1.png", musica="mina", cor=(255, 190, 90),
        vel=320, vel_max=470, grade_y0=C.GRADE_Y0, prof=(0, 110),
        estalactites=None, geysers=None, escuro=False, lava=0.55,
        dica="Quebre os blocos e pegue o minério antes que ele caia na lava!",
        layout=[
            "ppp.....ppp",
            "ptttttttttp",
            "tttppgppptt",
            "ptttttttttp",
            ".ttttttttt.",
            "..ttttttt..",
        ],
    ),
    dict(
        id=2, nome="Galeria de Prata", sub="O brilho das veias esconde uma surpresa explosiva",
        fundo="fundo_fase2.png", musica="mina", cor=(190, 215, 255),
        vel=340, vel_max=500, grade_y0=C.GRADE_Y0, prof=(110, 260),
        estalactites=None, geysers=None, escuro=False, lava=0.7,
        dica="TNT explode os vizinhos. Granito só cede à dinamite!",
        layout=[
            "G.sssssss.G",
            "ppsppxppspp",
            "ssspppppsss",
            "pGpsssssGpp",
            "ppxppgppxpp",
            "tpppppppppt",
            "..ttttttt..",
        ],
    ),
    dict(
        id=3, nome="Caverna Cega", sub="Sem luz, só o brilho do ouro mostra o caminho",
        fundo="fundo_fase3.png", musica="mina", cor=(255, 215, 90),
        vel=355, vel_max=520, grade_y0=C.GRADE_Y0, prof=(260, 440),
        estalactites=7.5, geysers=None, escuro=True, lava=0.85,
        dica="Escuro! Ouro e diamante brilham à distância. Cuidado com as estalactites!",
        layout=[
            "o.o.o.o.o.o",
            "sssGsssGsss",
            "ooosooosooo",
            "psxpgpgpxsp",
            "GppppdppppG",
            ".sssoooosss",
        ],
    ),
    dict(
        id=4, nome="Gruta de Cristal", sub="Diamantes por toda parte... e lava jorrando do chão",
        fundo="fundo_fase4.png", musica="mina", cor=(110, 210, 255),
        vel=370, vel_max=540, grade_y0=C.GRADE_Y0, prof=(440, 680),
        estalactites=9.0, geysers=6.5, escuro=False, lava=1.0,
        dica="Gêiseres de lava! Fuja da faixa vermelha no chão.",
        layout=[
            "dGdGdGdGdGd",
            "ooxoooooxoo",
            "sdsdsgsdsds",
            "GoooGxGoooG",
            "ppdpppppdpp",
            ".ssssgssss.",
            "..ooo.ooo..",
        ],
    ),
    dict(
        id=5, nome="O Núcleo", sub="O coração do planeta acorda",
        fundo="fundo_fase5.png", musica="chefe", cor=(255, 90, 60),
        vel=380, vel_max=560, grade_y0=232, prof=(680, 1000),
        estalactites=None, geysers=None, escuro=False, lava=1.3, chefe=True,
        dica="Acerte o olho do Núcleo! Ele esquenta a cada fase da luta.",
        layout=[
            "G.tp.d.pt.G",
            "G.........G",
            "Gt.......tG",
        ],
        reabastece=[
            "..t.p.p.t..",
            ".g.t...t.g.",
            "..pp.x.pp..",
        ],
    ),
]

for _f in FASES:
    for _linha in _f["layout"] + _f.get("reabastece", []):
        assert len(_linha) == C.COLUNAS, (_f["nome"], _linha)

NOMES_BLOCO = {"t": "terra", "p": "pedra", "s": "prata", "o": "ouro", "d": "diamante",
               "g": "gema", "G": "granito", "x": "tnt"}
