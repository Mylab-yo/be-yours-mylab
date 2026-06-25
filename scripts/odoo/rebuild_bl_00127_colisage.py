"""Rebuild colisage of MYVO/OUT/00127 (SHOP HAIR) into 12 single-product cartons.

Target (user spec):
  - Shampoing Gel Douche 500ml : 135 u -> 9 cartons x 15
  - Serum Barbe 50ml           : 126 u -> 2 cartons x 63
  - Huile a Barbe 50ml         :  63 u -> 1 carton  x 63

The deployed "Repartir en cartons" server action groups by carton-capacity
FAMILY (serum + huile both = 50) and mixes them, so we rebuild by hand here.

Run dry first (default), then `--apply` to mutate.
"""
import sys
from datetime import datetime
from scripts.odoo._client import execute, search_read, write, create, unlink

APPLY = "--apply" in sys.argv
PICKING_NAME = "MYVO/OUT/00127"

# product default_code -> (carton_capacity, label)
PLAN = {
    "shampoing-gel-douche-500-ml": (15, "Shampoing Gel Douche 500ml"),
    "serum-barbe-50-ml":           (63, "Serum Barbe 50ml"),
    "huile-a-barbe-50-ml":         (63, "Huile a Barbe 50ml"),
}
# order in which cartons are numbered
PRODUCT_ORDER = ["shampoing-gel-douche-500-ml", "serum-barbe-50-ml", "huile-a-barbe-50-ml"]


def banner(t):
    print("\n" + "=" * 60 + f"\n{t}\n" + "=" * 60)


