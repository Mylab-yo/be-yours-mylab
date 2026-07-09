# -*- coding: utf-8 -*-
"""Verify FORTIFIANT products + pl3 tiers read back correctly."""
from _client import search_read

KEYS = ["shampoing-fortifiant-200-ml", "shampoing-fortifiant-500-ml",
        "shampoing-fortifiant-1000-ml", "serum-fortifiant-50-ml"]

for key in KEYS:
    t = search_read("product.template", [("default_code", "=", key)],
        ["id","name","default_code","list_price","categ_id","weight",
         "taxes_id","supplier_taxes_id","type","sale_ok","purchase_ok"])
    if not t:
        print(f"!! MISSING {key}"); continue
    t = t[0]
    print(f"\n[{t['id']}] {t['name']}  SKU={t['default_code']}")
    print(f"    categ={t['categ_id'][1]} | poids={t['weight']}kg | list_price={t['list_price']} "
          f"| TVA={t['taxes_id']} achat={t['supplier_taxes_id']} | type={t['type']} "
          f"| vente={t['sale_ok']} achat_ok={t['purchase_ok']}")
    items = search_read("product.pricelist.item",
        [("pricelist_id","=",3),("product_tmpl_id","=",t["id"])],
        ["min_quantity","fixed_price"])
    items.sort(key=lambda x: x["min_quantity"])
    tiers = " · ".join(f"{int(i['min_quantity'])}->{i['fixed_price']}" for i in items)
    print(f"    pl3 tiers ({len(items)}): {tiers if tiers else '(aucun)'}")
