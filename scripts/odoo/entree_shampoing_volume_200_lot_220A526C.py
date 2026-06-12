"""Entree stock : 150 u. de shampoing volume 200ml (variant 2403), lot 220A526C, dans MYVO/Stock/Fini.

Idempotent : si le lot existe deja pour ce produit, on le reutilise ; si un quant existe deja
pour (produit, lot, emplacement), on n'empile pas une 2e fois.
"""
from _client import execute, search, create

PRODUCT_ID = 2403           # shampoing volume 200ml (product.product)
LOCATION_ID = 47            # MYVO/Stock/Fini
LOT_NAME = "220A526C"
QTY = 150.0

# 1. Lot (reuse si deja present pour CE produit)
lot_ids = search("stock.lot", [("name", "=", LOT_NAME), ("product_id", "=", PRODUCT_ID)])
if lot_ids:
    lot_id = lot_ids[0]
    print(f"[lot] existant reutilise : id={lot_id}")
else:
    lot_id = create("stock.lot", {"name": LOT_NAME, "product_id": PRODUCT_ID})
    print(f"[lot] cree : id={lot_id} name={LOT_NAME}")

# 2. Quant + ajustement d'inventaire
quant_ids = search("stock.quant", [
    ("product_id", "=", PRODUCT_ID),
    ("lot_id", "=", lot_id),
    ("location_id", "=", LOCATION_ID),
])
if quant_ids:
    qid = quant_ids[0]
    print(f"[quant] existant id={qid} -> on fixe inventory_quantity={QTY}")
else:
    qid = create("stock.quant", {
        "product_id": PRODUCT_ID,
        "location_id": LOCATION_ID,
        "lot_id": lot_id,
    })
    print(f"[quant] cree id={qid}")

# inventory_quantity = compte physique, puis on applique
execute("stock.quant", "write", [[qid], {"inventory_quantity": QTY}])
execute("stock.quant", "action_apply_inventory", [[qid]])
print(f"[inventaire] applique : {QTY} u. sur quant {qid}")

# 3. Verification
from _client import search_read
p = search_read("product.product", [("id", "=", PRODUCT_ID)], ["name", "qty_available"])
q = search_read("stock.quant", [("id", "=", qid)], ["quantity", "lot_id", "location_id"])
print("\n=== VERIF ===")
print(f"  produit : {p[0]['name']} | qty_available globale = {p[0]['qty_available']}")
print(f"  quant   : {q[0]['quantity']} u. | lot={q[0]['lot_id']} | loc={q[0]['location_id']}")
