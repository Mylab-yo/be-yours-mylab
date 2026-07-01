# Section Repigmentants — Catalogue PDF — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produire une section « Repigmentants / Coloristeur » de 3 pages A4 paysage calquée sur le catalogue MY.LAB existant, en PDF, et un catalogue complet V2 avec la section insérée après la page 31.

**Architecture:** HTML/CSS print (1 fichier, 3 `.page`) → rendu via Chrome headless en PDF A4 paysage → fusion avec le V1 via pypdf (insertion après p.31). Source versionnée dans `docs/catalogue/repigmentants/`, livrables PDF dans `Catalogue mylab/`.

**Tech Stack:** HTML5 + CSS print (`@page`), Chrome headless (`--print-to-pdf`), Python 3 + pypdf 6.8.0, curl.

## Global Constraints

- Page : **A4 paysage 297 × 210 mm**, `@page { size: 297mm 210mm; margin: 0 }`, fond blanc.
- Style calqué sur le catalogue : titres **CAPITALES sans-serif espacées** (« LES … »), corps lisible interligne ~1.5, tableaux tarifs avec **dotted leaders**, **couleur d'accent** propre à la section relevée visuellement sur le V1.
- **Aucune donnée fabriquée** : pas d'INCI/actifs inventés ni de % naturel précis inventé. Copy/actifs récupérés des fiches produit live ; à défaut, claims connus uniquement (« sans sulfate · sans paraben · sans silicone », vegan) + bénéfices génériques honnêtes, et claim section « jusqu'à 96 % d'origine naturelle ».
- **6 teintes, platine inclus** : Blond Soleil, Blond Vanille, Chocolat, Cuivre, Marron Noisette, Platine.
- Prix **verbatim** du spec, **HT et à l'unité**.
- **Ne pas toucher** au thème Shopify, product-map, collections, checkout.
- Chrome : `/c/Program Files/Google/Chrome/Application/chrome.exe`.
- Branche : `feat/catalogue-repigmentants`. Source PDF V1 : `Catalogue mylab/MY.LAB_catalogue_2025_V1.pdf` (51 pages).
- Spec de référence : `docs/superpowers/specs/2026-06-30-catalogue-repigmentants-design.md`.

---

### Task 1: Scaffold, images des teintes, relevé visuel V1

**Files:**
- Create: `docs/catalogue/repigmentants/img/` (12 images)
- Create: `docs/catalogue/repigmentants/download_images.py`
- Reference (read only): `assets/bulk-product-images.json`, `Catalogue mylab/MY.LAB_catalogue_2025_V1.pdf`

**Interfaces:**
- Produces: dossier `docs/catalogue/repigmentants/img/` contenant `shampoing-<teinte>.jpg` et `masque-<teinte>.jpg` pour les 6 teintes ; constantes design (couleur d'accent hex, position d'insertion confirmée) notées dans le plan/spec.

- [ ] **Step 1: Créer le dossier et le script de téléchargement**

Create `docs/catalogue/repigmentants/download_images.py`:

```python
import json, re, pathlib, urllib.request

ROOT = pathlib.Path(__file__).parent
IMG = ROOT / "img"; IMG.mkdir(parents=True, exist_ok=True)
SRC = ROOT.parents[1] / "assets" / "bulk-product-images.json"

data = json.loads(SRC.read_text(encoding="utf-8"))
WANT = {  # handle -> nom de fichier local
    "shampoing-coloristeur-blond-soleil": "shampoing-blond-soleil",
    "shampoing-coloristeur-blond-vanille": "shampoing-blond-vanille",
    "shampoing-coloristeur-chocolat": "shampoing-chocolat",
    "shampoing-coloristeur-cuivre": "shampoing-cuivre",
    "shampoing-coloristeur-marron-noisette": "shampoing-marron-noisette",
    "shampoing-dejaunisseur-platine": "shampoing-platine",
    "masque-coloristeur-blond-soleil": "masque-blond-soleil",
    "masque-coloristeur-blond-vanille": "masque-blond-vanille",
    "masque-coloristeur-chocolat": "masque-chocolat",
    "masque-coloristeur-cuivre": "masque-cuivre",
    "masque-coloristeur-marron-noisette": "masque-marron-noisette",
    "masque-dejaunisseur-platine": "masque-platine",
}
ok = 0
for handle, fname in WANT.items():
    url = data.get(handle)
    if not url:
        print("MANQUE", handle); continue
    url = re.sub(r"_200x200(\.\w+)", r"_800x800\1", url)
    dest = IMG / (fname + ".jpg")
    urllib.request.urlretrieve(url, dest)
    sz = dest.stat().st_size
    print(f"{fname}: {sz} octets")
    if sz > 3000: ok += 1
print(f"OK {ok}/12")
```

