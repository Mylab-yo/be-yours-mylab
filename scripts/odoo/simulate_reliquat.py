"""SIMULATION (lecture seule) du bouton 'Preparer le dispo'.

Pour chaque BL sortant confirme : compare la quantite demandee au stock dispo
(free_qty a l'emplacement source) et montre ce qui PARTIRAIT vs ce qui irait
en RELIQUAT. N'ecrit RIEN, ne reserve RIEN, ne valide RIEN.

Usage:
  python -m scripts.odoo.simulate_reliquat                 # scan ~20 BL confirmes
  python -m scripts.odoo.simulate_reliquat MYVO/OUT/00133  # un BL precis
"""
import sys
from scripts.odoo._client import search_read, execute


def avail_at(product_id, location_id):
    """free_qty (dispo non reserve) du produit a l'emplacement source."""
    r = execute("product.product", "read", [[product_id], ["free_qty"]],
                {"context": {"location": location_id}})
    return r[0].get("free_qty") or 0.0


def simulate(picking):
    pid = picking["id"]
    loc = picking["location_id"][0] if picking.get("location_id") else False
    moves = search_read("stock.move", [("picking_id", "=", pid)],
                        ["product_id", "product_uom_qty"], limit=100)
    lines = []
    for m in moves:
        prod = m["product_id"]
        if not prod:
            continue
        demand = m.get("product_uom_qty") or 0.0
        avail = avail_at(prod[0], loc) if loc else 0.0
        ship = max(0.0, min(demand, avail))
        relq = demand - ship
        lines.append({"name": prod[1], "demand": demand, "avail": avail,
                      "ship": ship, "relq": relq})
    return lines


def classify(lines):
    tot_relq = sum(l["relq"] for l in lines)
    tot_ship = sum(l["ship"] for l in lines)
    if tot_relq == 0:
        return "COMPLET"      # tout part
    if tot_ship == 0:
        return "RIEN DISPO"   # rien ne part -> garde-fou
    return "PARTIEL"          # -> reliquat


def show(picking, lines, verdict):
    print(f"\n{'='*72}\n{picking['name']}  <- {picking.get('origin') or '?'}  "
          f"[{verdict}]  client={picking['partner_id'][1][:30] if picking.get('partner_id') else '?'}")
    print(f"  {'Produit':<40} {'Dem.':>5} {'Dispo':>6} {'Expédie':>8} {'Reliquat':>9}")
    for l in lines:
        flag = "  <-- reliquat" if l["relq"] > 0 and l["ship"] > 0 else (
            "  <-- 0 dispo" if l["ship"] == 0 else "")
        print(f"  {l['name'][:40]:<40} {l['demand']:>5.0f} {l['avail']:>6.0f} "
              f"{l['ship']:>8.0f} {l['relq']:>9.0f}{flag}")


def main():
    if len(sys.argv) > 1:
        pks = search_read("stock.picking", [("name", "=", sys.argv[1])],
                          ["id", "name", "origin", "partner_id", "location_id"], limit=1)
    else:
        pks = search_read("stock.picking",
            [("picking_type_code", "=", "outgoing"), ("state", "=", "confirmed")],
            ["id", "name", "origin", "partner_id", "location_id"], limit=20)
    if not pks:
        print("Aucun BL trouve")
        return

    buckets = {"PARTIEL": [], "RIEN DISPO": [], "COMPLET": []}
    for p in pks:
        lines = simulate(p)
        if not lines:
            continue
        v = classify(lines)
        buckets[v].append((p, lines))

    print(f"Scanne {len(pks)} BL confirme(s) : "
          f"{len(buckets['PARTIEL'])} partiels, {len(buckets['COMPLET'])} complets, "
          f"{len(buckets['RIEN DISPO'])} sans stock")

    # Detaille en priorite les PARTIELS (cas reliquat le plus parlant), puis 1 de chaque
    for p, lines in buckets["PARTIEL"][:4]:
        show(p, lines, "PARTIEL")
    for v in ("COMPLET", "RIEN DISPO"):
        if buckets[v]:
            show(buckets[v][0][0], buckets[v][0][1], v)


if __name__ == "__main__":
    main()
