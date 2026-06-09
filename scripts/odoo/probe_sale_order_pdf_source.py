"""Debug : find ALL reports/actions/templates that could produce a quote PDF."""
from scripts.odoo._client import search_read

# 1) All ir.actions.report related to sale or report
print("=== All ir.actions.report for sale.order / containing 'sale' or 'quote' or 'devis' ===")
reports = search_read(
    "ir.actions.report",
    ["|", "|", "|", "|",
     ("model", "=", "sale.order"),
     ("report_name", "ilike", "sale"),
     ("report_name", "ilike", "quote"),
     ("report_name", "ilike", "devis"),
     ("name", "ilike", "devis"),
    ],
    ["id", "name", "model", "report_name", "print_report_name", "binding_model_id", "binding_type"],
)
for r in sorted(reports, key=lambda x: x["id"]):
    bind = r["binding_model_id"][1] if r["binding_model_id"] else "-"
    print(f"  ID {r['id']:4d} | model={r['model']:20s} | binding={bind:20s} | name={r['name']}")
    print(f"           report_name={r['report_name']}")
    print(f"           print_report_name={r['print_report_name']!r}")

# 2) Mail templates referenced for sale order
print("\n=== Mail templates for model 'sale.order' ===")
tmpls = search_read(
    "mail.template",
    [("model", "=", "sale.order")],
    ["id", "name", "report_template_ids", "report_name", "subject"],
)
for t in tmpls:
    print(f"  template#{t['id']} : {t['name']!r}")
    print(f"    subject     = {t['subject']!r}")
    print(f"    report_name = {t['report_name']!r}")
    print(f"    report_templates = {t['report_template_ids']}")

# 3) Check sale.order.template_id or any default report config
print("\n=== sale_pdf_quote_builder module / quote templates ? ===")
# Some Odoo versions have sale.order.template with report_name override
try:
    qt = search_read(
        "sale.order.template",
        [],
        ["id", "name"],
        limit=10,
    )
    print(f"  sale.order.template count : {len(qt)}")
    for q in qt:
        print(f"    template#{q['id']} : {q['name']}")
except Exception as e:
    print(f"  No sale.order.template ({e})")
