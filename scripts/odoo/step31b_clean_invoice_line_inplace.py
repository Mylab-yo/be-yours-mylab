"""Replace the inheritance view from step31 with a direct str.replace on
the primary invoice template (view 1143).

Per memory project_odoo_pdf_branding: inheritance views via xpath have
been tested and found unstable on this Odoo instance — direct edit of
arch_base is the established pattern.

Idempotent: detects if the patch is already applied.

Run: python step31b_clean_invoice_line_inplace.py
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from _client import search_read, write, unlink

# 1. Remove the previous inheritance view if it exists (from step31)
prev = search_read("ir.ui.view",
                   [("name", "=", "mylab.report_invoice_document_clean_line")],
                   ["id"])
if prev:
    unlink("ir.ui.view", [prev[0]["id"]])
    print(f"✓ Removed previous inheritance view [{prev[0]['id']}]")

# 2. Read view 1143 arch_db
v = search_read("ir.ui.view", [("id", "=", 1143)], ["arch_db"])[0]
arch = v["arch_db"]

# Target: the product line span (uniquely identified by the "Bacon Burger"
# placeholder text Odoo ships with).
OLD = '<span t-if="line.name" t-field="line.name" t-options="{\'widget\': \'text\'}">Bacon Burger</span>'
NEW = (
    '<span t-if="line.product_id" t-out="line.product_id.name">Bacon Burger</span>'
    '<span t-elif="line.name" t-field="line.name" t-options="{\'widget\': \'text\'}"/>'
)

# Idempotency: detect already-patched
if 'line.product_id" t-out="line.product_id.name">Bacon Burger' in arch:
    print("✓ View 1143 already patched — nothing to do")
    sys.exit(0)

if OLD not in arch:
    print(f"ERROR: target span not found in view 1143.")
    print(f"Looked for: {OLD}")
    print()
    # Help debugging — show what the span looks like
    import re
    for m in re.finditer(r'line\.name.{0,80}Bacon Burger', arch):
        print(f"  Found near 'Bacon Burger': {arch[max(0,m.start()-200):m.end()+50]}")
    sys.exit(1)

new_arch = arch.replace(OLD, NEW, 1)
write("ir.ui.view", [1143], {"arch_base": new_arch})
print("✓ View 1143 patched in place — product line now renders product_id.name")
print()
print("Reprints d'anciennes factures + nouvelles factures vont afficher le nom propre.")
print("Test : ouvre une facture dans Odoo → Imprimer → PDF.")
