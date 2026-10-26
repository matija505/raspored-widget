"""Crta jedan dan rasporeda kao kvadratnu PNG karticu za KWGT widget 2x2 (Image element s URL-om)."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONTS = Path(__file__).parent / "fonts"
S = 2  # crta se u dvostrukoj rezoluciji pa smanji, za glatke rubove
W = H = 1000  # kvadrat, kao widget 2x2
OPACITY = 245

CARD = (30, 32, 37, 255)
CHIP = (50, 53, 61, 255)
WHITE = (244, 246, 249, 255)
MUTED = (150, 157, 170, 255)
DIM = (82, 87, 98, 255)
RED = (255, 96, 96, 255)
RED_ROW = (62, 36, 40, 255)
RED_CHIP = (110, 40, 46, 255)
LINE_RED = (220, 52, 52, 255)
GREEN = (98, 216, 142, 255)
GREEN_BG = (30, 62, 44, 255)
AMBER = (255, 196, 72, 255)
AMBER_BG = (70, 56, 24, 255)

DANI = ["PON", "UTO", "SRI", "ČET", "PET", "SUB", "NED"]


def font(weight, size):
    return ImageFont.truetype(str(FONTS / f"Inter-{weight}.ttf"), round(size * S))


def pill(d, x_right, cy, t, f, fg, bg):
    """Zaobljena oznaka desno poravnata na x_right; vraća lijevi rub."""
    h = 52 * S
    w = d.textlength(t, font=f) + 2 * 20 * S
    d.rounded_rectangle([x_right - w, cy - h / 2, x_right, cy + h / 2], radius=h / 2, fill=bg)
    d.text((x_right - w / 2, cy), t, font=f, fill=fg, anchor="mm")
    return x_right - w


def struck(d, x, y, t, f, color):
    """Tekst s pravom crtom preko sredine; vraća širinu. y je sredina retka."""
    d.text((x, y), t, font=f, fill=color, anchor="lm")
    w = d.textlength(t, font=f)
    d.line([x - 3 * S, y, x + w + 3 * S, y], fill=color, width=4 * S)
    return w


def render(day, razred, azurirano, path):
    img = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, W * S - 1, H * S - 1], radius=64 * S, fill=CARD)
    pad = 48 * S
    right = W * S - pad

    # --- zaglavlje: "UTO 27.10." + status desno, ispod smjena i vrijeme
    dd, mm = int(day["datum"][8:]), int(day["datum"][5:7])
    d.text((pad, pad + 34 * S), f"{day['dan']}", font=font("Bold", 66), fill=WHITE, anchor="lm")
    sub = f"{dd}.{mm}. · {day['smjena']}"
    if day["dolazak"]:
        sub += f" · {day['dolazak']}–{day['kraj']}"
    d.text((pad, pad + 104 * S), sub, font=font("Medium", 36), fill=MUTED, anchor="lm")

    pf = font("SemiBold", 30)
    n = day["broj_izmjena"]
    if n:
        label = f"{n} izmjene" if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else f"{n} izmjena"
        pill(d, right, pad + 34 * S, label, pf, RED, RED_CHIP)
    elif day["izmjene_objavljene"]:
        pill(d, right, pad + 34 * S, "bez izmjena", pf, GREEN, GREEN_BG)
    else:
        pill(d, right, pad + 34 * S, "čeka objavu", pf, MUTED, CHIP)
    if day["skraceni_sati"]:
        pill(d, right, pad + 102 * S, "skraćeni", pf, AMBER, AMBER_BG)

    y = pad + 150 * S
    if day["cijeli_dan"]:
        d.rounded_rectangle([pad, y, right, y + 56 * S], radius=16 * S, fill=RED_ROW)
        d.text((pad + 20 * S, y + 28 * S), day["cijeli_dan"], font=font("SemiBold", 30), fill=RED, anchor="lm")
        y += 70 * S

    # --- sati: [broj] vrijeme  PREDMET  (precrtana kratica / učionica)
    sati = day["sati"]
    bottom = H * S - 36 * S
    row_h = min(92 * S, (bottom - y) // max(len(sati), 1))
    size = min(44, row_h / S * 0.5)
    num_f, time_f = font("Bold", size * 0.72), font("Medium", size * 0.86)
    subj_f, small_f = font("SemiBold", size), font("SemiBold", size * 0.74)
    bw = round(size * 1.15 * S)
    x_time = pad + bw + round(size * 2.75 * S)  # desni rub stupca s vremenom
    x_subj = x_time + round(size * 0.55 * S)
    for s in sati:
        cy = y + row_h / 2
        changed = s["izmjena"] or s["otpada"]
        free = not s["predmet"] and not s["otpada"]
        if changed:
            d.rounded_rectangle([pad - 16 * S, y + 5 * S, right + 16 * S, y + row_h - 5 * S], radius=18 * S,
                                fill=RED_ROW)
        d.rounded_rectangle([pad, cy - bw / 2, pad + bw, cy + bw / 2], radius=12 * S,
                            fill=RED_CHIP if changed else CHIP)
        d.text((pad + bw / 2, cy), str(s["sat"]), font=num_f, anchor="mm",
               fill=RED if changed else (DIM if free else WHITE))
        d.text((x_time, cy), s["od"] or "", font=time_f, fill=DIM if free else MUTED, anchor="rm")

        x = x_subj
        if free:
            d.text((x, cy), "—", font=subj_f, fill=DIM, anchor="lm")
        elif s["otpada"]:
            w = d.textlength("---", font=subj_f)
            d.text((x, cy), "---", font=subj_f, fill=RED, anchor="lm")
            if s["izvorno"]:
                struck(d, x + w + 16 * S, cy, s["izvorna_kratica"], small_f, RED)
        else:
            d.text((x, cy), s["predmet"], font=subj_f, fill=WHITE, anchor="lm")
            w = d.textlength(s["predmet"], font=subj_f)
            if s["izmjena"] and s["izvorno"]:
                struck(d, x + w + 16 * S, cy, s["izvorna_kratica"], small_f, RED)
            elif s["izmjena"]:
                d.text((x + w + 16 * S, cy), "novo", font=small_f, fill=RED, anchor="lm")
            elif s["ucionica"]:
                d.text((right, cy), f"uč. {s['ucionica']}", font=small_f, fill=MUTED, anchor="rm")
        y += row_h
        if s["sat"] == 3 and s is not sati[-1]:  # veliki odmor
            d.line([pad + bw + 12 * S, y, right, y], fill=LINE_RED, width=3 * S)

    d.text((right, H * S - 24 * S), azurirano, font=font("Regular", 18), fill=DIM, anchor="rm")

    alpha = img.getchannel("A").point(lambda a: a * OPACITY // 255)
    img.putalpha(alpha)
    # paleta od 256 boja: ~4x manja datoteka, razlika se ne vidi
    img = img.resize((W, H), Image.LANCZOS).quantize(256, method=Image.Quantize.FASTOCTREE)
    img.save(path, optimize=True)
