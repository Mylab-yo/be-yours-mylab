"""Read-only probe: list all pickings + packages + SO state for LA TRESSE PARISIENNE."""
from scripts.odoo._client import search_read, search

# Find SO S00418
sos = search_read("sale.order", [("name", "=", "S00418")],
                  ["id", "name", "state", "partner_id", "locked", "picking_ids"])
if not sos:
    print("SO S00418 introuvable")
    raise SystemExit(0)
so = sos[0]
print(f"=== SO {so['name']} (id={so['id']}) ===")
print(f"  state={so['state']}  locked={so['locked']}  partner={so['partner_id']}")
print(f"  picking_ids={so['picking_ids']}")
print()

# All pickings linked to this SO (outgoing + returns)
pickings = search_read("stock.picking",
    ["|", ("origin", "=", so['name']), ("id", "in", so['picking_ids'])],
    ["id", "name", "state", "origin", "picking_type_id", "scheduled_date",
     "move_line_ids", "backorder_id", "return_id"])
print(f"=== Pickings ({len(pickings)}) ===")
for p in pickings:
    print(f"\n  [{p['id']}] {p['name']}  state={p['state']}  type={p['picking_type_id'][1] if p['picking_type_id'] else '?'}")
    print(f"      origin={p['origin']}  backorder_id={p['backorder_id']}  scheduled={p['scheduled_date']}")
    if p['move_line_ids']:
        mls = search_read("stock.move.line",
            [("id", "in", p['move_line_ids'])],
            ["id", "product_id", "quantity", "result_package_id", "state"])
        pkg_ids = set()
        for ml in mls:
            if ml['result_package_id']:
                pkg_ids.add(ml['result_package_id'][0])
        print(f"      move_lines: {len(mls)}  packages_used: {len(pkg_ids)}")
        if pkg_ids:
            pkgs = search_read("stock.quant.package",
                [("id", "in", list(pkg_ids))],
                ["id", "name"])
            for pkg in pkgs:
                print(f"        - pkg#{pkg['id']}: {pkg['name']}")
