"""Find any picking related to S00422 / CENDREE (origin or partner search)."""
from scripts.odoo._client import search_read

# Search by origin first
pickings_by_origin = search_read(
    "stock.picking",
    [("origin", "ilike", "S00422")],
    ["id", "name", "state", "origin", "partner_id", "scheduled_date",
     "date_done", "backorder_id", "sale_id"],
)
print(f"=== Pickings with origin like 'S00422' ({len(pickings_by_origin)}) ===")
for p in pickings_by_origin:
    sale = p["sale_id"][1] if p["sale_id"] else "-"
    bo = p["backorder_id"][1] if p["backorder_id"] else "-"
    partner = p["partner_id"][1] if p["partner_id"] else "-"
    print(f"  P#{p['id']:5d} | {p['name']:25s} | state={p['state']:10s} | "
          f"origin={p['origin']!r:30s} | partner={partner} | sale_id={sale} | "
          f"bo={bo} | done={p.get('date_done')}")

# Search by partner CENDREE id=1970
pickings_by_partner = search_read(
    "stock.picking",
    [("partner_id", "=", 1970)],
    ["id", "name", "state", "origin", "scheduled_date",
     "date_done", "backorder_id", "sale_id", "create_date"],
)
print(f"\n=== Pickings for partner CENDREE (id=1970) ({len(pickings_by_partner)}) ===")
for p in pickings_by_partner:
    sale = p["sale_id"][1] if p["sale_id"] else "-"
    bo = p["backorder_id"][1] if p["backorder_id"] else "-"
    print(f"  P#{p['id']:5d} | {p['name']:25s} | state={p['state']:10s} | "
          f"origin={p['origin']!r:25s} | sale_id={sale} | bo={bo} | "
          f"created={p.get('create_date')} | done={p.get('date_done')}")

# Also check sale.order procurement_group_id for hidden link
sos = search_read(
    "sale.order",
    [("name", "=", "S00422")],
    ["id", "procurement_group_id"],
)
if sos and sos[0].get("procurement_group_id"):
    pg_id = sos[0]["procurement_group_id"][0]
    print(f"\n=== Procurement group {pg_id} ===")
    pickings_by_pg = search_read(
        "stock.picking",
        [("group_id", "=", pg_id)],
        ["id", "name", "state", "origin", "date_done", "backorder_id"],
    )
    for p in pickings_by_pg:
        bo = p["backorder_id"][1] if p["backorder_id"] else "-"
        print(f"  P#{p['id']:5d} | {p['name']:25s} | state={p['state']:10s} | "
              f"origin={p['origin']!r} | bo={bo} | done={p.get('date_done')}")
else:
    print("\n=== No procurement_group_id on S00422 ===")
