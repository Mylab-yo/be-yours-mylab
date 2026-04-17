"""Create/update the QWeb view and ir.actions.report for MyLab BL."""
from pathlib import Path
from scripts.odoo._client import search, create, write

VIEW_NAME = "mylab.report_deliveryslip_document"
VIEW_KEY = "mylab.report_deliveryslip_document"
REPORT_NAME = "Bon de livraison MyLab"
REPORT_FILENAME = "BL_${object.name}.pdf"
TEMPLATE_FILE = Path("scripts/odoo/templates/bl_deliveryslip.xml")


def main():
    # 1. Read template XML
    arch = TEMPLATE_FILE.read_text(encoding="utf-8")
    # Strip <?xml ?> declaration: Odoo's arch_base expects a fragment (already unicode)
    if arch.lstrip().startswith("<?xml"):
        arch = arch[arch.index("?>") + 2:].lstrip()

    # 2. Upsert ir.ui.view (QWeb template)
    view_values = {
        "name": VIEW_NAME,
        "type": "qweb",
        "arch_base": arch,
        "key": VIEW_KEY,
    }
    existing_view = search("ir.ui.view", [("key", "=", VIEW_KEY)])
    if existing_view:
        write("ir.ui.view", existing_view, {"arch_base": arch})
        view_id = existing_view[0]
        print(f"Updated QWeb view id={view_id}")
    else:
        view_id = create("ir.ui.view", view_values)
        print(f"Created QWeb view id={view_id}")

    # 3. Find stock.picking model id
    model_ids = search("ir.model", [("model", "=", "stock.picking")])
    model_id = model_ids[0]

    # 4. Upsert ir.actions.report
    report_values = {
        "name": REPORT_NAME,
        "model": "stock.picking",
        "report_type": "qweb-pdf",
        "report_name": VIEW_KEY,
        "report_file": VIEW_KEY,
        "binding_model_id": model_id,
        "binding_type": "report",
        "print_report_name": f"'BL - ' + object.name",
    }
    existing_report = search("ir.actions.report",
                             [("report_name", "=", VIEW_KEY)])
    if existing_report:
        write("ir.actions.report", existing_report, report_values)
        print(f"Updated report action id={existing_report[0]}")
    else:
        new_id = create("ir.actions.report", report_values)
        print(f"Created report action id={new_id}")


if __name__ == "__main__":
    main()
