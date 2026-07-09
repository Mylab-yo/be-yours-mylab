"""Correction platine SILVER GLOW S00422 : receptions clientes = 138 + 315 + 315 = 768.
  00085 mv#635 : 126 -> 138  (1re reception)
  00116 mv#964 : 924 -> 912  (reste a livrer = 1680 - 768)
"""
from scripts.odoo._client import execute, search_read

TARGETS = {
    635: ("00085 Shampoing platine 100ml", 138),
    964: ("00116 Shampoing platine 100ml", 912),
}
ids = list(TARGETS.keys())

before = {m["id"]: m for m in search_read(
    "stock.move", [("id", "in", ids)], ["id", "product_uom_qty", "quantity", "state"])}
print("=== BEFORE ===")
for mid in ids:
    b = before[mid]
    print(f"  mv#{mid} demand={b['product_uom_qty']} done={b['quantity']} state={b['state']} -> {TARGETS[mid][1]} ({TARGETS[mid][0]})")

for mid, (label, target) in TARGETS.items():
    execute("stock.move", "write", [[mid], {"quantity": float(target)}])
    execute("stock.move", "write", [[mid], {"product_uom_qty": float(target)}])
    print(f"  WROTE mv#{mid} -> {target}")

after = {m["id"]: m for m in search_read(
    "stock.move", [("id", "in", ids)], ["id", "product_uom_qty", "quantity", "state"])}
print("\n=== AFTER ===")
for mid in ids:
    a = after[mid]
    tgt = TARGETS[mid][1]
    flag = "OK" if abs(a["quantity"] - tgt) < 0.01 and abs(a["product_uom_qty"] - tgt) < 0.01 else "!! MISMATCH"
    print(f"  mv#{mid} demand={a['product_uom_qty']} done={a['quantity']} state={a['state']} target={tgt} {flag}")

# Confirm SO delivered platine
so = search_read("sale.order", [("name", "=", "S00422")], ["id"])[0]
line = search_read("sale.order.line",
                   [("order_id", "=", so["id"]), ("product_id.name", "like", "platine 100")],
                   ["product_uom_qty", "qty_delivered", "name"])
for l in line:
    print(f"\nSO platine: ordered={l['product_uom_qty']} delivered={l['qty_delivered']} ({l['name']})")
