"""Create 'Renumeroter cartons' server action + button on stock.picking.

Usage in UI: open a picking, click the new 'Renumeroter cartons' button in
the header (next to 'Repartir en cartons'). It scans all packages used by
the picking, sorts them by id ASC, and renames them as 'Carton 1/N - <suffix>'
keeping the family label after ' - '. Run this AFTER manual changes (move lines
displaced between cartons, carton emptied, etc) to get clean numbering.
"""
from scripts.odoo._client import search, create, write, search_read

ACTION_NAME = "Renumeroter cartons"
VIEW_KEY = "mylab.picking_form_renumber_button"

CODE = """# Renumber packages used by this picking (1/N -> N/N) keeping the family label
for picking in records:
    pkg_ids = set()
    for ml in picking.move_line_ids:
        if ml.result_package_id:
            pkg_ids.add(ml.result_package_id.id)
    if not pkg_ids:
        continue
    pkgs = env["stock.quant.package"].browse(sorted(pkg_ids))
    total = len(pkgs)
    idx = 1
    for pkg in pkgs:
        name = pkg.name or ""
        # Extract suffix after first " - " if present
        if " - " in name:
            parts = name.split(" - ", 1)
            suffix = parts[1]
            new_name = "Carton " + str(idx) + "/" + str(total) + " - " + suffix
        else:
            new_name = "Carton " + str(idx) + "/" + str(total)
        pkg.write({"name": new_name})
        idx = idx + 1
"""


def main():
    # 1. Create / update server action
    model_ids = search("ir.model", [("model", "=", "stock.picking")])
    sa_values = {
        "name": ACTION_NAME,
        "model_id": model_ids[0],
        "binding_model_id": model_ids[0],
        "binding_type": "action",
        "state": "code",
        "code": CODE,
    }
    existing_sa = search("ir.actions.server", [("name", "=", ACTION_NAME),
                                                ("binding_model_id.model", "=", "stock.picking")])
    if existing_sa:
        write("ir.actions.server", existing_sa, sa_values)
        sa_id = existing_sa[0]
        print(f"Updated server action id={sa_id}")
    else:
        sa_id = create("ir.actions.server", sa_values)
        print(f"Created server action id={sa_id}")

    # 2. Inherit picking form view to add button in header
    ref = search_read("ir.model.data",
                      [("module", "=", "stock"), ("name", "=", "view_picking_form")],
                      ["res_id"], limit=1)
    parent_id = ref[0]["res_id"]

    arch = f"""<data>
    <xpath expr="//header" position="inside">
        <button name="{sa_id}" type="action"
                string="Renumeroter cartons"
                invisible="state not in ('assigned','done')"/>
    </xpath>
</data>"""

    view_values = {
        "name": VIEW_KEY,
        "type": "form",
        "model": "stock.picking",
        "inherit_id": parent_id,
        "arch_base": arch,
        "key": VIEW_KEY,
    }
    existing_v = search("ir.ui.view", [("key", "=", VIEW_KEY)])
    if existing_v:
        write("ir.ui.view", existing_v, {"arch_base": arch})
        print(f"Updated inherited view id={existing_v[0]}")
    else:
        vid = create("ir.ui.view", view_values)
        print(f"Created inherited view id={vid}")


if __name__ == "__main__":
    main()
