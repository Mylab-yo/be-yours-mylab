"""Reorganise MYVO/OUT/00053 (HOLICARE) en 30 cartons 'Pack Démarrage' + 25 cartons loose.

DRY_RUN=True par défaut : affiche le plan détaillé sans toucher à Odoo.
Mettre DRY_RUN=False pour appliquer.

Pré-requis validés :
- Picking id=69, state=assigned, partner=HOLICARE, SO=S00463
- 13 moves / 35 move_lines / 27 packages 'Carton N/27' à virer
- Composition pack (×30) : 1 chaque (shampoing nour/pur/ha 500ml + masque nour/vol 400ml
  + bain miraculeux 50ml) + 3 pompes 500ml + 1 SKU 'Packs démarrage Holicare'
"""
from datetime import datetime
from scripts.odoo._client import search_read, write, create, unlink, search

PICKING_ID = 69
PICKING_NAME = "MYVO/OUT/00053"
N_PACKS = 30
PACK_SKU_NAME = "Packs démarrage Holicare"

# product default_code → qty per single starter pack
PACK_PER_UNIT = {
    "shampoing-nourrissant-500-ml": 1,
    "shampoing-purifiant-500-ml": 1,
    "shampoing-ha-repulpe-500-ml": 1,
    "masque-nourrissant-400-ml": 1,
    "masque-volume-400-ml": 1,
    "bain-miraculeux-50-ml": 1,
}
POMPES_PRODUCT_NAME = "POMPES 500ML"
POMPES_PER_PACK = 3

# Override carton capacity (0 = pas défini dans Odoo)
CAP_OVERRIDE = {
    "bain-miraculeux-50-ml": 50,
}

# Loose categorization order for naming
LOOSE_ORDER = [
    ("shampoing-nourrissant-500-ml", "500ml shampoing/crème"),
    ("shampoing-purifiant-500-ml",   "500ml shampoing/crème"),
    ("shampoing-ha-repulpe-500-ml",  "500ml shampoing/crème"),
    ("masque-nourrissant-400-ml",    "400ml masque"),
    ("masque-volume-400-ml",         "400ml masque"),
    ("bain-miraculeux-50-ml",        "50ml bain miraculeux"),
    ("shampoing-nourrissant-200-ml", "200ml shampoing"),
    ("shampoing-purifiant-200-ml",   "200ml shampoing"),
    ("shampoing-ha-repulpe-200-ml",  "200ml shampoing"),
    ("masque-nourrissant-200-ml",    "200ml masque"),
    ("masque-volume-200-ml",         "200ml masque"),
]


DRY_RUN = False  # APPLIED 2026-06-08


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
        ["id", "move_id", "product_id", "quantity", "result_package_id",
         "location_id", "location_dest_id", "product_uom_id"],
    )

    pkgs = search_read(
        "stock.quant.package",
        [("name", "like", "Carton %/27")],
        ["id", "name"],
    )

    # Build map product_id → (default_code, name, weight, capacity)
    prod_ids = list({m["product_id"][0] for m in moves})
    prods = search_read(
        "product.product",
        [("id", "in", prod_ids)],
        ["id", "default_code", "name", "weight"],
    )
    tmpls = search_read(
        "product.template",
        [("id", "in", list({p["id"] for p in prods}))],
        ["id"],  # we will read from product.product via product_tmpl_id later
    )
    # Read x_carton_capacity at template level using default_code lookup
    prods_full = search_read(
        "product.product",
        [("id", "in", prod_ids)],
        ["id", "default_code", "name", "weight", "product_tmpl_id"],
    )
    tmpl_ids = list({p["product_tmpl_id"][0] for p in prods_full if p["product_tmpl_id"]})
    tmpls_full = search_read(
        "product.template",
        [("id", "in", tmpl_ids)],
        ["id", "x_carton_capacity"],
    )
    cap_by_tmpl = {t["id"]: t.get("x_carton_capacity") or 0 for t in tmpls_full}

    prod_map = {}
    for p in prods_full:
        tmpl_id = p["product_tmpl_id"][0] if p["product_tmpl_id"] else None
        cap = cap_by_tmpl.get(tmpl_id, 0)
        code = p.get("default_code") or p["name"]
        if code in CAP_OVERRIDE:
            cap = CAP_OVERRIDE[code]
        prod_map[p["id"]] = {
            "id": p["id"],
            "code": code,
            "name": p["name"],
            "weight": p.get("weight") or 0,
            "capacity": cap,
            "tmpl_id": tmpl_id,
        }

    return picking, moves, mls, pkgs, prod_map