- [ ] **Step 2: Lancer le téléchargement**

Run: `python "docs/catalogue/repigmentants/download_images.py"`
Expected: `OK 12/12` (12 fichiers > 3000 octets dans `img/`).

- [ ] **Step 3: Relevé visuel du V1 (palette, polices, gabarit, frontière Déjaunisseurs)**

Lire visuellement les pages du V1 pour fixer les constantes design et confirmer l'insertion. Utiliser l'outil Read (PDF, paramètre `pages`) sur :
- pages 29–32 → confirmer que la **page 31 est bien la dernière page Déjaunisseurs** (la 32 démarre une autre gamme). Si la frontière diffère, noter le bon index d'insertion.
- une page divider, une page propriétés, une page tarifs d'une gamme couleur (ex. Protecteurs de couleur p.26–28 ou Déjaunisseurs p.29–31) → relever : couleur d'accent (hex approx.), graisse/casse des titres, style du tableau tarifs, pictos/claims.

- [ ] **Step 4: Consigner les constantes relevées**

Mettre à jour `docs/superpowers/specs/2026-06-30-catalogue-repigmentants-design.md` (section « Points à confirmer ») avec : couleur d'accent retenue (hex), index d'insertion confirmé (après page N), et toute correction de gabarit.

- [ ] **Step 5: Commit**

```bash
git add docs/catalogue/repigmentants/download_images.py docs/catalogue/repigmentants/img docs/superpowers/specs/2026-06-30-catalogue-repigmentants-design.md
git commit -m "feat(catalogue): assets teintes repigmentants + relevé design V1"
```

---

### Task 2: Pipeline de build (render + merge) validé sur page stub

**Files:**
- Create: `docs/catalogue/repigmentants/index.html` (stub : 3 pages vides A4 paysage)
- Create: `docs/catalogue/repigmentants/styles.css` (base `@page` + `.page`)
- Create: `docs/catalogue/repigmentants/build.py`

**Interfaces:**
- Consumes: `index.html`, `styles.css`, images de Task 1.
- Produces:
  - `build.py` exposant le rendu+fusion ; sorties `Catalogue mylab/MY.LAB_repigmentants_section.pdf` (3 pages) et `Catalogue mylab/MY.LAB_catalogue_2025_V2.pdf`.
  - Constante `INSERT_AFTER_PAGE = 31` (index 1-based confirmé en Task 1).

- [ ] **Step 1: CSS de base**

Create `docs/catalogue/repigmentants/styles.css`:

```css
@page { size: 297mm 210mm; margin: 0; }
* { box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
html, body { margin: 0; padding: 0; }
body { font-family: "Helvetica Neue", Arial, sans-serif; color: #1a1a1a; }
.page {
  width: 297mm; height: 210mm; position: relative; overflow: hidden;
  page-break-after: always; background: #fff;
}
.page:last-child { page-break-after: auto; }
```

- [ ] **Step 2: HTML stub (3 pages vides numérotées)**

Create `docs/catalogue/repigmentants/index.html`:

```html
<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<link rel="stylesheet" href="styles.css"></head>
<body>
  <section class="page"><h1 style="padding:40px">PAGE 1 (stub)</h1></section>
  <section class="page"><h1 style="padding:40px">PAGE 2 (stub)</h1></section>
  <section class="page"><h1 style="padding:40px">PAGE 3 (stub)</h1></section>
</body></html>
```