def main():
    pk = search_read("stock.picking", [("name", "=", PICKING_NAME)],
                     ["id", "name", "state", "company_id"])
    if not pk:
        print("Picking not found"); return
    pk = pk[0]
    PID, COMPANY = pk["id"], pk["company_id"][0]
    print(f"{pk['name']} (#{PID}) | state={pk['state']} | company={COMPANY}")
    if pk["state"] in ("done", "cancel"):
        print("Picking is done/cancel -> abort"); return

    # --- moves: map default_code -> move meta
    moves = search_read("stock.move", [("picking_id", "=", PID)],
                        ["id", "product_id", "product_uom", "location_id",
                         "location_dest_id", "product_uom_qty", "quantity"])
    move_by_code = {}
    for m in moves:
        code = search_read("product.product", [("id", "=", m["product_id"][0])],
                           ["default_code"])[0]["default_code"]
        move_by_code[code] = m

    for code in PLAN:
        if code not in move_by_code:
            print(f"!! missing move for {code} -> abort"); return

    banner("BEFORE")
    old_pkg_ids = set()
    for m in moves:
        mls = search_read("stock.move.line", [("move_id", "=", m["id"])],
                          ["id", "quantity", "lot_id", "result_package_id"])
        code = next(c for c, mm in move_by_code.items() if mm["id"] == m["id"])
        print(f"\n{code}: move done={m['quantity']:.0f} (demand {m['product_uom_qty']:.0f})")
        for ml in mls:
            lot = ml["lot_id"][1] if ml["lot_id"] else "-"
            p = ml["result_package_id"][1] if ml["result_package_id"] else "-"
            if ml["result_package_id"]:
                old_pkg_ids.add(ml["result_package_id"][0])
            print(f"   ml#{ml['id']} qty={ml['quantity']:.0f} lot={lot} pkg={p}")

    # ---- Build target plan (per product: list of (lot_id, qty) chunks) ----
    banner("TARGET PLAN")
    # per product: consolidated pool by lot, then greedily fill cartons of capacity
    plan_chunks = {}  # code -> list of cartons, each carton = list of (lot_id, qty)
    for code in PRODUCT_ORDER:
        m = move_by_code[code]
        cap, label = PLAN[code]
        mls = search_read("stock.move.line", [("move_id", "=", m["id"])],
                          ["id", "quantity", "lot_id"])
        # consolidate qty per lot (lot_id int or 0)
        pool = {}
        for ml in mls:
            lot = ml["lot_id"][0] if ml["lot_id"] else 0
            pool[lot] = pool.get(lot, 0) + ml["quantity"]
        total = sum(pool.values())
        # flatten into ordered list of (lot, qty), lots first then no-lot
        flat = sorted(pool.items(), key=lambda kv: (kv[0] == 0, kv[0]))
        # greedily fill cartons
        cartons = []
        cur = []
        cur_units = 0
        for lot, qty in flat:
            while qty > 0:
                if cur_units >= cap:
                    cartons.append(cur); cur = []; cur_units = 0
                space = cap - cur_units
                take = min(space, qty)
                cur.append((lot, take))
                cur_units += take
                qty -= take
        if cur:
            cartons.append(cur)
        plan_chunks[code] = cartons
        print(f"\n{code}: total={total:.0f} cap={cap} -> {len(cartons)} cartons")
        for i, c in enumerate(cartons, 1):
            desc = " + ".join(f"{q:.0f}(lot {l})" if l else f"{q:.0f}(no-lot)" for l, q in c)
            print(f"   carton: {desc}  [{sum(q for _, q in c):.0f}]")

    total_cartons = sum(len(v) for v in plan_chunks.values())
    print(f"\nTOTAL CARTONS = {total_cartons}")

    if not APPLY:
        print("\n--- DRY RUN (no changes). Re-run with --apply to execute. ---")
        return

    # ============ APPLY ============
    banner("APPLYING")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1) detach all move lines from packages
    all_ml_ids = search_read("stock.move.line", [("picking_id", "=", PID)], ["id"])
    write("stock.move.line", [ml["id"] for ml in all_ml_ids], {"result_package_id": False})
    print(f"Detached {len(all_ml_ids)} move lines from packages")

    # 2) delete old auto packages (now empty)
    for pid in sorted(old_pkg_ids):
        q = search_read("stock.quant.package", [("id", "=", pid)], ["id", "quant_ids"])
        if q and not q[0]["quant_ids"]:
            unlink("stock.quant.package", [pid])
    print(f"Deleted old packages: {sorted(old_pkg_ids)}")

    # 3) consolidate each move's lines per lot into a single editable line
    pool_lines = {}  # code -> {lot_id: ml_id}
    for code in PRODUCT_ORDER:
        m = move_by_code[code]
        mls = search_read("stock.move.line", [("move_id", "=", m["id"])],
                          ["id", "quantity", "lot_id"])
        by_lot = {}
        for ml in mls:
            by_lot.setdefault(ml["lot_id"][0] if ml["lot_id"] else 0, []).append(ml)
        keep = {}
        for lot, lines in by_lot.items():
            kept = lines[0]
            tot = sum(l["quantity"] for l in lines)
            if len(lines) > 1:
                unlink("stock.move.line", [l["id"] for l in lines[1:]])
            write("stock.move.line", [kept["id"]], {"quantity": tot})
            keep[lot] = kept["id"]
        pool_lines[code] = keep
    print("Consolidated move lines per lot")

    # 4) create 12 packages + assign chunks (splitting consolidated lines as needed)
    counter = 1
    for code in PRODUCT_ORDER:
        m = move_by_code[code]
        cap, label = PLAN[code]
        # remaining qty available per lot line (mutable)
        avail = {}
        for lot, ml_id in pool_lines[code].items():
            q = search_read("stock.move.line", [("id", "=", ml_id)], ["quantity"])[0]["quantity"]
            avail[lot] = {"ml_id": ml_id, "qty": q, "used": False}
        for carton in plan_chunks[code]:
            pkg = create("stock.quant.package", {"name": f"Carton {counter}/{total_cartons} - {label}"})
            for lot, qty in carton:
                src = avail[lot]
                if not src["used"]:
                    # first use of this lot line: shrink-or-assign
                    if abs(src["qty"] - qty) < 1e-6:
                        write("stock.move.line", [src["ml_id"]],
                              {"result_package_id": pkg, "quantity": qty})
                        src["used"] = True
                        src["qty"] = 0
                        continue
                    else:
                        # assign this slice to current pkg, keep remainder on the line
                        write("stock.move.line", [src["ml_id"]],
                              {"result_package_id": pkg, "quantity": qty})
                        src["used"] = True
                        src["qty"] -= qty
                        continue
                # subsequent slices of same lot: create a new line for the remainder slice
                new_ml = create("stock.move.line", {
                    "move_id": m["id"],
                    "picking_id": PID,
                    "product_id": m["product_id"][0],
                    "product_uom_id": m["product_uom"][0],
                    "location_id": m["location_id"][0],
                    "location_dest_id": m["location_dest_id"][0],
                    "quantity": qty,
                    "lot_id": lot or False,
                    "result_package_id": pkg,
                    "company_id": COMPANY,
                    "date": now,
                })
                src["qty"] -= qty
            print(f"  Carton {counter}/{total_cartons} - {label} : {[ (l, q) for l,q in carton ]}")
            counter += 1

    # ============ VERIFY ============
    banner("AFTER / VERIFY")
    for m in moves:
        code = next((c for c, mm in move_by_code.items() if mm["id"] == m["id"]), m["product_id"][1])
        mv = search_read("stock.move", [("id", "=", m["id"])], ["product_uom_qty", "quantity"])[0]
        mls = search_read("stock.move.line", [("move_id", "=", m["id"])],
                          ["id", "quantity", "lot_id", "result_package_id"])
        tot = sum(x["quantity"] for x in mls)
        flag = "OK" if abs(tot - mv["quantity"]) < 1e-6 else "!! MISMATCH"
        print(f"\n{code}: move done={mv['quantity']:.0f} | sum(lines)={tot:.0f} {flag}")
        for ml in sorted(mls, key=lambda x: (x["result_package_id"] or [9999])[0]):
            lot = ml["lot_id"][1] if ml["lot_id"] else "-"
            p = ml["result_package_id"][1] if ml["result_package_id"] else "-"
            print(f"   ml#{ml['id']} qty={ml['quantity']:.0f} lot={lot} pkg={p}")

    # list final packages
    pkgs = search_read("stock.quant.package",
                       [("id", "in", [])], ["id", "name"])  # placeholder
    final_pkg_ids = sorted({ (ml["result_package_id"] or [0])[0]
                             for mm in moves
                             for ml in search_read("stock.move.line", [("move_id","=",mm["id"])],
                                                   ["result_package_id"]) } - {0})
    banner("FINAL PACKAGES")
    for p in search_read("stock.quant.package", [("id", "in", final_pkg_ids)], ["id", "name"]):
        print(f"  pkg#{p['id']} {p['name']}")
    print(f"\nTotal packages: {len(final_pkg_ids)}")


if __name__ == "__main__":
    main()