def plan_distribution(moves, prod_map):
    """For each move, decide how many units go to each pack carton + loose cartons."""
    plan = {}  # move_id → {pack_per: int, loose_qty: int, loose_chunks: [int], cap: int}
    for mv in moves:
        prod_id = mv["product_id"][0]
        prod = prod_map[prod_id]
        total = int(mv["quantity"])
        code = prod["code"]

        if code in PACK_PER_UNIT:
            pack_per = PACK_PER_UNIT[code]
        elif prod["name"] == POMPES_PRODUCT_NAME or prod_id == 2410:
            pack_per = POMPES_PER_PACK
        elif prod["name"] == PACK_SKU_NAME:
            pack_per = 1  # the SKU line itself
        else:
            pack_per = 0

        pack_total = pack_per * N_PACKS
        loose = total - pack_total
        if loose < 0:
            raise ValueError(f"NEGATIVE loose for {code}: total={total} pack_total={pack_total}")

        cap = prod["capacity"] or loose or 1
        loose_chunks = []
        remaining = loose
        while remaining > 0:
            take = min(cap, remaining)
            loose_chunks.append(take)
            remaining -= take

        plan[mv["id"]] = {
            "product_id": prod_id,
            "code": code,
            "name": prod["name"],
            "total": total,
            "pack_per": pack_per,
            "pack_total": pack_total,
            "loose_qty": loose,
            "loose_chunks": loose_chunks,
            "capacity": cap,
            "location_id": mv["location_id"][0],
            "location_dest_id": mv["location_dest_id"][0],
            "uom_id": mv["product_uom"][0],
        }
    return plan


def print_plan(plan, prod_map):
    print(f"\n{'='*80}")
    print(f"  PLAN DE RÉORG MYVO/OUT/00053 — {N_PACKS} packs Holicare + loose")
    print(f"{'='*80}")
    print(f"\n{'Produit':40s} | {'total':>5s} | {'pack/u':>6s} | {'pack tot':>8s} | "
          f"{'loose':>5s} | loose chunks")
    print("-" * 110)
    grand_total = 0
    pack_total_all = 0
    loose_total_all = 0
    for mv_id, p in plan.items():
        chunks = ",".join(str(c) for c in p["loose_chunks"]) or "-"
        print(f"{(p['code'] or p['name'])[:40]:40s} | {p['total']:>5d} | "
              f"{p['pack_per']:>6d} | {p['pack_total']:>8d} | {p['loose_qty']:>5d} | "
              f"[{chunks}]")
        grand_total += p["total"]
        pack_total_all += p["pack_total"]
        loose_total_all += p["loose_qty"]
    print("-" * 110)
    print(f"{'TOTAL':40s} | {grand_total:>5d} | {'':>6s} | {pack_total_all:>8d} | "
          f"{loose_total_all:>5d}")

    # Count packages
    n_loose = sum(len(p["loose_chunks"]) for p in plan.values())
    print(f"\n=> {N_PACKS} packages Pack Demarrage + {n_loose} packages Loose = {N_PACKS+n_loose} cartons total")


