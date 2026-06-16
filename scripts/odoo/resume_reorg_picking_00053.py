"""RESUME script for the partial reorg crash on MYVO/OUT/00053.

State at start:
- mv#332 (masque-nourrissant-400-ml) is DONE (30 pack + 5 loose mls)
- 12 other moves PENDING (still have old detached mls)
- 30 'Pack Demarrage Holicare N/30' pkgs exist (280-309), each with 1 ml for mn-400
- 25 'Loose N/25 - ...' pkgs exist (310-334), 13 occupied 12 empty
- 27 old 'Carton N/27' pkgs still present (to be unlinked)

This script:
1. Looks up existing pack + loose pkg ids by name
2. For each PENDING move, creates new pack mls + new loose mls in the right pkgs
3. Unlinks the orphaned (detached) old mls
4. Finally unlinks the 27 old 'Carton N/27' pkgs

All print statements are ASCII-safe (no Unicode arrows).
"""
from datetime import datetime
from scripts.odoo._client import search_read, write, create, unlink

PICKING_ID = 69
N_PACKS = 30
SKIP_MOVE_IDS = {332}  # mv#332 already done

PACK_PER_UNIT = {
    "shampoing-nourrissant-500-ml": 1,
    "shampoing-purifiant-500-ml": 1,
    "shampoing-ha-repulpe-500-ml": 1,
    "masque-nourrissant-400-ml": 1,
    "masque-volume-400-ml": 1,
    "bain-miraculeux-50-ml": 1,
}
POMPES_PRODUCT_ID = 2410
POMPES_PER_PACK = 3
PACK_SKU_PRODUCT_ID = 2591

CAP_OVERRIDE = {
    "bain-miraculeux-50-ml": 50,
}

LOOSE_ORDER = [
    "shampoing-nourrissant-500-ml",
    "shampoing-purifiant-500-ml",
    "shampoing-ha-repulpe-500-ml",
    "masque-nourrissant-400-ml",
    "masque-volume-400-ml",
    "bain-miraculeux-50-ml",
    "shampoing-nourrissant-200-ml",
    "shampoing-purifiant-200-ml",
    "shampoing-ha-repulpe-200-ml",
    "masque-nourrissant-200-ml",
    "masque-volume-200-ml",
]


