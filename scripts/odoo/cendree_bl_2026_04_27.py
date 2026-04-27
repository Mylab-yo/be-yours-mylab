"""One-shot : crée 4 SKUs + 2 BL pour CENDREE (partner 1970) — 2026-04-27.

BL #1 (palette, livrée maintenant) :
  - shampoing silver glow 200ml × 1242
  - masque silver care 200ml × 784
  - shampoing hydratant 200ml × 720
  - repair oil 50ml × 100

BL #2 (envoi colis séparé daté 27/04/2026) :
  - shampoing silver glow 200ml × 240 (3 colis × 80)

Prix = 0 (sans pricelist).
Pickings confirmés mais NON validés (à valider manuellement après contrôle physique).
"""
from datetime import date
from scripts.odoo._client import execute, search, search_read, create, write

PARTNER_ID = 1970
COMPANY_ID = 3
TAX_ID = 103         # 20% G
CATEG_ID = 1         # All
UOM_ID = 1           # Units

# -----------------------------------------------------------------------------
# 1. Mise à jour téléphone client
# -----------------------------------------------------------------------------
partner = search_read("res.partner", [("id", "=", PARTNER_ID)],
                     ["name", "phone", "email"])[0]
print(f"Client: {partner['name']} (phone actuel: {partner['phone']})")
if not partner["phone"]:
    write("res.partner", [PARTNER_ID], {"phone": "+33 6 42 73 55 68"})
    print("  → phone ajouté: +33 6 42 73 55 68")

# -----------------------------------------------------------------------------
# 2. Création des 4 SKUs (idempotent : skip si default_code existe déjà)
# -----------------------------------------------------------------------------
NEW_PRODUCTS = [
    {
        "name": "shampoing silver glow 200ml",
        "default_code": "shampoing-silver-glow-200ml",
        "x_carton_capacity": 80,
    },
    {
        "name": "masque silver care 200ml",
        "default_code": "masque-silver-care-200ml",
        "x_carton_capacity": 54,
    },
    {
        "name": "shampoing hydratant 200ml",
        "default_code": "shampoing-hydratant-200ml",
        "x_carton_capacity": 80,
    },
    {
        "name": "repair oil 50ml",
        "default_code": "repair-oil-50ml",
        "x_carton_capacity": 50,
    },
]

product_ids = {}  # default_code -> product.product id

for p in NEW_PRODUCTS:
    existing = search_read("product.product",
                           [("default_code", "=", p["default_code"])],
                           ["id", "name"])
    if existing:
        pid = existing[0]["id"]
        print(f"  ✓ exists  {pid}: {existing[0]['name']}")
    else:
        vals = {
            "name": p["name"],
            "default_code": p["default_code"],
            "type": "consu",              # Odoo 18: "Goods" (ex-storable)
            "is_storable": True,           # Odoo 18: track inventory
            "categ_id": CATEG_ID,
            "uom_id": UOM_ID,
            "uom_po_id": UOM_ID,
            "sale_ok": True,
            "purchase_ok": True,
            "list_price": 0.0,
            "taxes_id": [(6, 0, [TAX_ID])],
            "company_id": COMPANY_ID,
            "x_carton_capacity": p["x_carton_capacity"],
        }
        # product.product.create accepte les champs product.template
        pid = create("product.product", vals)
        print(f"  + created {pid}: {p['name']} (cap={p['x_carton_capacity']})")
    product_ids[p["default_code"]] = pid

# -----------------------------------------------------------------------------
# 3. Création des 2 sale.orders (sans prix)
# -----------------------------------------------------------------------------
def make_so(name_suffix, lines, commitment_date=None):
    """lines = [(product_default_code, qty), ...]"""
    so_vals = {
        "partner_id": PARTNER_ID,
        "company_id": COMPANY_ID,
        "client_order_ref": name_suffix,
        "order_line": [
            (0, 0, {
                "product_id": product_ids[code],
                "product_uom_qty": qty,
                "price_unit": 0.0,
                "tax_id": [(6, 0, [])],     # pas de taxe (BL sans prix)
            })
            for code, qty in lines
        ],
    }
    if commitment_date:
        so_vals["commitment_date"] = commitment_date
    so_id = create("sale.order", so_vals)
    so = search_read("sale.order", [("id", "=", so_id)], ["name"])[0]
    print(f"  + SO {so_id} ({so['name']}) — {name_suffix}")
    # Confirmer
    execute("sale.order", "action_confirm", [[so_id]])
    print(f"    confirmé → picking auto-généré")
    # Récup pickings
    picks = search_read("stock.picking",
                        [("sale_id", "=", so_id)],
                        ["id", "name", "state", "scheduled_date"])
    for pk in picks:
        print(f"    picking {pk['id']}: {pk['name']} state={pk['state']}")
    return so_id, picks

print("\n--- BL #1 (palette) ---")
so1, picks1 = make_so(
    "Palette CENDREE 2026-04-27",
    [
        ("shampoing-silver-glow-200ml", 1242),
        ("masque-silver-care-200ml", 784),
        ("shampoing-hydratant-200ml", 720),
        ("repair-oil-50ml", 100),
    ],
)

print("\n--- BL #2 (envoi colis 27/04) ---")
so2, picks2 = make_so(
    "Envoi colis CENDREE 2026-04-27",
    [
        ("shampoing-silver-glow-200ml", 240),
    ],
    commitment_date="2026-04-27 12:00:00",
)

# -----------------------------------------------------------------------------
# Résumé final
# -----------------------------------------------------------------------------
print("\n" + "=" * 60)
print("RÉSUMÉ")
print("=" * 60)
print(f"Client     : {partner['name']} (id {PARTNER_ID})")
print(f"Produits créés : {list(product_ids.values())}")
print(f"SO #1 (palette)        : {so1} → pickings {[p['id'] for p in picks1]}")
print(f"SO #2 (envoi 27/04)    : {so2} → pickings {[p['id'] for p in picks2]}")
print(f"\nÀ faire dans Odoo :")
print(f"  1. Ouvrir chaque picking, vérifier les quantités")
print(f"  2. Valider (Done) une fois le contrôle physique fait")
print(f"  3. Imprimer BL via ⚙️ breadcrumb → Imprimer → 'Bon de livraison MyLab'")