def execute_reorg(picking, moves, mls_existing, old_pkgs, plan, prod_map):
    company_id = picking["company_id"][0]
    now_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n=== EXECUTING reorg on picking #{PICKING_ID} ({PICKING_NAME}) ===")

    # Step 1: Detach all current packages from existing move_lines
    ml_ids = [ml["id"] for ml in mls_existing]
    print(f"\n[1] Detaching result_package_id on {len(ml_ids)} existing move_lines...")
    if ml_ids:
        write("stock.move.line", ml_ids, {"result_package_id": False})

    # Step 2: Create 30 Pack Démarrage packages
    print(f"\n[2] Creating {N_PACKS} 'Pack Démarrage Holicare N/{N_PACKS}' packages...")
    pack_pkg_ids = []
    for n in range(1, N_PACKS + 1):
        pkg_id = create("stock.quant.package", {
            "name": f"Pack Démarrage Holicare {n}/{N_PACKS}",
        })
        pack_pkg_ids.append(pkg_id)
    print(f"    Created pkg ids: {pack_pkg_ids[0]}..{pack_pkg_ids[-1]}")

    # Step 3: For each move, create new split move_lines and unlink old ones
    print(f"\n[3] Splitting move_lines per move...")

    # Build loose package counter (single numbering across all categories)
    loose_total = sum(len(p["loose_chunks"]) for p in plan.values())
    loose_idx = 0
    loose_pkg_cache = {}  # (move_id, chunk_idx) → pkg_id

    # Pre-create loose packages in LOOSE_ORDER to match the natural categorisation
    # We iterate plan items in LOOSE_ORDER's product order for clean numbering
    loose_order_pids = []
    for code, _ in LOOSE_ORDER:
        for mv_id, p in plan.items():
            if p["code"] == code:
                loose_order_pids.append(mv_id)
                break
    # Append leftover moves (POMPES, Pack SKU) — they have loose_qty=0 in our plan
    for mv_id, p in plan.items():
        if mv_id not in loose_order_pids and p["loose_qty"] > 0:
            loose_order_pids.append(mv_id)

    for mv_id in loose_order_pids:
        p = plan[mv_id]
        for chunk_idx, chunk_qty in enumerate(p["loose_chunks"]):
            loose_idx += 1
            cat = next((c for code, c in LOOSE_ORDER if code == p["code"]), p["code"])
            pname = (p["code"] or p["name"]).replace("-", " ")
            pkg_id = create("stock.quant.package", {
                "name": f"Loose {loose_idx}/{loose_total} - {pname} ({chunk_qty} ex.)",
            })
            loose_pkg_cache[(mv_id, chunk_idx)] = pkg_id

    # Now split move_lines per move
    for mv in moves:
        mv_id = mv["id"]
        p = plan[mv_id]
        prod_id = p["product_id"]
        loc_id = p["location_id"]
        dest_id = p["location_dest_id"]
        uom_id = p["uom_id"]

        # Get existing move_lines for this move
        these_mls = [ml for ml in mls_existing if ml["move_id"][0] == mv_id]
        old_ml_ids = [ml["id"] for ml in these_mls]

        new_ml_ids = []

        # Pack split: N_PACKS move_lines of qty=pack_per
        if p["pack_per"] > 0:
            for n in range(N_PACKS):
                new_ml = create("stock.move.line", {
                    "move_id": mv_id,
                    "picking_id": PICKING_ID,
                    "product_id": prod_id,
                    "product_uom_id": uom_id,
                    "location_id": loc_id,
                    "location_dest_id": dest_id,
                    "quantity": p["pack_per"],
                    "result_package_id": pack_pkg_ids[n],
                    "company_id": company_id,
                    "date": now_dt,
                })
                new_ml_ids.append(new_ml)

        # Loose split: one move_line per loose chunk
        for chunk_idx, chunk_qty in enumerate(p["loose_chunks"]):
            pkg_id = loose_pkg_cache[(mv_id, chunk_idx)]
            new_ml = create("stock.move.line", {
                "move_id": mv_id,
                "picking_id": PICKING_ID,
                "product_id": prod_id,
                "product_uom_id": uom_id,
                "location_id": loc_id,
                "location_dest_id": dest_id,
                "quantity": chunk_qty,
                "result_package_id": pkg_id,
                "company_id": company_id,
                "date": now_dt,
            })
            new_ml_ids.append(new_ml)

        # Now unlink the old aggregated move_lines (they had result_package_id=False set)
        if old_ml_ids:
            unlink("stock.move.line", old_ml_ids)

        print(f"  mv#{mv_id} {(p['code'] or p['name'])[:40]:40s} | "
              f"{len(old_ml_ids)} → {len(new_ml_ids)} mls")

    # Step 4: Unlink old 'Carton N/27' packages
    print(f"\n[4] Unlinking {len(old_pkgs)} old 'Carton N/27' packages...")
    old_pkg_ids = [pkg["id"] for pkg in old_pkgs]
    if old_pkg_ids:
        try:
            unlink("stock.quant.package", old_pkg_ids)
            print(f"    Deleted: {old_pkg_ids}")
        except Exception as e:
            print(f"    WARN couldn't delete all (probably some still referenced): {e}")

    print(f"\n=== DONE ===")


def main():
    picking, moves, mls, pkgs, prod_map = load_state()
    print(f"Loaded picking #{picking['id']} {picking['name']} state={picking['state']}")
    print(f"  {len(moves)} moves | {len(mls)} move_lines | {len(pkgs)} old packages")

    plan = plan_distribution(moves, prod_map)
    print_plan(plan, prod_map)

    if DRY_RUN:
        print(f"\n[DRY_RUN=True] No changes applied. Set DRY_RUN=False to execute.")
    else:
        execute_reorg(picking, moves, mls, pkgs, plan, prod_map)


if __name__ == "__main__":
    main()
