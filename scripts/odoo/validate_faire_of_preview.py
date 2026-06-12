"""Valide (READ-ONLY) la logique d'aperçu du skill Hermes faire-of : Étapes 1-3 répliquées
à l'identique contre Odoo réel. N'exécute JAMAIS l'OF. Teste 2 cas :
  - un produit avec vrac en stock (lot déductible)
  - shampoing volume 200ml (vrac=0 -> pas de lot déductible, doit le signaler)
"""
import re, sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # console Windows cp1252 -> emojis OK
except Exception:
    pass
from _client import _models, DB, UID, API_KEY  # réutilise l'auth desktop


def call(model, method, *args, **kw):
    # réplique EXACTE du helper du SKILL.md
    return _models.execute_kw(DB, UID, API_KEY, model, method, list(args), kw)


def parse(msg):
    m = re.search(r'\blot\s+(\S+)', msg, re.I)
    lot_override = m.group(1) if m else None
    s = re.sub(r'\blot\s+\S+', '', msg, flags=re.I)
    s = re.sub(r'\b(of|ordre de fabrication|produire|conditionner|fabriquer|lancer( une)? production)\b',
               '', s, flags=re.I)
    bare = list(re.finditer(r'(?:[x*]\s*|qt[ée]\s*)?(\d+(?:[.,]\d+)?)(?!\s*(?:ml|cl|l|g|kg)\b)',
                            s, re.I))
    if bare:
        tok = bare[-1]
        qty = float(tok.group(1).replace(',', '.'))
        s = s[:tok.start()] + s[tok.end():]
    else:
        qty = None
    name = s.strip(' -:x*')
    return name, qty, lot_override


def preview(msg):
    print(f"\n########## INPUT: {msg!r}")
    name, qty, lot_override = parse(msg)
    print(f"parse -> name={name!r} qty={qty} lot_override={lot_override!r}")

    # Étape 2
    tmpl_ids = call('product.template', 'search', [('name', 'ilike', name)])
    candidates = []
    for t in tmpl_ids:
        boms = call('mrp.bom', 'search', [('product_tmpl_id', '=', t)], limit=1)
        if not boms:
            continue
        tmpl = call('product.template', 'read', [t], fields=['name', 'product_variant_id'])[0]
        candidates.append({'tmpl': t, 'name': tmpl['name'],
                           'variant': tmpl['product_variant_id'][0], 'bom': boms[0]})
    print(f"candidats avec BoM: {[(c['name'], c['variant']) for c in candidates]}")
    if not candidates:
        print("=> REFUS: pas un produit fabriqué"); return
    if len(candidates) > 1:
        print("=> DEMANDE: préciser lequel"); return
    c = candidates[0]; variant = c['variant']

    # Étape 3
    bom = call('mrp.bom', 'read', [c['bom']], fields=['product_qty', 'bom_line_ids'])[0]
    ratio = qty / bom['product_qty']
    lines = call('mrp.bom.line', 'read', bom['bom_line_ids'],
                 fields=['product_id', 'product_qty', 'product_uom_id'])
    comps = []; bulk_lot = None
    for l in lines:
        pid = l['product_id'][0]
        p = call('product.product', 'read', [pid],
                 fields=['name', 'qty_available', 'tracking', 'uom_id'])[0]
        need = l['product_qty'] * ratio
        comps.append({'name': p['name'], 'need': need, 'avail': p['qty_available'],
                      'tracking': p['tracking'], 'uom': l['product_uom_id'][1]})
        if p['tracking'] == 'lot' and bulk_lot is None:
            q = call('stock.quant', 'search_read',
                     [('product_id', '=', pid), ('location_id.usage', '=', 'internal'),
                      ('quantity', '>', 0)],
                     fields=['lot_id', 'quantity'], order='in_date asc')
            lots = [r for r in q if r['lot_id']]
            if lots:
                bulk_lot = {'name': lots[0]['lot_id'][1],
                            'others': [r['lot_id'][1] for r in lots[1:]]}
    finished_lot = lot_override or (bulk_lot['name'] if bulk_lot else None)

    # Aperçu rendu
    print(f"--- APERÇU ---")
    print(f"🏭 OF — {c['name']} × {qty}")
    print(f"Lot fini proposé : {finished_lot}")
    if bulk_lot:
        extra = f" ; autres lots: {bulk_lot['others']}" if bulk_lot['others'] else ""
        print(f"Origine vrac : {bulk_lot['name']}{extra}")
    for cp in comps:
        warn = "  ⚠️ passera en négatif" if cp['avail'] - cp['need'] < 0 else ""
        print(f"  • {cp['name']} : {cp['need']} {cp['uom']} (stock {cp['avail']} → {cp['avail']-cp['need']}){warn}")
    if finished_lot is None:
        print("=> DEMANDE: pas de lot déductible (vrac=0) et pas d'override → demander le n° de lot")


# Cas 1 : produit avec vrac en stock (lot déductible)
preview("OF masque volume 200ml 50")
# Cas 2 : shampoing volume 200ml — vrac=0 maintenant → pas de lot déductible
preview("OF shampoing volume 200ml 30")
# Cas 3 : override explicite malgré vrac=0
preview("OF shampoing volume 200ml 30 lot TESTLOT9")
