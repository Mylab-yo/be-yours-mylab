"""Diagnose partial state after crash on reorganize_picking_00053_starter_packs."""
from scripts.odoo._client import search_read

# Existing Pack and Loose packages
pkgs = search_read(
    "stock.quant.package",
    ["|", ("name", "like", "Pack Demarrage Holicare"), ("name", "like", "Loose %/25"),],
    ["id", "name"],
)
pkgs_by_name = {p["name"]: p["id"] for p in pkgs}
print(f"=== Pack + Loose packages found: {len(pkgs)} ===")
for p in sorted(pkgs, key=lambda x: x["id"]):
    print(f"  pkg#{p['id']:4d} | {p['name']}")

# Also fetch with é
pkgs2 = search_read(
    "stock.quant.package",
    [("name", "like", "Pack D")],
    ["id", "name"],
)
print(f"\n=== Pack D-prefix packages (may include accented): {len(pkgs2)} ===")
print(f"  First: {pkgs2[0] if pkgs2 else 'none'}")
print(f"  Last: {pkgs2[-1] if pkgs2 else 'none'}")

# Old Carton N/27 still there?
old = search_read(
    "stock.quant.package",
    [("name", "like", "Carton %/27")],
    ["id", "name"],
)
print(f"\n=== Old 'Carton N/27' packages still present: {len(old)} ===")
for p in sorted(old, key=lambda x: x["id"])[:5]:
    print(f"  pkg#{p['id']:4d} | {p['name']}")
if len(old) > 5:
    print(f"  ... and {len(old)-5} more")

# Move-by-move status: which moves already have new (qty=1 or qty=3) mls in Pack Demarrage?
print("\n=== Per-move status ===")
moves = search_read(
    "stock.move",
    [("picking_id", "=", 69)],
    ["id", "product_id", "quantity"],
)
for mv in moves:
    mls = search_read(
        "stock.move.line",
        [("move_id", "=", mv["id"])],
        ["id", "quantity", "result_package_id"],
    )
    total = sum(ml["quantity"] for ml in mls)
    n_pack = sum(1 for ml in mls if ml["result_package_id"] and "Pack D" in (ml["result_package_id"][1] or ""))
    n_loose = sum(1 for ml in mls if ml["result_package_id"] and "Loose" in (ml["result_package_id"][1] or ""))
    n_orphan = sum(1 for ml in mls if not ml["result_package_id"])
    status = "DONE" if n_orphan == 0 and (n_pack > 0 or n_loose > 0) else ("PARTIAL" if n_pack + n_loose > 0 else "PENDING")
    print(f"  mv#{mv['id']:4d} | qty={mv['quantity']:5.1f}/{total:5.1f} | "
          f"pack_mls={n_pack:3d} | loose_mls={n_loose:2d} | orphan_mls={n_orphan:2d} | {status:8s} | "
          f"{mv['product_id'][1][:50]}")
