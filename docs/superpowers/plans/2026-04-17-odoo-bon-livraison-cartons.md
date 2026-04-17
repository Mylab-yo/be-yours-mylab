# Bon de livraison Odoo avec répartition en cartons — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter un bon de livraison PDF Odoo qui calcule automatiquement la répartition des produits en cartons (via capacité produit définie), avec édition manuelle possible, et affichage compact récap + détail carton pour vérification client à la réception.

**Architecture:** 3 pièces dans Odoo (aucun module) : (1) champ custom `x_carton_capacity` sur `product.template`, (2) action serveur "Répartir en cartons" sur `stock.picking` qui crée des `stock.quant.package` selon un algo de regroupement par famille, (3) template QWeb PDF custom qui remplace le BL par défaut. Déploiement via scripts Python XML-RPC idempotents.

**Tech Stack:** Python 3.11+, `xmlrpc.client` (stdlib), `python-dotenv`, Odoo 17, QWeb templates XML.

**Spec :** [docs/superpowers/specs/2026-04-17-odoo-bon-livraison-cartons-design.md](../specs/2026-04-17-odoo-bon-livraison-cartons-design.md)

---

## File Structure

**Fichiers à créer** :
- `scripts/odoo/__init__.py` — package marker
- `scripts/odoo/_client.py` — helper XML-RPC partagé (connexion, execute, search_read)
- `scripts/odoo/stepstep01_create_carton_field.py` — crée `x_carton_capacity` sur `product.template`
- `scripts/odoo/stepstep02_init_carton_capacity.py` — peuple le champ via parsing nom produit
- `scripts/odoo/stepstep03_create_server_action.py` — crée l'`ir.actions.server` "Répartir en cartons"
- `scripts/odoo/stepstep04_create_bl_report.py` — crée `ir.ui.view` (QWeb) + `ir.actions.report`
- `scripts/odoo/stepstep05_add_picking_button.py` — crée vue héritée `stock.view_picking_form` avec bouton
- `scripts/odoo/templates/bl_deliveryslip.xml` — source QWeb du template BL (lu par `stepstep04_create_bl_report.py`)
- `scripts/odoo/server_action_code.py` — source Python de l'action serveur (lue par `stepstep03_create_server_action.py`)
- `scripts/odoo/README.md` — instructions pour exécuter les scripts dans l'ordre

**Convention de nommage :** préfixe `stepNN_` (et non `NN_`) car Python n'autorise pas les identifiants commençant par un chiffre — `python -m scripts.odoo.01_xxx` échouerait.

**Responsabilités** :
- Chaque script Odoo est idempotent : s'il est relancé, il met à jour le record existant plutôt que d'en créer un doublon.
- `_client.py` est la seule source de dépendance `xmlrpc.client` — les autres scripts n'importent que `from _client import odoo`.
- Le code de l'action serveur est maintenu en fichier séparé (`server_action_code.py`) pour être lisible et diff-able dans git, même si Odoo le stocke comme chaîne.
- Le QWeb template est en fichier `.xml` séparé pour la même raison.

---

## Prérequis environnement

Avant de commencer :

- [ ] **Vérifier que `.env.local` existe** avec les credentials Odoo

```bash
ls "d:/Configurateur Designs MyLab/mylab-configurateur/.env.local"
```