- [ ] **Step 3: Build script (render Chrome + merge pypdf)**

Create `docs/catalogue/repigmentants/build.py`:

```python
import subprocess, sys, pathlib
from pypdf import PdfReader, PdfWriter

ROOT = pathlib.Path(__file__).parent
CAT = ROOT.parents[1] / "Catalogue mylab"
V1 = CAT / "MY.LAB_catalogue_2025_V1.pdf"
SECTION = CAT / "MY.LAB_repigmentants_section.pdf"
V2 = CAT / "MY.LAB_catalogue_2025_V2.pdf"
HTML = ROOT / "index.html"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
INSERT_AFTER_PAGE = 31  # 1-based, confirmé Task 1

def render():
    url = HTML.resolve().as_uri()
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    "--virtual-time-budget=10000",
                    f"--print-to-pdf={SECTION}", url], check=True, timeout=120)
    r = PdfReader(str(SECTION))
    b = r.pages[0].mediabox
    print(f"section: {len(r.pages)} pages, {float(b.width):.1f}x{float(b.height):.1f} pts")
    assert len(r.pages) == 3, "la section doit faire 3 pages"
    assert abs(float(b.width) - 841.9) < 3 and abs(float(b.height) - 595.3) < 3, "A4 paysage attendu"

def merge():
    v1 = PdfReader(str(V1)); sec = PdfReader(str(SECTION)); w = PdfWriter()
    for p in v1.pages[:INSERT_AFTER_PAGE]: w.add_page(p)
    for p in sec.pages: w.add_page(p)
    for p in v1.pages[INSERT_AFTER_PAGE:]: w.add_page(p)
    with open(V2, "wb") as f: w.write(f)
    total = len(v1.pages) + len(sec.pages)
    out = PdfReader(str(V2))
    print(f"V2: {len(out.pages)} pages (attendu {total})")
    assert len(out.pages) == total

if __name__ == "__main__":
    render()
    if "--merge" in sys.argv: merge()
```

- [ ] **Step 4: Vérifier le rendu (stub)**

Run: `python "docs/catalogue/repigmentants/build.py"`
Expected: `section: 3 pages, 841.9x595.3 pts` sans AssertionError.

- [ ] **Step 5: Vérifier la fusion (stub)**

Run: `python "docs/catalogue/repigmentants/build.py" --merge`
Expected: `V2: 54 pages (attendu 54)` sans AssertionError.

- [ ] **Step 6: Commit**

```bash
git add docs/catalogue/repigmentants/index.html docs/catalogue/repigmentants/styles.css docs/catalogue/repigmentants/build.py
git commit -m "feat(catalogue): pipeline build PDF (render Chrome + merge pypdf) validé sur stub"
```

---

### Task 3: Page 1 — Divider « LES REPIGMENTANTS »

**Files:**
- Modify: `docs/catalogue/repigmentants/index.html` (page 1)
- Modify: `docs/catalogue/repigmentants/styles.css`

**Interfaces:**
- Consumes: images `img/shampoing-*.jpg`, couleur d'accent (Task 1).
- Produces: page 1 finalisée (titre, types produits, claim section, visuel teintes).

- [ ] **Step 1: Écrire le HTML de la page 1**

Remplacer la 1re `<section class="page">` par le divider : kicker « COLORISTEUR », titre `<h1>LES REPIGMENTANTS</h1>`, sous-ligne types `SHAMPOING · MASQUE`, claim section « Jusqu'à 96 % d'origine naturelle · Vegan · Fabriqué en France », et une rangée des 6 flacons shampoing (`img/shampoing-<teinte>.jpg`) en bandeau. Utiliser une barre d'accent à la couleur de section.

