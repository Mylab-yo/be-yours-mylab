"""Reorganize MYVO/OUT/00053 according to user's detailed physical inventory.

Plan :
- 30 packs "Pack Demarrage Holicare N/30" each containing the FULL composition
  (1 SHP NOUR 500 + 1 SHP PUR 500 + 1 SHP HA REPULPE 500 + 1 MSQ NOUR 400
   + 1 MSQ VOL 400 + 1 BAIN MIRA 50 + 3 POMPES 500 + 1 SKU)
- 31 loose cartons as detailed by user (one is mixed = 3 products in same carton)
- MSQ NOUR 400 short by 2 units (loose 144 vs picking expected 146) → backorder

DRY_RUN=True : show plan only.
"""
from datetime import datetime
from scripts.odoo._client import search_read, write, create, unlink

PICKING_ID = 69
N_PACKS = 30

DRY_RUN = False  # APPLIED 2026-06-09

# Product code mapping
# code -> (id, uom_id, location_id, location_dest_id, move_id, name)
# Will be populated dynamically

# Pack composition (per pack)
PACK_COMPO = [
    ("shampoing-nourrissant-500-ml", 1),
    ("shampoing-purifiant-500-ml", 1),
    ("shampoing-ha-repulpe-500-ml", 1),
    ("masque-nourrissant-400-ml", 1),
    ("masque-volume-400-ml", 1),
    ("bain-miraculeux-50-ml", 1),
    ("POMPES500", 3),  # POMPES 500ML (no default_code, identify by id)
    ("PACK_SKU", 1),   # Packs demarrage Holicare SKU
]

POMPES_PRODUCT_ID = 2410   # POMPES 500ML
PACK_SKU_PRODUCT_ID = 2591 # Packs demarrage Holicare

# Loose cartons per user's detailed inventory
# Format: list of (label, [(product_code, qty), ...])
LOOSE_CARTONS = [
    # 6 cartons MSQ NOUR 400 a 24 (manque 2 globalement)
    ("MSQ NOUR 400 x24 (1)",  [("masque-nourrissant-400-ml", 24)]),
    ("MSQ NOUR 400 x24 (2)",  [("masque-nourrissant-400-ml", 24)]),
    ("MSQ NOUR 400 x24 (3)",  [("masque-nourrissant-400-ml", 24)]),
    ("MSQ NOUR 400 x24 (4)",  [("masque-nourrissant-400-ml", 24)]),
    ("MSQ NOUR 400 x24 (5)",  [("masque-nourrissant-400-ml", 24)]),
    ("MSQ NOUR 400 x24 (6)",  [("masque-nourrissant-400-ml", 24)]),
    # MSQ NOUR 200
    ("MSQ NOUR 200 x24",      [("masque-nourrissant-200-ml", 24)]),
    ("MSQ NOUR 200 x12",      [("masque-nourrissant-200-ml", 12)]),
    # MSQ VOL 400
    ("MSQ VOL 400 x24",       [("masque-volume-400-ml", 24)]),
    ("MSQ VOL 400 x22",       [("masque-volume-400-ml", 22)]),
    # MSQ VOL 200
    ("MSQ VOL 200 x24",       [("masque-volume-200-ml", 24)]),
    # SHP PUR 500
    ("SHP PUR 500 x23 (1)",   [("shampoing-purifiant-500-ml", 23)]),
    ("SHP PUR 500 x23 (2)",   [("shampoing-purifiant-500-ml", 23)]),
    # SHP PUR 200
    ("SHP PUR 200 x40",       [("shampoing-purifiant-200-ml", 40)]),
    ("SHP PUR 200 x10",       [("shampoing-purifiant-200-ml", 10)]),
    # SHP HA REPULPE 500
    ("SHP HA 500 x23 (1)",    [("shampoing-ha-repulpe-500-ml", 23)]),
    ("SHP HA 500 x23 (2)",    [("shampoing-ha-repulpe-500-ml", 23)]),
    ("SHP HA 500 x23 (3)",    [("shampoing-ha-repulpe-500-ml", 23)]),
    ("SHP HA 500 x23 (4)",    [("shampoing-ha-repulpe-500-ml", 23)]),
    ("SHP HA 500 x23 (5)",    [("shampoing-ha-repulpe-500-ml", 23)]),
    # SHP HA 200
    ("SHP HA 200 x30",        [("shampoing-ha-repulpe-200-ml", 30)]),
    # SHP NOUR 500
    ("SHP NOUR 500 x23 (1)",  [("shampoing-nourrissant-500-ml", 23)]),
    ("SHP NOUR 500 x23 (2)",  [("shampoing-nourrissant-500-ml", 23)]),
    ("SHP NOUR 500 x23 (3)",  [("shampoing-nourrissant-500-ml", 23)]),
    ("SHP NOUR 500 x18",      [("shampoing-nourrissant-500-ml", 18)]),
    # SHP NOUR 200
    ("SHP NOUR 200 x30",      [("shampoing-nourrissant-200-ml", 30)]),
    # BAIN MIRA
    ("BAIN MIRA 50 x50 (1)",  [("bain-miraculeux-50-ml", 50)]),
    ("BAIN MIRA 50 x50 (2)",  [("bain-miraculeux-50-ml", 50)]),
    ("BAIN MIRA 50 x50 (3)",  [("bain-miraculeux-50-ml", 50)]),
    ("BAIN MIRA 50 x30",      [("bain-miraculeux-50-ml", 30)]),
    # MIXED carton (4 SHP PUR 500 + 5 SHP HA REPULPE 500 + 2 MSQ VOL 200)
    ("MIXE 4xSHP PUR 500 + 5xSHP HA 500 + 2xMSQ VOL 200",
     [
        ("shampoing-purifiant-500-ml", 4),
        ("shampoing-ha-repulpe-500-ml", 5),
        ("masque-volume-200-ml", 2),
     ]),
]


