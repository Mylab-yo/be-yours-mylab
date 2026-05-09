"""Create 'Vider et supprimer ce carton' server action on stock.quant.package.

Usage in UI: from a picking, double-click on a package (Carton X/N) to open it,
then Action menu -> 'Vider et supprimer ce carton'. All move lines pointing at
this package are released (result_package_id = False) and the package is deleted
if it has no real stock quants. Run on a picking before validation.
After this, click 'Renumeroter cartons' on the picking to clean up X/N suffixes.
"""
from scripts.odoo._client import search, create, write

ACTION_NAME = "Vider et supprimer ce carton"

CODE = """# Empty + delete the selected package(s) (release move lines + unlink if no quants)
deleted = 0
emptied_only = 0
for pkg in records:
    mls = env["stock.move.line"].search([("result_package_id", "=", pkg.id)])
    if mls:
        mls.write({"result_package_id": False})
    if not pkg.quant_ids:
        pkg.unlink()
        deleted = deleted + 1
    else:
        emptied_only = emptied_only + 1

if deleted or emptied_only:
    log("Vide carton: " + str(deleted) + " supprime(s), " + str(emptied_only) + " vide(s) sans suppression")
"""


def main():
    model_ids = search("ir.model", [("model", "=", "stock.quant.package")])
    sa_values = {
        "name": ACTION_NAME,
        "model_id": model_ids[0],
        "binding_model_id": model_ids[0],
        "binding_type": "action",
        "state": "code",
        "code": CODE,
    }
    existing_sa = search("ir.actions.server", [("name", "=", ACTION_NAME),
                                                ("binding_model_id.model", "=", "stock.quant.package")])
    if existing_sa:
        write("ir.actions.server", existing_sa, sa_values)
        print(f"Updated server action id={existing_sa[0]}")
    else:
        sa_id = create("ir.actions.server", sa_values)
        print(f"Created server action id={sa_id}")


if __name__ == "__main__":
    main()
