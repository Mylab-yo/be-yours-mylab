# Stock MRP Odoo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Déployer la gestion de stock MRP centralisée dans Odoo (bulks, packaging, BoMs, réappro auto) avec sync Shopify en stock projeté, conformément au spec `docs/superpowers/specs/2026-05-20-stock-mrp-odoo-design.md`.

**Architecture:** 7 scripts Python idempotents (XML-RPC vers Odoo 18 Community) dans `scripts/odoo/step3x_*.py`, suivis de 3 modifications/créations de workflows n8n (folder Yo) puis d'une session manuelle d'inventaire et de go-live. Tous les scripts sont relançables sans effet de bord.

**Tech Stack:** Python 3.11+ (XML-RPC via `scripts/odoo/_client.py`), Odoo 18 Community, n8n (folder Yo `Z2t5yT17QDhgf2XO`), Gmail (envoi récap), Shopify Admin API (sync stock indirect via Odoo).

---

## Pré-requis & contexte fichiers

**Fichiers existants à connaître:**
- [scripts/odoo/_client.py](scripts/odoo/_client.py) — helper XML-RPC partagé. Variables `URL`, `DB`, `UID`, `API_KEY`. Méthodes : `execute`, `search_read`, `create`, `write`, `search`, `unlink`. Auth via `.env.local` du repo `mylab-configurateur`.
- [scripts/odoo/README.md](scripts/odoo/README.md) — convention `stepNN_` et ordre d'exécution existant (step01-step28 utilisés).
- [assets/ml-product-map.json](assets/ml-product-map.json) — source de vérité formule → handles Shopify (200/500/1000ml ou 200/400/1000ml). Clé JSON = handle 200ml = nom canonique de la formule.
- Workflow n8n existant à patcher : `1AUxe9M9d9cNKz6W` ("Sync Stock Odoo→Shopify", poll 5h, matching SKU, location Shopify `107265032526`).
- Workflow n8n existant lié : `Xj8T5a7aO8drZk5v` (Shopify orders/paid → Odoo SO confirmée).
- Folder n8n cible : Yo `Z2t5yT17QDhgf2XO`, project `HUgJsuxI2uJxkLLk`.

**Fichiers à créer (résumé) :**

| Path | Responsabilité |
|---|---|
| `scripts/odoo/data/bulk_formulas.csv` | Liste des 50 formules → SKU bulk + famille + fournisseur (FP / interne) |
| `scripts/odoo/data/packaging_products.csv` | Liste des ~15 SKUs packaging avec stocks mini/max + fournisseur |
| `scripts/odoo/data/packaging_vendors.csv` | Coordonnées fournisseurs packaging (nom, email, lead time) |
| `scripts/odoo/data/finished_to_components.csv` | Mapping produit fini Odoo → bulk + flacon + bouchon (~150 lignes) |
| `scripts/odoo/step30_create_locations.py` | Créer locations Bulk/Packaging/Fini |
| `scripts/odoo/step31_create_custom_field.py` | Champ `x_mylab_bom_summary` sur `product.template` |
| `scripts/odoo/step32_create_packaging_vendors.py` | Créer fournisseurs packaging |
| `scripts/odoo/step33_create_bulk_products.py` | Créer ~50 produits bulk |
| `scripts/odoo/step34_create_packaging_products.py` | Créer ~15 SKUs packaging |
| `scripts/odoo/step35_create_boms.py` | Créer ~150 BoMs + populer `x_mylab_bom_summary` |
| `scripts/odoo/step36_create_reorder_rules.py` | Créer ~65 règles min/max |
| `scripts/odoo/step37_seed_initial_inventory.py` | Helper saisie inventaire initial (CSV → stock.quant) |

**Convention scripts :**
- `from scripts.odoo._client import execute, search_read, create, write, search`
- Lancer depuis racine repo : `python -m scripts.odoo.step30_create_locations`
- Idempotent : second run = 0 modif. Affiche `[CREATE]` / `[SKIP]` / `[UPDATE]` par ligne.
- Print final : `Done. Created: X, Skipped: Y, Updated: Z`

**Toutes opérations sont en company_id=3 (SARL STARTEC)**, sauf création de produits qui sont multi-company (laisser `company_id=False` pour `product.template`).

---

## Phase 0 : Préparation des CSV d'entrée

### Task 0 : Construire les CSV à partir de `ml-product-map.json` + saisies manuelles

**Files:**
- Create: `scripts/odoo/data/bulk_formulas.csv`
- Create: `scripts/odoo/data/packaging_products.csv`
- Create: `scripts/odoo/data/packaging_vendors.csv`
- Create: `scripts/odoo/data/finished_to_components.csv`
- Create: `scripts/odoo/build_csv_inputs.py`

- [ ] **Step 1: Créer le script qui dérive bulks + mappings depuis ml-product-map.json**

Créer `scripts/odoo/build_csv_inputs.py` :

```python
"""Génère les CSV d'entrée pour les scripts step3x_ à partir de ml-product-map.json.

Sortie :
- data/bulk_formulas.csv   (formule → BULK SKU + famille + fournisseur)
- data/finished_to_components.csv (SKU fini → bulk + flacon + bouchon)

Les CSV vendors et packaging restent à compléter manuellement (TBD spec).
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MAP = json.loads((ROOT.parent.parent / "assets" / "ml-product-map.json").read_text(encoding="utf-8"))

# Famille → catégorie de bulk (cf spec, Section 4 du design)
TYPE_TO_FAMILY = {
    "shampoing": "shampoings",
    "apres-shampoing": "shampoings",
    "creme": "shampoings",
    "masque": "masques",
    "serum": "serums_huiles",
    "huile": "serums_huiles",
    "spray": "shampoings",  # spray texturisant : conditionné en flacon ambré 200ml
    "bain": "serums_huiles",  # bain miraculeux : 50ml
}

# Produits fabriqués en interne (cf spec)
INTERNAL_FORMULAS = {
    "serum",  # tous les sérums
    "huile-barbe",
    "bain-miraculeux",
    "spray-texturisant",
}

# Packaging par (famille, contenance) → (sku_flacon, sku_bouchon)
PACKAGING_MAP = {
    ("shampoings", "200"): ("FLACON-PLA-200", "BOUCHON-24-410"),
    ("shampoings", "500"): ("FLACON-PLA-500", "BOUCHON-24-410"),
    ("shampoings", "1000"): ("FLACON-PLA-1000", "BOUCHON-28-410"),
    ("masques", "200"): ("POT-200", "CAPOT-200"),
    ("masques", "400"): ("POT-400", "CAPOT-400"),
    ("masques", "1000"): ("FLACON-PLA-1000", "BOUCHON-28-410"),
    ("serums_huiles", "50"): ("BOUTEILLE-VERRE-AMBRE-50", "DISPENSER-SERUM"),  # dispenser pour sérum
    # cas spéciaux gérés en dur ci-dessous (huile barbe → pipette, spray texturisant → pulvérisateur)
}

# Cas spéciaux : (formule, contenance) → (flacon, bouchon)
SPECIAL_COMPONENTS = {
    ("huile-barbe", "50"): ("BOUTEILLE-VERRE-AMBRE-50", "PIPETTE"),
    ("spray-texturisant", "200"): ("FLACON-AMBRE-200", "PULVERISATEUR-SPRAY"),
}

# Poids bulk par contenance (kg) — yield 100%
BULK_KG = {"50": 0.05, "200": 0.2, "400": 0.4, "500": 0.5, "1000": 1.0}


def _is_internal(formula_key: str) -> bool:
    return any(formula_key.startswith(f) or formula_key == f for f in INTERNAL_FORMULAS)


def build_bulk_formulas():
    """Sortie: SKU bulk + famille + route (Buy / Manufacture)."""
    rows = []
    for key, data in MAP.items():
        if key.startswith("_"):
            continue
        family = TYPE_TO_FAMILY.get(data.get("type", ""), "shampoings")
        is_internal = _is_internal(key)
        rows.append({
            "bulk_sku": f"BULK-{key}",
            "bulk_name": f"Bulk {key.replace('-', ' ')}",
            "family": family,
            "route": "Manufacture" if is_internal else "Buy",
            "vendor": "" if is_internal else "FP Cosmetics",
            "min_qty_kg": 20,
            "max_qty_kg": 200,
        })
    return rows


def build_finished_to_components():
    """Sortie: SKU fini → bulk + flacon + bouchon."""
    rows = []
    for key, data in MAP.items():
        if key.startswith("_"):
            continue
        family = TYPE_TO_FAMILY.get(data.get("type", ""), "shampoings")
        bulk_sku = f"BULK-{key}"
        for contenance, handle in data.get("sizes", {}).items():
            # Préférer un mapping spécial si défini
            if (key, contenance) in SPECIAL_COMPONENTS:
                flacon, bouchon = SPECIAL_COMPONENTS[(key, contenance)]
            elif (family, contenance) in PACKAGING_MAP:
                flacon, bouchon = PACKAGING_MAP[(family, contenance)]
            else:
                flacon, bouchon = "", ""  # à compléter manuellement
            rows.append({
                "finished_sku": handle,
                "bulk_sku": bulk_sku,
                "bulk_qty_kg": BULK_KG.get(contenance, 0),
                "flacon_sku": flacon,
                "bouchon_sku": bouchon,
                "contenance": contenance,
                "family": family,
            })
    return rows


def write_csv(path: Path, rows: list[dict]):
    if not rows:
        print(f"  (empty) {path.name}")
        return
    path.parent.mkdir(exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {len(rows)} rows → {path}")


if __name__ == "__main__":
    print("Building CSV inputs from ml-product-map.json...")
    write_csv(ROOT / "data" / "bulk_formulas.csv", build_bulk_formulas())
    write_csv(ROOT / "data" / "finished_to_components.csv", build_finished_to_components())
    print("Done. Now manually create:")
    print("  - data/packaging_vendors.csv (template provided in plan Task 0 Step 4)")
    print("  - data/packaging_products.csv (template provided in plan Task 0 Step 5)")
```

