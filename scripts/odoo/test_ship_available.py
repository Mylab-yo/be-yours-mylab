"""Teste l'action 'Preparer le dispo' sur un BL, SANS valider (reversible).
Execute l'action serveur puis annule la reservation -> aucun mouvement de stock.

Usage: python -m scripts.odoo.test_ship_available MYVO/OUT/00025"""
import sys
from scripts.odoo._client import search, search_read, execute

name = sys.argv[1] if len(sys.argv) > 1 else None
domain = [("name", "=", name)] if name else \
    [("picking_type_code", "=", "outgoing"), ("state", "=", "confirmed")]
pk = search_read("stock.picking", domain, ["id", "name", "state"], limit=1)[0]
pid = pk["id"]
sa_id = search("ir.actions.server", [("name", "=", "Préparer le dispo")])[0]
print(f"BL {pk['name']} (id={pid}) state={pk['state']} — execution action {sa_id}")

err = None
try:
    execute("ir.actions.server", "run", [[sa_id]],
            {"context": {"active_model": "stock.picking",
                         "active_ids": [pid], "active_id": pid}})
    print("Action executee. Pre-remplissage :")
    moves = search_read("stock.move", [("picking_id", "=", pid)],
        ["product_id", "product_uom_qty", "quantity", "picked"])
    for m in moves:
        print(f"  {m['product_id'][1][:34]:<34} demande={m['product_uom_qty']:>4.0f} "
              f"fait={m.get('quantity'):>4.0f} picked={m.get('picked')}")
except Exception as e:
    err = e
    msg = str(e)
    print(f"EXCEPTION (attendu si garde-fou) : {msg[:200]}")
finally:
    # ORDRE IMPORTANT : remettre picked=False AVANT do_unreserve, sinon Odoo 18
    # garde la quantite des lignes "picked" et le BL reste en state=assigned.
    mv = search("stock.move", [("picking_id", "=", pid)])
    if mv:
        execute("stock.move", "write", [mv, {"picked": False}])
    try:
        execute("stock.picking", "do_unreserve", [[pid]])
    except Exception as ue:
        if "cannot marshal None" not in str(ue):
            raise
    after = search_read("stock.picking", [("id", "=", pid)], ["state"])[0]["state"]
    qsum = sum(m.get("quantity") or 0 for m in search_read(
        "stock.move", [("picking_id", "=", pid)], ["quantity"]))
    print(f"-> BL restaure (state={after}, sum(quantity)={qsum}, picked=False)")

if err and "Aucun stock disponible" in str(err):
    print("GARDE-FOU OK : UserError 'Aucun stock disponible' bien levee.")