def load_state():
    picking = search_read(
        "stock.picking",
        [("id", "=", PICKING_ID)],
        ["id", "name", "state", "company_id"],
    )[0]
    moves = search_read(
        "stock.move",
        [("picking_id", "=", PICKING_ID)],
        ["id", "product_id", "product_uom_qty", "quantity", "state",
         "location_id", "location_dest_id", "product_uom"],
    )
    mls = search_read(
        "stock.move.line",
        [("picking_id", "=", PICKING_ID)],
        ["id", "move_id", "quantity", "result_package_id"],
    )

    # Build product_id -> move map
    move_by_code = {}
    move_meta = {}
    prod_ids = list({m["product_id"][0] for m in moves})
    prods = search_read(
        "product.product",
        [("id", "in", prod_ids)],
        ["id", "default_code", "name"],
    )
    code_by_pid = {p["id"]: (p.get("default_code") or "") for p in prods}
    name_by_pid = {p["id"]: p["name"] for p in prods}
    for mv in moves:
        pid = mv["product_id"][0]
        code = code_by_pid.get(pid) or ""
        # Special tokens
        if pid == POMPES_PRODUCT_ID:
            move_by_code["POMPES500"] = mv
        elif pid == PACK_SKU_PRODUCT_ID:
            move_by_code["PACK_SKU"] = mv
        elif code:
            move_by_code[code] = mv
        else:
            print(f"WARN: unmapped product id={pid} name={name_by_pid[pid]}")
        move_meta[mv["id"]] = {
            "product_id": pid,
            "code": code or name_by_pid[pid],
            "loc_id": mv["location_id"][0],
            "dest_id": mv["location_dest_id"][0],
            "uom_id": mv["product_uom"][0],
            "demand": mv["product_uom_qty"],
            "current_done": mv["quantity"],
        }
    return picking, moves, mls, move_by_code, move_meta


def print_plan(move_by_code, move_meta):
    print(f"\n{'='*80}")
    print(f"  PLAN MYVO/OUT/00053 v2 - 30 packs + 31 loose")
    print(f"{'='*80}")

    # Compute target qty per product
    print(f"\n=== Per-product target qty ===")
    print(f"{'Product':40s} | {'demand':>6s} | {'pack':>5s} | {'loose':>5s} | {'target':>6s} | {'cur':>5s} | {'delta':>5s}")
    print("-" * 100)
    targets = {}
    for code, mv in move_by_code.items():
        mv_id = mv["id"]
        meta = move_meta[mv_id]
        # Compute pack contribution
        pack_per = 0
        for comp_code, qty in PACK_COMPO:
            if comp_code == code:
                pack_per = qty
                break
        pack_total = pack_per * N_PACKS
        # Compute loose total
        loose_total = 0
        for label, contents in LOOSE_CARTONS:
            for c, q in contents:
                if c == code:
                    loose_total += q
        target = pack_total + loose_total
        delta = target - meta["current_done"]
        targets[code] = (pack_total, loose_total, target)
        print(f"{code[:40]:40s} | {meta['demand']:>6.0f} | {pack_total:>5d} | {loose_total:>5d} | "
              f"{target:>6d} | {meta['current_done']:>5.0f} | {delta:>+5.0f}")

    # Cartons summary
    print(f"\n=== Pack cartons ===")
    print(f"  30 x Pack Demarrage Holicare with composition: "
          f"{', '.join(f'{q}{c}' for c, q in PACK_COMPO)}")

    print(f"\n=== Loose cartons ({len(LOOSE_CARTONS)}) ===")
    for i, (label, contents) in enumerate(LOOSE_CARTONS, 1):
        print(f"  L{i:2d}: {label}")
        for c, q in contents:
            print(f"        -> {q} x {c}")

    print(f"\n=> Total packages: 30 + {len(LOOSE_CARTONS)} = {30+len(LOOSE_CARTONS)} cartons")

    return targets


