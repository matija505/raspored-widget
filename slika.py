"""Crta jedan dan rasporeda kao PNG karticu za KWGT widget (Image element s URL-om)."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONTS = Path(__file__).parent / "fonts"
S = 2  # crta se u dvostrukoj rezoluciji pa smanji, za glatke rubove
W, H = 1080, 1000

OPACITY = 238  # prozirnost cijele kartice; boje ispod su neprozirne pa se ne prepisuju krivo
BG = (18, 21, 27, 255)


def over(rgb, a):
    """Boja rgb s prozirnošću a, već pomiješana s pozadinom kartice."""
    return tuple(round(c * a + b * (1 - a)) for c, b in zip(rgb, BG[:3])) + (255,)


BORDER = over((255, 255, 255), 0.09)
DIVIDER = over((255, 255, 255), 0.08)
WHITE = (240, 243, 247, 255)
MUTED = (139, 147, 161, 255)
DIM = (74, 81, 94, 255)
CHIP = (35, 40, 51, 255)
RED = (255, 99, 99, 255)
RED_BG = over((255, 82, 82), 0.11)
RED_CHIP = (92, 33, 38, 255)
GREEN = (91, 214, 138, 255)
GREEN_BG = (23, 48, 31, 255)
AMBER = (255, 194, 71, 255)
AMBER_BG = (58, 46, 20, 255)


def font(weight, size):
    return ImageFont.truetype(str(FONTS / f"Inter-{weight}.ttf"), size * S)


def text_w(d, t, f):
    return d.textlength(t, font=f)


def pill(d, x, y, t, f, fg, bg, align_right=False):
    """Zaobljena oznaka; vraća širinu. y je vrh oznake."""
    pad_x, h = 18 * S, 46 * S
    w = text_w(d, t, f) + 2 * pad_x
    if align_right:
        x -= w
    d.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=bg)
    d.text((x + pad_x, y + h / 2), t, font=f, fill=fg, anchor="lm")
    return w


def struck(d, x, y, t, f, color):
    """Tekst s pravom crtom preko sredine; vraća širinu. y je sredina retka."""
    d.text((x, y), t, font=f, fill=color, anchor="lm")
    w = text_w(d, t, f)
    d.line([x - 2 * S, y, x + w + 2 * S, y], fill=color, width=3 * S)
    return w


def render(day, razred, azurirano, path):
    img = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, W * S - 1, H * S - 1], radius=60 * S, fill=BG, outline=BORDER, width=2 * S)
    pad = 56 * S

    # zaglavlje
    d.text((pad, pad - 6 * S), day["dan"], font=font("Bold", 64), fill=WHITE, anchor="lt")
    d_, m_ = day["datum"][8:].lstrip("0"), day["datum"][5:7].lstrip("0")
    sub = f"{d_}.{m_}. · {day['smjena']}"
    if day["dolazak"]:
        sub += f" · {day['dolazak']}–{day['kraj']}"
    d.text((pad, pad + 78 * S), sub, font=font("Regular", 34), fill=MUTED, anchor="lt")

    chip_f = font("SemiBold", 26)
    x_right, y_chip = W * S - pad, pad + 4 * S
    if day["broj_izmjena"]:
        n = day["broj_izmjena"]
        label = f"{n} izmjene" if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else f"{n} izmjena"
        pill(d, x_right, y_chip, label, chip_f, RED, RED_CHIP, align_right=True)
    elif day["izmjene_objavljene"]:
        pill(d, x_right, y_chip, "bez izmjena", chip_f, GREEN, GREEN_BG, align_right=True)
    else:
        pill(d, x_right, y_chip, "čeka objavu", chip_f, MUTED, CHIP, align_right=True)
    if day["skraceni_sati"]:
        pill(d, x_right, y_chip + 58 * S, "skraćeni sati", chip_f, AMBER, AMBER_BG, align_right=True)

    y = pad + 140 * S
    if day["cijeli_dan"]:
        d.rounded_rectangle([pad, y, W * S - pad, y + 56 * S], radius=16 * S, fill=RED_BG)
        d.text((pad + 20 * S, y + 28 * S), day["cijeli_dan"], font=font("SemiBold", 28), fill=RED, anchor="lm")
        y += 72 * S
    d.line([pad, y, W * S - pad, y], fill=DIVIDER, width=2 * S)
    y += 14 * S

    # sati
    footer_h = 56 * S
    sati = day["sati"]
    row_h = min(84 * S, (H * S - footer_h - y - 10 * S) // max(len(sati), 1))
    num_f, time_f, subj_f, small_f = font("SemiBold", 26), font("Medium", 30), font("Medium", 34), font("Medium", 26)
    for s in sati:
        cy = y + row_h // 2
        changed = s["izmjena"] or s["otpada"]
        free = not s["predmet"] and not s["otpada"]
        if changed:
            d.rounded_rectangle([pad - 16 * S, y + 4 * S, W * S - pad + 16 * S, y + row_h - 4 * S],
                                radius=18 * S, fill=RED_BG)
        # broj sata
        bw = 46 * S
        d.rounded_rectangle([pad, cy - bw // 2, pad + bw, cy + bw // 2], radius=12 * S,
                            fill=RED_CHIP if changed else CHIP)
        d.text((pad + bw / 2, cy), str(s["sat"]), font=num_f, anchor="mm",
               fill=RED if changed else (DIM if free else WHITE))
        # vrijeme, poravnato desno u stupcu
        t = s["od"] or ""
        d.text((pad + bw + 120 * S, cy), t, font=time_f, fill=DIM if free else MUTED, anchor="rm")
        x = pad + bw + 150 * S
        if free:
            d.text((x, cy), "—", font=subj_f, fill=DIM, anchor="lm")
        elif s["otpada"]:
            w = d.textlength("---", font=subj_f)
            d.text((x, cy), "---", font=subj_f, fill=RED, anchor="lm")
            if s["izvorno"]:
                struck(d, x + w + 18 * S, cy, s["izvorna_kratica"], small_f, RED)
        else:
            d.text((x, cy), s["predmet"], font=subj_f, fill=WHITE, anchor="lm")
            w = d.textlength(s["predmet"], font=subj_f)
            if s["izmjena"] and s["izvorno"]:
                struck(d, x + w + 18 * S, cy, s["izvorna_kratica"], small_f, RED)
            elif s["izmjena"]:
                pill(d, x + w + 16 * S, cy - 23 * S, "novo", font("SemiBold", 24), RED, RED_CHIP)
        if s["ucionica"]:
            pill(d, W * S - pad, cy - 23 * S, f"uč. {s['ucionica']}", font("Medium", 24), MUTED, CHIP,
                 align_right=True)
        y += row_h

    d.text((W * S - pad, H * S - 34 * S), f"ažurirano {azurirano}", font=font("Regular", 22),
           fill=DIM, anchor="rm")
    d.text((pad, H * S - 34 * S), razred, font=font("SemiBold", 22), fill=DIM, anchor="lm")

    alpha = img.getchannel("A").point(lambda a: a * OPACITY // 255)
    img.putalpha(alpha)
    # paleta od 256 boja: ~4x manja datoteka, razlika se ne vidi
    img = img.resize((W, H), Image.LANCZOS).quantize(256, method=Image.Quantize.FASTOCTREE)
    img.save(path, optimize=True)