```html
<section class="page page--divider">
  <div class="divider__inner">
    <p class="kicker">Coloristeur</p>
    <h1 class="gamme-title">Les Repigmentants</h1>
    <p class="product-types">Shampoing &middot; Masque</p>
    <p class="section-claim">Jusqu'à 96 % d'origine naturelle &middot; Vegan &middot; Fabriqué en France</p>
    <div class="shade-strip">
      <img src="img/shampoing-blond-soleil.jpg" alt="Blond Soleil">
      <img src="img/shampoing-blond-vanille.jpg" alt="Blond Vanille">
      <img src="img/shampoing-chocolat.jpg" alt="Chocolat">
      <img src="img/shampoing-cuivre.jpg" alt="Cuivre">
      <img src="img/shampoing-marron-noisette.jpg" alt="Marron Noisette">
      <img src="img/shampoing-platine.jpg" alt="Platine">
    </div>
  </div>
</section>
```

- [ ] **Step 2: Styler la page 1**

Ajouter à `styles.css` : variable `--accent` (hex relevé Task 1), `.page--divider` (barre d'accent, centrage vertical), `.kicker` (CAPS espacées, couleur accent), `.gamme-title` (CAPS, grande taille, letter-spacing), `.product-types`, `.section-claim` (gris), `.shade-strip` (flex, 6 vignettes égales, hauteur ~70mm, object-fit contain).

```css
:root { --accent: #7A3FA0; } /* remplacer par la valeur relevée en Task 1 */
.page--divider { display:flex; align-items:center; justify-content:center; }
.page--divider::before { content:""; position:absolute; inset:0 0 auto 0; height:14mm; background:var(--accent); }
.divider__inner { text-align:center; width:240mm; }
.kicker { text-transform:uppercase; letter-spacing:.35em; font-size:12pt; color:var(--accent); margin:0 0 6mm; }
.gamme-title { text-transform:uppercase; letter-spacing:.12em; font-size:46pt; font-weight:700; margin:0 0 4mm; }
.product-types { text-transform:uppercase; letter-spacing:.2em; font-size:15pt; color:#333; margin:0 0 3mm; }
.section-claim { font-size:11pt; color:#666; margin:0 0 12mm; }
.shade-strip { display:flex; gap:6mm; justify-content:center; }
.shade-strip img { width:36mm; height:70mm; object-fit:contain; }
```

- [ ] **Step 3: Rendre et vérifier visuellement**

Run: `python "docs/catalogue/repigmentants/build.py"`
Then: ouvrir `Catalogue mylab/MY.LAB_repigmentants_section.pdf` (Read PDF, page 1) et vérifier : titre lisible, 6 flacons visibles, barre d'accent, aucun débordement hors page.

- [ ] **Step 4: Commit**

```bash
git add docs/catalogue/repigmentants/index.html docs/catalogue/repigmentants/styles.css
git commit -m "feat(catalogue): page 1 divider Repigmentants"
```

---

### Task 4: Page 2 — Propriétés & actifs + Nuancier

**Files:**
- Modify: `docs/catalogue/repigmentants/index.html` (page 2)
- Modify: `docs/catalogue/repigmentants/styles.css`
- Create: `docs/catalogue/repigmentants/fetch_copy.py` (récup copy live, optionnel)

**Interfaces:**
- Consumes: images `img/*` ; copy live si dispo.
- Produces: page 2 (paragraphe propriétés, actifs/claims, nuancier 6 teintes nommées, badge gamme).

- [ ] **Step 1: Récupérer la copy live (best effort)**

Create `docs/catalogue/repigmentants/fetch_copy.py` qui interroge les fiches produit pour récupérer descriptions/actifs réels :

```python
import json, urllib.request
STORE = "https://mylab-shop-3.myshopify.com"
HANDLES = ["shampoing-coloristeur-chocolat", "masque-coloristeur-chocolat"]
for h in HANDLES:
    try:
        with urllib.request.urlopen(f"{STORE}/products/{h}.js", timeout=15) as r:
            p = json.loads(r.read())
        print("##", h); print((p.get("description") or "")[:1200]); print()
    except Exception as e:
        print("ECHEC", h, e)
```

Run: `python "docs/catalogue/repigmentants/fetch_copy.py"`
Expected: descriptions affichées (sinon, ECHEC → utiliser le fallback honnête de l'étape 2).

- [ ] **Step 2: Écrire le HTML page 2**

Remplacer la 2e `<section class="page">`. Contenu : titre « PROPRIÉTÉS & ACTIFS », paragraphe d'usage (repris/condensé de la copy live si dispo, sinon : « Les soins repigmentants déposent des pigments à chaque lavage pour raviver l'intensité de la couleur, neutraliser les reflets indésirables et prolonger l'éclat entre deux colorations. »), ligne claims « sans sulfate · sans paraben · sans silicone · vegan », puis **nuancier** : 6 vignettes (flacon masque + nom de teinte), badge « GAMME REPIGMENTANTS » en pied.

```html
<section class="page page--props">
  <div class="props__inner">
    <h2 class="section-title">Propriétés &amp; actifs</h2>
    <p class="props__text">Les soins repigmentants déposent des pigments à chaque lavage pour raviver l'intensité de la couleur, neutraliser les reflets indésirables et prolonger l'éclat entre deux colorations. Shampoing et masque s'utilisent en duo pour un résultat progressif et personnalisable selon la fréquence.</p>
    <p class="claims">sans sulfate &middot; sans paraben &middot; sans silicone &middot; vegan</p>
    <h3 class="nuancier-title">Le nuancier — 6 teintes</h3>
    <div class="nuancier">
      <figure><img src="img/masque-blond-soleil.jpg" alt=""><figcaption>Blond Soleil</figcaption></figure>
      <figure><img src="img/masque-blond-vanille.jpg" alt=""><figcaption>Blond Vanille</figcaption></figure>
      <figure><img src="img/masque-chocolat.jpg" alt=""><figcaption>Chocolat</figcaption></figure>
      <figure><img src="img/masque-cuivre.jpg" alt=""><figcaption>Cuivre</figcaption></figure>
      <figure><img src="img/masque-marron-noisette.jpg" alt=""><figcaption>Marron Noisette</figcaption></figure>
      <figure><img src="img/masque-platine.jpg" alt=""><figcaption>Platine</figcaption></figure>
    </div>
    <p class="gamme-badge">Gamme Repigmentants</p>
  </div>
</section>
```

- [ ] **Step 3: Styler la page 2**

Ajouter à `styles.css` : `.page--props` padding 18mm, `.section-title` (CAPS accent), `.props__text` (max 200mm, interligne 1.55), `.claims` (CAPS espacées gris), `.nuancier` (grid 6 colonnes, `figure` centré, `img` 32mm×60mm contain, `figcaption` 10pt), `.gamme-badge` (CAPS, accent, bas de page).

```css
.page--props { padding:18mm; }
.section-title { text-transform:uppercase; letter-spacing:.12em; color:var(--accent); font-size:24pt; margin:0 0 6mm; }
.props__text { max-width:230mm; font-size:12pt; line-height:1.55; color:#333; margin:0 0 5mm; }
.claims { text-transform:uppercase; letter-spacing:.18em; font-size:10pt; color:#888; margin:0 0 10mm; }
.nuancier-title { text-transform:uppercase; letter-spacing:.1em; font-size:13pt; margin:0 0 5mm; }
.nuancier { display:grid; grid-template-columns:repeat(6,1fr); gap:6mm; }
.nuancier figure { margin:0; text-align:center; }
.nuancier img { width:32mm; height:60mm; object-fit:contain; }
.nuancier figcaption { margin-top:3mm; font-size:10pt; letter-spacing:.04em; }
.gamme-badge { position:absolute; bottom:12mm; left:18mm; text-transform:uppercase; letter-spacing:.2em; color:var(--accent); font-size:11pt; }
```

- [ ] **Step 4: Rendre et vérifier**

Run: `python "docs/catalogue/repigmentants/build.py"`
Then: Read PDF page 2 → vérifier : 6 vignettes nommées alignées, paragraphe lisible, badge en pied, pas de débordement.

- [ ] **Step 5: Commit**

```bash
git add docs/catalogue/repigmentants/index.html docs/catalogue/repigmentants/styles.css docs/catalogue/repigmentants/fetch_copy.py
git commit -m "feat(catalogue): page 2 propriétés + nuancier 6 teintes"
```

---

### Task 5: Page 3 — Tarifs Repigmentants

**Files:**
- Modify: `docs/catalogue/repigmentants/index.html` (page 3)
- Modify: `docs/catalogue/repigmentants/styles.css`

**Interfaces:**
- Produces: page 3 (tableaux tarifs shampoing + masque, prix verbatim, dotted leaders, mention HT/unité).

- [ ] **Step 1: Écrire le HTML page 3 (prix verbatim du spec)**

Remplacer la 3e `<section class="page">`. Deux blocs (Shampoing, Masque), chaque format = une ligne par palier avec dotted leader.

```html
<section class="page page--tarifs">
  <div class="tarifs__inner">
    <h2 class="section-title">Tarifs — Repigmentants</h2>
    <div class="tarifs__grid">
      <div class="tarif-block">
        <h3>Shampoing Repigmentant</h3>
        <p class="fmt">200 ml</p>
        <ul class="tiers">
          <li><span>×6</span><b>7,50 €</b></li><li><span>×12</span><b>7,10 €</b></li>
          <li><span>×24</span><b>6,75 €</b></li><li><span>×48</span><b>6,00 €</b></li>
          <li><span>×96</span><b>5,40 €</b></li>
        </ul>
        <p class="fmt">1000 ml</p>
        <ul class="tiers">
          <li><span>×1</span><b>28,90 €</b></li><li><span>×3</span><b>27,45 €</b></li>
          <li><span>×6</span><b>24,50 €</b></li><li><span>×12</span><b>21,60 €</b></li>
        </ul>
      </div>
      <div class="tarif-block">
        <h3>Masque Repigmentant</h3>
        <p class="fmt">200 ml</p>
        <ul class="tiers">
          <li><span>×6</span><b>9,60 €</b></li><li><span>×12</span><b>9,10 €</b></li>
          <li><span>×24</span><b>8,60 €</b></li><li><span>×48</span><b>7,65 €</b></li>
          <li><span>×96</span><b>6,90 €</b></li>
        </ul>
        <p class="fmt">400 ml</p>
        <ul class="tiers">
          <li><span>×4</span><b>16,90 €</b></li><li><span>×8</span><b>15,90 €</b></li>
        </ul>
        <p class="fmt">1000 ml</p>
        <ul class="tiers">
          <li><span>×1</span><b>34,90 €</b></li><li><span>×3</span><b>33,15 €</b></li>
          <li><span>×6</span><b>29,65 €</b></li><li><span>×12</span><b>26,15 €</b></li>
        </ul>
      </div>
    </div>
    <p class="tarifs__note">Prix HT et à l'unité.</p>
  </div>
</section>
```

- [ ] **Step 2: Styler la page 3 (dotted leaders)**

```css
.page--tarifs { padding:18mm; }
.tarifs__grid { display:grid; grid-template-columns:1fr 1fr; gap:18mm; margin-top:8mm; }
.tarif-block h3 { text-transform:uppercase; letter-spacing:.08em; font-size:15pt; border-bottom:2px solid var(--accent); padding-bottom:2mm; }
.tarif-block .fmt { text-transform:uppercase; letter-spacing:.1em; font-size:11pt; color:var(--accent); margin:6mm 0 2mm; }
.tiers { list-style:none; margin:0; padding:0; }
.tiers li { display:flex; align-items:baseline; font-size:12pt; padding:1.5mm 0; }
.tiers li span { white-space:nowrap; }
.tiers li::after { content:""; flex:1; margin:0 2mm; border-bottom:1px dotted #aaa; transform:translateY(-3px); }
.tiers li b { font-weight:600; white-space:nowrap; }
.tarifs__note { margin-top:10mm; font-size:10pt; color:#888; }
```

(Note : la dotted leader est obtenue via `li::after` entre `<span>` et `<b>` ; ré-ordonner par flex si besoin pour placer le pointillé entre quantité et prix.)

- [ ] **Step 3: Rendre et vérifier les prix**

Run: `python "docs/catalogue/repigmentants/build.py"`
Then vérifier que tous les prix du spec sont présents dans le PDF :

```bash
python -c "from pypdf import PdfReader; t=PdfReader(r'Catalogue mylab/MY.LAB_repigmentants_section.pdf').pages[2].extract_text(); import sys; \
[sys.exit('MANQUE '+p) for p in ['7,50','5,40','28,90','21,60','9,60','6,90','16,90','15,90','34,90','26,15'] if p not in t]; print('tous les prix OK')"
```
Expected: `tous les prix OK`.

- [ ] **Step 4: Commit**

```bash
git add docs/catalogue/repigmentants/index.html docs/catalogue/repigmentants/styles.css
git commit -m "feat(catalogue): page 3 tarifs Repigmentants"
```

---

### Task 6: Finalisation — accent/copy appliqués, fusion V2, QA, livraison

**Files:**
- Modify: `docs/catalogue/repigmentants/styles.css` (accent définitif), `index.html` (copy définitive)
- Output: `Catalogue mylab/MY.LAB_repigmentants_section.pdf`, `Catalogue mylab/MY.LAB_catalogue_2025_V2.pdf`

**Interfaces:**
- Consumes: tout le travail Tasks 1–5.
- Produces: les 2 PDF livrables, vérifiés.

- [ ] **Step 1: Appliquer accent + copy définitifs**

Mettre `--accent` à la valeur relevée (Task 1) et intégrer la copy live (Task 4) si récupérée. Vérifier les 4 « points à confirmer » du spec (accent, % naturel/claim, copy, nom couverture).

- [ ] **Step 2: Build complet + fusion**

Run: `python "docs/catalogue/repigmentants/build.py" --merge`
Expected: `section: 3 pages…` puis `V2: 54 pages (attendu 54)`.

- [ ] **Step 3: QA insertion (la section est bien en pages 32–34)**

```bash
python -c "from pypdf import PdfReader; r=PdfReader(r'Catalogue mylab/MY.LAB_catalogue_2025_V2.pdf'); \
print('pages', len(r.pages)); \
print('p32 has REPIGMENT:', 'REPIGMENT' in r.pages[31].extract_text().upper())"
```
Expected: `pages 54` et `p32 has REPIGMENT: True`.

- [ ] **Step 4: Revue visuelle finale**

Read PDF `MY.LAB_catalogue_2025_V2.pdf` pages 31–35 : confirmer enchaînement Déjaunisseurs (31) → Repigmentants (32–34) → gamme suivante (35), cohérence visuelle avec le reste.

- [ ] **Step 5: Commit + livraison**

```bash
git add docs/catalogue/repigmentants "Catalogue mylab/MY.LAB_repigmentants_section.pdf" "Catalogue mylab/MY.LAB_catalogue_2025_V2.pdf"
git commit -m "feat(catalogue): section Repigmentants finalisée + catalogue V2 fusionné"
```

Puis envoyer les 2 PDF à l'utilisateur (SendUserFile) pour validation.

---

## Self-Review

**Spec coverage :** Livrables (section + V2) → Tasks 2/6 ✓. Gabarit 3 pages → Tasks 3/4/5 ✓. Nuancier 6 teintes platine inclus → Tasks 1/4 ✓. Tarifs verbatim → Task 5 ✓. Insertion après p.31 → Tasks 1(confirm)/2/6 ✓. Pipeline Chrome+pypdf → Task 2 ✓. Points à confirmer (accent/%/copy/nom) → Tasks 1/4/6 ✓. Source versionnée → tous ✓. Pas de modif site → respecté (aucune tâche ne touche `assets`/`sections`/`templates` du thème) ✓.

**Placeholders :** la couleur `--accent: #7A3FA0` est une valeur de départ explicitement remplacée en Task 1/6 par le relevé ; la copy a un fallback honnête écrit en toutes lettres. Aucun « TODO » non résolu.

**Cohérence types :** `INSERT_AFTER_PAGE`, noms de fichiers images (`shampoing-<teinte>.jpg` / `masque-<teinte>.jpg`), classes CSS (`--accent`, `.page--divider/props/tarifs`, `.nuancier`, `.tiers`) sont identiques entre tâches. `build.py` (render/merge) cohérent Tasks 2/6.
