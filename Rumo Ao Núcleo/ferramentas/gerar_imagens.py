"""
Gera TODAS as imagens do jogo (sprites, blocos, fundos) em assets/img.
Só é necessário rodar se você quiser regenerar os assets (precisa de numpy + pillow).
Uso:  python gerar_imagens.py
"""
import math
import os
import random

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "img")
os.makedirs(RAIZ, exist_ok=True)
FONTE_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def salvar(img, nome):
    img.save(os.path.join(RAIZ, nome))


def fonte(tam):
    try:
        return ImageFont.truetype(FONTE_BOLD, tam)
    except OSError:
        return ImageFont.load_default()


# ---------------------------------------------------------------- utilidades
def fbm(w, h, seed, oitavas=5, base=3):
    rng = np.random.default_rng(seed)
    acc = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(oitavas):
        gw = base * (2 ** o)
        gh = max(2, int(gw * h / w) + 2)
        pequeno = (rng.random((gh, gw)) * 255).astype(np.uint8)
        img = Image.fromarray(pequeno).resize((w, h), Image.BICUBIC)
        acc += amp * np.asarray(img, np.float32) / 255.0
        tot += amp
        amp *= 0.5
    acc /= tot
    acc = (acc - acc.min()) / (acc.max() - acc.min() + 1e-6)
    return acc


def colorir(n, paradas):
    ts = [p[0] for p in paradas]
    out = np.zeros(n.shape + (3,), np.float32)
    for c in range(3):
        out[..., c] = np.interp(n, ts, [p[1][c] for p in paradas])
    return out


def gradiente_v(w, h, topo, base):
    t = np.linspace(0, 1, h)[:, None, None]
    a = np.array(topo, np.float32)[None, None, :]
    b = np.array(base, np.float32)[None, None, :]
    arr = a * (1 - t) + b * t
    arr = np.repeat(arr, w, axis=1)
    return arr


def para_img(arr):
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def somar_brilho(base_img, camada_rgba, intensidade=1.0, blur=0):
    """Composição aditiva de uma camada RGBA (brilho) sobre uma imagem RGB."""
    if blur:
        camada_rgba = camada_rgba.filter(ImageFilter.GaussianBlur(blur))
    a = np.asarray(camada_rgba, np.float32)
    rgb = a[..., :3] * (a[..., 3:4] / 255.0) * intensidade
    base = np.asarray(base_img.convert("RGB"), np.float32) + rgb
    return para_img(base)


def vinheta(img, forca=0.55):
    w, h = img.size
    y, x = np.mgrid[0:h, 0:w]
    dx = (x - w / 2) / (w / 2)
    dy = (y - h / 2) / (h / 2)
    d = np.clip(np.sqrt(dx ** 2 * 0.9 + dy ** 2 * 0.5), 0, 1.5)
    f = 1 - forca * np.clip(d - 0.35, 0, 1) ** 1.6
    arr = np.asarray(img.convert("RGB"), np.float32) * f[..., None]
    return para_img(arr)


def caminhada(rng, x, y, ang, comp, passo=6, desvio=0.5):
    pts = [(x, y)]
    n = int(comp / passo)
    for _ in range(n):
        ang += rng.uniform(-desvio, desvio)
        x += math.cos(ang) * passo
        y += math.sin(ang) * passo
        pts.append((x, y))
    return pts


# ---------------------------------------------------------------- BLOCOS
BW, BH = 60, 24
S = 6

PAL = {
    "terra":    dict(topo=(150, 108, 68), base=(98, 66, 38), borda=(52, 33, 18), claro=(190, 146, 98)),
    "pedra":    dict(topo=(150, 154, 162), base=(96, 100, 110), borda=(40, 42, 50), claro=(198, 202, 210)),
    "prata":    dict(topo=(118, 128, 146), base=(70, 78, 96), borda=(32, 36, 48), claro=(170, 182, 204)),
    "ouro":     dict(topo=(128, 102, 70), base=(80, 62, 42), borda=(40, 30, 20), claro=(176, 144, 100)),
    "diamante": dict(topo=(84, 128, 168), base=(44, 76, 112), borda=(18, 36, 60), claro=(132, 186, 222)),
    "gema":     dict(topo=(70, 92, 84), base=(38, 54, 50), borda=(14, 24, 22), claro=(110, 150, 136)),
    "granito":  dict(topo=(86, 88, 96), base=(40, 42, 50), borda=(12, 12, 16), claro=(130, 134, 146)),
    "tnt":      dict(topo=(214, 70, 56), base=(150, 30, 28), borda=(60, 10, 10), claro=(255, 140, 110)),
}


def pepita(d, cx, cy, r, claro, medio, escuro, rng, facetas=8):
    pts = []
    for i in range(facetas):
        a = 2 * math.pi * i / facetas
        rr = r * rng.uniform(0.75, 1.1)
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr * 0.85))
    d.polygon(pts, fill=escuro)
    pts2 = [(cx + (x - cx) * 0.86 - r * 0.08, cy + (y - cy) * 0.86 - r * 0.1) for x, y in pts]
    d.polygon(pts2, fill=medio)
    pts3 = [(cx + (x - cx) * 0.5 - r * 0.22, cy + (y - cy) * 0.45 - r * 0.28) for x, y in pts]
    d.polygon(pts3, fill=claro)
    d.ellipse([cx - r * 0.45, cy - r * 0.55, cx - r * 0.15, cy - r * 0.3], fill=(255, 255, 255, 230))


