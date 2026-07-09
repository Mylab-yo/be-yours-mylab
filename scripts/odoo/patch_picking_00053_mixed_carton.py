"""Patch MIXED carton on MYVO/OUT/00053 : add 2 MSQ NOUR 400ml.

The mixed carton (Loose 31/31) contains 4 products, not 3.
After this patch:
- 4 SHP PUR 500
- 5 SHP HA REPULPE 500
- 2 MSQ VOL 200
- 2 MSQ NOUR 400 (NEW)

MSQ NOUR 400 total becomes 146 (= demand) -> no backorder needed.

Also rename the mixed package to reflect the 4 products.
"""
from datetime import datetime
from scripts.odoo._client import search_read, write, create

PICKING_ID = 69
MSQ_NOUR_400_PRODUCT_ID = None  # will look up


def main():
    # Find mixed pkg
    pkg = search_read(
        "stock.quant.package",
        [("name", "like", "MIXE")],
        ["id", "name"],
    )
    if not pkg:
        print("MIXED pkg not found!")
        return
    pkg = pkg[0]
    print(f"Mixed pkg : pkg#{pkg['id']} {pkg['name']!r}")

    # Find the move for MSQ NOUR 400
    moves = search_read(
        "stock.move",
        [("picking_id", "=", PICKING_ID)],
        ["id", "product_id", "location_id", "location_dest_id", "product_uom"],
    )
    msq_nour_400_mv = None
    for mv in moves:
        prods = search_read("product.product",
                            [("id", "=", mv["product_id"][0])],
                            ["default_code"])
        if prods and prods[0]["default_code"] == "masque-nourrissant-400-ml":
            msq_nour_400_mv = mv
            break
    if not msq_nour_400_mv:
        print("MSQ NOUR 400 move not found!")
        return
    print(f"MSQ NOUR 400 move : mv#{msq_nour_400_mv['id']}")

    # Picking metadata
    picking = search_read("stock.picking", [("id", "=", PICKING_ID)],
                          ["company_id"])[0]
    company_id = picking["company_id"][0]
    now_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Create the new ml: 2 MSQ NOUR 400 in the mixed pkg
    new_ml = create("stock.move.line", {
        "move_id": msq_nour_400_mv["id"],
        "picking_id": PICKING_ID,
        "product_id": msq_nour_400_mv["product_id"][0],
        "product_uom_id": msq_nour_400_mv["product_uom"][0],
        "location_id": msq_nour_400_mv["location_id"][0],
        "location_dest_id": msq_nour_400_mv["location_dest_id"][0],
        "quantity": 2,
        "result_package_id": pkg["id"],
        "company_id": company_id,
        "date": now_dt,
    })
    print(f"Created new ml#{new_ml} : qty=2 MSQ NOUR 400 in pkg#{pkg['id']}")

    # Rename the mixed pkg to include the 4 products
    new_name = "Loose 31/31 - MIXE 4xSHP PUR 500 + 5xSHP HA 500 + 2xMSQ VOL 200 + 2xMSQ NOUR 400"
    write("stock.quant.package", [pkg["id"]], {"name": new_name})
    print(f"Renamed pkg : {new_name!r}")

    # Verify
    print("\n=== Verification ===")
    mls = search_read("stock.move.line", [("result_package_id", "=", pkg["id"])],
                      ["product_id", "quantity"])
    print(f"Mixed pkg now contains {len(mls)} mls:")
    for ml in sorted(mls, key=lambda x: x["product_id"][1]):
        print(f"  qty={ml['quantity']:5.1f} | {ml['product_id'][1]}")

    # Check mv#332 total
    final_mv = search_read("stock.move", [("id", "=", msq_nour_400_mv["id"])],
                           ["product_uom_qty", "quantity"])[0]
    delta = final_mv["quantity"] - final_mv["product_uom_qty"]
    flag = "OK" if delta == 0 else f"DELTA {delta:+.0f}"
    print(f"\nMSQ NOUR 400 move : demand={final_mv['product_uom_qty']:.0f} | "
          f"done={final_mv['quantity']:.0f} | {flag}")


if __name__ == "__main__":
    main()
