"""Check product types of S00422 lines to know which need stock pickings."""
from scripts.odoo._client import search_read

sols = search_read(
    "sale.order.line",
    [("order_id", "=", 389), ("display_type", "=", False)],
    ["id", "name", "product_id", "product_uom_qty", "qty_delivered", "move_ids"],
)
prod_ids = [sl["product_id"][0] for sl in sols if sl["product_id"]]
prods = search_read(
    "product.product",
    [("id", "in", prod_ids)],
    ["id", "name", "type"],
)
ptype_map = {p["id"]: p for p in prods}

print(f"{'sol':>6} {'pid':>6} {'type':>10} {'ordered':>9} {'done':>8} {'moves':>6}  product")
for sl in sols:
    pid = sl["product_id"][0] if sl["product_id"] else None
    p = ptype_map.get(pid, {})
    print(f"{sl['id']:>6} {pid or 0:>6} {str(p.get('type','?')):>10} "
          f"{sl['product_uom_qty']:>9.2f} {sl['qty_delivered']:>8.2f} "
          f"{len(sl['move_ids'] or []):>6}  {sl['name'][:60]}")
