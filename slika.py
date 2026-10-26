"""Crta jedan dan rasporeda kao PNG karticu za KWGT widget (Image element s URL-om).

Stil po uzoru na Racify F1 widget: siva kartica, veliki predmeti velikim slovima,
vremena u svjetlijim zaobljenim poljima, crvena crta na velikom odmoru.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONTS = Path(__file__).parent / "fonts"
S = 2  # crta se u dvostrukoj rezoluciji pa smanji, za glatke rubove
W, H = 1080, 1180
OPACITY = 248

CARD = (44, 44, 48, 255)
PANEL = (62, 62, 67, 255)
CHIP = (68, 68, 74, 255)
WHITE = (246, 246, 248, 255)
MUTED = (172, 172, 180, 255)
DIM = (98, 98, 106, 255)
F1_RED = (225, 16, 16, 255)
RED = (255, 92, 92, 255)
RED_CHIP = (96, 40, 44, 255)
GREEN = (96, 214, 140, 255)
AMBER = (255, 196, 72, 255)

MJESECI = ["SIJ", "VELJ", "OŽU", "TRA", "SVI", "LIP", "SRP", "KOL", "RUJ", "LIS", "STU", "PRO"]


def font(name, size):
    return ImageFont.truetype(str(FONTS / f"{name}.ttf"), round(size * S))


def spaced(d, xy, t, f, fill, tracking=0, anchor="lm", draw=True):
    """Tekst s razmakom među slovima (Pillow to nema); vraća širinu."""
    track = tracking * S
    widths = [d.textlength(ch, font=f) for ch in t]
    total = sum(widths) + track * max(len(t) - 1, 0)
    if draw:
        x, y = xy
        if anchor[0] == "r":
            x -= total
        for ch, w in zip(t, widths):
            d.text((x, y), ch, font=f, fill=fill, anchor="l" + anchor[1])
            x += w + track
    return total


def chip(d, x_right, cy, t, f, fg, bg, h=58):
    """Zaobljeno polje desno poravnato na x_right, iste širine za sva vremena; vraća lijevi rub."""
    h *= S
    w = max(d.textlength(t, font=f), d.textlength("00:00 – 00:00", font=f)) + 2 * 20 * S
    d.rounded_rectangle([x_right - w, cy - h / 2, x_right, cy + h / 2], radius=14 * S, fill=bg)
    d.text((x_right - w / 2, cy), t, font=f, fill=fg, anchor="mm")
    return x_right - w


def struck(d, x, y, t, f, color):
    """Tekst s pravom crtom preko sredine; vraća širinu. y je sredina retka."""
    w = spaced(d, (x, y), t, f, color, tracking=1)
    d.line([x - 3 * S, y, x + w + 3 * S, y], fill=color, width=4 * S)
    return w


def render(day, razred, azurirano, path):
    img = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, W * S - 1, H * S - 1], radius=56 * S, fill=CARD)
    pad = 44 * S
    right = W * S - pad

    # --- zaglavlje: datum | panel s danom | status
    top, head_h = pad, 150 * S
    dan, mj = int(day["datum"][8:]), MJESECI[int(day["datum"][5:7]) - 1]
    date_w = 150 * S
    d.text((pad + date_w / 2, top + 48 * S), str(dan), font=font("TitilliumWeb-Black", 78), fill=WHITE, anchor="mm")
    d.rounded_rectangle([pad + 6 * S, top + 98 * S, pad + date_w - 6 * S, top + 140 * S], radius=21 * S, fill=WHITE)
    mj_f = font("TitilliumWeb-Black", 32)
    w_mj = spaced(d, (0, 0), mj, mj_f, CARD, tracking=3, draw=False)
    spaced(d, (pad + date_w / 2 - w_mj / 2, top + 119 * S), mj, mj_f, CARD, tracking=3)

    status_w = 250 * S
    px0, px1 = pad + date_w + 18 * S, right - status_w - 18 * S
    d.rounded_rectangle([px0, top, px1, top + head_h], radius=24 * S, fill=PANEL)
    spaced(d, (px0 + 28 * S, top + 52 * S), day["dan"].upper(), font("TitilliumWeb-Bold", 58), WHITE, tracking=2)
    sub = f"{razred} · {day['smjena'].upper()}"
    if day["dolazak"]:
        sub += f" · {day['dolazak']} – {day['kraj']}"
    spaced(d, (px0 + 30 * S, top + 112 * S), sub, font("TitilliumWeb-SemiBold", 30), MUTED, tracking=1)

    sf = font("TitilliumWeb-Bold", 36)
    n = day["broj_izmjena"]
    if n:
        label = f"{n} IZMJENE" if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else f"{n} IZMJENA"
        status = [(label, RED)]
    elif day["izmjene_objavljene"]:
        status = [("BEZ IZMJENA", GREEN)]
    else:
        status = [("ČEKA OBJAVU", MUTED)]
    if day["skraceni_sati"]:
        status.append(("SKRAĆENI SATI", AMBER))
    ys = [top + head_h / 2] if len(status) == 1 else [top + 48 * S, top + 104 * S]
    for i, ((t, col), y) in enumerate(zip(status, ys)):
        spaced(d, (right, y), t, sf if i == 0 else font("TitilliumWeb-Bold", 28), col, tracking=2, anchor="rm")

    y = top + head_h + 22 * S
    if day["cijeli_dan"]:
        d.rounded_rectangle([pad, y, right, y + 60 * S], radius=16 * S, fill=RED_CHIP)
        d.text((pad + 24 * S, y + 30 * S), day["cijeli_dan"].upper(), font=font("TitilliumWeb-Bold", 30), fill=RED,
               anchor="lm")
        y += 76 * S

    # --- sati
    footer_h = 44 * S
    sati = day["sati"]
    row_h = min(96 * S, (H * S - footer_h - y) // max(len(sati), 1))
    chip_f, label_f, abbr_f = font("Inter-SemiBold", 32), font("TitilliumWeb-SemiBold", 32), font("TitilliumWeb-Bold", 34)
    for s in sati:
        cy = y + row_h / 2
        changed = s["izmjena"] or s["otpada"]
        free = not s["predmet"] and not s["otpada"]

        # desno: vrijeme u polju, lijevo od njega "8. SAT" (i učionica)
        t = f"{s['od']} – {s['do']}" if s["od"] and s["do"] else (s["od"] or "")
        cx = chip(d, right, cy, t, chip_f, DIM if free else WHITE, RED_CHIP if changed else (PANEL if free else CHIP))
        label = f"{s['sat']}. SAT"
        if s["ucionica"]:
            label = f"UČ. {s['ucionica']} · " + label
        lx = cx - 22 * S - spaced(d, (cx - 22 * S, cy), label, label_f, DIM if free else MUTED, tracking=1,
                                  anchor="rm")

        # lijevo: predmet velikim slovima, smanji ako ne stane
        x = pad + (14 * S if changed else 0)
        if changed:
            d.rounded_rectangle([pad - 4 * S, cy - 24 * S, pad + 4 * S, cy + 24 * S], radius=4 * S, fill=F1_RED)
        if free:
            spaced(d, (x, cy), "—", font("TitilliumWeb-Bold", 46), DIM)
        elif s["otpada"]:
            w = spaced(d, (x, cy), "---", font("TitilliumWeb-Black", 46), RED, tracking=2)
            if s["izvorno"]:
                struck(d, x + w + 20 * S, cy, s["izvorna_kratica"], abbr_f, RED)
        else:
            name = s["predmet"].upper()
            extra = 0
            if s["izmjena"]:
                extra = 20 * S + (spaced(d, (0, 0), s["izvorna_kratica"], abbr_f, RED, tracking=1, draw=False)
                                  if s["izvorno"] else spaced(d, (0, 0), "NOVO", abbr_f, RED, 1, draw=False))
            size = 46
            while size > 30:
                f = font("TitilliumWeb-Black", size)
                if x + spaced(d, (0, 0), name, f, WHITE, 2, draw=False) + extra < lx - 24 * S:
                    break
                size -= 2
            w = spaced(d, (x, cy), name, f, WHITE, tracking=2)
            if s["izmjena"] and s["izvorno"]:
                struck(d, x + w + 20 * S, cy, s["izvorna_kratica"], abbr_f, RED)
            elif s["izmjena"]:
                spaced(d, (x + w + 20 * S, cy), "NOVO", abbr_f, RED, tracking=1)

        y += row_h
        if s["sat"] == 3 and s is not sati[-1]:  # veliki odmor
            d.line([pad, y, right, y], fill=F1_RED, width=3 * S)

    d.text((right, H * S - 26 * S), f"ažurirano {azurirano}", font=font("Inter-Regular", 20), fill=DIM, anchor="rm")

    alpha = img.getchannel("A").point(lambda a: a * OPACITY // 255)
    img.putalpha(alpha)
    # paleta od 256 boja: ~4x manja datoteka, razlika se ne vidi
    img = img.resize((W, H), Image.LANCZOS).quantize(256, method=Image.Quantize.FASTOCTREE)
    img.save(path, optimize=True)
