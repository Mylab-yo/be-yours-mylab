"""Probe l'etat du suivi colis dans Odoo : transporteurs, champs tracking sur BL,
templates mail livraison, derniers BL avec/sans tracking."""
from scripts.odoo._client import search_read, execute

print("=" * 70)
print("1) Transporteurs (delivery.carrier)")
try:
    carriers = search_read("delivery.carrier", [],
        ["id", "name", "delivery_type", "active"], limit=50)
    for c in carriers:
        print(f"  id={c['id']:>3} type={c.get('delivery_type'):<12} active={c.get('active')}  {c['name']}")
except Exception as e:
    print("  ERREUR:", e)

print("=" * 70)
print("2) Champs 'carrier'/'tracking' sur stock.picking")
try:
    fg = execute("stock.picking", "fields_get", [], {"attributes": ["string", "type"]})
    for fname, meta in sorted(fg.items()):
        if "carrier" in fname or "tracking" in fname:
            print(f"  {fname:<28} {meta.get('type'):<10} {meta.get('string')}")
except Exception as e:
    print("  ERREUR:", e)

print("=" * 70)
print("3) Derniers 8 BL sortants (picking_type_code=outgoing)")
try:
    pks = search_read("stock.picking",
        [("picking_type_code", "=", "outgoing")],
        ["id", "name", "state", "carrier_id", "carrier_tracking_ref", "date_done"],
        limit=8)
    for p in pks:
        print(f"  {p['name']:<16} state={p['state']:<10} "
              f"carrier={p.get('carrier_id')} ref={p.get('carrier_tracking_ref')!r}")
except Exception as e:
    print("  ERREUR:", e)

print("=" * 70)
print("4) Templates mail sur model stock.picking")
try:
    tmpls = search_read("mail.template",
        [("model", "=", "stock.picking")],
        ["id", "name", "subject", "email_to", "partner_to"], limit=20)
    if not tmpls:
        print("  (aucun)")
    for t in tmpls:
        print(f"  id={t['id']:>3} {t['name']!r} subject={t.get('subject')!r}")
except Exception as e:
    print("  ERREUR:", e)