def execute_reorg(picking, moves, mls, move_by_code, move_meta, targets):
    company_id = picking["company_id"][0]
    now_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Step 1: detach all current ml packages + wipe all mls except 1 per move
    print(f"\n[1] Wiping existing move_lines on picking #{PICKING_ID}...")
    if mls:
        ml_ids = [ml["id"] for ml in mls]
        # Detach packages
        write("stock.move.line", ml_ids, {"result_package_id": False})
        # Unlink all
        unlink("stock.move.line", ml_ids)
        print(f"    Deleted {len(ml_ids)} existing move_lines")

    # Step 2: create 30 pack packages
    print(f"\n[2] Creating {N_PACKS} Pack Demarrage packages...")
    pack_pkg_ids = []
    for n in range(1, N_PACKS + 1):
        pkg_id = create("stock.quant.package", {
            "name": f"Pack Demarrage Holicare {n}/{N_PACKS}",
        })
        pack_pkg_ids.append(pkg_id)
    print(f"    Created pkg ids {pack_pkg_ids[0]}..{pack_pkg_ids[-1]}")

    # Step 3: create 31 loose packages
    print(f"\n[3] Creating {len(LOOSE_CARTONS)} loose packages...")
    loose_pkg_ids = []
    for i, (label, _) in enumerate(LOOSE_CARTONS, 1):
        pkg_id = create("stock.quant.package", {
            "name": f"Loose {i}/{len(LOOSE_CARTONS)} - {label}",
        })
        loose_pkg_ids.append(pkg_id)
    print(f"    Created pkg ids {loose_pkg_ids[0]}..{loose_pkg_ids[-1]}")

    # Step 4: create new move_lines
    print(f"\n[4] Creating move_lines...")

    # 4a: For each pack, create a move_line per composition item
    pack_ml_count = 0
    for n in range(N_PACKS):
        pkg_id = pack_pkg_ids[n]
        for comp_code, comp_qty in PACK_COMPO:
            mv = move_by_code.get(comp_code)
            if not mv:
                print(f"    WARN: no move for pack composition {comp_code!r}, skipping")
                continue
            mv_id = mv["id"]
            meta = move_meta[mv_id]
            create("stock.move.line", {
                "move_id": mv_id,
                "picking_id": PICKING_ID,
                "product_id": meta["product_id"],
                "product_uom_id": meta["uom_id"],
                "location_id": meta["loc_id"],
                "location_dest_id": meta["dest_id"],
                "quantity": comp_qty,
                "result_package_id": pkg_id,
                "company_id": company_id,
                "date": now_dt,
            })
            pack_ml_count += 1
    print(f"    Created {pack_ml_count} move_lines for packs")

    # 4b: For each loose carton, create move_lines per content
    loose_ml_count = 0
    for i, (label, contents) in enumerate(LOOSE_CARTONS):
        pkg_id = loose_pkg_ids[i]
        for comp_code, comp_qty in contents:
            mv = move_by_code.get(comp_code)
            if not mv:
                print(f"    WARN: no move for loose code {comp_code!r}, skipping carton {label}")
                continue
            mv_id = mv["id"]
            meta = move_meta[mv_id]
            create("stock.move.line", {
                "move_id": mv_id,
                "picking_id": PICKING_ID,
                "product_id": meta["product_id"],
                "product_uom_id": meta["uom_id"],
                "location_id": meta["loc_id"],
                "location_dest_id": meta["dest_id"],
                "quantity": comp_qty,
                "result_package_id": pkg_id,
                "company_id": company_id,
                "date": now_dt,
            })
            loose_ml_count += 1
    print(f"    Created {loose_ml_count} move_lines for loose")

    print(f"\n[5] Verifying final state...")
    final = search_read(
        "stock.move",
        [("picking_id", "=", PICKING_ID)],
        ["id", "product_id", "product_uom_qty", "quantity"],
    )
    for mv in final:
        delta = mv["quantity"] - mv["product_uom_qty"]
        flag = "OK" if delta == 0 else f"DELTA {delta:+.0f}"
        prod = mv["product_id"][1] if mv["product_id"] else "?"
        print(f"  mv#{mv['id']:4d} {prod[:50]:50s} | demand={mv['product_uom_qty']:5.0f} | "
              f"done={mv['quantity']:5.0f} | {flag}")

    print("\n=== DONE ===")


def main():
    picking, moves, mls, move_by_code, move_meta = load_state()
    print(f"Picking #{picking['id']} state={picking['state']}")
    print(f"  Moves: {len(moves)} | move_lines: {len(mls)}")
    print(f"  Mapped move codes: {sorted(move_by_code.keys())}")
    targets = print_plan(move_by_code, move_meta)
    if DRY_RUN:
        print(f"\n[DRY_RUN=True] No changes applied.")
    else:
        execute_reorg(picking, moves, mls, move_by_code, move_meta, targets)


if __name__ == "__main__":
    main()
