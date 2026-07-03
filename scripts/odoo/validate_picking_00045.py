"""Valide MYVO/OUT/00045 (id=61) SANS LOT.

Le picking-type a use_create_lots=use_existing_lots=False -> Odoo n'exige pas de
lot a la validation. Les 12 moves sont deja assigned/reserves (quantity=demande),
donc pas de reliquat. button_validate devrait terminer directement.
"""
from _client import execute, search_read

PID = 61
NAME = "MYVO/OUT/00045"

pk = search_read("stock.picking", [("id", "=", PID)], ["name", "state"])[0]
assert pk["name"] == NAME, f"ID/NAME mismatch: {pk['name']}"
print(f"AVANT : {pk['name']} state={pk['state']}")
if pk["state"] == "done":
    raise SystemExit("Deja valide (done) — rien a faire.")
assert pk["state"] == "assigned", f"Etat inattendu {pk['state']} (attendu assigned)"

res = execute("stock.picking", "button_validate", [[PID]])
print(f"button_validate -> {res!r}")

# Si un wizard est renvoye (backorder/immediate), le traiter
if isinstance(res, dict) and res.get("res_model"):
    model = res["res_model"]
    ctx = res.get("context", {})
    print(f"  wizard renvoye: {model} ctx={ctx}")
    if model == "stock.backorder.confirmation":
        wiz = execute(model, "create", [{"pick_ids": [(6, 0, [PID])]}], {"context": ctx})
        execute(model, "process", [[wiz]])   # cree le reliquat + valide
        print("  -> backorder confirmation process()")
    elif model == "stock.immediate.transfer":
        wiz = execute(model, "create", [{"pick_ids": [(6, 0, [PID])]}], {"context": ctx})
        execute(model, "process", [[wiz]])
        print("  -> immediate transfer process()")
    else:
        print(f"  !! wizard non gere automatiquement: {model} — a traiter a la main")

# Verif finale
pk2 = search_read("stock.picking", [("id", "=", PID)],
                  ["name", "state", "date_done", "backorder_ids"])[0]
print(f"\nAPRES : {pk2['name']} state={pk2['state']} date_done={pk2.get('date_done')} "
      f"backorders={pk2.get('backorder_ids')}")

mv = search_read("stock.move", [("picking_id", "=", PID)],
                 ["product_id", "product_uom_qty", "quantity", "state"])
print("\n=== moves apres validation ===")
for m in mv:
    print(f"  {m['product_id'][1][:40]:40} demande={m['product_uom_qty']} "
          f"done={m.get('quantity')} state={m['state']}")
