"""Probe current print_report_name on key Odoo reports."""
from scripts.odoo._client import search_read

# Find all reports related to sale, invoice, delivery
reports = search_read(
    "ir.actions.report",
    ["|", "|", "|", "|", "|",
     ("model", "=", "sale.order"),
     ("model", "=", "account.move"),
     ("model", "=", "stock.picking"),
     ("report_name", "like", "saleorder"),
     ("report_name", "like", "invoice"),
     ("report_name", "like", "delivery"),
    ],
    ["id", "name", "model", "report_name", "print_report_name", "binding_model_id"],
)

print(f"=== Reports found: {len(reports)} ===\n")
for r in sorted(reports, key=lambda x: (x["model"], x["name"])):
    print(f"--- ID {r['id']} | model={r['model']} ---")
    print(f"  name         : {r['name']}")
    print(f"  report_name  : {r['report_name']}")
    print(f"  print_report_name : {r['print_report_name']!r}")
    print()
