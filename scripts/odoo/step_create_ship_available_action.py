"""Cree/maj l'action serveur 'Preparer le dispo' sur stock.picking + le bouton d'en-tete."""
from pathlib import Path
from scripts.odoo._client import search, create, write, search_read

ACTION_NAME = "Préparer le dispo"
MODEL_NAME = "stock.picking"
CODE_FILE = Path("scripts/odoo/ship_available_code.py")
VIEW_KEY = "mylab.picking_form_ship_available_button"


def upsert_action(model_id):
    code = CODE_FILE.read_text(encoding="utf-8")
    values = {"name": ACTION_NAME, "model_id": model_id, "state": "code",
              "code": code, "binding_model_id": model_id, "binding_type": "action"}
    existing = search("ir.actions.server",
                      [("name", "=", ACTION_NAME), ("model_id", "=", model_id)])
    if existing:
        write("ir.actions.server", existing, values)
        print(f"Updated server action id={existing[0]}")
        return existing[0]
    new_id = create("ir.actions.server", values)
    print(f"Created server action id={new_id}")
    return new_id


def upsert_button(sa_id):
    ref = search_read("ir.model.data",
        [("module", "=", "stock"), ("name", "=", "view_picking_form")],
        ["res_id"], limit=1)
    if not ref:
        raise RuntimeError("Vue parente stock.view_picking_form introuvable")
    parent_id = ref[0]["res_id"]
    arch = f"""<data>
    <xpath expr="//header" position="inside">
        <button name="{sa_id}" type="action"
                string="Préparer le dispo"
                class="btn-primary"
                invisible="state not in ('confirmed','assigned','waiting')"/>
    </xpath>
</data>"""
    values = {"name": VIEW_KEY, "type": "form", "model": "stock.picking",
              "inherit_id": parent_id, "arch_base": arch, "key": VIEW_KEY}
    existing = search("ir.ui.view", [("key", "=", VIEW_KEY)])
    if existing:
        write("ir.ui.view", existing, {"arch_base": arch})
        print(f"Updated button view id={existing[0]}")
    else:
        print(f"Created button view id={create('ir.ui.view', values)}")


def main():
    model_id = search("ir.model", [("model", "=", MODEL_NAME)])[0]
    sa_id = upsert_action(model_id)
    upsert_button(sa_id)


if __name__ == "__main__":
    main()