- [ ] **Step 2: Lancer le script de build**

```bash
python -m scripts.odoo.build_csv_inputs
```

Expected output :
```
Building CSV inputs from ml-product-map.json...
  wrote ~50 rows → .../data/bulk_formulas.csv
  wrote ~150 rows → .../data/finished_to_components.csv
Done. Now manually create: ...
```

- [ ] **Step 3: Vérifier visuellement les CSV générés**

Ouvrir `scripts/odoo/data/bulk_formulas.csv` et vérifier :
- Toutes les formules sont présentes
- Les 4 produits fab interne (`BULK-serum-*`, `BULK-huile-barbe`, `BULK-bain-miraculeux`, `BULK-spray-texturisant`) ont `route=Manufacture` et `vendor=""`
- Tous les autres ont `vendor=FP Cosmetics`

Ouvrir `scripts/odoo/data/finished_to_components.csv` et vérifier les lignes avec `flacon_sku=""` ou `bouchon_sku=""` (mapping non trouvé → à compléter manuellement). Note le nombre.

- [ ] **Step 4: Créer manuellement `packaging_vendors.csv`**

Créer `scripts/odoo/data/packaging_vendors.csv` avec ce contenu (à compléter par Yoann avec les vraies coordonnées) :

```csv
vendor_code,vendor_name,email,phone,lead_time_days,notes
VERR-AMBR,Verrerie Ambrée FR,TBD@email.fr,,14,Bouteilles verre ambré 50ml
PLAS-FLAC,Plastique Flacons FR,TBD@email.fr,,21,Flacons plastique 200/500/1000ml
POT-MASQUE,Pots Masques FR,TBD@email.fr,,21,Pots + capots masques
PUMP-DISP,Pompes & Dispensers,TBD@email.fr,,14,Pompes 200/500/1000ml + dispensers + pipettes
SPRAY-FR,Pulvérisateurs Spray,TBD@email.fr,,14,Pulvérisateurs spray texturisant
```