def main():
    print("=== RESUME reorg MYVO/OUT/00053 ===\n")

    # Look up pack pkg ids by N
    pack_pkgs = search_read(
        "stock.quant.package",
        [("name", "like", "Pack D")],
        ["id", "name"],
    )
    # Match "Pack Demarrage Holicare N/30" (with or without accent)
    pack_by_n = {}
    for pk in pack_pkgs:
        # Extract N from name
        parts = pk["name"].split()
        for part in parts:
            if "/" in part and part.endswith("/30"):
                n = int(part.split("/")[0])
                pack_by_n[n] = pk["id"]
                break
    print(f"Found {len(pack_by_n)} pack packages (expected 30)")
    assert len(pack_by_n) == 30, f"Missing pack pkgs! Got {sorted(pack_by_n.keys())}"

    # Look up loose pkg ids by their full sequence number
    loose_pkgs = search_read(
        "stock.quant.package",
        [("name", "like", "Loose ")],
        ["id", "name"],
    )
    loose_by_n = {}
    for pk in loose_pkgs:
        # Parse "Loose N/25 - ..."
        parts = pk["name"].split()
        if len(parts) >= 2 and "/" in parts[1] and parts[1].endswith("/25"):
            n = int(parts[1].split("/")[0])
            loose_by_n[n] = (pk["id"], pk["name"])
    print(f"Found {len(loose_by_n)} loose packages (expected 25)")
    assert len(loose_by_n) == 25, f"Missing loose pkgs! Got {sorted(loose_by_n.keys())}"

    # Load picking + moves
    picking = search_read("stock.picking", [("id", "=", PICKING_ID)],
                         ["id", "name", "state", "company_id"])[0]
    company_id = picking["company_id"][0]
    print(f"Picking #{picking['id']} state={picking['state']}\n")

    # Load product metadata for capacities
    moves = search_read(
        "stock.move",
        [("picking_id", "=", PICKING_ID)],
        ["id", "product_id", "quantity", "location_id", "location_dest_id", "product_uom"],
    )

    prod_ids = list({m["product_id"][0] for m in moves})
    prods_full = search_read(
        "product.product",
        [("id", "in", prod_ids)],
        ["id", "default_code", "name", "product_tmpl_id"],
    )
    tmpl_ids = list({p["product_tmpl_id"][0] for p in prods_full if p["product_tmpl_id"]})
    tmpls = search_read(
        "product.template",
        [("id", "in", tmpl_ids)],
        ["id", "x_carton_capacity"],
    )
    cap_by_tmpl = {t["id"]: t.get("x_carton_capacity") or 0 for t in tmpls}
    prod_map = {}
    for p in prods_full:
        tmpl_id = p["product_tmpl_id"][0] if p["product_tmpl_id"] else None
        cap = cap_by_tmpl.get(tmpl_id, 0)
        code = p.get("default_code") or p["name"]
        if code in CAP_OVERRIDE:
            cap = CAP_OVERRIDE[code]
        prod_map[p["id"]] = {"code": code, "name": p["name"], "capacity": cap, "tmpl_id": tmpl_id}

    # Determine pack_per for each move
    def pack_per_for(move):
        prod_id = move["product_id"][0]
        code = prod_map[prod_id]["code"]
        if code in PACK_PER_UNIT:
            return 1
        if prod_id == POMPES_PRODUCT_ID:
            return POMPES_PER_PACK
        if prod_id == PACK_SKU_PRODUCT_ID:
            return 1
        return 0

    # Compute loose chunk plan per move, in LOOSE_ORDER
    # Then build a global loose-number assignment matching the original script's sequencing
    move_by_code = {prod_map[m["product_id"][0]]["code"]: m for m in moves}

    # Replay loose numbering exactly as original script did
    loose_assign = {}  # move_id -> [(chunk_qty, loose_n), ...]
    n_counter = 0
    for code in LOOSE_ORDER:
        if code not in move_by_code:
            continue
        mv = move_by_code[code]
        total = int(mv["quantity"])
        pp = pack_per_for(mv)
        loose_qty = total - pp * N_PACKS
        if loose_qty <= 0:
            continue
        cap = prod_map[mv["product_id"][0]]["capacity"] or loose_qty
        remaining = loose_qty
        chunks = []
        while remaining > 0:
            take = min(cap, remaining)
            n_counter += 1
            chunks.append((take, n_counter))
            remaining -= take
        loose_assign[mv["id"]] = chunks

    # Verify the loose numbering matches existing pkgs by reading their name and qty
    print("=== Verifying loose pkg name <-> plan alignment ===")
    for mv_id, chunks in loose_assign.items():
        prod_name = prod_map[moves_by_id(mv_id, moves)["product_id"][0]]["name"]
        for qty, n in chunks:
            pkg_id, pkg_name = loose_by_n[n]
            print(f"  Loose {n:2d}/25 [pkg#{pkg_id}] => {qty} ex. {prod_name[:40]:40s} | name='{pkg_name}'")
    print()

    # Resume per pending move
    now_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("=== Processing PENDING moves ===")
    for mv in moves:
        mv_id = mv["id"]
        if mv_id in SKIP_MOVE_IDS:
            print(f"  SKIP mv#{mv_id} (already done)")
            continue

        prod_id = mv["product_id"][0]
        code = prod_map[prod_id]["code"]
        pp = pack_per_for(mv)
        total = int(mv["quantity"])
        loc_id = mv["location_id"][0]
        dest_id = mv["location_dest_id"][0]
        uom_id = mv["product_uom"][0]

        # 1) Read existing (orphan) move_lines for this move
        existing_mls = search_read(
            "stock.move.line",
            [("move_id", "=", mv_id), ("result_package_id", "=", False)],
            ["id", "quantity"],
        )
        old_ml_ids = [ml["id"] for ml in existing_mls]
        old_total = sum(ml["quantity"] for ml in existing_mls)

        # 2) Create pack mls (1 per Pack Demarrage)
        new_count = 0
        if pp > 0:
            for n in range(1, N_PACKS + 1):
                create("stock.move.line", {
                    "move_id": mv_id,
                    "picking_id": PICKING_ID,
                    "product_id": prod_id,
                    "product_uom_id": uom_id,
                    "location_id": loc_id,
                    "location_dest_id": dest_id,
                    "quantity": pp,
                    "result_package_id": pack_by_n[n],
                    "company_id": company_id,
                    "date": now_dt,
                })
                new_count += 1

        # 3) Create loose mls
        for qty, n in loose_assign.get(mv_id, []):
            pkg_id, _ = loose_by_n[n]
            create("stock.move.line", {
                "move_id": mv_id,
                "picking_id": PICKING_ID,
                "product_id": prod_id,
                "product_uom_id": uom_id,
                "location_id": loc_id,
                "location_dest_id": dest_id,
                "quantity": qty,
                "result_package_id": pkg_id,
                "company_id": company_id,
                "date": now_dt,
            })
            new_count += 1

        # 4) Unlink old mls
        if old_ml_ids:
            unlink("stock.move.line", old_ml_ids)

        print(f"  OK mv#{mv_id:4d} pack/u={pp} total={total} old_mls={len(old_ml_ids)}(sum={old_total:.0f}) "
              f"new_mls={new_count} | {code[:40]}")

    # 5) Unlink old Carton N/27 packages
    print("\n=== Cleanup old 'Carton N/27' packages ===")
    old_pkgs = search_read(
        "stock.quant.package",
        [("name", "like", "Carton %/27")],
        ["id", "name"],
    )
    old_pkg_ids = [p["id"] for p in old_pkgs]
    print(f"  Found {len(old_pkg_ids)} old pkgs: {old_pkg_ids}")
    if old_pkg_ids:
        try:
            unlink("stock.quant.package", old_pkg_ids)
            print(f"  DELETED {len(old_pkg_ids)} old pkgs")
        except Exception as e:
            print(f"  WARN couldn't delete: {e}")

    print("\n=== RESUME DONE ===")


def moves_by_id(mid, moves):
    for m in moves:
        if m["id"] == mid:
            return m
    raise KeyError(mid)


if __name__ == "__main__":
    main()
