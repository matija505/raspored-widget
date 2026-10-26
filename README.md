# Raspored 3.G – widget

GitHub Actions svakih 15 min (radnim danom) pokreće `widget.py`, koji:

1. otvori https://www.tsrb.hr/b-smjena/ i nađe Google Doc s dnevnim izmjenama,
2. izvuče redak za 3.G (X = sat otpada, kratica = zamjena), dodatne sate s učionicama
   ("8. SAT: 3.G-FIZ - UČ. 116") i skraćenu satnicu ako je objavljena,
3. spoji to s rasporedom iz `raspored.json` (ujutro/popodne se izmjenjuje svaki tjedan),
4. zapiše `docs/danas.json` i `docs/danas.txt`.

Prikazuje se današnji dan dok nastava ne završi, a nakon toga sljedeći radni dan.

## 1. Objava na GitHub (GitHub Desktop)

1. GitHub Desktop → **File → Add local repository** → odaberi ovu mapu → "create a repository" → **Create repository**.
2. **Publish repository**, makni kvačicu **Keep this code private** (widget mora moći čitati datoteku bez prijave).
3. Na github.com u repou: **Actions** → ako pita, *enable workflows* → "Ažuriraj raspored" → **Run workflow** (prvo pokretanje).

Link za widget:

```
https://raw.githubusercontent.com/matija505/raspored-widget/main/docs/danas.json
```

## 2. Widget na Samsungu (KWGT)

1. Instaliraj **KWGT Kustom Widget Maker** iz Play Storea.
2. Dugi pritisak na početni zaslon → Widgeti → KWGT → odaberi veličinu (npr. 4×3).
3. Dodirni prazni widget → **+** → **Text**.
4. Kod teksta dodirni polje i upiši formulu:

   ```
   $wg("https://raw.githubusercontent.com/matija505/raspored-widget/main/docs/danas.json", json, ".tekst_kwgt")$
   ```

   `tekst_kwgt` već ima boje. Crvena kratica je predmet koji je izmjenom maknut:
   `Matematika - OS` znači da umjesto Operacijskih sustava imaš Matematiku, a `--- - OS`
   da sat otpada. Sivi `---` je sat koji ionako nemaš.
5. Za osvježavanje: KWGT → Postavke → *Update interval* (npr. 15 min).
6. Spremi (ikona diskete gore desno).

### Sutrašnji dan

KWGT widgeti se ne mogu scrollati, zato postoje dvije opcije:

**A) Dodir za prebacivanje danas ↔ sutra** (widget ostaje iste veličine)

1. U editoru widgeta: kartica **Globals** → **+** → **Switch**, nazovi ga `sutra`.
2. Formula teksta:

   ```
   $if(gv(sutra)=1, wg("https://raw.githubusercontent.com/matija505/raspored-widget/main/docs/danas.json", json, ".sljedeci.tekst_kwgt"), wg("https://raw.githubusercontent.com/matija505/raspored-widget/main/docs/danas.json", json, ".tekst_kwgt"))$
   ```

3. Tekst → kartica **Touch** → **+** → akcija *Switch global* → `sutra`.

Dodir na widget sad prebacuje između danas i sutra.

**B) Oba dana jedan ispod drugog**: u formuli umjesto `.tekst_kwgt` stavi `.oba_kwgt`
i povećaj widget (npr. 4×5).

Ostala polja u JSON-u, ako želiš složeniji izgled: `.dolazak`, `.kraj`, `.broj_izmjena`,
`.smjena`, `.azurirano`, `.sljedeci.tekst_kwgt`...

## Održavanje

- **Smjena krivo pogođena** (npr. nakon praznika): u `raspored.json` u `smjena_iznimke` dodaj
  `"2026-12-07": "popodne"` (ponedjeljak tog tjedna).
- **Novi raspored**: promijeni `raspored` u `raspored.json`.
- **Nepoznata kratica** u izmjenama prikazuje se kako piše; dodaj je u `kratice_skole`.
- Test lokalno: `python widget.py 2026-10-27T06:00`