**Note**: les `TBD@email.fr` et noms exacts seront remplacés par Yoann (à demander lors de l'exécution du plan).

- [ ] **Step 5: Créer manuellement `packaging_products.csv`**

Créer `scripts/odoo/data/packaging_products.csv` :

```csv
sku,name,vendor_code,uom,min_qty,max_qty,notes
FLACON-PLA-200,Flacon plastique blanc 200ml,PLAS-FLAC,Units,1000,10000,Shampoings/crèmes/après-sham 200ml
FLACON-PLA-500,Flacon plastique blanc 500ml,PLAS-FLAC,Units,100,1000,Shampoings/crèmes/après-sham 500ml
FLACON-PLA-1000,Flacon plastique blanc 1000ml,PLAS-FLAC,Units,50,500,Shampoings/crèmes/après-sham 1000ml
FLACON-AMBRE-200,Flacon ambré 200ml,PLAS-FLAC,Units,100,1000,Spray texturisant (TBD)
POT-200,Pot 200ml,POT-MASQUE,Units,200,2000,Masques 200ml (jumelé CAPOT-200)
CAPOT-200,Capot 200ml,POT-MASQUE,Units,200,2000,Masques 200ml (jumelé POT-200)
POT-400,Pot 400ml,POT-MASQUE,Units,100,1000,Masques 400ml (TBD si distinct)
CAPOT-400,Capot 400ml,POT-MASQUE,Units,100,1000,Masques 400ml (TBD si distinct)
BOUTEILLE-VERRE-AMBRE-50,Bouteille verre ambré 50ml,VERR-AMBR,Units,200,2000,Sérums + huile barbe + bain miraculeux
BOUCHON-24-410,Bouchon 24/410,PUMP-DISP,Units,500,5000,Flacons 200/500ml
BOUCHON-28-410,Bouchon 28/410,PUMP-DISP,Units,50,500,Flacons 1000ml
POMPE-200-500,Pompe 200/500ml,PUMP-DISP,Units,200,2000,Option crèmes/masques (mix 90/10)
POMPE-1000,Pompe 1000ml,PUMP-DISP,Units,100,1000,Option 1000ml — aussi vendue seule (produit fini)
DISPENSER-SERUM,Dispenser pompe sérum,PUMP-DISP,Units,100,1000,Sérum 50ml uniquement
PIPETTE,Pipette compte-gouttes,PUMP-DISP,Units,100,1000,Huile barbe 50ml
PULVERISATEUR-SPRAY,Pulvérisateur spray,SPRAY-FR,Units,100,1000,Spray texturisant (TBD)
```

**Note**: les valeurs marquées `TBD` (lignes FLACON-AMBRE-200, POT-400, CAPOT-400, POMPE-1000, PULVERISATEUR-SPRAY) sont à confirmer avec Yoann avant exécution des scripts.

- [ ] **Step 6: Commit**

```bash
git add scripts/odoo/build_csv_inputs.py scripts/odoo/data/
git commit -m "feat(odoo): build CSV inputs for stock MRP setup"
```

---

## Phase A : Modélisation Odoo (Tasks 1-7)

### Task 1 : Locations Bulk / Packaging / Fini

**Files:**
- Create: `scripts/odoo/step30_create_locations.py`

- [ ] **Step 1: Découvrir l'ID du warehouse principal**

Créer un script de probe rapide :

```bash
python -c "from scripts.odoo._client import search_read; print(search_read('stock.warehouse', [], ['id','name','code','view_location_id']))"
```

Noter l'ID du warehouse principal (typiquement le seul, code="WH"). On l'appellera `WAREHOUSE_ID` dans la suite. La `view_location_id` est le parent où créer les sous-locations.

- [ ] **Step 2: Écrire le script step30**

Créer `scripts/odoo/step30_create_locations.py` :

```python
"""Création des locations stock : WH/Stock/Bulk, WH/Stock/Packaging, WH/Stock/Fini.

Idempotent : skip si une location avec le même nom existe déjà sous le même parent.
"""
from scripts.odoo._client import execute, search_read, create

LOCATIONS = [
    {"name": "Bulk", "usage": "internal"},
    {"name": "Packaging", "usage": "internal"},
    {"name": "Fini", "usage": "internal"},
]


def get_main_stock_location() -> int:
    """Récupère la location 'WH/Stock' (parent des sous-locations)."""
    rows = search_read("stock.location", [
        ("usage", "=", "internal"),
        ("name", "=", "Stock"),
    ], ["id", "name", "complete_name"])
    if not rows:
        raise RuntimeError("Location 'Stock' introuvable — vérifier que le warehouse est configuré")
    # Filtrer celle qui est sous un warehouse (i.e. dont le complete_name commence par 'WH/Stock')
    stock_locs = [r for r in rows if r["complete_name"].startswith("WH/")]
    if not stock_locs:
        raise RuntimeError(f"Location WH/Stock introuvable parmi: {rows}")
    return stock_locs[0]["id"]


def main():
    parent_id = get_main_stock_location()
    print(f"Parent location WH/Stock : id={parent_id}")
    created, skipped = 0, 0
    for loc in LOCATIONS:
        existing = search_read("stock.location", [
            ("location_id", "=", parent_id),
            ("name", "=", loc["name"]),
        ], ["id", "complete_name"])
        if existing:
            print(f"  [SKIP] {existing[0]['complete_name']} (id={existing[0]['id']})")
            skipped += 1
            continue
        new_id = create("stock.location", {
            "name": loc["name"],
            "usage": loc["usage"],
            "location_id": parent_id,
        })
        print(f"  [CREATE] WH/Stock/{loc['name']} (id={new_id})")
        created += 1
    print(f"\nDone. Created: {created}, Skipped: {skipped}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Lancer le script**

```bash
python -m scripts.odoo.step30_create_locations
```

Expected output (premier run) :
```
Parent location WH/Stock : id=<N>
  [CREATE] WH/Stock/Bulk (id=<X>)
  [CREATE] WH/Stock/Packaging (id=<Y>)
  [CREATE] WH/Stock/Fini (id=<Z>)

Done. Created: 3, Skipped: 0
```

- [ ] **Step 4: Tester l'idempotence — relancer**

```bash
python -m scripts.odoo.step30_create_locations
```

Expected :
```
  [SKIP] WH/Stock/Bulk (id=<X>)
  [SKIP] WH/Stock/Packaging (id=<Y>)
  [SKIP] WH/Stock/Fini (id=<Z>)

Done. Created: 0, Skipped: 3
```

- [ ] **Step 5: Vérification visuelle dans Odoo**

Ouvrir https://odoo.startec-paris.com → Inventaire → Configuration → Emplacements. Vérifier que `WH/Stock/Bulk`, `WH/Stock/Packaging`, `WH/Stock/Fini` sont présents.

- [ ] **Step 6: Commit**

```bash
git add scripts/odoo/step30_create_locations.py
git commit -m "feat(odoo): create stock locations Bulk/Packaging/Fini (step30)"
```

---

### Task 2 : Custom field `x_mylab_bom_summary`

**Files:**
- Create: `scripts/odoo/step31_create_custom_field.py`

Ce champ stockera (en JSON sur le produit fini) la BoM résumée utilisée par le workflow n8n de sync stock Shopify. Format : `{"bulk_sku": "...", "bulk_kg": 0.2, "flacon_sku": "...", "bouchon_sku": "...", "family": "shampoings", "contenance": "200"}`.

- [ ] **Step 1: Écrire le script step31**

Créer `scripts/odoo/step31_create_custom_field.py` :

```python
"""Création du champ custom x_mylab_bom_summary sur product.template.

Champ Text (stocke un JSON). Utilisé par le workflow n8n de sync stock Shopify
pour calculer le stock projeté sans avoir à re-parser la BoM Odoo à chaque sync.

Idempotent : skip si le champ existe déjà.
"""
from scripts.odoo._client import execute, search_read, create

FIELD_NAME = "x_mylab_bom_summary"
FIELD_MODEL = "product.template"
FIELD_LABEL = "MyLab BoM Summary (JSON)"


def main():
    model_rows = search_read("ir.model", [("model", "=", FIELD_MODEL)], ["id"])
    if not model_rows:
        raise RuntimeError(f"Model {FIELD_MODEL} introuvable")
    model_id = model_rows[0]["id"]

    existing = search_read("ir.model.fields", [
        ("model", "=", FIELD_MODEL),
        ("name", "=", FIELD_NAME),
    ], ["id", "name", "ttype"])
    if existing:
        print(f"  [SKIP] {FIELD_NAME} existe déjà (id={existing[0]['id']}, type={existing[0]['ttype']})")
        return

    new_id = create("ir.model.fields", {
        "name": FIELD_NAME,
        "field_description": FIELD_LABEL,
        "model_id": model_id,
        "model": FIELD_MODEL,
        "ttype": "text",
        "state": "manual",  # champ custom (pas issu d'un module)
        "store": True,
        "copied": False,
    })
    print(f"  [CREATE] {FIELD_NAME} sur {FIELD_MODEL} (id={new_id})")
    print("\nDone.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Lancer le script**

```bash
python -m scripts.odoo.step31_create_custom_field
```

Expected (premier run) :
```
  [CREATE] x_mylab_bom_summary sur product.template (id=<N>)
Done.
```

- [ ] **Step 3: Tester l'idempotence**

```bash
python -m scripts.odoo.step31_create_custom_field
```

Expected :
```
  [SKIP] x_mylab_bom_summary existe déjà (id=<N>, type=text)
```

- [ ] **Step 4: Vérification XML-RPC**

```bash
python -c "from scripts.odoo._client import search_read; print(search_read('ir.model.fields', [('name','=','x_mylab_bom_summary')], ['id','name','model','ttype','state']))"
```

Attendu : `[{'id': N, 'name': 'x_mylab_bom_summary', 'model': 'product.template', 'ttype': 'text', 'state': 'manual'}]`

- [ ] **Step 5: Commit**

```bash
git add scripts/odoo/step31_create_custom_field.py
git commit -m "feat(odoo): add x_mylab_bom_summary custom field on product.template (step31)"
```

---

### Task 3 : Fournisseurs packaging

**Files:**
- Create: `scripts/odoo/step32_create_packaging_vendors.py`

- [ ] **Step 1: Demander à Yoann de finaliser `packaging_vendors.csv`**

Avant de lancer ce script, demander à Yoann les coordonnées réelles (nom, email, lead time) de chacun de ses fournisseurs packaging. Mettre à jour `scripts/odoo/data/packaging_vendors.csv`.

- [ ] **Step 2: Écrire le script step32**

Créer `scripts/odoo/step32_create_packaging_vendors.py` :

```python
"""Création des fournisseurs packaging dans res.partner.

Lit data/packaging_vendors.csv. Idempotent : match par 'ref' (vendor_code stocké en réf interne).
"""
import csv
from pathlib import Path
from scripts.odoo._client import execute, search_read, create, write

CSV_PATH = Path(__file__).parent / "data" / "packaging_vendors.csv"


def main():
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))
    created, skipped, updated = 0, 0, 0
    for r in rows:
        code = r["vendor_code"].strip()
        existing = search_read("res.partner", [("ref", "=", code)], ["id", "name", "email"])
        values = {
            "name": r["vendor_name"].strip(),
            "email": r["email"].strip(),
            "phone": r.get("phone", "").strip(),
            "ref": code,
            "is_company": True,
            "supplier_rank": 1,
            "comment": r.get("notes", "").strip(),
        }
        if existing:
            partner_id = existing[0]["id"]
            # Mettre à jour si nom ou email a changé
            if existing[0]["name"] != values["name"] or existing[0]["email"] != values["email"]:
                write("res.partner", [partner_id], values)
                print(f"  [UPDATE] {code} → {values['name']} (id={partner_id})")
                updated += 1
            else:
                print(f"  [SKIP] {code} (id={partner_id})")
                skipped += 1
            continue
        new_id = create("res.partner", values)
        print(f"  [CREATE] {code} → {values['name']} (id={new_id})")
        created += 1
    print(f"\nDone. Created: {created}, Updated: {updated}, Skipped: {skipped}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Lancer le script**

```bash
python -m scripts.odoo.step32_create_packaging_vendors
```

Expected (premier run, ~5 fournisseurs) :
```
  [CREATE] VERR-AMBR → Verrerie Ambrée FR (id=<X>)
  [CREATE] PLAS-FLAC → Plastique Flacons FR (id=<X>)
  [CREATE] POT-MASQUE → Pots Masques FR (id=<X>)
  [CREATE] PUMP-DISP → Pompes & Dispensers (id=<X>)
  [CREATE] SPRAY-FR → Pulvérisateurs Spray (id=<X>)

Done. Created: 5, Updated: 0, Skipped: 0
```

- [ ] **Step 4: Tester idempotence**

Relancer le script : tous les `[SKIP]`. Si email/nom modifié dans le CSV : `[UPDATE]`.

- [ ] **Step 5: Vérification Odoo**

Contacts → filtrer par "Fournisseur" → vérifier la présence des 5 fournisseurs.

- [ ] **Step 6: Commit**

```bash
git add scripts/odoo/step32_create_packaging_vendors.py
git commit -m "feat(odoo): create packaging vendors from CSV (step32)"
```

---

### Task 4 : Produits bulk (~50)

**Files:**
- Create: `scripts/odoo/step33_create_bulk_products.py`

- [ ] **Step 1: Découvrir l'ID de la route "Buy" et "Manufacture"**

```bash
python -c "from scripts.odoo._client import search_read; print(search_read('stock.route', [], ['id','name']))"
```

Noter les IDs des routes `Buy` et `Manufacture`. Les coder en dur dans le script (`ROUTE_BUY_ID`, `ROUTE_MANUFACTURE_ID`).

- [ ] **Step 2: Écrire le script step33**

Créer `scripts/odoo/step33_create_bulk_products.py` :

```python
"""Création des produits bulk dans product.template.

Lit data/bulk_formulas.csv. Idempotent : match par default_code (SKU).
Tracking by lot. Unité kg. Routes Buy ou Manufacture selon CSV.
"""
import csv
from pathlib import Path
from scripts.odoo._client import execute, search_read, create, write

CSV_PATH = Path(__file__).parent / "data" / "bulk_formulas.csv"

# À REMPLIR depuis Step 1 du Task 4
ROUTE_BUY_ID = None  # ex: 5
ROUTE_MANUFACTURE_ID = None  # ex: 6

# Catégorie produit MyLab pour les bulks (créée à la volée si absente)
CATEGORY_NAME = "Matières premières / Bulk"


def get_or_create_category() -> int:
    existing = search_read("product.category", [("name", "=", CATEGORY_NAME)], ["id"])
    if existing:
        return existing[0]["id"]
    return create("product.category", {"name": CATEGORY_NAME})


def get_uom_kg() -> int:
    rows = search_read("uom.uom", [("name", "=", "kg")], ["id"])
    if not rows:
        raise RuntimeError("UoM 'kg' introuvable")
    return rows[0]["id"]


def get_vendor_id(name: str) -> int | None:
    if not name:
        return None
    rows = search_read("res.partner", [("name", "=", name), ("supplier_rank", ">", 0)], ["id"])
    if not rows:
        # Tenter FP Cosmetics : peut exister sous un nom légèrement différent
        rows = search_read("res.partner", [("name", "ilike", "FP Cosmetics")], ["id"])
    return rows[0]["id"] if rows else None


def main():
    assert ROUTE_BUY_ID and ROUTE_MANUFACTURE_ID, "Renseigne ROUTE_BUY_ID et ROUTE_MANUFACTURE_ID (Task 4 Step 1)"
    category_id = get_or_create_category()
    uom_kg_id = get_uom_kg()
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))
    created, skipped = 0, 0

    for r in rows:
        sku = r["bulk_sku"].strip()
        existing = search_read("product.template", [("default_code", "=", sku)], ["id", "name"])
        if existing:
            print(f"  [SKIP] {sku} (id={existing[0]['id']})")
            skipped += 1
            continue

        route_id = ROUTE_BUY_ID if r["route"].strip() == "Buy" else ROUTE_MANUFACTURE_ID
        vendor_id = get_vendor_id(r["vendor"].strip())

        values = {
            "name": r["bulk_name"].strip(),
            "default_code": sku,
            "type": "product",  # storable
            "categ_id": category_id,
            "uom_id": uom_kg_id,
            "uom_po_id": uom_kg_id,
            "tracking": "lot",
            "route_ids": [(6, 0, [route_id])],
            "sale_ok": False,
            "purchase_ok": r["route"].strip() == "Buy",
            "company_id": False,  # multi-company
        }
        new_id = create("product.template", values)

        # Lier le fournisseur si applicable (table seller_ids)
        if vendor_id and r["route"].strip() == "Buy":
            execute("product.supplierinfo", "create", [{
                "partner_id": vendor_id,
                "product_tmpl_id": new_id,
                "delay": 14,  # default 14 jours, à ajuster manuellement par formule
            }])

        print(f"  [CREATE] {sku} → {values['name']} (id={new_id})")
        created += 1

    print(f"\nDone. Created: {created}, Skipped: {skipped}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Lancer le script**

```bash
python -m scripts.odoo.step33_create_bulk_products
```

Expected (premier run, ~50 lignes) :
```
  [CREATE] BULK-shampoing-nourrissant → Bulk shampoing nourrissant (id=<X>)
  ... (~50 lignes)
Done. Created: ~50, Skipped: 0
```

- [ ] **Step 4: Tester idempotence**

Relancer : tous `[SKIP]`. `Done. Created: 0, Skipped: ~50`.

- [ ] **Step 5: Vérification**

```bash
python -c "from scripts.odoo._client import search_read; print(len(search_read('product.template', [('default_code','=like','BULK-%')], ['id'])))"
```

Doit retourner le nombre de bulks créés (~50).

Vérifier aussi dans Odoo qu'un bulk a bien `Tracking = By Lots`, `UoM = kg`, et route correctement assignée.

- [ ] **Step 6: Commit**

```bash
git add scripts/odoo/step33_create_bulk_products.py
git commit -m "feat(odoo): create bulk products with lot tracking (step33)"
```

---

### Task 5 : Produits packaging (~15)

**Files:**
- Create: `scripts/odoo/step34_create_packaging_products.py`

- [ ] **Step 1: Écrire le script step34**

Créer `scripts/odoo/step34_create_packaging_products.py` :

```python
"""Création des produits packaging dans product.template.

Lit data/packaging_products.csv. Idempotent : match par default_code (SKU).
Pas de tracking lot. UoM 'Units'. Route Buy + seller_ids vers fournisseur packaging.
"""
import csv
from pathlib import Path
from scripts.odoo._client import execute, search_read, create

CSV_PATH = Path(__file__).parent / "data" / "packaging_products.csv"

# À REMPLIR depuis Task 4 Step 1
ROUTE_BUY_ID = None  # même que step33

CATEGORY_NAME = "Packaging"


def get_or_create_category() -> int:
    existing = search_read("product.category", [("name", "=", CATEGORY_NAME)], ["id"])
    return existing[0]["id"] if existing else create("product.category", {"name": CATEGORY_NAME})


def get_uom_units() -> int:
    rows = search_read("uom.uom", [("name", "=", "Units")], ["id"])
    if not rows:
        raise RuntimeError("UoM 'Units' introuvable")
    return rows[0]["id"]


def get_vendor_by_code(code: str) -> int | None:
    rows = search_read("res.partner", [("ref", "=", code)], ["id"])
    return rows[0]["id"] if rows else None


def main():
    assert ROUTE_BUY_ID, "Renseigne ROUTE_BUY_ID (cf Task 4 Step 1)"
    category_id = get_or_create_category()
    uom_units_id = get_uom_units()
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))
    created, skipped = 0, 0

    for r in rows:
        sku = r["sku"].strip()
        existing = search_read("product.template", [("default_code", "=", sku)], ["id"])
        if existing:
            print(f"  [SKIP] {sku} (id={existing[0]['id']})")
            skipped += 1
            continue

        vendor_id = get_vendor_by_code(r["vendor_code"].strip())
        values = {
            "name": r["name"].strip(),
            "default_code": sku,
            "type": "product",
            "categ_id": category_id,
            "uom_id": uom_units_id,
            "uom_po_id": uom_units_id,
            "tracking": "none",
            "route_ids": [(6, 0, [ROUTE_BUY_ID])],
            "sale_ok": sku == "POMPE-1000",  # seule la pompe 1000ml est aussi vendue
            "purchase_ok": True,
            "company_id": False,
        }
        new_id = create("product.template", values)

        if vendor_id:
            execute("product.supplierinfo", "create", [{
                "partner_id": vendor_id,
                "product_tmpl_id": new_id,
                "delay": 14,  # ajuster manuellement par fournisseur
            }])

        print(f"  [CREATE] {sku} → {values['name']} (id={new_id})")
        created += 1

    print(f"\nDone. Created: {created}, Skipped: {skipped}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Lancer le script**

```bash
python -m scripts.odoo.step34_create_packaging_products
```

Expected : ~15 `[CREATE]` lignes.

- [ ] **Step 3: Tester idempotence**

Relancer : tous `[SKIP]`.

- [ ] **Step 4: Vérification**

```bash
python -c "from scripts.odoo._client import search_read; rows = search_read('product.template', [('categ_id.name','=','Packaging')], ['default_code','name']); [print(r) for r in rows]"
```

Doit lister les ~15 SKUs packaging.

- [ ] **Step 5: Commit**

```bash
git add scripts/odoo/step34_create_packaging_products.py
git commit -m "feat(odoo): create packaging products with vendors (step34)"
```

---

### Task 6 : Nomenclatures (BoMs) et populating `x_mylab_bom_summary`

**Files:**
- Create: `scripts/odoo/step35_create_boms.py`

- [ ] **Step 1: Compléter manuellement les lignes vides de `finished_to_components.csv`**

Avant de lancer le script, ouvrir `scripts/odoo/data/finished_to_components.csv` et vérifier toutes les lignes ont `flacon_sku` et `bouchon_sku` non vides. Pour les lignes vides (cas spéciaux non détectés) — les remplir manuellement après discussion avec Yoann.

- [ ] **Step 2: Écrire le script step35**

Créer `scripts/odoo/step35_create_boms.py` :

```python
"""Création des nomenclatures (BoMs) pour les produits finis qui consomment du bulk.

Lit data/finished_to_components.csv. Idempotent : si une BoM existe déjà pour
un produit fini, elle est mise à jour (lignes recalculées). Sinon créée.

Populate aussi le champ x_mylab_bom_summary (JSON) sur le produit fini, utilisé
par le workflow n8n de sync stock Shopify.
"""
import csv
import json
from pathlib import Path
from scripts.odoo._client import execute, search_read, create, write, search

CSV_PATH = Path(__file__).parent / "data" / "finished_to_components.csv"


def get_product_id_by_sku(sku: str) -> int | None:
    """Retourne le product.product (variant) id pour ce SKU.
    Pour un produit sans variants, c'est le seul variant du template."""
    if not sku:
        return None
    rows = search_read("product.product", [("default_code", "=", sku)], ["id", "product_tmpl_id"])
    return rows[0]["id"] if rows else None


def get_template_id_by_sku(sku: str) -> int | None:
    rows = search_read("product.template", [("default_code", "=", sku)], ["id"])
    return rows[0]["id"] if rows else None


def main():
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))
    created, updated, skipped, missing = 0, 0, 0, 0

    for r in rows:
        finished_sku = r["finished_sku"].strip()
        bulk_sku = r["bulk_sku"].strip()
        flacon_sku = r["flacon_sku"].strip()
        bouchon_sku = r["bouchon_sku"].strip()
        bulk_kg = float(r["bulk_qty_kg"])

        if not (flacon_sku and bouchon_sku):
            print(f"  [SKIP-EMPTY] {finished_sku} (composants manquants dans CSV)")
            skipped += 1
            continue

        # Récupérer les IDs produits
        finished_tmpl_id = get_template_id_by_sku(finished_sku)
        finished_product_id = get_product_id_by_sku(finished_sku)
        bulk_id = get_product_id_by_sku(bulk_sku)
        flacon_id = get_product_id_by_sku(flacon_sku)
        bouchon_id = get_product_id_by_sku(bouchon_sku)

        if not all([finished_tmpl_id, finished_product_id, bulk_id, flacon_id, bouchon_id]):
            details = {
                "finished": finished_tmpl_id,
                "bulk": bulk_id,
                "flacon": flacon_id,
                "bouchon": bouchon_id,
            }
            print(f"  [MISSING] {finished_sku}: produit introuvable {details}")
            missing += 1
            continue

        # Vérifier si BoM existe
        bom_existing = search_read("mrp.bom", [("product_tmpl_id", "=", finished_tmpl_id)], ["id"])

        bom_lines = [
            (0, 0, {"product_id": bulk_id, "product_qty": bulk_kg}),
            (0, 0, {"product_id": flacon_id, "product_qty": 1}),
            (0, 0, {"product_id": bouchon_id, "product_qty": 1}),
        ]

        if bom_existing:
            # Update : recréer les lignes
            bom_id = bom_existing[0]["id"]
            # Supprimer les anciennes lignes
            old_line_ids = search("mrp.bom.line", [("bom_id", "=", bom_id)])
            if old_line_ids:
                execute("mrp.bom.line", "unlink", [old_line_ids])
            # Recréer
            write("mrp.bom", [bom_id], {"bom_line_ids": bom_lines})
            print(f"  [UPDATE] BoM pour {finished_sku} (id={bom_id})")
            updated += 1
        else:
            bom_id = create("mrp.bom", {
                "product_tmpl_id": finished_tmpl_id,
                "product_qty": 1,
                "type": "normal",
                "bom_line_ids": bom_lines,
            })
            print(f"  [CREATE] BoM pour {finished_sku} (bom_id={bom_id})")
            created += 1

        # Populer x_mylab_bom_summary
        summary = json.dumps({
            "bulk_sku": bulk_sku,
            "bulk_kg": bulk_kg,
            "flacon_sku": flacon_sku,
            "bouchon_sku": bouchon_sku,
            "family": r["family"].strip(),
            "contenance": r["contenance"].strip(),
        })
        write("product.template", [finished_tmpl_id], {"x_mylab_bom_summary": summary})

    print(f"\nDone. Created: {created}, Updated: {updated}, Skipped: {skipped}, Missing: {missing}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Lancer le script (mode "dry-run" mental — vérifier les MISSING d'abord)**

```bash
python -m scripts.odoo.step35_create_boms
```

Si des `[MISSING]` apparaissent → vérifier que les produits finis correspondants existent bien dans Odoo (table `product.template`, default_code = handle Shopify). Les corriger avant de continuer.

Expected sans erreur : ~150 `[CREATE]`, puis `Done. Created: ~150, Skipped: 0, Missing: 0`.

- [ ] **Step 4: Tester idempotence**

Relancer : toutes les BoMs déjà existantes → `[UPDATE]` (même contenu, pas de différence fonctionnelle, mais lignes recréées).

Note : pour vraie idempotence "no-op si identique", il faudrait comparer les lignes existantes avant de recréer. Pour la première version on accepte le re-write (pas de side-effect côté stock — les BoMs ne touchent pas au stock).

- [ ] **Step 5: Vérification**

```bash
python -c "from scripts.odoo._client import search_read; print('BoMs:', len(search_read('mrp.bom', [], ['id']))); print('Products avec summary:', len(search_read('product.template', [('x_mylab_bom_summary','!=',False)], ['id'])))"
```

Doit retourner ~150 BoMs et ~150 produits avec summary.

Ouvrir Odoo : Fabrication → Nomenclatures → ouvrir "Shampoing nourrissant 200ml" → vérifier les 3 lignes (0.2 kg bulk, 1 flacon, 1 bouchon).

- [ ] **Step 6: Commit**

```bash
git add scripts/odoo/step35_create_boms.py
git commit -m "feat(odoo): create BoMs and populate x_mylab_bom_summary (step35)"
```

---

### Task 7 : Règles de réapprovisionnement (min/max)

**Files:**
- Create: `scripts/odoo/step36_create_reorder_rules.py`

- [ ] **Step 1: Écrire le script step36**

Créer `scripts/odoo/step36_create_reorder_rules.py` :

```python
"""Création des règles de réapprovisionnement (stock.warehouse.orderpoint).

Une règle par bulk + une règle par packaging.
Lit data/bulk_formulas.csv et data/packaging_products.csv.
Idempotent : match par produit (chaque produit ne doit avoir qu'une seule règle active).
"""
import csv
from pathlib import Path
from scripts.odoo._client import execute, search_read, create, write

BULK_CSV = Path(__file__).parent / "data" / "bulk_formulas.csv"
PACK_CSV = Path(__file__).parent / "data" / "packaging_products.csv"


def get_product_id(sku: str) -> int | None:
    rows = search_read("product.product", [("default_code", "=", sku)], ["id"])
    return rows[0]["id"] if rows else None


def get_warehouse_id() -> int:
    rows = search_read("stock.warehouse", [], ["id"], limit=1)
    if not rows:
        raise RuntimeError("Aucun warehouse")
    return rows[0]["id"]


def get_bulk_location_id(warehouse_id: int) -> int:
    rows = search_read("stock.location", [("complete_name", "=", "WH/Stock/Bulk")], ["id"])
    return rows[0]["id"]


def get_packaging_location_id() -> int:
    rows = search_read("stock.location", [("complete_name", "=", "WH/Stock/Packaging")], ["id"])
    return rows[0]["id"]


def upsert_rule(product_id: int, location_id: int, warehouse_id: int, min_qty: float, max_qty: float, label: str):
    existing = search_read("stock.warehouse.orderpoint", [
        ("product_id", "=", product_id),
        ("location_id", "=", location_id),
    ], ["id"])
    values = {
        "product_id": product_id,
        "location_id": location_id,
        "warehouse_id": warehouse_id,
        "product_min_qty": min_qty,
        "product_max_qty": max_qty,
        "qty_multiple": 1,
    }
    if existing:
        write("stock.warehouse.orderpoint", [existing[0]["id"]], values)
        print(f"  [UPDATE] {label} (rule_id={existing[0]['id']})")
        return "updated"
    new_id = create("stock.warehouse.orderpoint", values)
    print(f"  [CREATE] {label} (rule_id={new_id})")
    return "created"


def main():
    warehouse_id = get_warehouse_id()
    bulk_loc = get_bulk_location_id(warehouse_id)
    pack_loc = get_packaging_location_id()
    stats = {"created": 0, "updated": 0, "missing": 0}

    print("=== Bulks ===")
    for r in csv.DictReader(BULK_CSV.open(encoding="utf-8")):
        sku = r["bulk_sku"].strip()
        pid = get_product_id(sku)
        if not pid:
            print(f"  [MISSING] {sku} introuvable")
            stats["missing"] += 1
            continue
        outcome = upsert_rule(pid, bulk_loc, warehouse_id,
                              float(r["min_qty_kg"]), float(r["max_qty_kg"]), sku)
        stats[outcome] += 1

    print("\n=== Packaging ===")
    for r in csv.DictReader(PACK_CSV.open(encoding="utf-8")):
        sku = r["sku"].strip()
        pid = get_product_id(sku)
        if not pid:
            print(f"  [MISSING] {sku} introuvable")
            stats["missing"] += 1
            continue
        outcome = upsert_rule(pid, pack_loc, warehouse_id,
                              float(r["min_qty"]), float(r["max_qty"]), sku)
        stats[outcome] += 1

    print(f"\nDone. Created: {stats['created']}, Updated: {stats['updated']}, Missing: {stats['missing']}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Lancer le script**

```bash
python -m scripts.odoo.step36_create_reorder_rules
```

Expected : ~65 `[CREATE]`, puis `Done. Created: ~65, Updated: 0, Missing: 0`.

- [ ] **Step 3: Tester idempotence**

Relancer : tous `[UPDATE]` (les valeurs sont identiques mais la commande passe). Pas de duplication de règles.

- [ ] **Step 4: Vérification**

```bash
python -c "from scripts.odoo._client import search_read; rules = search_read('stock.warehouse.orderpoint', [], ['name','product_id','product_min_qty','product_max_qty']); print(f'Total: {len(rules)}'); [print(r) for r in rules[:5]]"
```

Doit retourner ~65 règles avec min/max corrects.

Ouvrir Odoo : Inventaire → Opérations → Règles de réapprovisionnement. Vérifier les seuils.

- [ ] **Step 5: Forcer le calcul Odoo et vérifier qu'aucune RFQ erronée n'est créée**

Comme tous les stocks sont à 0 au démarrage et qu'aucune commande n'est encore en cours, **toutes** les règles vont déclencher des RFQ au premier calcul. Pour éviter cette explosion :

**IMPORTANT** : Ne **pas** lancer manuellement `Scheduler → Run Scheduler` dans Odoo tant que les inventaires initiaux (Phase C) ne sont pas saisis. Sinon Odoo créera ~65 RFQ vides en draft.

Si jamais c'est trop tard et qu'elles ont été créées, les supprimer manuellement dans Odoo : Achats → Demandes de prix → filtrer `state=draft AND date_order >= aujourd'hui` → sélection multiple → Action → Supprimer.

Pour éviter le problème, le scheduler est désactivé dans la Phase C Step 1 (avant inventaire) puis réactivé en Phase C Step 6.

- [ ] **Step 6: Commit**

```bash
git add scripts/odoo/step36_create_reorder_rules.py
git commit -m "feat(odoo): create reorder rules for bulks and packaging (step36)"
```

---

## Phase B : Workflows n8n (Tasks 8-10)

### Task 8 : Patcher le workflow `1AUxe9M9d9cNKz6W` — sync stock Shopify en mode projeté

**Files:**
- Modify: workflow n8n `1AUxe9M9d9cNKz6W` (via UI ou MCP n8n)
- Create: `docs/n8n/sync_stock_projected_logic.md` (documentation du patch)

- [ ] **Step 1: Récupérer la définition actuelle du workflow**

Via MCP n8n ou via API REST n8n :

```bash
# Via API REST (depuis WSL ou bash) — adapter URL et token :
curl -s -H "X-N8N-API-KEY: $N8N_API_KEY" \
  https://n8n.startec-paris.com/api/v1/workflows/1AUxe9M9d9cNKz6W > /tmp/sync_stock_current.json
```

Sauvegarder la copie : `docs/n8n/backup_1AUxe9M9d9cNKz6W_$(date +%F).json` (ne pas commit — sensible — déjà gitignored selon memory).

- [ ] **Step 2: Identifier les nodes à modifier**

Lire `/tmp/sync_stock_current.json` et repérer :
- Le node qui appelle Odoo en XML-RPC pour récupérer les stocks (typiquement un `Function` ou `Code` node + `HTTP Request`)
- Le node qui pousse vers Shopify `inventory_level/set.json`
- Le node de matching SKU entre les deux

- [ ] **Step 3: Concevoir la nouvelle logique**

La logique cible (à intégrer dans un node `Code` JavaScript) :

```javascript
// INPUT items: un par produit fini Odoo, avec :
//   - default_code (SKU)
//   - qty_available (stock fini physique)
//   - x_mylab_bom_summary (JSON string)
//   - bulk_stocks (map SKU bulk → qty kg, fournie par un node précédent)
//   - packaging_stocks (map SKU packaging → qty unités)

const MIX = {
  shampoings: { "200": 0.77, "500": 0.07, "1000": 0.16 },
  masques: { "200": 0.80, "400": 0.03, "1000": 0.17 },
  serums_huiles: { "50": 1.0 },
};

const POIDS_PAR_BOUTEILLE = { "50": 0.05, "200": 0.2, "400": 0.4, "500": 0.5, "1000": 1.0 };

return items.map(item => {
  const data = item.json;
  const fini = data.qty_available || 0;
  const summaryRaw = data.x_mylab_bom_summary;

  // Pas de BoM = coffret/duo/produit annexe → stock physique pur
  if (!summaryRaw) {
    data.stock_projete = fini;
    return { json: data };
  }

  let summary;
  try { summary = JSON.parse(summaryRaw); }
  catch { data.stock_projete = fini; return { json: data }; }

  const bulkKg = data.bulk_stocks?.[summary.bulk_sku] || 0;
  const flacon = data.packaging_stocks?.[summary.flacon_sku] || 0;
  const bouchon = data.packaging_stocks?.[summary.bouchon_sku] || 0;

  const mix = MIX[summary.family]?.[summary.contenance] || 0;
  const poids = POIDS_PAR_BOUTEILLE[summary.contenance] || summary.bulk_kg || 0.2;

  const potentielBulk = (bulkKg * mix) / poids;
  const potentiel = Math.floor(Math.min(potentielBulk, flacon, bouchon));

  data.stock_projete = fini + potentiel;
  return { json: data };
});
```

- [ ] **Step 4: Ajouter un node préliminaire qui charge les stocks bulk + packaging**

Ce node fait un seul appel XML-RPC pour récupérer tous les stocks de bulks + packaging d'un coup (au lieu d'un par produit fini), et les expose en map dans le contexte du workflow.

