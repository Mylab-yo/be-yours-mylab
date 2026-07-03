"""Valide MYVO/OUT/00045 (id=61) avec un LOT GENERIQUE sur les 4 lignes lot-less.

Odoo refuse la sortie d'un produit tracke par lot sans numero de lot. Choix Yoann :
lot placeholder unique 'SANS-LOT-20260703' cree par produit, assigne aux lignes
sans lot, puis validation. Le stock du lot passe negatif (autorise). Idempotent.
"""
from _client import execute, search, search_read, create, write

PID = 61
NAME = "MYVO/OUT/00045"
LOT_NAME = "SANS-LOT-20260703"
COMPANY_ID = 3

pk = search_read("stock.picking", [("id", "=", PID)], ["name", "state"])[0]
assert pk["name"] == NAME, f"ID/NAME mismatch: {pk['name']}"
print(f"AVANT : {pk['name']} state={pk['state']}")
if pk["state"] == "done":
    raise SystemExit("Deja valide (done) — rien a faire.")
assert pk["state"] == "assigned", f"Etat inattendu {pk['state']}"

# 1. Lignes sans lot
mls = search_read("stock.move.line",
                  [("picking_id", "=", PID), ("lot_id", "=", False)],
                  ["id", "product_id", "quantity"])
print(f"\n{len(mls)} ligne(s) sans lot a traiter :")

for ml in mls:
    prod_id = ml["product_id"][0]
    prod_name = ml["product_id"][1]

    # lot generique existant pour ce produit ?
    existing = search("stock.lot",
                      [("name", "=", LOT_NAME), ("product_id", "=", prod_id)])
    if existing:
        lot_id = existing[0]
        print(f"  [{prod_name[:38]:38}] lot existant {LOT_NAME} (id={lot_id})")
    else:
        lot_id = create("stock.lot", {
            "name": LOT_NAME,
            "product_id": prod_id,
            "company_id": COMPANY_ID,
        })
        print(f"  [{prod_name[:38]:38}] lot cree {LOT_NAME} (id={lot_id})")

    write("stock.move.line", [ml["id"]], {"lot_id": lot_id})
    print(f"      -> ml {ml['id']} qty={ml['quantity']} : lot_id={lot_id} assigne")

# 2. Validation
res = execute("stock.picking", "button_validate", [[PID]])
print(f"\nbutton_validate -> {res!r}")
if isinstance(res, dict) and res.get("res_model") == "stock.backorder.confirmation":
    ctx = res.get("context", {})
    wiz = execute("stock.backorder.confirmation", "create",
                  [{"pick_ids": [(6, 0, [PID])]}], {"context": ctx})
    execute("stock.backorder.confirmation", "process", [[wiz]])
    print("  -> backorder confirmation process()")
elif isinstance(res, dict) and res.get("res_model"):
    print(f"  !! wizard non gere : {res['res_model']} — a traiter a la main")

# 3. Verif finale
pk2 = search_read("stock.picking", [("id", "=", PID)],
                  ["name", "state", "date_done", "backorder_ids"])[0]
print(f"\nAPRES : {pk2['name']} state={pk2['state']} date_done={pk2.get('date_done')} "
      f"backorders={pk2.get('backorder_ids')}")
