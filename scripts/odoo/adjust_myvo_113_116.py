"""Adjust delivery quantities on MYVO/OUT/00113 (done) and MYVO/OUT/00116 (assigned)
to reconcile SO S00422 (CENDREE) with the client's reception sheet.

Decisions (confirmed by Yoann 2026-06-10):
  00113 (done) : Shampoing platine 100ml 189->315 ; dejaunisseur 200ml 200->120
  00116 (assigned):
    - platine 1050->924  (conserve order total 1680)
    - boucles 214->186 ; nourrissant/hydratant 198->192 ; purifiant 94->82
    - volume 94->66 ; leave-in (reparateur ss rincage) 311->305 ; masque nourrissant 340->340 (noop)
    - dejaunisseur 200ml 80->160 (conservation: +80 from 00113's -80)
    - masque gloss 200ml: untouched (not in client table)

Each target is written to BOTH product_uom_qty (demand) and quantity (done).
"""
from scripts.odoo._client import execute, search_read

# move_id -> (label, target_qty)
TARGETS = {
    # --- 00113 (done) ---
    944: ("00113 Shampoing platine 100ml", 315),
    945: ("00113 dejaunisseur platine 200ml", 120),
    # --- 00116 (assigned) ---
    964: ("00116 Shampoing platine 100ml", 924),
    871: ("00116 Shampoing boucles 100ml", 186),
    873: ("00116 shampoing nourrissant 100ml (HYDRATANT)", 192),
    700: ("00116 shampoing purifiant 100ml", 82),
    872: ("00116 Shampoing volume 100ml", 66),
    874: ("00116 masque reparateur sans rincage 100ml (LEAVE-IN)", 305),
    875: ("00116 masque nourrissant 100ml (MASQUE SC)", 340),
    965: ("00116 dejaunisseur platine 200ml", 160),
}

ids = list(TARGETS.keys())
before = {m["id"]: m for m in search_read(
    "stock.move", [("id", "in", ids)],
    ["id", "product_uom_qty", "quantity", "state"])}

print("=== BEFORE ===")
for mid in ids:
    b = before[mid]
    print(f"  mv#{mid:5d} | demand={b['product_uom_qty']:7.1f} done={b['quantity']:7.1f} "
          f"state={b['state']:9s} -> target={TARGETS[mid][1]:4d} | {TARGETS[mid][0]}")

print("\n=== WRITING ===")
for mid, (label, target) in TARGETS.items():
    # quantity (done) first, then demand
    try:
        execute("stock.move", "write", [[mid], {"quantity": float(target)}])
        execute("stock.move", "write", [[mid], {"product_uom_qty": float(target)}])
        print(f"  mv#{mid:5d} OK -> {target}  ({label})")
    except Exception as e:
        print(f"  mv#{mid:5d} ERROR: {e}  ({label})")

after = {m["id"]: m for m in search_read(
    "stock.move", [("id", "in", ids)],
    ["id", "product_uom_qty", "quantity", "state"])}

print("\n=== AFTER ===")
ok = True
for mid in ids:
    a = after[mid]
    tgt = TARGETS[mid][1]
    flag = "OK" if abs(a["quantity"] - tgt) < 0.01 and abs(a["product_uom_qty"] - tgt) < 0.01 else "!! MISMATCH"
    if flag != "OK":
        ok = False
    print(f"  mv#{mid:5d} | demand={a['product_uom_qty']:7.1f} done={a['quantity']:7.1f} "
          f"state={a['state']:9s} target={tgt:4d}  {flag}")

print("\nALL TARGETS MATCH" if ok else "\n*** SOME MOVES DID NOT TAKE — review above ***")
