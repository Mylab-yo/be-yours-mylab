"""Confirme les champs Odoo 18 utilises par l'action 'Preparer le dispo'.
Reversible : action_assign puis do_unreserve -> remet le picking dans son etat initial."""
from scripts.odoo._client import search_read, execute

pk = search_read("stock.picking",
    [("picking_type_code", "=", "outgoing"), ("state", "=", "confirmed")],
    ["id", "name", "state"], limit=1)[0]
pid = pk["id"]
print(f"Picking test: {pk['name']} (id={pid}) state={pk['state']}")

print("\nChamps stock.move (quantity/picked/product_uom_qty/state) :")
fg = execute("stock.move", "fields_get", [["quantity", "picked", "product_uom_qty", "state"]],
             {"attributes": ["string", "type", "readonly"]})
for f, m in fg.items():
    print(f"  {f}: {m}")
print("product.product a 'is_storable' ?",
      "is_storable" in execute("product.product", "fields_get", [], {"attributes": ["type"]}))

moves = search_read("stock.move", [("picking_id", "=", pid)],
    ["product_id", "product_uom_qty", "quantity", "picked", "state"])
print("\nAVANT action_assign :")
for m in moves:
    print(f"  {m['product_id'][1][:30]:<30} demande={m['product_uom_qty']} quantity={m.get('quantity')} picked={m.get('picked')} state={m['state']}")

execute("stock.picking", "action_assign", [[pid]])
moves = search_read("stock.move", [("picking_id", "=", pid)],
    ["product_id", "product_uom_qty", "quantity", "picked", "state"])
print("\nAPRES action_assign (quantity doit = reserve) :")
for m in moves:
    print(f"  {m['product_id'][1][:30]:<30} demande={m['product_uom_qty']} quantity={m.get('quantity')} picked={m.get('picked')} state={m['state']}")

execute("stock.picking", "do_unreserve", [[pid]])
print("\ndo_unreserve OK -> picking restaure")
