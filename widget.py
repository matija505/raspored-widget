"""Skida dnevne izmjene s tsrb.hr i spaja ih s rasporedom 3.G.

Rezultat: docs/danas.json (za KWGT widget) i docs/danas.txt.
Pokretanje: python widget.py            (sada)
            python widget.py 2026-10-27T06:00   (testiranje za neko vrijeme)
"""
import html
import json
import os
import re
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).parent
DANI = ["PON", "UTO", "SRI", "ČET", "PET", "SUB", "NED"]
DANI_PUNO = ["Ponedjeljak", "Utorak", "Srijeda", "Četvrtak", "Petak", "Subota", "Nedjelja"]
MJESECI = {"siječ": 1, "veljač": 2, "ožuj": 3, "travn": 4, "svib": 5, "lipn": 6,
           "srpn": 7, "kolovoz": 8, "rujn": 9, "listopad": 10, "studen": 11, "prosin": 12}
DOC_FALLBACK = ("https://docs.google.com/document/d/e/2PACX-1vR4dC3ga-Qsix1gXvAraOEkHmg_53Hn"
                "ZyYzeIjWUk11EqocGuou0KiVfd9I1oJB2D9DW96TV1mtIgQY/pub?embedded=true")


def zagreb_now():
    """Trenutno vrijeme u Zagrebu (CET/CEST) bez ovisnosti o tzdata."""
    utc = datetime.now(timezone.utc)
    y = utc.year
    last_sun = lambda m: max(date(y, m, d) for d in range(25, 32) if date(y, m, d).weekday() == 6)
    dst_start = datetime.combine(last_sun(3), datetime.min.time(), timezone.utc) + timedelta(hours=1)
    dst_end = datetime.combine(last_sun(10), datetime.min.time(), timezone.utc) + timedelta(hours=1)
    offset = 2 if dst_start <= utc < dst_end else 1
    return (utc + timedelta(hours=offset)).replace(tzinfo=None)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (raspored-widget)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(s).replace("\xa0", " ")).strip()


class DocParser(HTMLParser):
    """Pretvara objavljeni Google Doc u niz blokova: ('text', str) i ('table', [[(tekst, colspan)]])."""

    def __init__(self):
        super().__init__()
        self.blocks, self.table, self.row, self.cell, self.colspan = [], None, None, None, 1
        self.para, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("style", "script"):
            self.skip += 1
        elif tag == "table":
            self.flush()
            self.table = []
        elif tag == "tr" and self.table is not None:
            self.row = []
        elif tag == "td" and self.row is not None:
            self.cell, self.colspan = [], int(a.get("colspan") or 1)
        elif tag in ("p", "br") and self.cell is not None:
            self.cell.append("\n")
        elif tag == "p":
            self.flush()

    def handle_endtag(self, tag):
        if tag in ("style", "script"):
            self.skip -= 1
        elif tag == "td" and self.cell is not None:
            self.row.append((clean(" ".join("".join(self.cell).split("\n"))), self.colspan))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            self.blocks.append(("table", self.table))
            self.table = None
        elif tag == "p" and self.table is None:
            self.flush()

    def handle_data(self, data):
        if self.skip:
            return
        if self.cell is not None:
            self.cell.append(data)
        elif self.table is None:
            self.para.append(data)

    def flush(self):
        t = clean("".join(self.para))
        if t:
            self.blocks.append(("text", t))
        self.para = []


def parse_date(text):
    m = re.search(r"(\d{1,2})\.\s*([a-zčćžšđ]+)\w*\s+(\d{4})", text.lower())
    if not m:
        return None
    for prefix, month in MJESECI.items():
        if m.group(2).startswith(prefix[:5]):
            return date(int(m.group(3)), month, int(m.group(1)))
    return None


def parse_time(s):
    return s.replace(".", ":").strip()