Doit contenir (d'après la memory) :
```
ODOO_URL=https://odoo.startec-paris.com
ODOO_DB=OdooYJ
ODOO_USER=<user>
ODOO_API_KEY=e6d35b4261b948664841075e8fffc3510c8db437
```

- [ ] **Installer python-dotenv** si pas déjà fait

```bash
pip install python-dotenv
```

- [ ] **Créer le dossier scripts/odoo**

```bash
mkdir -p d:/be-yours-mylab/scripts/odoo/templates
```

---

## Task 1: Créer le helper XML-RPC partagé

**Files:**
- Create: `scripts/odoo/__init__.py`
- Create: `scripts/odoo/_client.py`

- [ ] **Step 1: Créer le package marker**

Créer `scripts/odoo/__init__.py` (vide).

```bash
touch d:/be-yours-mylab/scripts/odoo/__init__.py
```

- [ ] **Step 2: Écrire le client XML-RPC**

Créer `scripts/odoo/_client.py` :

```python
"""Odoo XML-RPC client helper for MyLab scripts."""
import os
import xmlrpc.client
from pathlib import Path
from dotenv import load_dotenv

# Load .env.local from configurateur repo (source of truth per memory)
ENV_PATH = Path(r"d:\Configurateur Designs MyLab\mylab-configurateur\.env.local")
if not ENV_PATH.exists():
    raise FileNotFoundError(f"Missing env file: {ENV_PATH}")
load_dotenv(ENV_PATH)

URL = os.environ["ODOO_URL"]
DB = os.environ["ODOO_DB"]
USER = os.environ["ODOO_USER"]
API_KEY = os.environ["ODOO_API_KEY"]

_common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
UID = _common.authenticate(DB, USER, API_KEY, {})
if not UID:
    raise RuntimeError("Odoo authentication failed")

_models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")


def execute(model: str, method: str, args: list, kwargs: dict | None = None):
    """Call any Odoo model method."""
    return _models.execute_kw(DB, UID, API_KEY, model, method, args, kwargs or {})


def search_read(model: str, domain: list, fields: list, limit: int = 0):
    return execute(model, "search_read", [domain], {"fields": fields, "limit": limit})


def create(model: str, values: dict) -> int:
    return execute(model, "create", [values])


def write(model: str, ids: list, values: dict) -> bool:
    return execute(model, "write", [ids, values])


def search(model: str, domain: list, limit: int = 0) -> list:
    return execute(model, "search", [domain], {"limit": limit})


def unlink(model: str, ids: list) -> bool:
    return execute(model, "unlink", [ids])


if __name__ == "__main__":
    # Sanity check: list first 3 products
    prods = search_read("product.template", [("sale_ok", "=", True)],
                        ["id", "name"], limit=3)
    print(f"Connected as UID={UID}")
    for p in prods:
        print(f"  {p['id']}: {p['name']}")
```

- [ ] **Step 3: Tester la connexion**

```bash
cd d:/be-yours-mylab && python -m scripts.odoo._client
```

Expected output: `Connected as UID=8` suivi de 3 produits listés.

- [ ] **Step 4: Commit**

```bash
cd d:/be-yours-mylab
git add scripts/odoo/__init__.py scripts/odoo/_client.py
git commit -m "Add Odoo XML-RPC client helper for BL carton scripts"
```

---

## Task 2: Créer le champ `x_carton_capacity` sur product.template

**Files:**
- Create: `scripts/odoo/step01_create_carton_field.py`

- [ ] **Step 1: Écrire le script de création du champ**

Créer `scripts/odoo/step01_create_carton_field.py` :

```python
"""Create custom field x_carton_capacity on product.template.

Idempotent: if the field already exists, does nothing.
"""
from scripts.odoo._client import execute, search, create

FIELD_NAME = "x_carton_capacity"
MODEL_NAME = "product.template"


def main():
    # Find model id
    model_ids = search("ir.model", [("model", "=", MODEL_NAME)])
    if not model_ids:
        raise RuntimeError(f"Model {MODEL_NAME} not found")
    model_id = model_ids[0]

    # Check if field already exists
    existing = search("ir.model.fields",
                      [("model", "=", MODEL_NAME), ("name", "=", FIELD_NAME)])
    if existing:
        print(f"Field {FIELD_NAME} already exists (id={existing[0]}), skipping")
        return

    # Create field
    field_id = create("ir.model.fields", {
        "name": FIELD_NAME,
        "field_description": "Capacité carton (unités)",
        "model_id": model_id,
        "ttype": "integer",
        "help": "Nombre d'unités par carton d'expédition. 0 = pas de carton défini.",
    })
    print(f"Created field {FIELD_NAME} (id={field_id}) on {MODEL_NAME}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Exécuter le script**

```bash
cd d:/be-yours-mylab && python -m scripts.odoo.step01_create_carton_field
```

Expected : `Created field x_carton_capacity (id=XXXX) on product.template`. Si relancé : `Field x_carton_capacity already exists (id=XXXX), skipping`.

- [ ] **Step 3: Vérifier dans l'UI Odoo**

Ouvrir https://odoo.startec-paris.com, aller sur un produit, ouvrir Mode Développeur → onglet "Champs". Chercher `x_carton_capacity`. Le champ doit exister.

- [ ] **Step 4: Commit**

```bash
git add scripts/odoo/step01_create_carton_field.py
git commit -m "Add script to create x_carton_capacity field on product.template"
```

---

## Task 3: Initialiser x_carton_capacity par parsing des noms produits

**Files:**
- Create: `scripts/odoo/step02_init_carton_capacity.py`
- Create (log output): `scripts/odoo/init_carton_capacity.csv`

- [ ] **Step 1: Écrire le script d'initialisation**

Créer `scripts/odoo/step02_init_carton_capacity.py` :

```python
"""Initialize x_carton_capacity on all products from name parsing.

Mapping:
- 50ml sérum/huile           -> 50
- 200ml masque               -> 24
- 400ml masque               -> 24
- 200ml shampoing/crème      -> 40
- 500ml shampoing/crème      -> 23
- 1000ml shampoing/masque    -> 12
- autres (pack, coffret...)  -> 0

Writes a CSV log for manual review.
"""
import csv
import re
from pathlib import Path
from scripts.odoo._client import search_read, write

OUT_CSV = Path("scripts/odoo/init_carton_capacity.csv")


def detect_capacity(name: str) -> tuple[int, str]:
    """Return (capacity, reason) based on product name."""
    n = name.lower()

    # Size detection
    has_50ml = bool(re.search(r"\b50\s*ml\b", n))
    has_200ml = bool(re.search(r"\b200\s*ml\b", n))
    has_400ml = bool(re.search(r"\b400\s*ml\b", n))
    has_500ml = bool(re.search(r"\b500\s*ml\b", n))
    has_1l = bool(re.search(r"\b(1000\s*ml|1\s*l)\b", n))

    # Type detection (keyword match)
    is_masque = "masque" in n
    is_serum_huile = ("sérum" in n or "serum" in n or "huile" in n)
    is_shamp_creme = ("shampoing" in n or "shampooing" in n or
                      "crème" in n or "creme" in n)

    # Exclusions: packs, coffrets, testeurs, duo, trio
    if any(k in n for k in ["pack", "coffret", "testeur", "duo", "trio"]):
        return (0, "exclusion: pack/coffret/testeur/duo/trio")

    if has_50ml and is_serum_huile:
        return (50, "50ml serum/huile")
    if has_200ml and is_masque:
        return (24, "200ml masque")
    if has_400ml and is_masque:
        return (24, "400ml masque")
    if has_200ml and is_shamp_creme:
        return (40, "200ml shampoing/creme")
    if has_500ml and is_shamp_creme:
        return (23, "500ml shampoing/creme")
    if has_1l and (is_shamp_creme or is_masque):
        return (12, "1L shampoing/creme/masque")

    return (0, "no rule matched")


def main():
    products = search_read("product.template",
                           [("sale_ok", "=", True)],
                           ["id", "name", "default_code", "x_carton_capacity"])
    print(f"Loaded {len(products)} products")

    rows = []
    to_update_by_capacity: dict[int, list[int]] = {}

    for p in products:
        cap, reason = detect_capacity(p["name"])
        current = p.get("x_carton_capacity") or 0
        changed = (cap != current)
        rows.append({
            "id": p["id"],
            "sku": p.get("default_code") or "",
            "name": p["name"],
            "current": current,
            "new": cap,
            "reason": reason,
            "changed": "YES" if changed else "",
        })
        if changed:
            to_update_by_capacity.setdefault(cap, []).append(p["id"])

    # Write CSV log
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "sku", "name", "current",
                                          "new", "reason", "changed"])
        w.writeheader()
        w.writerows(rows)
    print(f"Log written: {OUT_CSV}")

    # Batch updates
    for cap, ids in to_update_by_capacity.items():
        write("product.template", ids, {"x_carton_capacity": cap})
        print(f"  Set capacity={cap} on {len(ids)} products")

    # Summary
    counts = {}
    for r in rows:
        counts[r["new"]] = counts.get(r["new"], 0) + 1
    print("\nSummary:")
    for cap in sorted(counts):
        print(f"  capacity={cap}: {counts[cap]} products")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Exécuter le script**

