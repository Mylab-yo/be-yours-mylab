"""Create a fresh outgoing picking for SO S00418 (LA TRESSE PARISIENNE).

After reset_so_s00418.py wiped the previous deliveries, we need a new
clean picking attached to the SO. Odoo won't auto-regenerate it because
all previous pickings are done/cancel and SO line edits are blocked.

This script creates one stock.picking + one stock.move per SO line
(skipping services and zero-qty), confirms and assigns it.
"""
from scripts.odoo._client import search_read, create, execute

SO_ID = 385
PICKING_TYPE_ID = 10  # MYLAB: Bons de livraison
LOC_SRC = 28          # MYVO/Stock
LOC_DEST = 5          # Partners/Customers


def main():
    so = search_read("sale.order", [("id", "=", SO_ID)],
        ["name", "partner_id", "partner_shipping_id", "company_id", "warehouse_id"])[0]

    # Idempotence: if a non-cancel/non-done picking already exists with origin = S00418, skip
    existing = search_read("stock.picking",
        [("origin", "=", so['name']),
         ("picking_type_id", "=", PICKING_TYPE_ID),
         ("state", "not in", ("done", "cancel"))],
        ["id", "name", "state"])
    if existing:
        print(f"SKIP: picking actif existe deja: {existing}")
        return

    # Create picking
    picking_vals = {
        "partner_id": so['partner_shipping_id'][0],
        "picking_type_id": PICKING_TYPE_ID,
        "location_id": LOC_SRC,
        "location_dest_id": LOC_DEST,
        "origin": so['name'],
        "company_id": so['company_id'][0],
    }
    picking_id = create("stock.picking", picking_vals)
    print(f"Picking #{picking_id} cree")

    # Get SO lines with remaining qty + storable products only
    lines = search_read("sale.order.line", [("order_id", "=", SO_ID)],
        ["id", "product_id", "product_uom_qty", "qty_delivered", "name", "product_uom"])

    moves_created = 0
    skipped_services = 0
    skipped_zero = 0
    for l in lines:
        if not l['product_id']:
            continue
        remaining = l['product_uom_qty'] - l['qty_delivered']
        if remaining <= 0:
            skipped_zero += 1
            continue
        prod = search_read("product.product", [("id", "=", l['product_id'][0])],
            ["id", "name", "type", "is_storable"])[0]
        # In Odoo 18: storable products have is_storable=True (or type='consu' with is_storable)
        if not prod.get('is_storable'):
            skipped_services += 1
            continue

        move_vals = {
            "name": (l['name'] or prod['name'])[:60],
            "product_id": l['product_id'][0],
            "product_uom_qty": remaining,
            "product_uom": l['product_uom'][0],
            "picking_id": picking_id,
            "location_id": LOC_SRC,
            "location_dest_id": LOC_DEST,
            "sale_line_id": l['id'],
            "company_id": so['company_id'][0],
        }
        mid = create("stock.move", move_vals)
        moves_created += 1
        print(f"  + move #{mid}: {prod['name'][:50]:50s}  qty={remaining}")

    print(f"\nTotal: {moves_created} moves crees, {skipped_services} services skippes, {skipped_zero} lignes deja livrees")

    # Confirm + assign
    execute("stock.picking", "action_confirm", [[picking_id]])
    execute("stock.picking", "action_assign", [[picking_id]])

    p_after = search_read("stock.picking", [("id", "=", picking_id)],
        ["name", "state"])[0]
    print(f"\nPicking final: {p_after['name']}  state={p_after['state']}")
    print(f"\nProchaines etapes UI Odoo:")
    print(f"  1. Ouvrir {p_after['name']}")
    print(f"  2. Cliquer 'Repartir en cartons'")
    print(f"  3. Verifier le BL (Bon de livraison MyLab via icone engrenage)")
    print(f"  4. Valider le transfert quand pret")


if __name__ == "__main__":
    main()