Pseudocode (JavaScript dans n8n) :

```javascript
// Récupère tous les bulks + packaging via le node HTTP Request XML-RPC précédent
// Items en entrée : liste de produits avec default_code et qty_available
const bulk_stocks = {};
const packaging_stocks = {};
for (const item of items) {
  const sku = item.json.default_code;
  if (sku.startsWith("BULK-")) {
    bulk_stocks[sku] = item.json.qty_available;
  } else {
    packaging_stocks[sku] = item.json.qty_available;
  }
}
// Forward to next node attached to each finished product
return [{ json: { bulk_stocks, packaging_stocks } }];
```

- [ ] **Step 5: Modifier le node de push Shopify**

Le node qui appelle `POST /admin/api/.../inventory_levels/set.json` doit utiliser `data.stock_projete` au lieu de `data.qty_available`.

- [ ] **Step 6: Sauvegarder + tester en mode "dry-run"**

Avant de réactiver le workflow, le lancer en mode manuel sur 5 produits seulement. Comparer le `stock_projete` calculé avec un calcul manuel sur ces 5 produits.

- [ ] **Step 7: Activer le workflow et observer le premier run live**

Cron 5h. Vérifier qu'après la première exécution :
- Les SKUs Shopify ont bien des stocks différents de `qty_available` Odoo (puisqu'ils intègrent le potentiel bulk + packaging)
- Aucun produit sans BoM (coffret) n'est touché de manière inattendue

- [ ] **Step 8: Documenter le patch**

Créer `docs/n8n/sync_stock_projected_logic.md` avec :
- Diagramme des nodes mis à jour
- Le code JavaScript des deux nodes ajoutés (avec commentaires)
- Lien vers le spec
- Date du patch + workflow ID

- [ ] **Step 9: Commit**

```bash
git add docs/n8n/sync_stock_projected_logic.md
git commit -m "docs(n8n): document stock sync projected mode (workflow 1AUxe9M9d9cNKz6W)"
```

---

### Task 9 : Créer le workflow "RFQ récap lundi"

**Files:**
- Create: workflow n8n nouveau, dans folder Yo
- Create: `docs/n8n/rfq_weekly_recap.md` (documentation)

- [ ] **Step 1: Définir le squelette du workflow**

Nodes (séquence) :
1. **Cron Trigger** : `0 8 * * 1` (lundi 8h Europe/Paris)
2. **HTTP Request XML-RPC Odoo** : `search_read` sur `purchase.order` avec `state='draft' AND date_order >= NOW-7d`
3. **Code** : grouper par fournisseur, formater le récap HTML
4. **Gmail node** : envoyer à `yoann@mylab-shop.com` (compte service `n8n@startec-paris.com`)
5. **If** : si zéro RFQ → envoyer un email court "rien à commander cette semaine"

- [ ] **Step 2: Construire la requête XML-RPC**

```javascript
// Node HTTP Request, method POST, URL = https://odoo.startec-paris.com/xmlrpc/2/object
// Body (en XML-RPC) — à construire dans un node Function précédent :

const xmlBody = `<?xml version="1.0"?>
<methodCall>
  <methodName>execute_kw</methodName>
  <params>
    <param><value><string>{{$env.ODOO_DB}}</string></value></param>
    <param><value><int>{{$env.ODOO_UID}}</int></value></param>
    <param><value><string>{{$env.ODOO_API_KEY}}</string></value></param>
    <param><value><string>purchase.order</string></value></param>
    <param><value><string>search_read</string></value></param>
    <param><value><array><data>
      <value><array><data>
        <value><array><data>
          <value><string>state</string></value>
          <value><string>=</string></value>
          <value><string>draft</string></value>
        </data></array></value>
      </data></array></value>
    </data></array></value></param>
    <param><value><struct>
      <member><name>fields</name><value><array><data>
        <value><string>id</string></value>
        <value><string>name</string></value>
        <value><string>partner_id</string></value>
        <value><string>date_order</string></value>
        <value><string>order_line</string></value>
      </data></array></value></member>
    </struct></value></param>
  </params>
</methodCall>`;
```

Pour simplifier, utiliser plutôt un node `Function` qui appelle XML-RPC via `this.helpers.httpRequest` avec le body XML pré-formaté (cf. memory `feedback_n8n_dev.md` — pas de `fetch()`).

- [ ] **Step 3: Code node de formatage**

```javascript
// items[0].json = { rfq_list: [...] }
const rfqs = items[0].json.rfq_list || [];

if (rfqs.length === 0) {
  return [{
    json: {
      to: "yoann@mylab-shop.com",
      subject: "[MyLab] Pas de réappro à faire cette semaine",
      html: "Aucune RFQ en draft cette semaine. Bon début de semaine !"
    }
  }];
}

// Grouper par fournisseur
const byVendor = {};
for (const rfq of rfqs) {
  const vendor = rfq.partner_id[1] || "Inconnu";
  if (!byVendor[vendor]) byVendor[vendor] = [];
  byVendor[vendor].push(rfq);
}

let html = `<h2>Récap RFQ à valider cette semaine</h2>`;
html += `<p>${rfqs.length} RFQ en attente :</p>`;
for (const [vendor, list] of Object.entries(byVendor)) {
  html += `<h3>${vendor} (${list.length} RFQ)</h3><ul>`;
  for (const rfq of list) {
    html += `<li><a href="https://odoo.startec-paris.com/web#id=${rfq.id}&model=purchase.order&view_type=form">${rfq.name}</a> — ${rfq.date_order}</li>`;
  }
  html += `</ul>`;
}
html += `<p><em>Clique sur chaque RFQ pour valider et envoyer.</em></p>`;

return [{
  json: {
    to: "yoann@mylab-shop.com",
    subject: `[MyLab] ${rfqs.length} RFQ à valider — récap lundi`,
    html: html
  }
}];
```

- [ ] **Step 4: Configurer le node Gmail**

Compte service `n8n@startec-paris.com` (cf memory). Champs :
- To: `{{$json.to}}`
- Subject: `{{$json.subject}}`
- HTML body: `{{$json.html}}`
- **Signature** : ajouter en bas le HTML de la signature MY.LAB (cf `feedback_gmail_signature.md` + `docs/signature-email.html`).

- [ ] **Step 5: Placer le workflow dans le folder Yo**

Via MCP n8n ou UI : déplacer le nouveau workflow dans folder `Z2t5yT17QDhgf2XO` (id Yo), project `HUgJsuxI2uJxkLLk`.

- [ ] **Step 6: Tester en exécution manuelle**

Lancer le workflow en mode manuel via l'UI n8n. Vérifier qu'un email arrive avec le récap formaté (ou le message "pas de RFQ").

- [ ] **Step 7: Activer le workflow**

État = Active. Le cron lundi 8h sera respecté.

- [ ] **Step 8: Documenter**

Créer `docs/n8n/rfq_weekly_recap.md` avec :
- ID du workflow créé
- Squelette des nodes
- Comment ajuster le cron / le destinataire
- Date de création

- [ ] **Step 9: Commit**

```bash
git add docs/n8n/rfq_weekly_recap.md
git commit -m "docs(n8n): document RFQ weekly recap workflow"
```

---

### Task 10 : Mini-workflow `orders/cancelled` → annulation SO Odoo

**Files:**
- Create: workflow n8n nouveau dans folder Yo
- Create: `docs/n8n/order_cancellation_sync.md`

- [ ] **Step 1: Cloner le workflow `Xj8T5a7aO8drZk5v` comme base**

Le workflow existant traite `orders/paid` → SO Odoo confirmée. On reproduit la structure (webhook Shopify + transformation + appel Odoo) mais pour `orders/cancelled` → annulation SO.

Récupérer la définition de `Xj8T5a7aO8drZk5v` :

```bash
curl -s -H "X-N8N-API-KEY: $N8N_API_KEY" \
  https://n8n.startec-paris.com/api/v1/workflows/Xj8T5a7aO8drZk5v > /tmp/orders_paid_workflow.json
```

- [ ] **Step 2: Construire le nouveau workflow**

Nodes :
1. **Webhook node** : path `/shopify-order-cancelled`, méthode POST, response code 200 immédiat
2. **HMAC verify** : optionnel (alignement avec workflow Xj8T...)
3. **Code** : extraire `order.id` ou `order.name` du payload Shopify, mapper vers le `sale.order.name` Odoo (typiquement `SO<id>`)
4. **HTTP Request XML-RPC Odoo** : `search_read` sale.order par nom
5. **HTTP Request XML-RPC Odoo** : `action_cancel` sur la SO trouvée
6. **Gmail** (optionnel) : notification à yoann@ pour traçabilité

- [ ] **Step 3: Configurer le webhook Shopify**

Dans Shopify Admin → Settings → Notifications → Webhooks :
- Event: `Order cancellation`
- Format: JSON
- URL: `https://n8n.startec-paris.com/webhook/shopify-order-cancelled`

- [ ] **Step 4: Tester avec une commande dummy**

Créer une commande test dans Shopify (commande payée immediate, puis cancellation). Vérifier que la SO Odoo correspondante passe à l'état "Cancelled".

- [ ] **Step 5: Placer dans folder Yo + activer**

- [ ] **Step 6: Documenter**

Créer `docs/n8n/order_cancellation_sync.md`.

- [ ] **Step 7: Commit**

```bash
git add docs/n8n/order_cancellation_sync.md
git commit -m "docs(n8n): document Shopify orders/cancelled → Odoo SO cancellation workflow"
```

---

## Phase C : Inventaire initial (Task 11)

### Task 11 : Saisie inventaire initial + helper script

**Files:**
- Create: `scripts/odoo/data/initial_inventory.csv` (template à remplir par Yoann)
- Create: `scripts/odoo/step37_seed_initial_inventory.py`

- [ ] **Step 1: Désactiver temporairement le scheduler Odoo**

Pour éviter que les règles min/max ne déclenchent des RFQ vides pendant la saisie d'inventaire (les stocks vont monter de 0 à leurs vraies valeurs en plusieurs étapes).

Créer un fichier temporaire `scripts/odoo/_disable_scheduler.py` :

```python
"""Désactive le cron 'Run Scheduler' d'Odoo. Sauvegarde l'ID dans un fichier
pour pouvoir le réactiver ensuite."""
from pathlib import Path
from scripts.odoo._client import search_read, write

# Trouver le cron du scheduler. En Odoo 18, il s'appelle typiquement "Run Scheduler"
# (parfois "Stock: Schedulers" selon les versions/modules)
crons = search_read("ir.cron", [
    ("cron_name", "in", ["Run Scheduler", "Stock: Schedulers", "Inventory: Run Scheduler"]),
], ["id", "cron_name", "active"])

if not crons:
    print("ERREUR: scheduler introuvable. Lister tous les crons avec :")
    print("  python -c \"from scripts.odoo._client import search_read; [print(c) for c in search_read('ir.cron', [], ['id','cron_name','active'])]\"")
    raise SystemExit(1)

# Désactiver tous les schedulers trouvés
for c in crons:
    if c["active"]:
        write("ir.cron", [c["id"]], {"active": False})
        print(f"  [DISABLED] {c['cron_name']} (id={c['id']})")
    else:
        print(f"  [ALREADY-OFF] {c['cron_name']} (id={c['id']})")

# Sauvegarder les IDs pour réactivation
ids = [c["id"] for c in crons]
Path(__file__).parent.joinpath(".scheduler_ids").write_text(",".join(map(str, ids)))
print(f"\nIDs sauvegardés dans .scheduler_ids → utiliser _enable_scheduler.py pour réactiver")
```

Et `scripts/odoo/_enable_scheduler.py` :

```python
"""Réactive les crons sauvegardés par _disable_scheduler.py."""
from pathlib import Path
from scripts.odoo._client import write

ids_file = Path(__file__).parent / ".scheduler_ids"
if not ids_file.exists():
    raise SystemExit("Aucun .scheduler_ids — rien à réactiver")

ids = [int(x) for x in ids_file.read_text().strip().split(",") if x]
write("ir.cron", ids, {"active": True})
print(f"  [ENABLED] {len(ids)} scheduler(s) réactivé(s) (ids={ids})")
ids_file.unlink()
```

Lancer :

```bash
python -m scripts.odoo._disable_scheduler
```

Expected :
```
  [DISABLED] Run Scheduler (id=<N>)
IDs sauvegardés dans .scheduler_ids → utiliser _enable_scheduler.py pour réactiver
```

Ajouter `.scheduler_ids` au `.gitignore` (déjà fait si présent).

- [ ] **Step 2: Préparer le template CSV inventaire**

Créer `scripts/odoo/data/initial_inventory.csv` :

```csv
sku,location,quantity,lot_name,note
BULK-shampoing-nourrissant,WH/Stock/Bulk,150,FP-2026-001,Fût en cours
BULK-masque-nourrissant,WH/Stock/Bulk,80,FP-2026-002,
FLACON-PLA-200,WH/Stock/Packaging,2500,,
FLACON-PLA-500,WH/Stock/Packaging,180,,
FLACON-PLA-1000,WH/Stock/Packaging,90,,
... etc (Yoann remplit)
```

Demander à Yoann de remplir ce CSV avec les vraies quantités en stock physique aujourd'hui.

- [ ] **Step 3: Écrire le script step37**

Créer `scripts/odoo/step37_seed_initial_inventory.py` :

```python
"""Saisie d'inventaire initial (stock.quant.create_inventory_adjustment).

Pour chaque ligne du CSV : crée un ajustement d'inventaire avec un lot si fourni.
Idempotent : si un quant existe déjà pour le triplet (product, location, lot),
met à jour la quantité au lieu d'ajouter.
"""
import csv
from pathlib import Path
from scripts.odoo._client import execute, search_read, create, write

CSV_PATH = Path(__file__).parent / "data" / "initial_inventory.csv"


def get_product_id(sku: str) -> int | None:
    rows = search_read("product.product", [("default_code", "=", sku)], ["id"])
    return rows[0]["id"] if rows else None


def get_location_id(complete_name: str) -> int:
    rows = search_read("stock.location", [("complete_name", "=", complete_name)], ["id"])
    if not rows:
        raise RuntimeError(f"Location {complete_name} introuvable")
    return rows[0]["id"]


def get_or_create_lot(product_id: int, lot_name: str) -> int:
    if not lot_name:
        return False
    rows = search_read("stock.lot", [
        ("name", "=", lot_name),
        ("product_id", "=", product_id),
    ], ["id"])
    if rows:
        return rows[0]["id"]
    return create("stock.lot", {
        "name": lot_name,
        "product_id": product_id,
    })


def main():
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))
    created, updated, missing = 0, 0, 0
    for r in rows:
        sku = r["sku"].strip()
        loc_name = r["location"].strip()
        qty = float(r["quantity"])
        lot_name = r.get("lot_name", "").strip()

        pid = get_product_id(sku)
        if not pid:
            print(f"  [MISSING] {sku}")
            missing += 1
            continue
        loc_id = get_location_id(loc_name)
        lot_id = get_or_create_lot(pid, lot_name) if lot_name else False

        # Vérifier si quant existe
        domain = [("product_id", "=", pid), ("location_id", "=", loc_id)]
        if lot_id:
            domain.append(("lot_id", "=", lot_id))
        existing = search_read("stock.quant", domain, ["id", "quantity"])

        if existing:
            write("stock.quant", [existing[0]["id"]], {"inventory_quantity": qty})
            execute("stock.quant", "action_apply_inventory", [existing[0]["id"]])
            print(f"  [UPDATE] {sku}@{loc_name}{f' lot={lot_name}' if lot_name else ''} → {qty}")
            updated += 1
        else:
            new_id = create("stock.quant", {
                "product_id": pid,
                "location_id": loc_id,
                "lot_id": lot_id or False,
                "inventory_quantity": qty,
            })
            execute("stock.quant", "action_apply_inventory", [new_id])
            print(f"  [CREATE] {sku}@{loc_name}{f' lot={lot_name}' if lot_name else ''} = {qty}")
            created += 1

    print(f"\nDone. Created: {created}, Updated: {updated}, Missing: {missing}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Lancer le script**

```bash
python -m scripts.odoo.step37_seed_initial_inventory
```

- [ ] **Step 5: Vérification**

Ouvrir Odoo → Inventaire → Rapports → Stock par emplacement. Vérifier :
- Les bulks ont les quantités attendues dans `WH/Stock/Bulk`
- Les packaging dans `WH/Stock/Packaging`
- Les lots bulk sont bien créés

- [ ] **Step 6: Réactiver le scheduler**

```bash
python -m scripts.odoo._enable_scheduler
```

Expected :
```
  [ENABLED] 1 scheduler(s) réactivé(s) (ids=[<N>])
```

- [ ] **Step 7: Commit**

```bash
git add scripts/odoo/step37_seed_initial_inventory.py scripts/odoo/data/initial_inventory.csv
git commit -m "feat(odoo): seed initial inventory with lot tracking (step37)"
```

Note : `initial_inventory.csv` contient des données potentiellement sensibles (quantités exactes). Si trop sensible, l'ajouter au `.gitignore`. Pour l'instant on commit le template seulement (sans les vraies quantités) — vérifier avec Yoann.

---

## Phase D : Go-live verification (Task 12)

### Task 12 : Tests de bout en bout

- [ ] **Step 1: Premier MO de conditionnement**

Dans Odoo → Fabrication → Ordres de fabrication → Nouveau :
- Produit : `Shampoing nourrissant 200ml`
- Quantité à produire : 10
- Composants pré-remplis depuis BoM : 2 kg bulk + 10 flacons + 10 bouchons
- Sélectionner le lot bulk (ex: `FP-2026-001`)
- Confirmer → Démarrer → Produire → Valider

Vérifier :
- Stock bulk décrémenté de 2 kg
- Stock flacon 200ml décrémenté de 10
- Stock bouchon décrémenté de 10
- Stock fini incrémenté de 10

- [ ] **Step 2: Premier MO fab interne**

Si un bulk fab interne est en stock (ex: `BULK-serum-purifiant` est fabriqué en interne) — vérifier qu'on peut faire un MO de conditionnement même si la route est `Manufacture` (pas seulement Buy).

- [ ] **Step 3: Test commande Shopify**

Passer une commande test depuis Shopify (1× Shampoing nourrissant 200ml). Vérifier dans l'ordre :
1. Workflow `Xj8T5a7aO8drZk5v` crée la SO Odoo confirmée
2. Réservation créée sur le produit fini (stock.move pending)
3. `virtual_available` du produit fini diminue de 1
4. Au prochain run du workflow `1AUxe9M9d9cNKz6W` (max 5h), le stock projeté Shopify est mis à jour

- [ ] **Step 4: Test annulation commande**

Annuler la commande test depuis Shopify. Vérifier :
1. Workflow `orders/cancelled` (Task 10) déclenché
2. SO Odoo passée à "Cancelled"
3. Réservation libérée → stock projeté remonte

- [ ] **Step 5: Simuler un seuil de réappro déclenché**

Forcer manuellement un bulk sous le seuil : ouvrir un bulk, descendre temporairement le stock à 10 kg via un ajustement d'inventaire. Lancer le scheduler manuellement (`Run Scheduler` dans Inventory → Operations). Vérifier qu'une RFQ draft est créée pour FP Cosmetics avec ce bulk.

- [ ] **Step 6: Attendre / simuler le récap lundi**

Soit attendre le prochain lundi 8h, soit lancer le workflow manuellement. Vérifier que l'email récap arrive avec la RFQ draft du Step 5.

- [ ] **Step 7: Restaurer l'état initial**

Annuler l'ajustement d'inventaire du Step 5, supprimer la RFQ test, supprimer la commande Shopify test. Tout doit revenir à un état propre.

- [ ] **Step 8: Documenter les observations**

Créer `docs/superpowers/notes/2026-MM-DD-stock-mrp-go-live.md` (date de la mise en route) avec :
- Date de go-live
- Anomalies constatées (s'il y en a)
- Ajustements à faire en Phase E
- Validation que tout fonctionne

- [ ] **Step 9: Commit + tag**

```bash
git add docs/superpowers/notes/
git commit -m "docs(notes): stock MRP go-live observations"
git tag -a stock-mrp-v1 -m "Stock MRP v1 go-live"
```

---

## Plan summary

| Phase | Tasks | Durée estimée |
|---|---|---|
| 0 — CSV inputs | Task 0 | 2h (incluant remplissage manuel) |
| A — Odoo modeling | Tasks 1-7 | 1-2 jours |
| B — n8n workflows | Tasks 8-10 | ½ journée |
| C — Inventaire initial | Task 11 | 1 jour (terrain inclus) |
| D — Go-live | Task 12 | ½ journée |
| **Total** | **12 tâches** | **~3-4 jours effectifs sur 2 semaines** |

## Notes finales

- **Phase E (optionnelle)** : voir spec section "Hors scope" pour les évolutions post-launch (wizard custom, seuils dynamiques, BoMs coffrets, etc.). Pas dans ce plan.
- **Sécurité** : ne jamais commit `.env.local` ni les `docs/n8n/backup_*.json` (workflows contiennent des tokens).
- **Rollback** : tous les scripts sont idempotents et n'ont pas de side-effects destructifs. En cas de problème en Phase A, supprimer les produits/règles via l'UI Odoo. En Phase B, désactiver les workflows n8n. La seule étape destructive est l'inventaire initial (Phase C) — qui modifie le stock physique. Aucun produit fini existant n'est touché.
