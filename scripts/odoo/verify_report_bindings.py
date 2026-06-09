"""Verify bindings on all patched reports are intact."""
from scripts.odoo._client import search_read

IDS = [412, 413, 449, 775, 507, 325, 327]

reports = search_read(
    "ir.actions.report",
    [("id", "in", IDS)],
    ["id", "name", "model", "binding_model_id", "binding_type",
     "binding_view_types", "print_report_name"],
)

print(f"{'ID':>4} | {'name':30s} | {'model':20s} | {'binding_type':15s} | {'binding_views':15s}")
print("-" * 100)
for r in sorted(reports, key=lambda x: x["id"]):
    bind_model = r["binding_model_id"][1] if r["binding_model_id"] else "NONE"
    print(f"{r['id']:>4} | {r['name'][:30]:30s} | {r['model'][:20]:20s} | "
          f"{r['binding_type'] or '-':15s} | {r['binding_view_types'] or '-':15s}")
    if not r["binding_model_id"]:
        print(f"      => MISSING binding_model_id !")
    if r["binding_type"] != "report":
        print(f"      => binding_type is {r['binding_type']!r} not 'report' !")
