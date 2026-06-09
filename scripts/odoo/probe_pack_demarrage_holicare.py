"""Probe the 'Packs demarrage Holicare' product + BoM + sibling pickings on S00463."""
from scripts.odoo._client import search_read, search

# 1. Find the pack product
prods = search_read(
    "product.product",
    [("name", "ilike", "Packs")],
    ["id", "name", "default_code", "type", "product_tmpl_id", "qty_available"],
)
print("=== Pack products matched ===")
for p in prods:
    print(f"  #{p['id']} | code={p['default_code']} | type={p['type']} | stock={p['qty_available']} | {p['name']}")

# Narrow to Holicare pack
pack_prods = [p for p in prods if "Holicare" in (p["name"] or "")]
if not pack_prods:
    print("No Holicare pack found, exiting")
    raise SystemExit
pack = pack_prods[0]
tmpl_id = pack["product_tmpl_id"][0]
print(f"\nUsing pack: #{pack['id']} ({pack['name']}) tmpl={tmpl_id}")

# 2. Check if it has a Bill of Materials (Manufacturing BoM)
boms = search_read(
    "mrp.bom",
    [("product_tmpl_id", "=", tmpl_id)],
    ["id", "product_id", "product_tmpl_id", "type", "product_qty", "bom_line_ids"],
)
print(f"\n=== mrp.bom matches ({len(boms)}) ===")
for b in boms:
    print(f"  BoM #{b['id']} | type={b['type']} | qty={b['product_qty']} | lines={len(b['bom_line_ids'])}")
    lines = search_read(
        "mrp.bom.line",
        [("bom_id", "=", b["id"])],
        ["id", "product_id", "product_qty"],
    )
    for l in lines:
        prod_name = l["product_id"][1] if l["product_id"] else "?"
        print(f"    - {l['product_qty']:6.2f} x {prod_name}")

# 3. Find all pickings linked to SO S00463
so = search_read("sale.order", [("name", "=", "S00463")], ["id", "name", "picking_ids"])
if so:
    pick_ids = so[0]["picking_ids"]
    print(f"\n=== Pickings on S00463 ({len(pick_ids)}) ===")
    pickings = search_read(
        "stock.picking",
        [("id", "in", pick_ids)],
        ["id", "name", "state", "scheduled_date", "backorder_id"],
    )
    for p in sorted(pickings, key=lambda x: x["name"]):
        bo = p["backorder_id"][1] if p["backorder_id"] else "-"
        print(f"  {p['name']} (id={p['id']}, state={p['state']}, scheduled={p['scheduled_date']}, backorder_of={bo})")

# 4. Look at the move for the pack product in MYVO/OUT/00053
print("\n=== Move(s) for pack product in MYVO/OUT/00053 ===")
moves = search_read(
    "stock.move",
    [("picking_id.name", "=", "MYVO/OUT/00053"), ("product_id", "=", pack["id"])],
    ["id", "product_uom_qty", "quantity", "state", "move_orig_ids", "move_dest_ids", "bom_line_id"],
)
for m in moves:
    print(f"  move #{m['id']} | demand={m['product_uom_qty']} | done={m['quantity']} | state={m['state']}")
    print(f"     orig_moves={m['move_orig_ids']}  dest_moves={m['move_dest_ids']}  bom_line={m['bom_line_id']}")
