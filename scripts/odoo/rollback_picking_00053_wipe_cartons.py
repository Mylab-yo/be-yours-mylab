"""Wipe all carton organization on MYVO/OUT/00053 to a clean slate.

After execution:
- Picking #69 still 'assigned'
- 13 move_lines (1 per move, full qty)
- 0 packages
- Ready to re-organize based on physical palette photos.
"""
from datetime import datetime
from scripts.odoo._client import search_read, write, unlink

PICKING_ID = 69


def main():
    print("=== ROLLBACK MYVO/OUT/00053 to clean slate ===\n")

    # Step 1: detach all packages from move_lines
    mls = search_read(
        "stock.move.line",
        [("picking_id", "=", PICKING_ID)],
        ["id", "move_id", "quantity", "result_package_id"],
    )
    print(f"[1] {len(mls)} move_lines found")
    ml_ids = [ml["id"] for ml in mls]
    if ml_ids:
        write("stock.move.line", ml_ids, {"result_package_id": False})
        print(f"    Detached result_package_id on all {len(ml_ids)} mls")

    # Step 2: per move, keep 1 ml at total qty, unlink the rest
    moves = search_read(
        "stock.move",
        [("picking_id", "=", PICKING_ID)],
        ["id", "product_id", "quantity"],
    )
    print(f"\n[2] Consolidating mls per move ({len(moves)} moves)")
    for mv in moves:
        these_mls = [ml for ml in mls if ml["move_id"][0] == mv["id"]]
        if not these_mls:
            print(f"    mv#{mv['id']:4d} no mls?? skip")
            continue
        # Sort by id, keep first
        these_mls.sort(key=lambda x: x["id"])
        keeper = these_mls[0]
        to_drop = [ml["id"] for ml in these_mls[1:]]

        write("stock.move.line", [keeper["id"]], {"quantity": mv["quantity"]})
        if to_drop:
            unlink("stock.move.line", to_drop)
        print(f"    mv#{mv['id']:4d} qty={mv['quantity']:5.1f} | kept ml#{keeper['id']} | dropped {len(to_drop)} mls")

    # Step 3: unlink the 55 packages
    print(f"\n[3] Unlink Pack Demarrage + Loose packages")
    pkgs = search_read(
        "stock.quant.package",
        ["|", ("name", "like", "Pack D"), ("name", "like", "Loose %/25")],
        ["id", "name"],
    )
    pkg_ids = [p["id"] for p in pkgs]
    print(f"    Found {len(pkg_ids)} packages to delete")
    if pkg_ids:
        try:
            unlink("stock.quant.package", pkg_ids)
            print(f"    DELETED {len(pkg_ids)} packages")
        except Exception as e:
            print(f"    WARN: {e}")

    print("\n=== DONE — picking now clean ===")
    # Final state probe
    final_mls = search_read(
        "stock.move.line",
        [("picking_id", "=", PICKING_ID)],
        ["id", "product_id", "quantity", "result_package_id"],
    )
    print(f"\nFinal: {len(final_mls)} move_lines:")
    for ml in sorted(final_mls, key=lambda x: x["id"]):
        prod = ml["product_id"][1] if ml["product_id"] else "?"
        print(f"  ml#{ml['id']:4d} | qty={ml['quantity']:5.1f} | {prod[:60]}")


if __name__ == "__main__":
    main()
