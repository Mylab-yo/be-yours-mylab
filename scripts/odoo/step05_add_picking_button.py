"""Add 'Répartir en cartons' button to stock.picking form view."""
from scripts.odoo._client import search, create, write, search_read

VIEW_NAME = "mylab.picking_form_carton_button"
VIEW_KEY = "mylab.picking_form_carton_button"
SERVER_ACTION_NAME = "Répartir en cartons"


def main():
    # Find parent view via ir.model.data (xml_id is not a field on ir.ui.view)
    ref = search_read("ir.model.data",
                      [("module", "=", "stock"), ("name", "=", "view_picking_form")],
                      ["res_id"], limit=1)
    if not ref:
        raise RuntimeError("Parent view stock.view_picking_form not found in ir.model.data")
    parent_id = ref[0]["res_id"]

    # Find server action
    sa_ids = search("ir.actions.server",
                    [("name", "=", SERVER_ACTION_NAME),
                     ("binding_model_id.model", "=", "stock.picking")])
    if not sa_ids:
        raise RuntimeError(f"Server action '{SERVER_ACTION_NAME}' not found — run task 6 first")
    sa_id = sa_ids[0]

    arch = f"""<data>
    <xpath expr="//header" position="inside">
        <button name="{sa_id}" type="action"
                string="Répartir en cartons"
                class="btn-primary"
                invisible="state not in ('assigned','done')"/>
    </xpath>
</data>"""

    view_values = {
        "name": VIEW_NAME,
        "type": "form",
        "model": "stock.picking",
        "inherit_id": parent_id,
        "arch_base": arch,
        "key": VIEW_KEY,
    }
    existing = search("ir.ui.view", [("key", "=", VIEW_KEY)])
    if existing:
        write("ir.ui.view", existing, {"arch_base": arch})
        print(f"Updated inherited view id={existing[0]}")
    else:
        new_id = create("ir.ui.view", view_values)
        print(f"Created inherited view id={new_id}")


if __name__ == "__main__":
    main()
