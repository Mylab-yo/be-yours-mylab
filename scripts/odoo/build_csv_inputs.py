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
    "spray_reparateur": "shampoings",  # spray texturisant + masque-reparateur-sans-rincage : flacon ambré 200ml
}

# Produits fabriqués en interne (cf spec)
INTERNAL_FORMULAS = {
    "serum",  # tous les sérums (startswith match)
    "huile-a-barbe",
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
    ("huile-a-barbe", "50"): ("BOUTEILLE-VERRE-AMBRE-50", "PIPETTE"),
    ("spray-texturisant", "200"): ("FLACON-AMBRE-200", "PULVERISATEUR-SPRAY"),
    ("masque-reparateur-sans-rincage", "200"): ("FLACON-AMBRE-200", "PULVERISATEUR-SPRAY"),
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
        type_ = data.get("type", "")
        if type_ not in TYPE_TO_FAMILY:
            print(f"  WARNING: type '{type_}' for formula '{key}' not in TYPE_TO_FAMILY, defaulting to 'shampoings'")
        family = TYPE_TO_FAMILY.get(type_, "shampoings")
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
        type_ = data.get("type", "")
        if type_ not in TYPE_TO_FAMILY:
            print(f"  WARNING: type '{type_}' for formula '{key}' not in TYPE_TO_FAMILY, defaulting to 'shampoings'")
        family = TYPE_TO_FAMILY.get(type_, "shampoings")
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
                "finished_sku": f"{key}-{contenance}-ml",  # format Odoo default_code (ex: shampoing-nourrissant-200-ml)
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
    print(f"  wrote {len(rows)} rows -> {path}")


if __name__ == "__main__":
    print("Building CSV inputs from ml-product-map.json...")
    write_csv(ROOT / "data" / "bulk_formulas.csv", build_bulk_formulas())
    write_csv(ROOT / "data" / "finished_to_components.csv", build_finished_to_components())
    print("Done.")
    print("Note: data/packaging_vendors.csv and data/packaging_products.csv exist as templates.")
    print("Edit them to fill in real vendor contacts (TBD@email.fr placeholders) before running step32+.")
