"""
Sintetiza TODOS os efeitos sonoros e as músicas do jogo (arquivos .wav em assets/sons).
Só é necessário rodar se quiser regenerar os sons (precisa de numpy).
Uso:  python gerar_sons.py
"""
import os
import wave

import numpy as np

SR = 22050
RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "sons")
os.makedirs(RAIZ, exist_ok=True)
RNG = np.random.default_rng(42)


# ------------------------------------------------------------------ síntese básica
def freq(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def osc(tipo, f, d):
    n = int(SR * d)
    f = np.full(n, f, np.float64) if np.isscalar(f) else np.asarray(f, np.float64)
    ph = 2 * np.pi * np.cumsum(f) / SR
    if tipo == "sine":
        return np.sin(ph)
    if tipo == "square":
        return np.sign(np.sin(ph))
    if tipo == "pulse":
        return np.where((ph / (2 * np.pi)) % 1 < 0.25, 1.0, -1.0)
    if tipo == "tri":
        return 2 / np.pi * np.arcsin(np.sin(ph))
    if tipo == "saw":
        return 2 * ((ph / (2 * np.pi)) % 1) - 1
    raise ValueError(tipo)


def ruido(d):
    return RNG.uniform(-1, 1, int(SR * d))


def passa_baixa(x, k):
    if k <= 1:
        return x
    ker = np.ones(k) / k
    return np.convolve(x, ker, mode="same")


def passa_alta(x, k):
    return x - passa_baixa(x, k)


def env(n, ataque=0.003, tau=0.1, soltar=0.01):
    t = np.arange(n) / SR
    e = np.exp(-t / max(tau, 1e-4))
    a = int(SR * ataque)
    if a > 0:
        e[:a] *= np.linspace(0, 1, a)
    r = int(SR * soltar)
    if 0 < r < n:
        e[-r:] *= np.linspace(1, 0, r)
    return e


def nota(tipo, f, d, vol=0.5, tau=None, ataque=0.003):
    s = osc(tipo, f, d)
    return s * env(len(s), ataque, tau if tau else d * 0.6, 0.01) * vol


def colocar(buf, sinal, inicio):
    i = int(SR * inicio)
    if i >= len(buf):
        return
    fim = min(len(buf), i + len(sinal))
    buf[i:fim] += sinal[: fim - i]


def juntar(*partes):
    n = max(len(p) for p in partes)
    out = np.zeros(n)
    for p in partes:
        out[: len(p)] += p
    return out


def normalizar(x, pico=0.85):
    m = np.max(np.abs(x)) + 1e-9
    return x / m * pico


def salvar(nome, x):
    x = np.clip(x, -1, 1)
    dados = (x * 32767).astype(np.int16)
    with wave.open(os.path.join(RAIZ, nome + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(dados.tobytes())


# ------------------------------------------------------------------ efeitos
def deslizar(f0, f1, d, tipo="sine", tau=None, vol=0.7):
    n = int(SR * d)
    f = np.linspace(f0, f1, n)
    s = osc(tipo, f, d)
    return s * env(n, 0.002, tau if tau else d * 0.5, 0.01) * vol


def sfx():
    out = {}
    out["rebater"] = juntar(deslizar(300, 150, 0.12, "sine", 0.05), ruido(0.03) * env(int(SR * 0.03), 0.001, 0.01) * 0.3)
    out["parede"] = deslizar(520, 420, 0.06, "tri", 0.03, 0.6)
    out["bloco"] = juntar(deslizar(420, 260, 0.07, "square", 0.03, 0.35), passa_alta(ruido(0.05), 5) * env(int(SR * 0.05), 0.001, 0.015) * 0.5)
    n = int(SR * 0.28)
    out["quebra"] = juntar(passa_baixa(ruido(0.28), 6) * env(n, 0.002, 0.08) * 0.9, deslizar(220, 70, 0.22, "tri", 0.08, 0.7))
    out["minerio"] = np.concatenate([nota("sine", 988, 0.07, 0.6, 0.05), nota("sine", 1319, 0.14, 0.6, 0.09)])
    out["ouro"] = np.concatenate([nota("sine", 1047, 0.06, 0.6, 0.05), nota("sine", 1319, 0.06, 0.6, 0.05), nota("sine", 1568, 0.16, 0.6, 0.1)])
    out["diamante"] = np.concatenate([nota("sine", f, 0.06, 0.55, 0.05) for f in (1319, 1568, 1976)] + [nota("sine", 2637, 0.28, 0.55, 0.16)])
    out["gema"] = juntar(np.concatenate([nota("tri", f, 0.07, 0.6, 0.06) for f in (784, 988, 1319, 1568, 1976)] + [nota("tri", 2093, 0.4, 0.6, 0.25)]),
                         np.concatenate([nota("sine", f * 2, 0.07, 0.25, 0.06) for f in (784, 988, 1319, 1568, 1976)] + [nota("sine", 4186, 0.4, 0.2, 0.25)]))
    out["powerup"] = np.concatenate([nota("square", freq(m), 0.065, 0.35, 0.05) for m in (72, 76, 79, 84)] + [nota("square", freq(88), 0.18, 0.35, 0.1)])
    n = int(SR * 0.9)
    out["explosao"] = juntar(passa_baixa(ruido(0.9), 14) * env(n, 0.002, 0.22) * 1.0, deslizar(110, 28, 0.8, "sine", 0.25, 0.9),
                             passa_baixa(ruido(0.9), 4) * env(n, 0.002, 0.07) * 0.5)
    out["vida_perdida"] = juntar(deslizar(620, 70, 0.7, "saw", 0.4, 0.5), deslizar(310, 40, 0.7, "square", 0.4, 0.3))
    out["menu_mover"] = nota("square", 660, 0.045, 0.3, 0.03)
    out["menu_ok"] = np.concatenate([nota("square", 660, 0.05, 0.35, 0.04), nota("square", 990, 0.11, 0.35, 0.07)])
    out["comprar"] = np.concatenate([nota("sine", f, 0.07, 0.6, 0.06) for f in (1047, 1319, 1568)] + [nota("sine", 2093, 0.3, 0.6, 0.2), ])
    out["erro"] = juntar(nota("square", 160, 0.18, 0.4, 0.12), nota("square", 150, 0.18, 0.3, 0.12))
    n = int(SR * 0.25)
    out["lancar"] = juntar(passa_baixa(ruido(0.25), 10) * np.linspace(0, 1, n) * env(n, 0.001, 0.2) * 0.8, deslizar(240, 900, 0.22, "sine", 0.18, 0.5))
    vib = 1 + 0.03 * np.sin(2 * np.pi * 18 * np.arange(int(SR * 0.7)) / SR)
    out["calor"] = juntar(osc("saw", np.linspace(180, 1300, int(SR * 0.7)) * vib, 0.7) * env(int(SR * 0.7), 0.01, 0.5) * 0.5,
                          passa_baixa(ruido(0.7), 5) * env(int(SR * 0.7), 0.01, 0.4) * 0.4)
    out["fase_ok"] = np.concatenate([nota("square", freq(m), d, 0.35, d * 0.8) for m, d in ((72, 0.1), (76, 0.1), (79, 0.1), (84, 0.16), (79, 0.1), (84, 0.45))])
    out["game_over"] = np.concatenate([nota("saw", freq(m), d, 0.4, d * 0.9) for m, d in ((67, 0.25), (63, 0.25), (60, 0.25), (55, 0.9))])
    out["chefe_hit"] = juntar(deslizar(180, 50, 0.3, "sine", 0.12, 0.9), deslizar(900, 300, 0.2, "square", 0.06, 0.25), passa_baixa(ruido(0.2), 6) * env(int(SR * 0.2), 0.001, 0.05) * 0.6)
    n = int(SR * 3.0)
    out["chefe_morre"] = juntar(passa_baixa(ruido(3.0), 18) * env(n, 0.01, 0.9) * 1.0, deslizar(90, 20, 2.8, "sine", 1.2, 0.9),
                                osc("saw", np.linspace(400, 2400, n), 3.0) * env(n, 0.05, 1.2) * 0.18)
    out["aviso"] = juntar(nota("square", 880, 0.08, 0.25, 0.05), np.concatenate([np.zeros(int(SR * 0.1)), nota("square", 880, 0.08, 0.25, 0.05)]))
    n = int(SR * 0.3)
    out["impacto"] = juntar(deslizar(140, 45, 0.3, "sine", 0.1, 0.9), passa_baixa(ruido(0.3), 5) * env(n, 0.001, 0.07) * 0.7)
    out["vida_extra"] = np.concatenate([nota("tri", freq(m), 0.09, 0.55, 0.08) for m in (67, 72, 76, 79, 84)] + [nota("tri", freq(88), 0.35, 0.55, 0.22)])
    out["combo"] = np.concatenate([nota("square", freq(m), 0.04, 0.3, 0.03) for m in (79, 83)])
    out["vitoria"] = np.concatenate([nota("square", freq(m), d, 0.38, d * 0.85) for m, d in
                                     ((72, 0.14), (72, 0.14), (72, 0.14), (76, 0.4), (74, 0.14), (74, 0.14), (74, 0.14), (79, 0.5), (79, 0.14), (84, 0.9))])
    for nome, x in out.items():
        salvar(nome, normalizar(x, 0.85))
    print("efeitos ok:", len(out))


# ------------------------------------------------------------------ músicas
def bateria_kick(buf, t, vol=0.8):
    colocar(buf, deslizar(150, 42, 0.22, "sine", 0.07, vol), t)


def bateria_caixa(buf, t, vol=0.5):
    n = int(SR * 0.14)
    colocar(buf, passa_alta(ruido(0.14), 6) * env(n, 0.001, 0.04) * vol + nota("tri", 190, 0.14, vol * 0.5, 0.04), t)


def bateria_hat(buf, t, vol=0.18):
    n = int(SR * 0.04)
    colocar(buf, passa_alta(ruido(0.04), 3) * env(n, 0.0005, 0.012) * vol, t)


def musica(nome, bpm, acordes, baixo_tipo, arp_vol, kick_todos, melodia, pad_vol=0.1, sino=False, bateria=True, repetir_acordes=1):
    beat = 60.0 / bpm
    compassos = len(acordes) * repetir_acordes
    total = compassos * 4 * beat
    buf = np.zeros(int(SR * total))
    seq = acordes * repetir_acordes
    for c, (raiz, tons) in enumerate(seq):
        t0 = c * 4 * beat
        # pad
        for m in tons:
            colocar(buf, nota("sine", freq(m + 12), 4 * beat, pad_vol, 4 * beat * 0.7, ataque=0.25) + nota("tri", freq(m), 4 * beat, pad_vol * 0.5, 4 * beat * 0.7, ataque=0.25), t0)
        # baixo (colcheias)
        for k in range(8):
            m = raiz - 12 + (12 if k % 4 == 3 else 0)
            colocar(buf, nota(baixo_tipo, freq(m), beat * 0.5, 0.34, beat * 0.3), t0 + k * beat / 2)
        # arpejo (semicolcheias)
        if arp_vol > 0:
            cadeia = [tons[0] + 12, tons[1] + 12, tons[2] + 12, tons[1] + 24]
            for k in range(16):
                m = cadeia[k % 4] + (12 if (k // 4) % 2 and k % 4 == 3 else 0)
                colocar(buf, nota("pulse", freq(m), beat / 4, arp_vol, beat / 8), t0 + k * beat / 4)
        # bateria
        if bateria:
            for b in range(4):
                if kick_todos or b in (0, 2):
                    bateria_kick(buf, t0 + b * beat)
                if b in (1, 3):
                    bateria_caixa(buf, t0 + b * beat)
            for k in range(8):
                bateria_hat(buf, t0 + k * beat / 2 + beat / 4, 0.12)
        if sino:
            for k in range(4):
                m = tons[(c + k) % 3] + 24
                colocar(buf, nota("sine", freq(m), beat * 2, 0.14, beat * 0.9, 0.002), t0 + k * beat)
    # melodia: lista de (compasso, batida, midi, duracao_em_batidas)
    for (c, b, m, d) in melodia:
        colocar(buf, nota("tri", freq(m), d * beat, 0.30, d * beat * 0.7, 0.01) + nota("sine", freq(m + 12), d * beat, 0.08, d * beat * 0.5, 0.01), c * 4 * beat + b * beat)
    buf = normalizar(buf, 0.8)
    f = int(SR * 0.004)
    buf[:f] *= np.linspace(0, 1, f)
    buf[-f:] *= np.linspace(1, 0, f)
    salvar(nome, buf)
    print(nome, round(total, 1), "s")


def musicas():
    # Mina: Lá menor (Am F C G | Am F Dm E)
    ac = [(45, [57, 60, 64]), (41, [53, 57, 60]), (48, [55, 60, 64]), (43, [55, 59, 62]),
          (45, [57, 60, 64]), (41, [53, 57, 60]), (50, [57, 62, 65]), (52, [56, 59, 64])]
    mel = [(4, 0, 81, 1), (4, 1, 84, 1), (4, 2, 88, 1.5), (4, 3.5, 86, 0.5),
           (5, 0, 84, 1), (5, 1, 81, 1), (5, 2, 77, 2),
           (6, 0, 81, 1), (6, 1, 86, 1), (6, 2, 89, 1.5), (6, 3.5, 86, 0.5),
           (7, 0, 83, 1), (7, 1, 80, 1), (7, 2, 83, 1), (7, 3, 88, 1)]
    musica("musica_mina", 104, ac, "tri", 0.10, False, mel)
    # Chefe: Ré menor, mais rápido e pesado
    ac2 = [(38, [50, 53, 57]), (34, [46, 50, 53]), (36, [48, 52, 55]), (45, [57, 61, 64]),
           (38, [50, 53, 57]), (34, [46, 50, 53]), (36, [48, 52, 55]), (45, [57, 61, 64])]
    mel2 = [(0, 0, 74, 0.5), (0, 0.5, 74, 0.5), (0, 1, 77, 1), (0, 2, 81, 1), (0, 3, 79, 1),
            (2, 0, 72, 0.5), (2, 0.5, 72, 0.5), (2, 1, 76, 1), (2, 2, 79, 1), (2, 3, 77, 1),
            (4, 0, 74, 0.5), (4, 0.5, 74, 0.5), (4, 1, 77, 1), (4, 2, 81, 1), (4, 3, 86, 1),
            (6, 0, 85, 0.5), (6, 1, 81, 0.5), (6, 2, 76, 1), (6, 3, 73, 1)]
    musica("musica_chefe", 142, ac2, "saw", 0.13, True, mel2, pad_vol=0.08)
    # Menu: lento, etéreo, sinos
    ac3 = [(45, [57, 60, 64]), (43, [55, 59, 62]), (41, [53, 57, 60]), (40, [52, 55, 59]),
           (45, [57, 60, 64]), (43, [55, 59, 62]), (41, [53, 57, 60]), (52, [56, 59, 64])]
    musica("musica_menu", 78, ac3, "sine", 0.0, False, [], pad_vol=0.16, sino=True, bateria=False)


if __name__ == "__main__":
    sfx()
    musicas()
    print("SONS PRONTOS em", os.path.abspath(RAIZ))
