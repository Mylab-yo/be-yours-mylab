"""Probe sale.order.template fields and any quotation_document model."""
from scripts.odoo._client import search_read, execute

# All fields on sale.order.template
print("=== sale.order.template - all fields ===")
fields = execute("sale.order.template", "fields_get", [[]],
                 {"attributes": ["type", "string"]})
relevant = [f for f in fields if any(k in f.lower() for k in
            ['pdf', 'report', 'file', 'attach', 'document', 'quot'])]
for f in sorted(relevant):
    print(f"  {f:40s} {fields[f]['type']:10s} - {fields[f]['string']}")

# Read template 1 with all those fields
print("\n=== Template 'DEVIS PAR DEFAUT YO' content for relevant fields ===")
tmpl = search_read("sale.order.template", [("id", "=", 1)], relevant)
if tmpl:
    for k, v in tmpl[0].items():
        if v not in (False, [], None, ""):
            print(f"  {k} = {v!r}")

# Check if there's a quotation_document model
print("\n=== Check quotation_document model ===")
try:
    qd_fields = execute("quotation.document", "fields_get", [[]],
                        {"attributes": ["type", "string"]})
    print(f"  quotation.document has {len(qd_fields)} fields")
    qd = search_read("quotation.document", [], list(qd_fields.keys()))
    for d in qd:
        print(f"  {d}")
except Exception as e:
    print(f"  Not 'quotation.document' : {e}")

# Try sale.pdf.form.field or similar
for model in ["sale.pdf.form.field", "header.footer.document.section",
              "ir.attachment"]:
    print(f"\n=== Check {model} ===")
    try:
        fs = execute(model, "fields_get", [[]], {"attributes": ["type"]})
        print(f"  {model} has {len(fs)} fields")
    except Exception as e:
        print(f"  no {model} : {str(e)[:100]}")

# Check ir.attachment for quote-related attachments
print("\n=== Quote-related ir.attachment ===")
atts = search_read(
    "ir.attachment",
    ["|", "|", "|",
     ("res_model", "=", "sale.order.template"),
     ("res_model", "=", "sale.pdf.form.field"),
     ("name", "ilike", "devis"),
     ("name", "ilike", "quote"),
    ],
    ["id", "name", "res_model", "res_id", "mimetype", "file_size"],
    limit=20,
)
for a in atts:
    print(f"  att#{a['id']} | {a['res_model']}#{a['res_id']} | "
          f"{a['name']!r} | {a['mimetype']} | {a['file_size']}b")