```bash
cd d:/be-yours-mylab && python -m scripts.odoo.step02_init_carton_capacity
```

Expected : sortie listant les updates par capacité + résumé. Fichier `scripts/odoo/init_carton_capacity.csv` créé.

- [ ] **Step 3: Ouvrir le CSV et vérifier manuellement**

Ouvrir `scripts/odoo/init_carton_capacity.csv` dans Excel/LibreOffice. Filtrer sur `new=0` et parcourir pour vérifier que tous les produits "hors carton" sont bien des packs/coffrets/testeurs. Si un produit normal est en `0`, noter son ID pour correction manuelle à la Task 4.

- [ ] **Step 4: Commit le script + le log CSV**

```bash
git add scripts/odoo/step02_init_carton_capacity.py scripts/odoo/init_carton_capacity.csv
git commit -m "Init x_carton_capacity on all products from name parsing"
```

---

## Task 4: Corrections manuelles des exceptions

**Files:** aucun (action dans l'UI Odoo).

- [ ] **Step 1: Pour chaque produit mal classé identifié à la Task 3**

Ouvrir le produit dans Odoo (URL directe : `https://odoo.startec-paris.com/web#id=<product_id>&model=product.template&view_type=form`).

Mode développeur activé → onglet "Information" → chercher champ "Capacité carton (unités)" → saisir la valeur correcte.

- [ ] **Step 2: Enregistrer**

Cliquer sur "Enregistrer" (ou Ctrl+S).

- [ ] **Step 3: Documenter les corrections dans un fichier**

Créer ou éditer `scripts/odoo/carton_capacity_corrections.md` avec la liste des exceptions corrigées manuellement (pour traçabilité future si on relance le script d'init).

Exemple :
```markdown
# Corrections manuelles x_carton_capacity

## 2026-04-17
- Product ID 1234 "Sérum Or 50ml Edition Limitée" : forcé à 50 (nom non standard)
- Product ID 5678 "Shampoing Solide 200g" : forcé à 0 (format différent, pas un carton)
```

- [ ] **Step 4: Commit**

```bash
git add scripts/odoo/carton_capacity_corrections.md
git commit -m "Document manual carton_capacity corrections"
```

---

## Task 5: Créer le code Python de l'action serveur

**Files:**
- Create: `scripts/odoo/server_action_code.py`

Ce fichier contient le code Python qui sera exécuté côté Odoo comme action serveur. Il est maintenu en fichier séparé pour la lisibilité — le script `step03_create_server_action.py` le lira et l'enverra à Odoo comme chaîne de caractères.

- [ ] **Step 1: Écrire le code de l'action serveur**

Créer `scripts/odoo/server_action_code.py` :

```python
"""
Code exécuté par l'action serveur "Répartir en cartons".

Contexte d'exécution Odoo (variables disponibles) :
- env : odoo.api.Environment
- records : recordset de stock.picking sélectionné
- model : env['stock.picking']
- log(message) : logger helper

Ce fichier est le contenu du champ 'code' de ir.actions.server.
Odoo l'exécute avec exec() dans un scope limité.
"""

# === LABELS DES FAMILLES ===
FAMILY_LABELS = {
    50: "50ml sérum/huile",
    40: "200ml crème/shampoing",
    24: "200/400ml masque",
    23: "500ml crème/shampoing",
    12: "1L shampoing/masque",
}


def family_label(capacity):
    return FAMILY_LABELS.get(capacity, f"Carton {capacity}u")


def purge_existing_packages(picking):
    """Remove previous auto-generated packages for this picking."""
    auto_package_prefix = "Carton "
    # Find packages referenced by this picking's move lines
    pkg_ids = set()
    for ml in picking.move_line_ids:
        if ml.result_package_id:
            pkg_ids.add(ml.result_package_id.id)
    # Unlink move line -> package
    picking.move_line_ids.write({"result_package_id": False})
    # Delete packages that have our auto-prefix AND are now orphan
    if pkg_ids:
        packages = env["stock.quant.package"].browse(list(pkg_ids))
        for pkg in packages:
            if pkg.name and pkg.name.startswith(auto_package_prefix):
                if not pkg.quant_ids:  # orphan = no quants
                    pkg.unlink()


def split_move_line(ml, qty_to_split):
    """Split a move line: reduce current qty, return a new move line with qty_to_split."""
    remaining = ml.qty_done - qty_to_split
    new_ml = ml.copy({
        "qty_done": qty_to_split,
        "result_package_id": False,
    })
    ml.qty_done = remaining
    return new_ml


def allocate_family(picking, capacity, move_lines, carton_counter):
    """Allocate move lines of one family into cartons. Returns list of package ids created."""
    if capacity == 0:
        # Family "Divers" : one single package for everything
        pkg = env["stock.quant.package"].create({
            "name": f"Carton {carton_counter[0]} - Divers",
        })
        for ml in move_lines:
            ml.result_package_id = pkg.id
        carton_counter[0] += 1
        return [pkg.id]

    label = family_label(capacity)
    total_units = sum(ml.qty_done for ml in move_lines)
    nb_full = int(total_units // capacity)
    remainder = int(total_units % capacity)
    nb_cartons = nb_full + (1 if remainder else 0)

    created_pkgs = []
    # Sequential fill
    current_pkg = None
    current_pkg_units = 0
    # Work on a list we can mutate (splits append new items)
    ml_list = list(move_lines)
    i = 0
    while i < len(ml_list):
        ml = ml_list[i]
        qty = ml.qty_done
        if qty <= 0:
            i += 1
            continue
        if current_pkg is None or current_pkg_units >= capacity:
            # Open new package
            current_pkg = env["stock.quant.package"].create({
                "name": f"Carton {carton_counter[0]} - {label}",
            })
            created_pkgs.append(current_pkg.id)
            current_pkg_units = 0
            carton_counter[0] += 1
        space = capacity - current_pkg_units
        if qty <= space:
            ml.result_package_id = current_pkg.id
            current_pkg_units += qty
            i += 1
        else:
            # Need to split: fill current carton, queue remainder
            new_ml = split_move_line(ml, space)
            new_ml.result_package_id = current_pkg.id
            current_pkg_units += space
            # ml still has (qty - space), continue in next iteration with same i
    return created_pkgs


def rename_packages_with_total(package_ids, carton_counter):
    """Rename packages to include X/Y suffix."""
    total = carton_counter[0] - 1
    packages = env["stock.quant.package"].browse(package_ids)
    for pkg in packages:
        # Name format: "Carton N - <label>" -> "Carton N/total - <label>"
        parts = pkg.name.split(" - ", 1)
        if len(parts) == 2 and parts[0].startswith("Carton "):
            idx = parts[0].replace("Carton ", "").strip()
            pkg.name = f"Carton {idx}/{total} - {parts[1]}"


# === MAIN ===
for picking in records:
    # 1. Purge
    purge_existing_packages(picking)

    # 2. Group move lines by capacity
    groups = {}
    for ml in picking.move_line_ids:
        cap = ml.product_id.x_carton_capacity or 0
        groups.setdefault(cap, []).append(ml)

    # 3. Allocate per family (sorted: real families first, Divers last)
    carton_counter = [1]  # list for mutability across helper calls
    all_created_pkgs = []
    sorted_caps = sorted(groups.keys(), key=lambda c: (c == 0, c))
    for cap in sorted_caps:
        pkgs = allocate_family(picking, cap, groups[cap], carton_counter)
        all_created_pkgs.extend(pkgs)

    # 4. Rename with total count
    rename_packages_with_total(all_created_pkgs, carton_counter)
```

- [ ] **Step 2: Commit**

```bash
git add scripts/odoo/server_action_code.py
git commit -m "Add Python code for 'Répartir en cartons' server action"
```

---

## Task 6: Déployer l'action serveur vers Odoo

**Files:**
- Create: `scripts/odoo/step03_create_server_action.py`

- [ ] **Step 1: Écrire le script de déploiement**

Créer `scripts/odoo/step03_create_server_action.py` :

```python
"""Create (or update) the 'Répartir en cartons' server action on stock.picking."""
from pathlib import Path
from scripts.odoo._client import execute, search, create, write

ACTION_NAME = "Répartir en cartons"
MODEL_NAME = "stock.picking"
CODE_FILE = Path("scripts/odoo/server_action_code.py")


def main():
    # Find model id
    model_ids = search("ir.model", [("model", "=", MODEL_NAME)])
    if not model_ids:
        raise RuntimeError(f"Model {MODEL_NAME} not found")
    model_id = model_ids[0]

    # Read code
    if not CODE_FILE.exists():
        raise FileNotFoundError(CODE_FILE)
    code = CODE_FILE.read_text(encoding="utf-8")

    values = {
        "name": ACTION_NAME,
        "model_id": model_id,
        "state": "code",
        "code": code,
        "binding_model_id": model_id,
        "binding_type": "action",
    }

    # Idempotent: find by name+model
    existing = search("ir.actions.server",
                      [("name", "=", ACTION_NAME), ("model_id", "=", model_id)])
    if existing:
        write("ir.actions.server", existing, values)
        print(f"Updated server action id={existing[0]}")
    else:
        new_id = create("ir.actions.server", values)
        print(f"Created server action id={new_id}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Exécuter le script**

```bash
cd d:/be-yours-mylab && python -m scripts.odoo.step03_create_server_action
```

Expected : `Created server action id=XXX` (ou `Updated...` si relancé).

- [ ] **Step 3: Vérifier dans l'UI Odoo**

Aller sur Paramètres → Technique → Actions → Actions serveur. Chercher "Répartir en cartons". Le code doit correspondre au fichier local.

- [ ] **Step 4: Commit**

```bash
git add scripts/odoo/step03_create_server_action.py
git commit -m "Add script to deploy 'Répartir en cartons' server action"
```

---

## Task 7: Test manuel de l'action serveur

**Files:** aucun (action dans l'UI Odoo).

- [ ] **Step 1: Créer un picking test dans Odoo**

Inventaire → Transferts → Nouveau. Remplir :
- Type d'opération : Livraison (outgoing)
- Partenaire : un client test
- Ajouter 3 lignes :
  - 46 × shampoing nourrissant 200ml
  - 30 × crème hydratante 200ml
  - 6 × masque nourrissant 1000ml (ou équivalent 1L)
- Confirmer → Marquer comme fait (Réserver et Valider ne sont pas forcément nécessaires ; on a besoin que les move lines existent).

Noter l'ID du picking (visible dans l'URL).

- [ ] **Step 2: Lancer l'action "Répartir en cartons"**

Sur le picking, menu Action (roue crantée) → "Répartir en cartons".

- [ ] **Step 3: Vérifier les packages créés**

Onglet "Opérations détaillées" (ou en bas de la fiche picking) → vérifier la colonne "Colis destination" :
- 40 × shampoing → "Carton 1/3 - 200ml crème/shampoing"
- 6 × shampoing + 30 × crème → "Carton 2/3 - 200ml crème/shampoing"
- 6 × masque → "Carton 3/3 - 1L shampoing/masque"

- [ ] **Step 4: Test d'idempotence**

Relancer l'action. Résultat attendu : les mêmes 3 packages (purge + recréation), pas 6.

- [ ] **Step 5: Test d'édition manuelle**

Dans "Opérations détaillées", déplacer manuellement 1 unité du carton 1 vers le carton 3 (changer le `result_package_id`). Enregistrer. Vérifier que le changement tient. (Pas besoin de relancer l'action — l'édition manuelle remplace.)

- [ ] **Step 6: Si erreur**

Si l'action échoue, noter le traceback complet (visible dans la popup d'erreur Odoo ou les logs VPS). Causes probables :
- Picking pas en état `assigned` ou `done` → les `move_line_ids` sont vides, rien à répartir.
- `qty_done = 0` sur toutes les lignes → aucune unité à répartir.
- Produit avec capacité non renseignée → va en "Divers" (normal).

- [ ] **Step 7: Commit (pas de fichier, mais marquer validation)**

Ajouter une note dans le CHANGELOG du projet (ou dans un commit empty) :

```bash
git commit --allow-empty -m "Manual QA: action 'Répartir en cartons' validated on test picking"
```

---

## Task 8: Créer le template QWeb du BL

**Files:**
- Create: `scripts/odoo/templates/bl_deliveryslip.xml`

- [ ] **Step 1: Écrire le template QWeb**

Créer `scripts/odoo/templates/bl_deliveryslip.xml` :

```xml
<?xml version="1.0" encoding="UTF-8"?>
<t t-name="mylab.report_deliveryslip_document">
    <t t-call="web.external_layout">
        <t t-set="doc" t-value="doc.with_context(lang=doc.partner_id.lang or 'fr_FR')"/>
        <div class="page" style="font-family: 'DM Sans', sans-serif; font-size: 9pt; color: #1a1a1a;">

            <!-- ========== HEADER ========== -->
            <div style="display: flex; justify-content: space-between; border-bottom: 2pt solid #c9a96e; padding-bottom: 8pt; margin-bottom: 10pt;">
                <div>
                    <h2 style="margin: 0; color: #1a1a1a; font-family: 'Cormorant Garamond', serif;">Bon de livraison</h2>
                    <div style="font-size: 11pt; font-weight: bold;"><span t-field="doc.name"/></div>
                    <div t-if="doc.origin">Réf. commande : <span t-field="doc.origin"/></div>
                    <div t-if="doc.scheduled_date">Date expédition : <span t-field="doc.scheduled_date" t-options="{'widget': 'date'}"/></div>
                </div>
                <div style="text-align: right;">
                    <div><strong>Client</strong></div>
                    <div t-field="doc.partner_id" t-options="{'widget': 'contact', 'fields': ['name', 'address'], 'no_marker': true}"/>
                </div>
            </div>

            <!-- ========== SUMMARY BADGE ========== -->
            <t t-set="packages" t-value="doc.move_line_ids.mapped('result_package_id')"/>
            <t t-set="nb_cartons" t-value="len(packages)"/>
            <t t-set="total_weight" t-value="sum(ml.product_id.weight * ml.qty_done for ml in doc.move_line_ids)"/>
            <div style="background: #1a1a1a; color: #c9a96e; padding: 6pt 10pt; border-radius: 3pt; display: inline-block; margin-bottom: 12pt; font-weight: bold;">
                <span t-esc="nb_cartons"/> cartons — <span t-esc="'%.2f' % total_weight"/> kg
                <span t-if="doc.carrier_id"> — <t t-esc="doc.carrier_id.name"/></span>
            </div>

            <!-- ========== SECTION 1: RECAP PRODUITS ========== -->
            <h3 style="color: #1a1a1a; font-family: 'Cormorant Garamond', serif; margin-top: 8pt; margin-bottom: 4pt;">Récapitulatif produits</h3>
            <table style="width: 100%; border-collapse: collapse; font-size: 9pt;">
                <thead>
                    <tr style="background: #f5f0e6; border-bottom: 1pt solid #c9a96e;">
                        <th style="text-align: left; padding: 4pt;">Référence</th>
                        <th style="text-align: left; padding: 4pt;">Désignation</th>
                        <th style="text-align: right; padding: 4pt;">Qté</th>
                        <th style="text-align: right; padding: 4pt;">Poids unit.</th>
                        <th style="text-align: right; padding: 4pt;">Poids total</th>
                    </tr>
                </thead>
                <tbody>
                    <!-- Aggregate per product -->
                    <t t-set="agg" t-value="{}"/>
                    <t t-foreach="doc.move_line_ids" t-as="ml">
                        <t t-set="pid" t-value="ml.product_id.id"/>
                        <t t-if="pid not in agg">
                            <t t-set="ignored" t-value="agg.update({pid: {'sku': ml.product_id.default_code or '', 'name': ml.product_id.name, 'qty': 0, 'weight': ml.product_id.weight or 0}})"/>
                        </t>
                        <t t-set="ignored" t-value="agg[pid].update({'qty': agg[pid]['qty'] + ml.qty_done})"/>
                    </t>
                    <t t-foreach="agg.values()" t-as="row">
                        <tr style="border-bottom: 0.5pt solid #e5e0d0;">
                            <td style="padding: 3pt 4pt;"><span t-esc="row['sku']"/></td>
                            <td style="padding: 3pt 4pt;"><span t-esc="row['name']"/></td>
                            <td style="padding: 3pt 4pt; text-align: right;"><span t-esc="int(row['qty'])"/></td>
                            <td style="padding: 3pt 4pt; text-align: right;"><span t-esc="'%.2f' % row['weight']"/> kg</td>
                            <td style="padding: 3pt 4pt; text-align: right;"><span t-esc="'%.2f' % (row['qty'] * row['weight'])"/> kg</td>
                        </tr>
                    </t>
                </tbody>
                <tfoot>
                    <tr style="border-top: 1pt solid #1a1a1a; font-weight: bold;">
                        <td colspan="2" style="padding: 4pt;">Total</td>
                        <td style="padding: 4pt; text-align: right;"><t t-esc="int(sum(r['qty'] for r in agg.values()))"/></td>
                        <td></td>
                        <td style="padding: 4pt; text-align: right;"><t t-esc="'%.2f' % total_weight"/> kg</td>
                    </tr>
                </tfoot>
            </table>

            <!-- ========== SECTION 2: DETAIL PAR CARTON ========== -->
            <h3 style="color: #1a1a1a; font-family: 'Cormorant Garamond', serif; margin-top: 14pt; margin-bottom: 4pt;">Détail par carton</h3>

            <t t-foreach="packages" t-as="pkg">
                <t t-set="pkg_mls" t-value="doc.move_line_ids.filtered(lambda m: m.result_package_id.id == pkg.id)"/>
                <t t-set="pkg_units" t-value="int(sum(ml.qty_done for ml in pkg_mls))"/>
                <t t-set="pkg_weight" t-value="sum(ml.qty_done * (ml.product_id.weight or 0) for ml in pkg_mls)"/>
                <t t-set="pkg_capacity" t-value="pkg_mls and (pkg_mls[0].product_id.x_carton_capacity or 0) or 0"/>
                <div style="border: 0.5pt solid #c9a96e; margin-bottom: 5pt; page-break-inside: avoid;">
                    <div style="background: #1a1a1a; color: #c9a96e; padding: 3pt 6pt; display: flex; justify-content: space-between; font-weight: bold; font-size: 10pt;">
                        <span>☐ <t t-esc="pkg.name"/></span>
                        <span>
                            <t t-if="pkg_capacity &gt; 0"><t t-esc="pkg_units"/>/<t t-esc="pkg_capacity"/></t>
                            <t t-if="pkg_capacity == 0"><t t-esc="pkg_units"/> unités</t>
                            — <t t-esc="'%.2f' % pkg_weight"/> kg
                        </span>
                    </div>
                    <div style="padding: 3pt 8pt;">
                        <t t-foreach="pkg_mls" t-as="ml">
                            <div>• <t t-esc="ml.product_id.name"/> ×<t t-esc="int(ml.qty_done)"/></div>
                        </t>
                    </div>
                </div>
            </t>

            <!-- ========== SIGNATURE ========== -->
            <div style="margin-top: 20pt; border: 0.5pt solid #1a1a1a; padding: 8pt; font-size: 9pt;">
                <div><strong>Reçu en bon état par :</strong> ____________________________</div>
                <div style="margin-top: 6pt;"><strong>Date :</strong> ________________ &#160;&#160;&#160; <strong>Signature :</strong></div>
                <div style="height: 28pt;"></div>
            </div>

        </div>
    </t>
</t>
```

- [ ] **Step 2: Commit**

```bash
git add scripts/odoo/templates/bl_deliveryslip.xml
git commit -m "Add QWeb template for MyLab carton-aware delivery slip"
```

---

## Task 9: Déployer le template PDF et son action report

**Files:**
- Create: `scripts/odoo/step04_create_bl_report.py`

- [ ] **Step 1: Écrire le script de déploiement**

Créer `scripts/odoo/step04_create_bl_report.py` :

```python
"""Create/update the QWeb view and ir.actions.report for MyLab BL."""
from pathlib import Path
from scripts.odoo._client import search, create, write

VIEW_NAME = "mylab.report_deliveryslip_document"
VIEW_KEY = "mylab.report_deliveryslip_document"
REPORT_NAME = "Bon de livraison MyLab"
REPORT_FILENAME = "BL_${object.name}.pdf"
TEMPLATE_FILE = Path("scripts/odoo/templates/bl_deliveryslip.xml")


def main():
    # 1. Read template XML
    arch = TEMPLATE_FILE.read_text(encoding="utf-8")

    # 2. Upsert ir.ui.view (QWeb template)
    view_values = {
        "name": VIEW_NAME,
        "type": "qweb",
        "arch_base": arch,
        "key": VIEW_KEY,
    }
    existing_view = search("ir.ui.view", [("key", "=", VIEW_KEY)])
    if existing_view:
        write("ir.ui.view", existing_view, {"arch_base": arch})
        view_id = existing_view[0]
        print(f"Updated QWeb view id={view_id}")
    else:
        view_id = create("ir.ui.view", view_values)
        print(f"Created QWeb view id={view_id}")

    # 3. Find stock.picking model id
    model_ids = search("ir.model", [("model", "=", "stock.picking")])
    model_id = model_ids[0]

    # 4. Upsert ir.actions.report
    report_values = {
        "name": REPORT_NAME,
        "model": "stock.picking",
        "report_type": "qweb-pdf",
        "report_name": VIEW_KEY,
        "report_file": VIEW_KEY,
        "binding_model_id": model_id,
        "binding_type": "report",
        "print_report_name": f"'BL - ' + object.name",
    }
    existing_report = search("ir.actions.report",
                             [("report_name", "=", VIEW_KEY)])
    if existing_report:
        write("ir.actions.report", existing_report, report_values)
        print(f"Updated report action id={existing_report[0]}")
    else:
        new_id = create("ir.actions.report", report_values)
        print(f"Created report action id={new_id}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Exécuter le script**

```bash
cd d:/be-yours-mylab && python -m scripts.odoo.step04_create_bl_report
```

Expected : `Created QWeb view id=XXX` et `Created report action id=XXX`.

- [ ] **Step 3: Tester l'impression PDF depuis Odoo**

Ouvrir le picking test (de la Task 7) → menu "Imprimer" → "Bon de livraison MyLab". Vérifier :
- Le PDF se génère sans erreur
- L'en-tête affiche bien client + numéro BL + badge cartons
- Le récap produits totalise correctement
- Chaque carton a son bloc avec titre noir/or + liste produits
- Le cadre signature est en bas
- Pas de coupure de carton entre 2 pages

- [ ] **Step 4: Si erreur de rendu**

Logs wkhtmltopdf : accessible via les logs Odoo sur le VPS. Erreurs courantes :
- Variable non définie dans QWeb → vérifier la syntaxe `t-esc` vs `t-field`
- Division par zéro → ajouter des gardes `t-if`

Éditer `scripts/odoo/templates/bl_deliveryslip.xml`, relancer le script de déploiement, retester.

- [ ] **Step 5: Commit**

```bash
git add scripts/odoo/step04_create_bl_report.py
git commit -m "Deploy QWeb view + report action for MyLab BL"
```

---

## Task 10: Ajouter le bouton "Répartir en cartons" dans la vue picking

**Files:**
- Create: `scripts/odoo/step05_add_picking_button.py`

- [ ] **Step 1: Écrire le script**

Créer `scripts/odoo/step05_add_picking_button.py` :

```python
"""Add 'Répartir en cartons' button to stock.picking form view."""
from scripts.odoo._client import search, create, write

VIEW_NAME = "mylab.picking_form_carton_button"
VIEW_KEY = "mylab.picking_form_carton_button"
SERVER_ACTION_NAME = "Répartir en cartons"


def main():
    # Find parent view
    parent = search("ir.ui.view", [("xml_id", "=", "stock.view_picking_form")])
    # Fallback: search by name
    if not parent:
        parent = search("ir.ui.view",
                        [("name", "=", "stock.picking.form"),
                         ("model", "=", "stock.picking")])
    if not parent:
        raise RuntimeError("Parent view stock.view_picking_form not found")
    parent_id = parent[0]

    # Find server action
    sa_ids = search("ir.actions.server",
                    [("name", "=", SERVER_ACTION_NAME),
                     ("binding_model_id.model", "=", "stock.picking")])
    if not sa_ids:
        raise RuntimeError(f"Server action '{SERVER_ACTION_NAME}' not found — run task 6 first")
    sa_id = sa_ids[0]

    arch = f"""<data>
    <xpath expr="//header" position="inside">
        <button name="{sa_id}" type="action"
                string="Répartir en cartons"
                class="btn-primary"
                invisible="state not in ('assigned','done')"/>
    </xpath>
</data>"""

    view_values = {
        "name": VIEW_NAME,
        "type": "form",
        "model": "stock.picking",
        "inherit_id": parent_id,
        "arch_base": arch,
        "key": VIEW_KEY,
    }
    existing = search("ir.ui.view", [("key", "=", VIEW_KEY)])
    if existing:
        write("ir.ui.view", existing, {"arch_base": arch})
        print(f"Updated inherited view id={existing[0]}")
    else:
        new_id = create("ir.ui.view", view_values)
        print(f"Created inherited view id={new_id}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Exécuter**

```bash
cd d:/be-yours-mylab && python -m scripts.odoo.step05_add_picking_button
```

Expected : `Created inherited view id=XXX`.

- [ ] **Step 3: Recharger la page Odoo et vérifier le bouton**

Ouvrir un picking en état "Assigné" ou "Fait". Le bouton "Répartir en cartons" doit apparaître en haut de la fiche (header).

- [ ] **Step 4: Commit**

```bash
git add scripts/odoo/step05_add_picking_button.py
git commit -m "Add 'Répartir en cartons' button to picking form"
```

---

## Task 11: Test end-to-end sur un picking réel

**Files:** aucun.

- [ ] **Step 1: Créer une vraie commande test**

Soit : devis Odoo → confirmer → le picking est créé automatiquement.
Soit : commande Shopify test → sync → picking créé.

Composition recommandée pour tester les cas d'usage :
- 60 × shampoing 200ml (1.5 cartons → 1 plein + 1 partiel)
- 18 × masque 400ml (moins d'un carton)
- 24 × shampoing 1000ml (2 cartons pleins)
- 1 × coffret découverte (famille Divers)

- [ ] **Step 2: Sur le picking en état "Assigné"**

Cliquer "Répartir en cartons" (bouton header). Vérifier la numérotation correcte des cartons et la bonne affectation.

- [ ] **Step 3: Simuler une édition manuelle**

Dans les opérations détaillées, déplacer 1 unité d'un carton à un autre via le champ Colis.

- [ ] **Step 4: Imprimer le BL**

Bouton Imprimer → Bon de livraison MyLab. Télécharger le PDF.

- [ ] **Step 5: Checklist visuelle sur le PDF**

- [ ] En-tête complet (numéro BL, client, date, référence commande)
- [ ] Badge "N cartons — X kg" visible
- [ ] Tableau récap avec tous les produits + totaux corrects
- [ ] Un bloc par carton avec numéro X/Y, famille, case à cocher
- [ ] Poids par carton cohérent avec les produits listés
- [ ] Aucun carton coupé entre 2 pages
- [ ] Cadre signature en bas
- [ ] Footer société (adresse, SIRET, TVA) visible

- [ ] **Step 6: Si bugs**

Noter dans un fichier `docs/superpowers/specs/2026-04-17-odoo-bon-livraison-cartons-feedback.md` :
- Écrans de captures avant/après
- Corrections nécessaires
- Priorités (bloquant vs cosmétique)

Ne pas chercher à tout corriger maintenant : on valide d'abord le workflow, les ajustements layout feront l'objet d'itérations Task 13+.

- [ ] **Step 7: Commit marquant validation E2E**

```bash
git commit --allow-empty -m "E2E test: BL carton workflow validated on real picking"
```

---

## Task 12: Documenter dans CLAUDE.md et README scripts

**Files:**
- Modify: `CLAUDE.md`
- Create: `scripts/odoo/README.md`

- [ ] **Step 1: Créer `scripts/odoo/README.md`**

```markdown
# Scripts Odoo MyLab

Scripts Python XML-RPC pour customisations Odoo (déploiement de champs, actions, vues, reports).

## Prérequis
- Python 3.11+
- `pip install python-dotenv`
- `.env.local` (dans le repo mylab-configurateur) avec `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_API_KEY`

## Ordre d'exécution (first-time setup du BL cartons)

```bash
# 1. Créer le champ x_carton_capacity
python -m scripts.odoo.step01_create_carton_field

# 2. Initialiser les valeurs depuis les noms produits
python -m scripts.odoo.step02_init_carton_capacity
# → ouvrir scripts/odoo/init_carton_capacity.csv pour vérif manuelle
# → corriger exceptions dans l'UI Odoo

# 3. Déployer l'action serveur
python -m scripts.odoo.step03_create_server_action

# 4. Déployer le template PDF + action report
python -m scripts.odoo.step04_create_bl_report

# 5. Ajouter le bouton dans la vue picking
python -m scripts.odoo.step05_add_picking_button
```

Tous les scripts sont **idempotents** : relançables sans effet de bord.

## Fichiers de code

- `_client.py` : helper XML-RPC partagé
- `server_action_code.py` : code Python de l'action "Répartir en cartons" (lu par 03_)
- `templates/bl_deliveryslip.xml` : source QWeb du BL (lu par 04_)

Pour modifier l'action ou le template, éditer le fichier source puis relancer le script de déploiement correspondant.
```

- [ ] **Step 2: Ajouter une section dans `CLAUDE.md`**

Éditer le fichier `CLAUDE.md` à la racine du repo. Ajouter une section après "## Key conventions" :

```markdown
## Odoo customizations

Des scripts Python XML-RPC pour déployer des customisations Odoo vivent dans `scripts/odoo/`. Ils couvrent :
- Champ `x_carton_capacity` sur `product.template` (capacité carton par produit)
- Action serveur "Répartir en cartons" sur `stock.picking`
- Template PDF bon de livraison custom avec détail par carton

Voir `scripts/odoo/README.md` pour l'ordre d'exécution. Tous les scripts sont idempotents.
```

- [ ] **Step 3: Commit**

```bash
git add scripts/odoo/README.md CLAUDE.md
git commit -m "Document Odoo BL carton scripts in README and CLAUDE.md"
```

---

## Task 13: Mettre à jour la memory

**Files:**
- Create: `C:/Users/startec/.claude/projects/d--be-yours-mylab/memory/project_odoo_bl_cartons.md`
- Modify: `C:/Users/startec/.claude/projects/d--be-yours-mylab/memory/MEMORY.md`

- [ ] **Step 1: Créer la memory du projet BL cartons**

Path : `C:/Users/startec/.claude/projects/d--be-yours-mylab/memory/project_odoo_bl_cartons.md`

```markdown
---
name: Odoo BL cartons
description: Bon de livraison Odoo customisé avec répartition automatique en cartons (x_carton_capacity + server action + QWeb template)
type: project
---

## Composants déployés dans Odoo

1. **Champ `x_carton_capacity`** (integer) sur `product.template`
   - Valeurs : 50, 40, 24, 23, 12, ou 0 (Divers)
   - Initialisé par script, corrections manuelles documentées dans `scripts/odoo/carton_capacity_corrections.md`

2. **Action serveur "Répartir en cartons"** sur `stock.picking`
   - Code dans `scripts/odoo/server_action_code.py`
   - Déployée via `scripts/odoo/step03_create_server_action.py`
   - Idempotente : purge packages précédents avant recréation

3. **Template QWeb `mylab.report_deliveryslip_document`** + action report "Bon de livraison MyLab"
   - Source dans `scripts/odoo/templates/bl_deliveryslip.xml`
   - Branding noir #1a1a1a / or #c9a96e (cohérent avec template devis ID 1286)

4. **Vue héritée** `mylab.picking_form_carton_button` ajoute le bouton dans le header du picking form

## Familles carton

| Capacité | Produits |
|---:|---|
| 50 | 50ml sérum/huile |
| 40 | 200ml crème/shampoing |
| 24 | 200/400ml masque |
| 23 | 500ml crème/shampoing |
| 12 | 1L shampoing/masque |
| 0 | Divers (packs, coffrets, testeurs) |

**Why:** Les clients B2B ont besoin d'un BL qui reflète la composition physique des cartons pour vérifier la livraison à réception sans recompter l'ensemble. La logistique STARTEC est structurée par conditionnement carton.

**How to apply:** Pour modifier la logique de répartition, éditer `scripts/odoo/server_action_code.py` puis relancer `step03_create_server_action.py`. Pour le layout PDF, éditer `scripts/odoo/templates/bl_deliveryslip.xml` puis relancer `step04_create_bl_report.py`. Spec complet : `docs/superpowers/specs/2026-04-17-odoo-bon-livraison-cartons-design.md`.
```

- [ ] **Step 2: Ajouter l'entrée dans MEMORY.md**

Éditer `C:/Users/startec/.claude/projects/d--be-yours-mylab/memory/MEMORY.md`. Ajouter dans le tableau des topics :

```markdown
| project_odoo_bl_cartons.md | BL Odoo avec répartition auto en cartons, template QWeb custom | 2026-04-17 |
```

- [ ] **Step 3: Pas de commit (memory est hors repo)**

Les fichiers memory sont dans `~/.claude/projects/`, pas dans le repo. Aucun commit git nécessaire.

---

## Self-review

**Couverture du spec :**
- Champ custom `x_carton_capacity` → Task 2 ✓
- Script d'initialisation → Task 3 ✓
- Corrections manuelles → Task 4 ✓
- Action serveur "Répartir en cartons" → Tasks 5 + 6 ✓
- Algorithme de répartition par famille + split séquentiel → Task 5 ✓
- Idempotence de l'action → Task 5 (purge_existing_packages) ✓
- Template PDF avec récap + détail cartons → Tasks 8 + 9 ✓
- Branding noir/or + footer société → Task 8 (styles inline + external_layout) ✓
- Bouton dans la vue picking → Task 10 ✓
- Test E2E → Task 11 ✓
- Documentation → Tasks 12 + 13 ✓

**Scan placeholders :** aucun TBD, TODO, "implement later" ou "handle edge cases" abstrait. Tous les steps montrent du code concret ou des actions UI précises.

**Cohérence des types :** les noms `x_carton_capacity`, `result_package_id`, `move_line_ids`, `mylab.report_deliveryslip_document` sont identiques dans toutes les tasks où ils apparaissent.

**Risques non couverts dans le spec mais présents dans le plan :**
- Task 7 mentionne l'exigence d'état `assigned`/`done` pour que move_line_ids existe (explicite dans le bouton Task 10 via `invisible="state not in..."`).
- Task 11 teste le cas "client Shopify" via sync, qui est une préoccupation explicite du spec.
