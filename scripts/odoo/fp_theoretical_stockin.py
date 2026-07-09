"""Stock theorique depuis le fichier FP Cosmetics (COMMANDE EN COURS FP).

Les quantites FP sont du VRAC en litres. On conditionne theoriquement selon
la repartition 70%/10%/20% -> 200ml / (500ml shampoing|creme, 400ml masque) / 1000ml,
on convertit en bouteilles, et on AJOUTE au stock Odoo actuel (stock virtuel en
attente de l'OF de conditionnement reel).

Stade retenu : OK FABRIQUE + EN COURS DE LIVRAISON uniquement.
Format manquant (pas de SKU) -> sa part est repliee sur le 200ml.

Dry-run par defaut. --apply pour ecrire l'ajustement d'inventaire Odoo.
"""
import sys, re
sys.path.insert(0, "scripts/odoo")
import _client as odoo

APPLY = "--apply" in sys.argv

# FP item -> (famille SKU MyLab, litres fabrique+livraison)  [mappings valides par Yoann]
FP = [
    ("SHP VOLUME",            "shampoing-volume",                100),
    ("SHP HA REPULPE",        "shampoing-ha-repulpe",            200),
    ("SHP GEL DOUCHE",        "shampoing-gel-douche",            200),
    ("MASQUE NOURRISSANT II", "masque-nourrissant",              200),
    ("MASQUE DEFINITION II",  "masque-boucles",                  100),
    ("MASQUE HA REPULPE II",  "masque-ha-repulpe",               200),
    ("MASQUE VOLUME",         "masque-volume",                   100),
    ("MASQUE COLORFIX",       "masque-gloss",                    100),  # gloss = colorfix : SKU absent
    ("MASQUE SPRAY 10 EN 1",  "masque-reparateur-sans-rincage",  200),
    ("CREME DEFINITION",      "creme-boucles",                   300),
    ("CREME VOLUME",          "creme-volume",                    100),
]

# Catalogue : famille -> {format_ml: (sku, qty_actuelle)}
CONT = re.compile(r"-(\d+)-ml$")
rows = odoo.search_read("product.product", [("is_storable", "=", True)],
                        ["default_code", "qty_available"], limit=2000)
fam = {}
for r in rows:
    sku = (r.get("default_code") or "").strip()
    m = CONT.search(sku) if sku else None
    if m:
        fam.setdefault(CONT.sub("", sku), {})[int(m.group(1))] = (sku, int(r.get("qty_available") or 0))

adjust = {}  # sku -> (qty_actuelle, qty_ajoutee)
print(f"{'Produit FP':<22} {'Format':<8} {'SKU':<40} {'Actuel':>7} {'+Theo':>7} {'=New':>7}")
for label, base, litres in FP:
    formats = fam.get(base)
    if not formats:
        print(f"{label:<22} -- SKU '{base}-*' ABSENT du catalogue (a creer / mapping a revoir) --")
        continue
    mid = 400 if base.startswith("masque") else 500
    plan = {200: 0.70, mid: 0.10, 1000: 0.20}
    litres200 = 0.0
    add = {}
    for size, pct in plan.items():
        part = litres * pct
        if size != 200 and size in formats:
            add[size] = part / (size / 1000.0)
        else:
            litres200 += part  # 200ml ou format manquant -> repli sur 200ml
    add[200] = add.get(200, 0) + litres200 / 0.2
    for size in sorted(add):
        if size not in formats:
            continue
        sku, cur = formats[size]
        a = int(round(add[size]))
        adjust[sku] = (cur, a)
        print(f"{label:<22} {str(size)+'ml':<8} {sku:<40} {cur:>7} {a:>+7} {cur+a:>7}")

print(f"\n{len(adjust)} SKU a ajuster.")
if not APPLY:
    print("DRY RUN : aucune ecriture Odoo. --apply pour appliquer.")
    sys.exit(0)

# APPLY : stock theorique dans un LOT dedie 'THEO-FP-<date>' par produit @ Fini (loc 47).
# - n'altere PAS les lots de production reels (qty_available = lots reels + lot theo)
# - valeur ABSOLUE = ajout (idempotent : re-run reecrit la meme valeur)
# - pattern correct : creer le quant si besoin, PUIS write inventory_quantity
#   (un quant cree avec inventory_quantity garde inventory_quantity_set=False -> apply no-op)
LOC_FINI = 47
THEO_LOT = "THEO-FP-20260617"


def lot_for(pid):
    r = odoo.search_read("stock.lot", [("name", "=", THEO_LOT), ("product_id", "=", pid)], ["id"])
    return r[0]["id"] if r else odoo.create("stock.lot", {"name": THEO_LOT, "product_id": pid})


def set_quant(pid, lot_id, qty):
    domain = [("product_id", "=", pid), ("location_id", "=", LOC_FINI),
              ("lot_id", "=", lot_id or False)]
    q = odoo.search_read("stock.quant", domain, ["id"])
    qid = q[0]["id"] if q else odoo.create(
        "stock.quant", {"product_id": pid, "location_id": LOC_FINI, "lot_id": lot_id or False})
    odoo.write("stock.quant", [qid], {"inventory_quantity": qty})
    odoo.execute("stock.quant", "action_apply_inventory", [qid])
    return qid


# Nettoyage des quants fantomes lot-less crees par la version buguee (quantite 0, lot_id False)
print("\n=== Nettoyage quants fantomes lot-less ===")
pids = {}
for sku in adjust:
    p = odoo.search_read("product.product", [("default_code", "=", sku)], ["id", "tracking"])
    if p:
        pids[sku] = (p[0]["id"], p[0]["tracking"])
phantoms = 0
for sku, (pid, _) in pids.items():
    for q in odoo.search_read("stock.quant",
                              [("product_id", "=", pid), ("location_id", "=", LOC_FINI),
                               ("lot_id", "=", False), ("quantity", "=", 0)],
                              ["id", "inventory_quantity"]):
        # stock.quant non supprimable -> on neutralise le comptage fantome a 0
        odoo.write("stock.quant", [q["id"]], {"inventory_quantity": 0})
        odoo.execute("stock.quant", "action_apply_inventory", [q["id"]])
        phantoms += 1
print(f"  {phantoms} quants fantomes neutralises (inventory_quantity=0)")

# Reset du quant 725 corrompu par le test de debug (shampoing-volume lot 220A526C -> 101)
try:
    odoo.write("stock.quant", [725], {"inventory_quantity": 101})
    odoo.execute("stock.quant", "action_apply_inventory", [725])
    print("  quant 725 (shampoing-volume lot reel) reset a 101")
except Exception as e:
    print("  reset 725:", repr(e)[:120])

print(f"\n=== APPLY : lot theorique {THEO_LOT} @ MYVO/Stock/Fini ===")
ok = 0
for sku, (cur, add) in adjust.items():
    if add == 0 or sku not in pids:
        continue
    pid, tracking = pids[sku]
    lot_id = lot_for(pid) if tracking == "lot" else False
    set_quant(pid, lot_id, add)
    print(f"  [OK] {sku}: lot theo = {add}")
    ok += 1
print(f"\n{ok} ajustements appliques dans Odoo.")
