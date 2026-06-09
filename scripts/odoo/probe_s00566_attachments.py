"""Probe attachments on order S00566 (id=533) and S00567 (id=534)."""
from scripts.odoo._client import search_read, execute

# Find order S00566
so = search_read("sale.order", [("name", "in", ["S00566", "S00567"])],
                 ["id", "name", "state", "create_date", "write_date"])
print("=== Orders ===")
for s in so:
    print(f"  S{s['name'][1:]} id={s['id']} state={s['state']} created={s['create_date']} updated={s['write_date']}")

# All attachments on these orders
print("\n=== Attachments on these orders ===")
ids = [s["id"] for s in so]
atts = search_read(
    "ir.attachment",
    ["|",
     ("res_model", "=", "sale.order"), ("res_id", "in", ids),
     ("name", "ilike", "S00566"),
    ],
    ["id", "res_model", "res_id", "name", "create_date", "mimetype", "file_size"],
)
for a in atts:
    print(f"  att#{a['id']} | {a['res_model']}#{a['res_id']} | {a['name']!r}")
    print(f"           created={a['create_date']} mime={a['mimetype']} size={a['file_size']}")

# Now check attachments on mail.compose.message
print("\n=== Recent mail.compose.message attachments ===")
atts2 = search_read(
    "ir.attachment",
    [("res_model", "=", "mail.compose.message"),
     ("name", "ilike", "Devis"),
    ],
    ["id", "name", "create_date"],
    limit=10,
)
for a in atts2:
    print(f"  att#{a['id']} | {a['name']!r} | {a['create_date']}")