def parse_doc(doc_html, razred):
    """Vraća {datum: {"smjena", "celije": {sat: tekst}, "cijeli_dan", "dodatno": {sat: (predmet, uč)}, "zvono"}}."""
    p = DocParser()
    p.feed(doc_html)
    p.flush()
    rz = razred.replace(".", r"\.?\s*")
    days, cur, mode, pending_date, last_sat = {}, None, None, None, None

    for kind, data in p.blocks:
        if kind == "text":
            up = data.upper()
            if "IZMJENE U RASPOREDU" in up:
                d = parse_date(data)
                mode = "izmjene"
                cur = days.setdefault(d, {"celije": {}, "dodatno": {}}) if d else None
            elif "ZVONA" in up:
                mode, pending_date = "zvono", parse_date(data)
            elif mode == "zvono" and parse_date(data):
                pending_date = parse_date(data)
            elif cur is not None:
                # npr. "8. SAT: 1.G- MAT-UČ. 1-3   3.G-FIZ - UČ. 116", a popis se može nastaviti u idućem retku
                for part in re.split(r"(?=\b\d+\s*[.:]\s*SAT\s*:)", data):
                    sm = re.match(r"\s*(\d+)\s*[.:]\s*SAT\s*:(.*)", part, re.I)
                    if sm:
                        last_sat, part = int(sm.group(1)), sm.group(2)
                    if last_sat is None:
                        continue
                    for im in re.finditer(r"(\d\.?[A-Z](?:\s*/\s*\d\.?[A-Z])*)\s*-\s*([^-]+?)\s*-\s*U[ČC]\.?\s*(\d+(?:\s*-\s*\d+)?)",
                                          part):
                        if re.search(rf"(^|/)\s*{rz}\s*($|/)", im.group(1)):
                            cur["dodatno"][last_sat] = (clean(im.group(2)), im.group(3).replace(" ", ""))
            continue
        last_sat = None

        rows = data
        if mode == "zvono":
            zv = {}
            for row in rows:
                cells = [c for c, _ in row]
                n = re.match(r"\s*(\d+)\.", cells[0] if cells else "")
                t = re.search(r"(\d{1,2}[.:]\d{2})\s*[–-]\s*(\d{1,2}[.:]\d{2})", " ".join(cells[1:2]))
                if n and t:
                    zv[n.group(1)] = [parse_time(t.group(1)), parse_time(t.group(2))]
            if pending_date and zv:
                days.setdefault(pending_date, {"celije": {}, "dodatno": {}})["zvono"] = zv
            mode = None
            continue

        if mode != "izmjene" or cur is None or not rows:
            continue
        header = rows[0]
        cur["smjena"] = "popodne" if "POSLIJE" in header[0][0].upper().replace(" ", "") else "ujutro"
        # stupac -> broj sata, prema zaglavlju
        cols, i = {}, 0
        for text, span in header[1:]:
            m = re.match(r"(\d+)", text)
            for _ in range(span):
                if m:
                    cols[i] = int(m.group(1))
                i += 1
        for row in rows[1:]:
            if not row or not re.fullmatch(rz, row[0][0].upper().replace(" ", "")):
                continue
            i = 0
            for text, span in row[1:]:
                if text and span >= len(cols) - 1:
                    cur["cijeli_dan"] = text
                elif text:
                    for k in range(span):
                        if i + k in cols:
                            cur["celije"][cols[i + k]] = text
                i += span
    return days


def smjena_za(d, cfg):
    monday = d - timedelta(days=d.weekday())
    if monday.isoformat() in cfg["smjena_iznimke"]:
        return cfg["smjena_iznimke"][monday.isoformat()]
    ref = date.fromisoformat(cfg["referentni_ponedjeljak"])
    weeks = (monday - ref).days // 7
    other = "popodne" if cfg["referentna_smjena"] == "ujutro" else "ujutro"
    return cfg["referentna_smjena"] if weeks % 2 == 0 else other


def kratko(name, cfg):
    return cfg["kratko"].get(name, name)


def kratica(short_name, cfg):
    """'Matematika' -> 'MAT', prema kraticama koje škola koristi u izmjenama."""
    for code, name in cfg["kratice_skole"].items():
        if name == short_name:
            return code
    return short_name


