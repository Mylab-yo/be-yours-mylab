"""Create/update the QWeb views (wrapper + document) and ir.actions.report for MyLab BL.

Two QWeb views are needed:
  - mylab.report_deliveryslip          : wrapper that loops over `docs` and sets `doc`
  - mylab.report_deliveryslip_document : actual content rendered for each picking

The report action points to the wrapper (else `doc` is undefined -> KeyError).
"""
from pathlib import Path
from scripts.odoo._client import search, create, write

WRAPPER_KEY = "mylab.report_deliveryslip"
DOC_KEY = "mylab.report_deliveryslip_document"
REPORT_NAME = "Bon de livraison MyLab"

WRAPPER_FILE = Path("scripts/odoo/templates/bl_deliveryslip_wrapper.xml")
DOC_FILE = Path("scripts/odoo/templates/bl_deliveryslip.xml")


def strip_xml_decl(text: str) -> str:
    if text.lstrip().startswith("<?xml"):
        return text[text.index("?>") + 2:].lstrip()
    return text


def upsert_view(key: str, arch: str) -> int:
    values = {"name": key, "type": "qweb", "arch_base": arch, "key": key}
    existing = search("ir.ui.view", [("key", "=", key)])
    if existing:
        write("ir.ui.view", existing, {"arch_base": arch})
        print(f"  Updated view {key} (id={existing[0]})")
        return existing[0]
    new_id = create("ir.ui.view", values)
    print(f"  Created view {key} (id={new_id})")
    return new_id


def main():
    # 1. Upsert wrapper view
    print("=== Wrapper view ===")
    wrapper_arch = strip_xml_decl(WRAPPER_FILE.read_text(encoding="utf-8"))
    upsert_view(WRAPPER_KEY, wrapper_arch)

    # 2. Upsert document view
    print("=== Document view ===")
    doc_arch = strip_xml_decl(DOC_FILE.read_text(encoding="utf-8"))
    upsert_view(DOC_KEY, doc_arch)

    # 3. Upsert report action -> point to wrapper
    print("=== Report action ===")
    model_ids = search("ir.model", [("model", "=", "stock.picking")])
    model_id = model_ids[0]
    report_values = {
        "name": REPORT_NAME,
        "model": "stock.picking",
        "report_type": "qweb-pdf",
        "report_name": WRAPPER_KEY,        # <- wrapper, not _document
        "report_file": WRAPPER_KEY,
        "binding_model_id": model_id,
        "binding_type": "report",
        "print_report_name": "'BL - ' + object.name",
    }
    # Find by report name (idempotent across report_name changes)
    existing = search("ir.actions.report", [("name", "=", REPORT_NAME)])
    if existing:
        write("ir.actions.report", existing, report_values)
        print(f"  Updated report action id={existing[0]} (report_name={WRAPPER_KEY})")
    else:
        new_id = create("ir.actions.report", report_values)
        print(f"  Created report action id={new_id}")


if __name__ == "__main__":
    main()
