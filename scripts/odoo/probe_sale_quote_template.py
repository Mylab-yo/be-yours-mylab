"""Check sale.order.template + sale_pdf_quote_builder module for filename override."""
from scripts.odoo._client import search_read

# Find quote template "DEVIS PAR DEFAUT YO"
qts = search_read(
    "sale.order.template",
    [],
    [],
    limit=20,
)
print(f"=== sale.order.template ({len(qts)}) ===")
for q in qts:
    print(f"  ID {q.get('id')} : {q.get('name')!r}")
    for k, v in q.items():
        if k in ('id', 'name'): continue
        # Show only short / interesting fields
        if isinstance(v, (str, int, bool, float)) or v is None:
            if v and 'pdf' in k.lower() or 'report' in k.lower() or 'file' in k.lower():
                print(f"    {k} = {v!r}")
        elif isinstance(v, list) and len(v) > 0:
            if 'pdf' in k.lower() or 'report' in k.lower() or 'file' in k.lower():
                print(f"    {k} = {v!r}")

# Find sale-related modules installed
print("\n=== Installed sale_* modules ===")
mods = search_read(
    "ir.module.module",
    [("state", "=", "installed"),
     "|", ("name", "like", "sale_"), ("name", "like", "pdf_quote")],
    ["id", "name", "shortdesc"],
)
for m in mods:
    print(f"  {m['name']:40s} | {m['shortdesc']}")
