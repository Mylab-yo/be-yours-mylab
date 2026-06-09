"""Inspect delivery line on S00488 (and the palette carrier product)."""
from scripts.odoo._client import search_read, search

# S00488 lines
so = search_read("sale.order", [("name", "=", "S00488")],
                 ["id", "name", "carrier_id", "shipping_weight", "partner_shipping_id"])[0]
print(f"=== {so['name']} ===")
print(f"  carrier_id: {so['carrier_id']}")
print(f"  shipping_weight: {so['shipping_weight']}")

# Print partner country
if so["partner_shipping_id"]:
    p = search_read("res.partner", [("id", "=", so["partner_shipping_id"][0])],
                    ["name", "country_id"])[0]
    print(f"  shipping_partner: {p['name']} / country={p['country_id']}")

# Order lines
lines = search_read("sale.order.line", [("order_id", "=", so["id"])],
                    ["id", "name", "product_id", "is_delivery", "price_unit", "product_uom_qty"])
print(f"\n  Lines ({len(lines)}):")
for line in lines:
    flag = "[DELIVERY]" if line.get("is_delivery") else "          "
    prod = line["product_id"][1] if line["product_id"] else "-"
    print(f"  {flag} id={line['id']} | name={line['name']!r} | prod={prod} | "
          f"price={line['price_unit']} | qty={line['product_uom_qty']}")

# Carrier 19 delivery product
print("\n=== Carrier id=19 (Envoi Palette) ===")
carrier = search_read("delivery.carrier", [("id", "=", 19)],
                      ["id", "name", "product_id", "delivery_type", "fixed_price",
                       "country_ids"])[0]
print(f"  name: {carrier['name']!r}")
print(f"  delivery_type: {carrier['delivery_type']}")
print(f"  fixed_price: {carrier['fixed_price']}")
print(f"  product_id: {carrier['product_id']}")
print(f"  country_ids count: {len(carrier['country_ids'])}")

# Inspect the delivery product
if carrier["product_id"]:
    prod = search_read("product.product", [("id", "=", carrier["product_id"][0])],
                       ["id", "name", "default_code", "list_price", "type"])[0]
    print(f"\n  delivery product#{prod['id']}: name={prod['name']!r}, code={prod['default_code']!r}, "
          f"list_price={prod['list_price']}, type={prod['type']}")