def build_day(d, cfg, izmjene):
    iz = izmjene.get(d, {})
    smjena = iz.get("smjena") or smjena_za(d, cfg)
    zvono = iz.get("zvono") or cfg["zvono"][smjena]
    redovni = {int(k): v for k, v in cfg["raspored"][smjena].get(DANI[d.weekday()], {}).items()}
    sati_brojevi = sorted(set(redovni) | set(iz.get("celije", {})) | set(iz.get("dodatno", {})))
    if sati_brojevi:  # popuni rupe od prvog sata smjene do zadnjeg sata tog dana
        prvi = min(int(k) for k in cfg["zvono"][smjena])
        sati_brojevi = list(range(prvi, max(sati_brojevi) + 1))

    sati = []
    for n in sati_brojevi:
        orig = redovni.get(n)
        cel = iz.get("celije", {}).get(n)
        dod = iz.get("dodatno", {}).get(n)
        s = {"sat": n, "od": None, "do": None, "predmet": kratko(orig, cfg) if orig else None,
             "izvorno": kratko(orig, cfg) if orig else None, "izmjena": False, "otpada": False, "ucionica": None}
        s["izvorna_kratica"] = kratica(s["izvorno"], cfg)
        t = zvono.get(str(n)) or cfg["zvono"][smjena].get(str(n))
        if t:
            s["od"], s["do"] = t
        if cel:
            s["izmjena"] = True
            if cel.strip().upper() == "X":
                s["otpada"], s["predmet"] = True, None
            else:
                s["predmet"] = cfg["kratice_skole"].get(cel.strip().upper(), cel.strip())
        if dod:
            subj = cfg["kratice_skole"].get(dod[0].upper(), dod[0])
            s["ucionica"] = dod[1]
            if not cel and (s["predmet"] or "").lower() != subj.lower():
                s["izmjena"], s["predmet"] = True, subj
        sati.append(s)

    odrzani = [s for s in sati if s["predmet"] and s["od"]]
    return {
        "dolazak": odrzani[0]["od"] if odrzani else None,
        "kraj": odrzani[-1]["do"] if odrzani else None,
        "datum": d.isoformat(),
        "dan": DANI_PUNO[d.weekday()],
        "datum_kratko": f"{DANI[d.weekday()]} {d.day}.{d.month}.",
        "smjena": smjena,
        "izmjene_objavljene": d in izmjene and bool(iz.get("smjena") or iz.get("celije") or iz.get("dodatno")),
        "broj_izmjena": sum(s["izmjena"] for s in sati),
        "cijeli_dan": iz.get("cijeli_dan"),
        "skraceni_sati": "zvono" in iz,
        "sati": sati,
    }


def pick_day(now, cfg, izmjene):
    """Danas dok nastava ne završi, inače sljedeći radni dan."""
    d = now.date()
    if d.weekday() < 5:
        day = build_day(d, cfg, izmjene)
        ends = [s["do"] for s in day["sati"] if s["do"] and s["predmet"]]
        if ends and now.strftime("%H:%M") < max(ends, key=lambda t: tuple(map(int, t.split(":")))).zfill(5):
            return d
    d += timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def render(day, bbcode):
    def c(color, t):
        return f"[c={color}]{t}[/c]" if bbcode else t

    head = f"{day['datum_kratko']} · {day['smjena']}"
    if day["broj_izmjena"]:
        head += " · " + c("#FF5252", f"{day['broj_izmjena']} izmj.")
    elif not day["izmjene_objavljene"]:
        head += " · izmjene još nisu objavljene"
    if day["skraceni_sati"]:
        head += " · " + c("#FFB300", "skraćeni sati")
    lines = [f"[b]{head}[/b]" if bbcode else head]
    if day["dolazak"]:
        lines.append(f"dolazak {day['dolazak']} · kraj {day['kraj']}")
    if day["cijeli_dan"]:
        lines.append(c("#FF5252", day["cijeli_dan"]))
    for s in day["sati"]:
        vrijeme = s["od"] or "?"
        # crveno = ono što je po rasporedu trebalo biti, a izmjenom je maknuto
        maknuto = f"- {s['izvorna_kratica']}" if s["izvorno"] else "(novo)"
        if s["otpada"]:
            txt = c("#FF5252", f"--- {maknuto}")
        elif not s["predmet"]:
            txt = c("#8A8A8A", "---")
        elif s["izmjena"]:
            txt = f"{s['predmet']} " + c("#FF5252", maknuto)
        else:
            txt = s["predmet"]
        if s["ucionica"]:
            txt += f" · uč. {s['ucionica']}"
        lines.append(f"{s['sat']}. {vrijeme:>5}  {txt}")
    return "\n".join(lines)