def cristal_prisma(d, cx, cy, r, claro, medio, escuro, rng, alto=1.5):
    """Estilhaço de cristal pontudo (base larga, ponta em cima)."""
    p = [(cx - r, cy + r * 0.7), (cx - r * 0.75, cy - r * 0.2), (cx, cy - r * alto),
         (cx + r * 0.75, cy - r * 0.2), (cx + r, cy + r * 0.7)]
    d.polygon(p, fill=medio, outline=escuro)
    meio = (cx + r * 0.05, cy + r * 0.7)
    d.polygon([p[0], p[1], p[2], (cx - r * 0.1, cy + r * 0.2)], fill=escuro)
    d.polygon([p[2], p[3], p[4], meio, (cx + r * 0.05, cy - r * 0.1)], fill=tuple(min(255, c + 10) for c in medio))
    d.polygon([p[2], (cx + r * 0.05, cy - r * 0.1), (cx - r * 0.1, cy + r * 0.2), p[1]], fill=claro)
    d.line([(cx - r * 0.35, cy - r * 0.2), (cx - r * 0.05, cy - r * alto * 0.7)], fill=(255, 255, 255, 235), width=max(1, S // 2))


def brilho4(d, cx, cy, r, cor=(255, 255, 255, 240)):
    d.polygon([(cx, cy - r), (cx + r * 0.22, cy - r * 0.22), (cx + r, cy), (cx + r * 0.22, cy + r * 0.22),
               (cx, cy + r), (cx - r * 0.22, cy + r * 0.22), (cx - r, cy), (cx - r * 0.22, cy - r * 0.22)], fill=cor)


def bloco_frame(tipo, variante, dano, quadro=0):
    pal = PAL[tipo]
    W, H = BW * S, BH * S
    rng = random.Random(hash((tipo, variante)) % 100000 + 7)
    base = gradiente_v(W, H, pal["topo"], pal["base"])
    if tipo == "tnt":
        base = gradiente_v(W, H, pal["topo"] if quadro == 0 else (255, 120, 70), pal["base"] if quadro == 0 else (210, 60, 40))
    ruido = fbm(W // 3, H // 3, hash((tipo, variante)) % 9999 + 3, 3, 4)
    ruido = np.asarray(Image.fromarray((ruido * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), np.float32) / 255.0
    fino = np.random.default_rng(variante * 31 + 5).normal(0, 7, (H, W, 1))
    amp = 34 if tipo in ("terra", "granito", "pedra") else 22
    arr = base + (ruido[..., None] - 0.5) * amp + fino
    img = para_img(arr).convert("RGBA")
    d = ImageDraw.Draw(img, "RGBA")

    # ---- depósitos / detalhes por tipo
    if tipo == "terra":
        for _ in range(12):
            x, y, r = rng.uniform(6, BW - 6) * S, rng.uniform(4, BH - 4) * S, rng.uniform(1.0, 2.6) * S
            cor = rng.choice([(70, 46, 26, 255), (60, 40, 22, 255), (170, 128, 84, 255)])
            d.ellipse([x - r, y - r * 0.8, x + r, y + r * 0.8], fill=cor)
        for _ in range(3):
            x, y = rng.uniform(8, BW - 8) * S, rng.uniform(5, BH - 5) * S
            d.line([(x, y), (x + rng.uniform(-6, 6) * S, y + rng.uniform(-3, 3) * S)], fill=(52, 34, 18, 200), width=S // 2)
    elif tipo == "pedra":
        for k in range(2):
            y0 = (6 + k * 9 + rng.uniform(-1, 1)) * S
            pts = [(0, y0)] + [(x * S, y0 + rng.uniform(-1.2, 1.2) * S) for x in range(8, BW, 8)] + [(W, y0)]
            d.line(pts, fill=(205, 208, 216, 120), width=S)
            d.line([(x, y + S) for x, y in pts], fill=(30, 32, 40, 120), width=S // 2)
        for _ in range(4):
            cx, cy = rng.uniform(8, BW - 8) * S, rng.uniform(5, BH - 5) * S
            r = rng.uniform(2.5, 4.5) * S
            poly = [(cx + math.cos(a) * r * rng.uniform(0.7, 1.1), cy + math.sin(a) * r * 0.7 * rng.uniform(0.7, 1.1)) for a in np.linspace(0, 6.28, 7)[:-1]]
            d.polygon(poly, fill=(210, 214, 222, 60))
    elif tipo in ("prata", "ouro"):
        if tipo == "prata":
            cl, md, es = (246, 250, 255, 255), (196, 206, 224, 255), (104, 116, 140, 255)
        else:
            cl, md, es = (255, 244, 170, 255), (246, 196, 62, 255), (156, 104, 20, 255)
        n = 5 + variante
        for i in range(n):
            cx = (6 + (BW - 12) * (i + rng.uniform(0.1, 0.9)) / n) * S
            cy = rng.uniform(7, BH - 7) * S
            pepita(d, cx, cy, rng.uniform(2.6, 4.4) * S, cl, md, es, rng)
        for _ in range(2 if tipo == "ouro" else 1):
            brilho4(d, rng.uniform(8, BW - 8) * S, rng.uniform(5, BH - 5) * S, 2.6 * S)
    elif tipo == "diamante":
        n = 4 + variante
        for i in range(n):
            cx = (7 + (BW - 14) * (i + rng.uniform(0.15, 0.85)) / n) * S
            cy = rng.uniform(11, BH - 5) * S
            cristal_prisma(d, cx, cy, rng.uniform(2.6, 3.8) * S, (196, 250, 255, 255), (96, 214, 238, 255), (34, 120, 160, 255), rng, rng.uniform(1.2, 1.9))
        brilho4(d, rng.uniform(10, BW - 10) * S, rng.uniform(5, 10) * S, 3 * S)
    elif tipo == "gema":
        cx, cy, r = BW / 2 * S, BH / 2 * S, 9 * S
        halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(halo).ellipse([cx - r * 1.3, cy - r * 1.3, cx + r * 1.3, cy + r * 1.3], fill=(80, 255, 170, 120))
        halo = halo.filter(ImageFilter.GaussianBlur(S * 3))
        img = Image.alpha_composite(img, halo)
        d = ImageDraw.Draw(img, "RGBA")
        pts = [(cx - r * 1.1, cy), (cx - r * 0.55, cy - r * 0.85), (cx + r * 0.55, cy - r * 0.85), (cx + r * 1.1, cy),
               (cx + r * 0.55, cy + r * 0.85), (cx - r * 0.55, cy + r * 0.85)]
        d.polygon(pts, fill=(30, 190, 110, 255), outline=(8, 80, 48, 255))
        d.polygon([pts[0], pts[1], (cx, cy)], fill=(18, 130, 80, 255))
        d.polygon([pts[1], pts[2], (cx, cy)], fill=(150, 255, 200, 255))
        d.polygon([pts[2], pts[3], (cx, cy)], fill=(70, 230, 150, 255))
        d.polygon([pts[4], pts[5], (cx, cy)], fill=(14, 100, 62, 255))
        d.line([pts[0], pts[3]], fill=(200, 255, 225, 120), width=S // 2)
        brilho4(d, cx - r * 0.35, cy - r * 0.45, 2.4 * S)
    elif tipo == "granito":
        for _ in range(40):
            x, y, r = rng.uniform(0, BW) * S, rng.uniform(0, BH) * S, rng.uniform(0.4, 1.2) * S
            d.ellipse([x - r, y - r, x + r, y + r], fill=rng.choice([(190, 194, 206, 160), (16, 16, 22, 200), (120, 90, 90, 140)]))
        for (px, py) in [(0, 0), (BW - 10, 0), (0, BH - 9), (BW - 10, BH - 9)]:
            d.rectangle([px * S, py * S, (px + 10) * S, (py + 9) * S], fill=(104, 108, 120, 255), outline=(20, 20, 26, 255), width=S // 2)
            d.ellipse([(px + 3.4) * S, (py + 3) * S, (px + 6.6) * S, (py + 6) * S], fill=(190, 194, 206, 255), outline=(30, 30, 36, 255))
        d.line([(10 * S, BH / 2 * S), ((BW - 10) * S, BH / 2 * S)], fill=(20, 20, 26, 200), width=S)
    elif tipo == "tnt":
        d.rectangle([0, 0, W, 4 * S], fill=(30, 30, 34, 255))
        d.rectangle([0, (BH - 4) * S, W, H], fill=(30, 30, 34, 255))
        for k in range(0, BW, 6):
            d.polygon([(k * S, 0), ((k + 3) * S, 0), ((k + 6) * S, 4 * S), ((k + 3) * S, 4 * S)], fill=(250, 200, 40, 255))
            d.polygon([(k * S, (BH - 4) * S), ((k + 3) * S, (BH - 4) * S), ((k + 6) * S, H), ((k + 3) * S, H)], fill=(250, 200, 40, 255))
        f = fonte(int(11.5 * S))
        tw = d.textlength("TNT", font=f)
        d.text(((W - tw) / 2, 3.9 * S), "TNT", font=f, fill=(255, 244, 226, 255), stroke_width=S // 2, stroke_fill=(70, 10, 10, 255))
        d.line([(BW - 8) * S and ((BW - 9) * S, 4 * S), ((BW - 5) * S, 1.5 * S)], fill=(210, 180, 120, 255), width=S)
        if quadro == 1:
            brilho4(d, (BW - 5) * S, 1.5 * S, 3.6 * S, (255, 240, 150, 255))

    # ---- chanfro (bevel) e contorno
    d.line([(S, S), (W - S, S)], fill=pal["claro"] + (200,), width=S)
    d.line([(S, S), (S, H - S)], fill=pal["claro"] + (130,), width=S)
    d.line([(S, H - S), (W - S, H - S)], fill=pal["borda"] + (200,), width=S)
    d.line([(W - S, S), (W - S, H - S)], fill=pal["borda"] + (160,), width=S)

    # ---- rachaduras
    crng = random.Random(hash((tipo, variante, "crack")) % 7777)
    cor_c = (14, 10, 8, 235)
    if dano >= 1:
        pts = caminhada(crng, W * crng.uniform(0.3, 0.55), 0, 1.45, H * 0.9, S * 2.2, 0.55)
        d.line(pts, fill=cor_c, width=int(S * 1.2), joint="curve")
        d.line([(x + S * 0.6, y) for x, y in pts], fill=(255, 255, 255, 40), width=max(1, S // 3))
    if dano >= 2:
        pts = caminhada(crng, W * crng.uniform(0.6, 0.8), H, -1.6, H * 0.95, S * 2.2, 0.6)
        d.line(pts, fill=cor_c, width=int(S * 1.2), joint="curve")
        pts = caminhada(crng, pts[len(pts) // 2][0], pts[len(pts) // 2][1], 0.2, W * 0.25, S * 2.2, 0.5)
        d.line(pts, fill=cor_c, width=int(S * 0.9), joint="curve")
    if dano >= 3:
        pts = caminhada(crng, 0, H * 0.55, 0.15, W * 0.6, S * 2.4, 0.5)
        d.line(pts, fill=cor_c, width=int(S * 1.2), joint="curve")
        pts = caminhada(crng, W, H * 0.4, math.pi - 0.2, W * 0.4, S * 2.4, 0.5)
        d.line(pts, fill=cor_c, width=int(S * 1.2), joint="curve")
        d.polygon([(0, 0), (7 * S, 0), (0, 5 * S)], fill=(0, 0, 0, 0))
        d.polygon([(W, H), (W - 8 * S, H), (W, H - 6 * S)], fill=(0, 0, 0, 0))

    # ---- máscara arredondada
    mascara = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mascara).rounded_rectangle([0, 0, W - 1, H - 1], radius=int(3.2 * S), fill=255)
    if dano >= 3:
        md = ImageDraw.Draw(mascara)
        md.polygon([(0, 0), (7 * S, 0), (0, 5 * S)], fill=0)
        md.polygon([(W, H), (W - 8 * S, H), (W, H - 6 * S)], fill=0)
    r, g, b, a = img.split()
    img = Image.merge("RGBA", (r, g, b, ImageChops.multiply(a, mascara)))
    # contorno escuro
    borda = ImageChops.subtract(mascara, mascara.filter(ImageFilter.MinFilter(S + 1 if (S + 1) % 2 else S + 2)))
    contorno = Image.new("RGBA", (W, H), pal["borda"] + (255,))
    img = Image.composite(contorno, img, borda)
    r, g, b, a = img.split()
    img = Image.merge("RGBA", (r, g, b, ImageChops.multiply(a, mascara)))
    return img.resize((BW, BH), Image.LANCZOS)


def gerar_blocos():
    cfg = {"terra": (4, 2), "pedra": (4, 2), "prata": (4, 2), "ouro": (4, 2), "diamante": (4, 2),
           "gema": (4, 1), "granito": (1, 1), "tnt": (2, 1)}
    for tipo, (quadros, variantes) in cfg.items():
        for v in range(variantes):
            folha = Image.new("RGBA", (BW * quadros, BH), (0, 0, 0, 0))
            for q in range(quadros):
                if tipo == "tnt":
                    f = bloco_frame(tipo, v, 0, quadro=q)
                else:
                    f = bloco_frame(tipo, v, q)
                folha.paste(f, (q * BW, 0))
            nome = f"bloco_{tipo}_{'ab'[v]}.png" if variantes > 1 else f"bloco_{tipo}.png"
            salvar(folha, nome)
    print("blocos ok")


# ---------------------------------------------------------------- BROCA (esfera giratória)
def esfera(fase, quente=False, tam=40, diametro=28, SS=5):
    N = tam * SS
    R = diametro * SS / 2
    y, x = np.mgrid[0:N, 0:N].astype(np.float32)
    nx = (x - N / 2) / R
    ny = (y - N / 2) / R
    r2 = nx ** 2 + ny ** 2
    dentro = r2 <= 1.0
    nz = np.sqrt(np.clip(1 - r2, 0, 1))
    lon = np.arctan2(nx, nz) - fase + 2.6 * ny
    sulcos = 6
    passo = 2 * math.pi / sulcos
    dist = np.abs(((lon + passo / 2) % passo) - passo / 2)
    larg = 0.27
    sulco = np.clip(1 - dist / larg, 0, 1) ** 1.2
    sulco *= (nz > 0.05)
    L = np.array([-0.45, -0.55, 0.7], np.float32)
    L /= np.linalg.norm(L)
    difuso = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1)
    H_ = L + np.array([0, 0, 1], np.float32)
    H_ /= np.linalg.norm(H_)
    espec = np.clip(nx * H_[0] + ny * H_[1] + nz * H_[2], 0, 1) ** 38
    fresnel = (1 - nz) ** 2.2
    if quente:
        cor = np.stack([np.clip(210 * difuso + 60, 0, 255), np.clip(70 * difuso + 20, 0, 255), np.clip(20 * difuso, 0, 255)], -1)
        brilho_s = np.stack([np.full_like(sulco, 255), 210 + 40 * sulco, 120 + 110 * sulco], -1)
    else:
        cor = np.stack([np.clip(118 * difuso + 26, 0, 255), np.clip(130 * difuso + 30, 0, 255), np.clip(150 * difuso + 36, 0, 255)], -1)
        brilho_s = np.stack([np.full_like(sulco, 255), 150 + 70 * sulco, 40 + 60 * sulco], -1)
    escuro = cor * 0.25
    cor = cor * (1 - sulco[..., None]) + escuro * sulco[..., None]
    cor = cor + brilho_s * (sulco[..., None] ** 1.1) * 0.9
    cor = cor + espec[..., None] * np.array([255, 245, 230]) * 0.9 * (1 - 0.6 * sulco[..., None])
    cor = cor + fresnel[..., None] * (np.array([255, 120, 50]) if quente else np.array([70, 130, 220])) * 0.55
    alfa = np.clip((1.0 - np.sqrt(r2)) * R * 0.9, 0, 1)
    alfa = np.where(dentro, alfa, 0)
    rgba = np.dstack([np.clip(cor, 0, 255), alfa * 255]).astype(np.uint8)
    im = Image.fromarray(rgba, "RGBA")
    # contorno
    cont = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    ImageDraw.Draw(cont).ellipse([N / 2 - R, N / 2 - R, N / 2 + R, N / 2 + R], outline=(26, 14, 10, 255) if not quente else (90, 20, 0, 255), width=int(SS * 1.1))
    im = Image.alpha_composite(im, cont)
    return im.resize((tam, tam), Image.LANCZOS)


def gerar_broca():
    for quente in (False, True):
        folha = Image.new("RGBA", (40 * 8, 40), (0, 0, 0, 0))
        for k in range(8):
            folha.paste(esfera(k * (2 * math.pi / 6) / 8, quente), (k * 40, 0))
        salvar(folha, "broca_quente.png" if quente else "broca.png")
    print("broca ok")


# ---------------------------------------------------------------- PLATAFORMAS
def plataforma(w, h=28):
    SS = 5
    W, H = w * SS, h * SS
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img, "RGBA")
    corpo_h = 20 * SS
    grad = gradiente_v(W, corpo_h, (176, 184, 196), (52, 56, 66))
    corpo = para_img(grad).convert("RGBA")
    m = Image.new("L", (W, corpo_h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, W - 1, corpo_h - 1], radius=8 * SS, fill=255)
    img.paste(corpo, (0, 0), m)
    d.rounded_rectangle([0, 0, W - 1, corpo_h - 1], radius=8 * SS, outline=(20, 22, 28, 255), width=2 * SS)
    d.line([(9 * SS, 2.6 * SS), (W - 9 * SS, 2.6 * SS)], fill=(240, 244, 250, 220), width=int(1.6 * SS))
    # faixa de risco central
    fw = int(w * 0.34)
    x0 = (w - fw) / 2
    faixa = Image.new("RGBA", (W, corpo_h), (0, 0, 0, 0))
    fd = ImageDraw.Draw(faixa)
    fd.rectangle([x0 * SS, 5 * SS, (x0 + fw) * SS, 15 * SS], fill=(26, 26, 30, 255))
    k = x0
    while k < x0 + fw + 8:
        fd.polygon([(k * SS, 15 * SS), ((k + 4) * SS, 15 * SS), ((k + 9) * SS, 5 * SS), ((k + 5) * SS, 5 * SS)], fill=(252, 190, 40, 255))
        k += 8
    cortar = Image.new("L", (W, corpo_h), 0)
    ImageDraw.Draw(cortar).rectangle([x0 * SS, 5 * SS, (x0 + fw) * SS, 15 * SS], fill=255)
    img.paste(faixa, (0, 0), ImageChops.multiply(cortar, m))
    d.rectangle([x0 * SS, 5 * SS, (x0 + fw) * SS, 15 * SS], outline=(20, 20, 24, 255), width=SS)
    # luzes âmbar nas pontas
    for cx in (9 * SS, W - 9 * SS):
        d.ellipse([cx - 3.6 * SS, 10 * SS - 3.6 * SS, cx + 3.6 * SS, 10 * SS + 3.6 * SS], fill=(255, 180, 40, 255), outline=(90, 50, 10, 255), width=SS // 2)
        d.ellipse([cx - 1.6 * SS, 10 * SS - 2.2 * SS, cx + 0.2 * SS, 10 * SS - 0.6 * SS], fill=(255, 250, 220, 255))
    # rodas
    for cx in (int(W * 0.2), int(W * 0.8)):
        d.ellipse([cx - 4.6 * SS, 19 * SS - 1 * SS, cx + 4.6 * SS, 19 * SS + 8.2 * SS], fill=(36, 38, 44, 255), outline=(10, 10, 12, 255), width=SS // 2)
        d.ellipse([cx - 1.6 * SS, 19 * SS + 2 * SS, cx + 1.6 * SS, 19 * SS + 5.2 * SS], fill=(150, 156, 168, 255))
    # rebites
    for cx in (int(W * 0.27), int(W * 0.73)):
        d.ellipse([cx - 1.3 * SS, 4 * SS, cx + 1.3 * SS, 6.6 * SS], fill=(140, 146, 158, 255), outline=(30, 30, 36, 255))
    return img.resize((w, h), Image.LANCZOS)


def gerar_plataformas():
    for w in (112, 126, 140, 154, 168, 188, 208, 230):
        salvar(plataforma(w), f"plataforma_{w}.png")
    print("plataformas ok")


# ---------------------------------------------------------------- POWER-UPS / MINÉRIOS / PERIGOS
def selo(cor_anel, desenhar, tam=34):
    SS = 8
    N = tam * SS
    img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse([SS, SS, N - SS, N - SS], fill=(18, 20, 28, 255), outline=cor_anel + (255,), width=int(2.6 * SS))
    d.ellipse([int(3.4 * SS), int(3.4 * SS), N - int(3.4 * SS), N - int(3.4 * SS)], fill=(34, 38, 52, 255))
    d.pieslice([int(3.4 * SS), int(3.4 * SS), N - int(3.4 * SS), N - int(3.4 * SS)], 200, 340, fill=(255, 255, 255, 26))
    desenhar(d, N, SS)
    return img.resize((tam, tam), Image.LANCZOS)


def gerar_powerups():
    def viga(d, N, SS):
        c = N / 2
        for y0 in (c - 7 * SS, c + 4 * SS):
            d.rounded_rectangle([c - 8 * SS, y0, c + 8 * SS, y0 + 3 * SS], radius=SS // 2, fill=(210, 220, 236, 255))
        d.rectangle([c - 1.8 * SS, c - 5 * SS, c + 1.8 * SS, c + 5 * SS], fill=(160, 172, 192, 255))
        d.line([(c - 8 * SS, c - 6.4 * SS), (c + 8 * SS, c - 6.4 * SS)], fill=(255, 255, 255, 180), width=SS // 2)

    def cristal(d, N, SS):
        c = N / 2
        p = [(c, c - 9 * SS), (c + 6 * SS, c - 2 * SS), (c + 4 * SS, c + 8 * SS), (c - 4 * SS, c + 8 * SS), (c - 6 * SS, c - 2 * SS)]
        d.polygon(p, fill=(176, 100, 240, 255), outline=(240, 200, 255, 255))
        d.polygon([p[0], p[1], (c, c)], fill=(222, 170, 255, 255))
        d.polygon([p[0], p[4], (c, c)], fill=(120, 60, 190, 255))
        d.polygon([p[3], p[4], (c, c)], fill=(96, 40, 160, 255))

    def picareta(d, N, SS):
        c = N / 2
        d.line([(c - 6 * SS, c + 9 * SS), (c + 5 * SS, c - 5 * SS)], fill=(150, 98, 52, 255), width=int(2.6 * SS))
        d.arc([c - 11 * SS, c - 12 * SS, c + 11 * SS, c + 6 * SS], 200, 340, fill=(214, 224, 238, 255), width=int(3 * SS))
        d.polygon([(c - 10.4 * SS, c - 3 * SS), (c - 8 * SS, c - 5 * SS), (c - 8.6 * SS, c)], fill=(230, 236, 246, 255))
        d.polygon([(c + 10.4 * SS, c - 3 * SS), (c + 8 * SS, c - 5 * SS), (c + 8.6 * SS, c)], fill=(230, 236, 246, 255))

    def dinamite(d, N, SS):
        c = N / 2
        for dx in (-4, 0, 4):
            d.rounded_rectangle([c + dx * SS - 1.8 * SS, c - 5 * SS, c + dx * SS + 1.8 * SS, c + 8 * SS], radius=SS, fill=(220, 56, 48, 255), outline=(90, 12, 12, 255), width=SS // 2)
        d.line([(c - 6 * SS, c - 1 * SS), (c + 6 * SS, c - 1 * SS)], fill=(250, 220, 90, 255), width=SS)
        d.line([(c, c - 5 * SS), (c + 3 * SS, c - 9 * SS)], fill=(230, 210, 160, 255), width=SS // 2 + 1)
        d.polygon([(c + 3 * SS, c - 11.4 * SS), (c + 3.8 * SS, c - 9.6 * SS), (c + 5.6 * SS, c - 9 * SS), (c + 3.8 * SS, c - 8.4 * SS), (c + 3 * SS, c - 6.6 * SS), (c + 2.2 * SS, c - 8.4 * SS), (c + 0.4 * SS, c - 9 * SS), (c + 2.2 * SS, c - 9.6 * SS)], fill=(255, 230, 110, 255))

    def capacete(d, N, SS):
        c = N / 2
        d.pieslice([c - 9 * SS, c - 9 * SS, c + 9 * SS, c + 9 * SS], 180, 360, fill=(250, 196, 40, 255), outline=(120, 80, 10, 255), width=SS // 2)
        d.rectangle([c - 11 * SS, c, c + 11 * SS, c + 3 * SS], fill=(232, 168, 30, 255), outline=(120, 80, 10, 255), width=SS // 2)
        d.rectangle([c - 1.6 * SS, c - 9 * SS, c + 1.6 * SS, c - 1 * SS], fill=(214, 150, 20, 255))
        d.ellipse([c - 3.6 * SS, c - 7 * SS, c + 3.6 * SS, c - 0.6 * SS], fill=(255, 250, 200, 255), outline=(150, 110, 20, 255), width=SS // 2)

    def lanterna(d, N, SS):
        c = N / 2
        d.rounded_rectangle([c - 5 * SS, c - 7 * SS, c + 5 * SS, c + 8 * SS], radius=2 * SS, fill=(70, 76, 92, 255), outline=(180, 190, 210, 255), width=SS // 2)
        d.ellipse([c - 3.6 * SS, c - 4.8 * SS, c + 3.6 * SS, c + 3.4 * SS], fill=(255, 238, 140, 255))
        d.ellipse([c - 1.6 * SS, c - 3 * SS, c + 0.4 * SS, c - 0.8 * SS], fill=(255, 255, 255, 255))
        d.arc([c - 3 * SS, c - 11 * SS, c + 3 * SS, c - 5 * SS], 180, 360, fill=(180, 190, 210, 255), width=SS)

    itens = {"viga": ((110, 190, 255), viga), "cristal": ((196, 120, 255), cristal), "picareta": ((190, 200, 220), picareta),
             "dinamite": ((255, 96, 80), dinamite), "capacete": ((255, 210, 70), capacete), "lanterna": ((255, 236, 130), lanterna)}
    for nome, (cor, fn) in itens.items():
        salvar(selo(cor, fn), f"pu_{nome}.png")
    print("powerups ok")


def gerar_minerios():
    def pepita_png(nome, claro, medio, escuro, facetas=7, tam=20):
        SS = 10
        N = tam * SS
        img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
        d = ImageDraw.Draw(img, "RGBA")
        rng = random.Random(hash(nome) % 999)
        pepita(d, N / 2, N / 2, 7.4 * SS, claro, medio, escuro, rng, facetas)
        salvar(img.resize((tam, tam), Image.LANCZOS), nome)

    pepita_png("min_cobre.png", (255, 190, 130, 255), (222, 120, 60, 255), (120, 52, 20, 255))
    pepita_png("min_prata.png", (250, 252, 255, 255), (198, 208, 226, 255), (104, 116, 140, 255))
    pepita_png("min_ouro.png", (255, 246, 176, 255), (248, 198, 64, 255), (160, 106, 20, 255))

    SS = 10
    N = 22 * SS
    img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(img, "RGBA")
    cristal_prisma(d, N / 2, N / 2 + 2 * SS, 5.6 * SS, (210, 252, 255, 255), (100, 218, 240, 255), (30, 120, 164, 255), random.Random(1), 1.5)
    salvar(img.resize((22, 22), Image.LANCZOS), "min_diamante.png")

    img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(img, "RGBA")
    cx = cy = N / 2
    r = 7.6 * SS
    pts = [(cx - r, cy), (cx - r * 0.5, cy - r * 0.85), (cx + r * 0.5, cy - r * 0.85), (cx + r, cy), (cx + r * 0.5, cy + r * 0.85), (cx - r * 0.5, cy + r * 0.85)]
    d.polygon(pts, fill=(30, 190, 110, 255), outline=(8, 80, 48, 255), width=SS // 2)
    d.polygon([pts[1], pts[2], (cx, cy)], fill=(150, 255, 200, 255))
    d.polygon([pts[0], pts[1], (cx, cy)], fill=(18, 130, 80, 255))
    d.polygon([pts[4], pts[5], (cx, cy)], fill=(14, 100, 62, 255))
    salvar(img.resize((22, 22), Image.LANCZOS), "min_gema.png")
    print("minerios ok")


def gerar_perigos():
    SS = 8
    # estalactite (gelo/rocha)
    w, h = 22, 52
    img = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img, "RGBA")
    p = [(1 * SS, 0), (w * SS - SS, 0), (w * SS * 0.6, h * SS * 0.55), (w * SS / 2, h * SS - SS), (w * SS * 0.4, h * SS * 0.55)]
    d.polygon(p, fill=(150, 200, 230, 255), outline=(40, 80, 120, 255))
    d.polygon([p[0], p[4], (w * SS / 2, h * SS - SS), (w * SS * 0.46, SS)], fill=(96, 150, 196, 255))
    d.polygon([p[1], p[2], (w * SS / 2, h * SS - SS), (w * SS * 0.54, SS)], fill=(200, 236, 255, 255))
    d.line([(w * SS * 0.38, 2 * SS), (w * SS * 0.45, h * SS * 0.5)], fill=(255, 255, 255, 210), width=SS)
    salvar(img.resize((w, h), Image.LANCZOS), "estalactite.png")
    # estilhaço do núcleo (magma)
    w, h = 20, 50
    img = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img, "RGBA")
    p = [(w * SS / 2, 0), (w * SS - SS, h * SS * 0.3), (w * SS * 0.64, h * SS - SS), (w * SS * 0.36, h * SS - SS), (SS, h * SS * 0.3)]
    d.polygon(p, fill=(255, 90, 60, 255), outline=(255, 220, 160, 255))
    d.polygon([p[0], p[4], (w * SS * 0.5, h * SS * 0.5)], fill=(190, 30, 90, 255))
    d.polygon([p[0], p[1], (w * SS * 0.5, h * SS * 0.5)], fill=(255, 170, 70, 255))
    d.polygon([(w * SS * 0.5, h * SS * 0.18), (w * SS * 0.64, h * SS * 0.42), (w * SS * 0.5, h * SS * 0.78), (w * SS * 0.36, h * SS * 0.42)], fill=(255, 248, 200, 230))
    salvar(img.resize((w, h), Image.LANCZOS), "estilhaco.png")
    print("perigos ok")


# ---------------------------------------------------------------- FUNDOS
W_BG, H_BG = 800, 1000


def brilhos(camada_size, pontos, cor, rng, tamanho=(1, 3)):
    cam = Image.new("RGBA", camada_size, (0, 0, 0, 0))
    d = ImageDraw.Draw(cam)
    for _ in range(pontos):
        x, y = rng.uniform(0, camada_size[0]), rng.uniform(0, camada_size[1])
        r = rng.uniform(*tamanho)
        d.ellipse([x - r, y - r, x + r, y + r], fill=cor + (rng.randint(90, 230),))
    return cam


def poste_madeira(d, x0, y0, x1, y1, rng):
    d.rectangle([x0, y0, x1, y1], fill=(92, 58, 30, 255), outline=(40, 24, 12, 255))
    d.rectangle([x0, y0, x0 + (x1 - x0) * 0.28, y1], fill=(130, 86, 46, 255))
    for _ in range(int((y1 - y0) / 14)):
        yy = rng.uniform(y0, y1)
        d.line([(x0 + 2, yy), (x1 - 2, yy + rng.uniform(-3, 3))], fill=(56, 34, 16, 200), width=1)


def fundo_rocha(nome, seed, paradas, extras):
    n = fbm(W_BG, H_BG, seed, 6, 3)
    estratos = (np.sin(np.linspace(0, 38, H_BG))[:, None] * 0.035)
    n = np.clip(n + estratos, 0, 1)
    rocha = fbm(W_BG, H_BG, seed + 1000, 7, 6)
    gy, gx = np.gradient(rocha * 14.0)
    relevo = np.clip(1 + (-gx * 0.9 - gy * 0.9) * 1.6, 0.5, 1.6)
    arr = colorir(n, paradas) * relevo[..., None]
    arr *= (0.82 + 0.3 * rocha[..., None])
    img = para_img(arr)
    rng = random.Random(seed)
    # rachaduras
    cam = Image.new("RGBA", (W_BG, H_BG), (0, 0, 0, 0))
    d = ImageDraw.Draw(cam)
    for _ in range(14):
        pts = caminhada(rng, rng.uniform(0, W_BG), rng.uniform(0, H_BG), rng.uniform(0, 6.28), rng.uniform(120, 340), 8, 0.55)
        d.line(pts, fill=(0, 0, 0, 120), width=2)
    img = Image.alpha_composite(img.convert("RGBA"), cam).convert("RGB")
    img = extras(img, rng)
    return vinheta(img, 0.62)


def extras_l1(img, rng):
    cam = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(cam)
    for xs in ((10, 38), (W_BG - 38, W_BG - 10)):
        poste_madeira(d, xs[0], 0, xs[1], H_BG, rng)
    for y in (250, 600, 950):
        d.rectangle([0, y, W_BG, y + 22], fill=(84, 52, 26, 255), outline=(36, 22, 10, 255))
        d.rectangle([0, y, W_BG, y + 7], fill=(122, 80, 42, 255))
        for x in range(30, W_BG, 90):
            d.ellipse([x - 3, y + 9, x + 3, y + 15], fill=(150, 150, 160, 255))
    img = Image.alpha_composite(img.convert("RGBA"), cam).convert("RGB")
    luz = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(luz)
    ld.polygon([(340, 0), (460, 0), (640, 520), (160, 520)], fill=(255, 232, 160, 90))
    img = somar_brilho(img, luz, 0.5, blur=36)
    lamp = Image.new("RGBA", img.size, (0, 0, 0, 0))
    lm = ImageDraw.Draw(lamp)
    for x, y in ((120, 255), (680, 605), (120, 955), (400, 255)):
        lm.ellipse([x - 22, y - 22, x + 22, y + 22], fill=(255, 190, 90, 255))
    return somar_brilho(img, lamp, 0.55, blur=24)


def veios(img, rng, cor, qtd=9, largura=2):
    cam = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(cam)
    for _ in range(qtd):
        pts = caminhada(rng, rng.uniform(0, W_BG), rng.uniform(0, H_BG), rng.uniform(0, 6.28), rng.uniform(160, 420), 10, 0.45)
        d.line(pts, fill=cor + (255,), width=largura)
    img = somar_brilho(img, cam, 0.9, blur=1.2)
    return somar_brilho(img, cam, 0.5, blur=6)


def extras_l2(img, rng):
    cam = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(cam)
    for xs in ((0, 46), (W_BG - 46, W_BG)):
        d.rectangle([xs[0], 0, xs[1], H_BG], fill=(34, 38, 50, 255))
        for y in range(0, H_BG, 62):
            d.line([(xs[0], y), (xs[1], y)], fill=(18, 20, 28, 255), width=2)
            d.line([(xs[0] + 6, y + 4), (xs[1] - 6, y + 4)], fill=(80, 90, 112, 120), width=1)
    for y in (260, 640):
        d.arc([30, y - 90, W_BG - 30, y + 90], 180, 360, fill=(26, 30, 42, 255), width=18)
        d.arc([34, y - 86, W_BG - 34, y + 86], 180, 360, fill=(90, 100, 124, 150), width=3)
    img = Image.alpha_composite(img.convert("RGBA"), cam).convert("RGB")
    img = veios(img, rng, (150, 190, 255), 11, 2)
    sp = brilhos(img.size, 60, (210, 230, 255), rng)
    return somar_brilho(img, sp, 0.9, blur=0.8)


def extras_l3(img, rng):
    img = veios(img, rng, (255, 190, 60), 13, 3)
    cam = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(cam)
    for xs in ((0, 36), (W_BG - 36, W_BG)):
        poste_madeira(d, xs[0], 0, xs[1], H_BG, rng)
    img = Image.alpha_composite(img.convert("RGBA"), cam).convert("RGB")
    tochas = Image.new("RGBA", img.size, (0, 0, 0, 0))
    td = ImageDraw.Draw(tochas)
    for y in (180, 520, 860):
        for x in (60, W_BG - 60):
            td.ellipse([x - 26, y - 34, x + 26, y + 34], fill=(255, 150, 40, 255))
    img = somar_brilho(img, tochas, 0.7, blur=34)
    sp = brilhos(img.size, 90, (255, 224, 120), rng)
    return somar_brilho(img, sp, 0.9, blur=0.8)


def cristal_grande(d, cx, cy, r, alto, cor_claro, cor_medio, cor_escuro):
    p = [(cx - r, cy), (cx - r * 0.5, cy - alto), (cx + r * 0.5, cy - alto * 1.12), (cx + r, cy), (cx + r * 0.5, cy + r * 0.6), (cx - r * 0.5, cy + r * 0.6)]
    d.polygon(p, fill=cor_medio, outline=cor_escuro)
    d.polygon([p[0], p[1], (cx, cy - alto * 0.3)], fill=cor_escuro)
    d.polygon([p[1], p[2], (cx, cy - alto * 0.3)], fill=cor_claro)
    d.polygon([p[3], p[2], (cx, cy - alto * 0.3)], fill=tuple(min(255, c + 22) for c in cor_medio))


def extras_l4(img, rng):
    cam = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(cam)
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for lado in (0, 1):
        for _ in range(9):
            y = rng.uniform(40, H_BG - 40)
            x = 0 if lado == 0 else W_BG
            r = rng.uniform(14, 28)
            alto = rng.uniform(60, 150)
            cx = x + (r * 0.4 if lado == 0 else -r * 0.4)
            cristal_grande(d, cx, y, r, alto, (190, 250, 255, 255), (70, 190, 230, 255), (20, 80, 130, 255))
            gd.ellipse([cx - r * 2, y - alto * 0.6, cx + r * 2, y + r], fill=(40, 200, 255, 255))
    for _ in range(11):
        x = rng.uniform(60, W_BG - 60)
        h = rng.uniform(40, 130)
        w = rng.uniform(14, 34)
        d.polygon([(x - w, 0), (x + w, 0), (x, h)], fill=(30, 56, 86, 255), outline=(10, 22, 40, 255))
        d.polygon([(x - w, 0), (x, 0), (x, h)], fill=(52, 92, 132, 255))
    img = Image.alpha_composite(img.convert("RGBA"), cam).convert("RGB")
    img = somar_brilho(img, glow, 0.45, blur=26)
    sp = brilhos(img.size, 120, (180, 245, 255), rng)
    return somar_brilho(img, sp, 0.9, blur=0.8)


def extras_l5(img, rng):
    cam = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(cam)
    for _ in range(18):
        x0, y0 = rng.uniform(0, W_BG), rng.uniform(0, H_BG)
        pts = caminhada(rng, x0, y0, rng.uniform(0, 6.28), rng.uniform(140, 380), 9, 0.55)
        d.line(pts, fill=(255, 96, 40, 255), width=rng.choice([2, 3, 4]))
        d.line(pts, fill=(255, 220, 140, 255), width=1)
    img = somar_brilho(img, cam, 1.0, blur=1.2)
    img = somar_brilho(img, cam, 0.7, blur=9)
    aneis = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ad = ImageDraw.Draw(aneis)
    for r in range(120, 620, 70):
        ad.ellipse([400 - r, 150 - r, 400 + r, 150 + r], outline=(220, 70, 255, 90), width=3)
    img = somar_brilho(img, aneis, 0.65, blur=3)
    nucleo = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(nucleo).ellipse([400 - 160, 150 - 160, 400 + 160, 150 + 160], fill=(255, 70, 160, 255))
    img = somar_brilho(img, nucleo, 0.55, blur=70)
    sp = brilhos(img.size, 100, (255, 170, 120), rng)
    return somar_brilho(img, sp, 0.9, blur=0.8)


def gerar_fundos():
    cfgs = [
        ("fundo_fase1.png", 11, [(0, (34, 22, 14)), (0.45, (82, 54, 32)), (0.8, (124, 86, 52)), (1, (150, 108, 70))], extras_l1),
        ("fundo_fase2.png", 22, [(0, (16, 18, 26)), (0.5, (44, 52, 70)), (0.85, (76, 88, 112)), (1, (100, 114, 140))], extras_l2),
        ("fundo_fase3.png", 33, [(0, (20, 14, 8)), (0.5, (62, 44, 22)), (0.85, (104, 76, 38)), (1, (136, 100, 52))], extras_l3),
        ("fundo_fase4.png", 44, [(0, (6, 14, 28)), (0.5, (16, 44, 74)), (0.85, (30, 80, 118)), (1, (50, 112, 150))], extras_l4),
        ("fundo_fase5.png", 55, [(0, (10, 4, 16)), (0.5, (34, 12, 44)), (0.85, (62, 20, 70)), (1, (92, 30, 84))], extras_l5),
    ]
    for nome, seed, paradas, extra in cfgs:
        salvar(fundo_rocha(nome, seed, paradas, extra), nome)
    print("fundos ok")


def gerar_fundo_menu():
    W, H = 800, 600
    rng = random.Random(77)
    n = fbm(W, H, 99, 6, 3)
    img = para_img(colorir(n, [(0, (8, 6, 22)), (0.5, (26, 16, 52)), (1, (62, 30, 82))]))
    cam = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(cam)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    # cristais ao fundo
    for _ in range(14):
        x = rng.uniform(0, W)
        r = rng.uniform(18, 40)
        alto = rng.uniform(90, 240)
        cor = rng.choice([((190, 250, 255, 255), (70, 190, 230, 255), (20, 80, 130, 255)), ((255, 200, 250, 255), (200, 90, 230, 255), (80, 20, 110, 255))])
        cristal_grande(d, x, H + 10, r, alto, *cor)
        gd.ellipse([x - r * 2, H - alto, x + r * 2, H], fill=cor[1])
    # paredes laterais (silhuetas)
    d.polygon([(0, 0), (150, 0), (90, 140), (130, 300), (60, 460), (0, 600)], fill=(6, 4, 12, 255))
    d.polygon([(W, 0), (W - 170, 0), (W - 100, 160), (W - 150, 320), (W - 70, 470), (W, 600)], fill=(6, 4, 12, 255))
    for _ in range(9):
        x = rng.uniform(150, W - 150)
        h = rng.uniform(40, 120)
        w = rng.uniform(16, 40)
        d.polygon([(x - w, 0), (x + w, 0), (x, h)], fill=(8, 6, 16, 255))
    img = Image.alpha_composite(img.convert("RGBA"), cam).convert("RGB")
    img = somar_brilho(img, glow, 0.5, blur=36)
    lava = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(lava).ellipse([-250, H - 130, W + 250, H + 260], fill=(255, 100, 30, 255))
    img = somar_brilho(img, lava, 0.9, blur=44)
    luz = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(luz).polygon([(330, 0), (470, 0), (640, H), (160, H)], fill=(180, 160, 255, 255))
    img = somar_brilho(img, luz, 0.14, blur=40)
    sp = brilhos((W, H), 140, (200, 190, 255), rng)
    img = somar_brilho(img, sp, 0.9, blur=0.7)
    salvar(vinheta(img, 0.6), "fundo_menu.png")
    print("fundo menu ok")


if __name__ == "__main__":
    gerar_blocos()
    gerar_broca()
    gerar_plataformas()
    gerar_powerups()
    gerar_minerios()
    gerar_perigos()
    gerar_fundos()
    gerar_fundo_menu()
    print("TUDO PRONTO em", os.path.abspath(RAIZ))
