"""Valide (READ-ONLY) la logique d'identification + état BL du skill gerer-bl.
N'exécute AUCUNE action (pas de cancel/copy/write). Mirroir de validate_faire_of_preview.py."""
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
from _client import _models, DB, UID, API_KEY


def call(model, method, *args, **kw):
    return _models.execute_kw(DB, UID, API_KEY, model, method, list(args), kw)


PICKING_TYPE_OUT = 10


def identify(term):
    print(f"\n########## TERM: {term!r}")
    dom = ['|', '|',
           ('name', 'ilike', term),
           ('partner_id.name', 'ilike', term),
           ('origin', 'ilike', term),
           ('picking_type_id', '=', PICKING_TYPE_OUT)]
    pks = call('stock.picking', 'search_read', dom,
               fields=['name', 'state', 'partner_id', 'origin', 'sale_id', 'move_ids'],
               order='id desc')
    print(f"{len(pks)} BL trouvés")
    for p in pks[:5]:
        print(f"  {p['name']} | état={p['state']} | client={p['partner_id']} | cmd={p['origin']}")
    if not pks:
        return
    p = pks[0]
    ml_ids = call('stock.move.line', 'search', [('picking_id', '=', p['id'])])
    mls = call('stock.move.line', 'read', ml_ids,
               fields=['product_id', 'quantity', 'lot_id']) if ml_ids else []
    print(f"--- état BL {p['name']} ({p['state']}) ---")
    for i, ml in enumerate(mls, 1):
        lot = ml['lot_id'][1] if ml['lot_id'] else '—'
        print(f"  {i}. {ml['product_id'][1][:42]:42} qty={ml['quantity']} lot={lot}")


# par numéro, par client, par commande
identify("00132")
identify("Hairdex")
identify("S00566")
# cas 0 résultat
identify("ZZZ-introuvable")