def opis_izmjena(day):
    """Samo promijenjeni sati, za tekst obavijesti. Prazno ako nema izmjena."""
    lines = []
    if day["cijeli_dan"]:
        lines.append(day["cijeli_dan"])
    for s in day["sati"]:
        maknuto = f"- {s['izvorna_kratica']}" if s["izvorno"] else "(novo)"
        if s["otpada"]:
            lines.append(f"{s['sat']}. --- {maknuto}")
        elif s["izmjena"]:
            lines.append(f"{s['sat']}. {s['predmet']} {maknuto}")
    if day["skraceni_sati"]:
        lines.append(f"Skraćeni sati, kraj {day['kraj']}")
    return "\n".join(lines)


def posalji_obavijesti(now, cfg, izmjene):
    """Za svaki dan od danas nadalje: ako su se izmjene za razred pojavile ili promijenile, pošalji ntfy obavijest."""
    topic = os.environ.get("NTFY_TOPIC")
    path = ROOT / "docs" / "obavijesti.json"
    poslano = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    novo = {}
    for d in sorted(izmjene):
        if d < now.date():
            continue
        day = build_day(d, cfg, izmjene)
        opis = opis_izmjena(day)
        novo[d.isoformat()] = opis
        if not opis or poslano.get(d.isoformat()) == opis:
            continue
        kada = "danas" if d == now.date() else "sutra" if d == now.date() + timedelta(days=1) else ""
        naslov = f"Izmjene {kada} {day['datum_kratko']}".replace("  ", " ")
        print(f"obavijest: {naslov}\n{opis}")
        if topic:
            body = json.dumps({"topic": topic, "title": naslov, "message": opis, "tags": ["school"],
                               "click": cfg["izmjene_stranica"]}).encode()
            req = urllib.request.Request("https://ntfy.sh/", data=body, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=30).close()
    if novo != {k: v for k, v in poslano.items() if k in novo} or set(poslano) - set(novo):
        path.write_text(json.dumps(novo, ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = json.loads((ROOT / "raspored.json").read_text(encoding="utf-8"))
    now = datetime.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else zagreb_now()

    try:
        page = fetch(cfg["izmjene_stranica"])
        m = re.search(r'src="(https://docs\.google\.com/document/d/e/[^"]+/pub[^"]*)"', page)
        doc_url = html.unescape(m.group(1)) if m else DOC_FALLBACK
        izmjene = parse_doc(fetch(doc_url), cfg["razred"])
        greska = None
    except Exception as e:  # bez interneta i dalje prikaži redovni raspored
        izmjene, greska = {}, str(e)

    d = pick_day(now, cfg, izmjene)
    nxt = d + timedelta(days=1)
    while nxt.weekday() >= 5:
        nxt += timedelta(days=1)
    day, sljedeci = build_day(d, cfg, izmjene), build_day(nxt, cfg, izmjene)
    for x in (day, sljedeci):
        x["tekst"], x["tekst_kwgt"] = render(x, bbcode=False), render(x, bbcode=True)
    out = {
        **day,
        "sljedeci": sljedeci,
        # oba dana jedan ispod drugog, za veći widget
        "oba_kwgt": day["tekst_kwgt"] + "\n\n" + sljedeci["tekst_kwgt"],
        "greska": greska,
    }

    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    if not greska:
        posalji_obavijesti(now, cfg, izmjene)
    path = docs / "danas.json"
    old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    old.pop("azurirano", None)
    if old == out:  # ništa novo, ne mijenjaj datoteku (nema praznih commitova)
        print("bez promjena")
        return
    out["azurirano"] = now.strftime("%d.%m. %H:%M")
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    tekst = out["tekst"] + "\n\n" + sljedeci["tekst"]
    (docs / "danas.txt").write_text(tekst + f"\n(ažurirano {out['azurirano']})\n", encoding="utf-8")
    print(tekst)


if __name__ == "__main__":
    main()
