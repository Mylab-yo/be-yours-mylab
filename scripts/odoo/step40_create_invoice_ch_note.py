"""Inject the Switzerland customs origin note into customer invoices.

Creates/updates a QWeb view that INHERITS the standard
`account.report_invoice_document` and xpath-injects a conditional block,
rendered only when the delivery address country is Switzerland
(o.partner_shipping_id.country_id.code == 'CH').

The note (EORI number, preferential origin declaration, VOC-free statement,
"Fait à Cavaillon, le <date>", signature) is stamped with the PDF generation
date via context_timestamp(); posted invoices then cache that PDF so the date
is frozen at first generation — the validated behaviour for a customs document.

Idempotent: upsert by `key`, relaunchable with no side effect (same pattern as
step04_create_bl_report).
"""
from pathlib import Path
from scripts.odoo._client import search, create, write, search_read

VIEW_KEY = "mylab.report_invoice_document_ch_note"
VIEW_NAME = "MyLab — Note origine export Suisse (facture)"
BASE_KEY = "account.report_invoice_document"

ARCH_FILE = Path("scripts/odoo/templates/invoice_ch_origin_note.xml")


def strip_xml_decl(text: str) -> str:
    if text.lstrip().startswith("<?xml"):
        return text[text.index("?>") + 2:].lstrip()
    return text


def main():
    # 1. Resolve the base invoice document view id (inherit target)
    base = search_read("ir.ui.view", [("key", "=", BASE_KEY), ("inherit_id", "=", False)],
                       ["id"])
    if not base:
        raise RuntimeError(f"Base view {BASE_KEY!r} not found")
    base_id = base[0]["id"]
    print(f"Base view {BASE_KEY} -> id={base_id}")

    # 2. Upsert the inheriting view
    arch = strip_xml_decl(ARCH_FILE.read_text(encoding="utf-8"))
    values = {
        "name": VIEW_NAME,
        "type": "qweb",
        "key": VIEW_KEY,
        "inherit_id": base_id,
        "mode": "extension",
        "arch_base": arch,
        "active": True,
    }
    existing = search("ir.ui.view", [("key", "=", VIEW_KEY)])
    if existing:
        write("ir.ui.view", existing, {"inherit_id": base_id, "arch_base": arch,
                                       "active": True})
        print(f"  Updated inherited view {VIEW_KEY} (id={existing[0]})")
    else:
        new_id = create("ir.ui.view", values)
        print(f"  Created inherited view {VIEW_KEY} (id={new_id})")


if __name__ == "__main__":
    main()
