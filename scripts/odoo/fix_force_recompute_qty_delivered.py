"""Force le recompute de qty_delivered sur sol#411, 412 apres lien tardif sale_line_id."""
from scripts.odoo._client import execute, search_read

# 1. Verifier que mv#968 (IN/00017) a aussi un sale_line_id
print("=== Avant ===")
for mv_id in (147, 148, 968, 969, 988, 989):
    mv = search_read("stock.move", [("id", "=", mv_id)],
                     ["id", "sale_line_id", "state", "quantity",
                      "location_id", "location_dest_id"])[0]
    sl = mv["sale_line_id"][0] if mv["sale_line_id"] else None
    print(f"  mv#{mv_id} state={mv['state']:6s} qty={mv['quantity']:6.1f} "
          f"sol={sl} loc {mv['location_id'][0]} -> {mv['location_dest_id'][0]}")

# 2. Trigger recompute en re-ecrivant quantity (meme valeur) sur les nouveaux moves
print("\n=== Trigger recompute via re-write quantity ===")
for mv_id in (988, 989):
    mv = search_read("stock.move", [("id", "=", mv_id)], ["quantity"])[0]
    q = mv["quantity"]
    execute("stock.move", "write", [[mv_id], {"quantity": q}])
    print(f"  mv#{mv_id}: re-wrote quantity={q}")

# 3. Verification
print("\n=== Apres ===")
sols = search_read("sale.order.line", [("id", "in", [411, 412])],
                   ["id", "qty_delivered", "qty_invoiced", "product_id"])
for s in sols:
    print(f"  sol#{s['id']} delivered={s['qty_delivered']} invoiced={s['qty_invoiced']} | "
          f"{s['product_id'][1] if s['product_id'] else '?'}")

so = search_read("sale.order", [("id", "=", 389)], ["invoice_status"])[0]
print(f"\nS00422 invoice_status: {so['invoice_status']}")
