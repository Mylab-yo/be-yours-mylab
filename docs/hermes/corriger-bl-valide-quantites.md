---
name: corriger-bl-valide-quantites
description: Corriger un bon de livraison MyLab déjà validé (done) quand les quantités / le partage livré-vs-reliquat sont faux dans Odoo. Couvre le cas « produit mis à tort en reliquat alors qu'il part » et « produit livré en trop / mauvais produit ». Use when on dit "corriger un BL validé", "le BL a les mauvaises quantités", "produit en reliquat alors qu'il est parti", "j'ai validé le BL avec une erreur", "dé-valider un BL", "annuler un BL déjà validé", "modifier une livraison validée".
version: 1.0.0
platforms: [hermes]
metadata:
  hermes:
    tags: [odoo, logistique, bon-de-livraison, reliquat, backorder, correction]
---

# Corriger un BL validé avec les mauvaises quantités (Odoo)

> Référence pour Hermes. Un BL validé (`state=done`) **ne se « dé-valide » pas** proprement dans
> Odoo : le stock est déjà sorti. On corrige par **validation partielle d'un backorder** ou par
> **retour**, jamais en forçant l'état. Toujours **diagnostic read-only d'abord**, puis garde-fou
> de confirmation, puis écriture.

## ⛔ La règle d'or

Un `stock.picking` en `state=done` est **verrouillé** (`is_locked=True`), ses moves sont `done`,
**les quants ont déjà bougé** (Stock → Clients). **Ne JAMAIS** forcer `state` en `draft`/`assigned`
via l'ORM : le picking dirait « pas livré » alors que le stock est parti → **inventaire faux** (et
la facture éventuelle reste). C'est exactement le piège vu sur S00601 (cf [[feedback_hermes_local_unreliable_odoo_writes]]).

Les seuls leviers propres :
- **Livrer ce qui manque** = valider partiellement le **backorder** (Cas A).
- **Reprendre ce qui est parti en trop** = créer un **retour** (Cas B).

## Étape 0 — Diagnostic read-only (TOUJOURS commencer ici)

Identifier la commande, **tous** ses pickings (le BL done + ses backorders), et le reste dû par ligne.

```python
import os, xmlrpc.client
URL, DB = os.environ["ODOO_URL"].strip(), os.environ["ODOO_DB"].strip()
LOGIN = os.environ.get("ODOO_LOGIN", os.environ.get("ODOO_USER", "")).strip()
KEY = os.environ["ODOO_API_KEY"].strip()
common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common", allow_none=True)
UID = common.authenticate(DB, LOGIN, KEY, {})
models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object", allow_none=True)
def ex(model, method, *a, **kw):
    try:
        return models.execute_kw(DB, UID, KEY, model, method, list(a), kw)
    except xmlrpc.client.Fault as e:
        if "cannot marshal None" in str(e):  # Odoo18 marshalle mal les retours None
            return None
        raise

# commande + reste dû par ligne (commandé - livré, tous BL confondus)
so = ex("sale.order", "search_read", [("name", "=", "S00601")], fields=["id"])[0]
lines = ex("sale.order.line", "search_read", [("order_id", "=", so["id"])],
           fields=["product_id", "product_uom_qty", "qty_delivered", "display_type", "product_type"])
# pickings de la commande
picks = ex("stock.picking", "search_read", [("origin", "=", "S00601")],
           fields=["id", "name", "state", "backorder_id"])
```

Pour chaque ligne storable, **reste = `product_uom_qty - qty_delivered`** ; un `reste > 0` = vrai
reliquat (hors `product_type == 'service'`, ex. « Frais de livraison DPD »).

## Cas A — Un produit est à tort en reliquat (il doit partir aujourd'hui)

Le produit est sur un **backorder** (`state=assigned`, dispo `quantity>0`). Il faut le **livrer**
et garder le reste en nouveau backorder.

1. Repérer le backorder (`stock.picking` avec `backorder_id` pointant le BL d'origine) et ses
   `stock.move.line` (id du produit à livrer + des produits à garder en reliquat).
2. **Sur la move.line** (PAS sur le move : `stock.move.quantity` est computed/stored) :
   - produit à livrer → `quantity = <qté>`, `picked = True` ;
   - produit à garder en reliquat → `quantity = 0`.
3. `button_validate([pid])` → renvoie un **wizard backorder** (`ir.actions.act_window`,
   `res_model='stock.backorder.confirmation'`, `context` avec `button_validate_picking_ids` + `default_pick_ids`).
4. Créer + traiter le wizard pour **créer le backorder** du reste.

```python
PK = 200  # le backorder
ex("stock.move.line", "write", [ML_A_GARDER], {"quantity": 0.0})           # reste en reliquat
ex("stock.move.line", "write", [ML_A_LIVRER], {"quantity": 6.0, "picked": True})
ex("stock.move", "write", [MOVE_A_LIVRER], {"picked": True})
res = ex("stock.picking", "button_validate", [PK])
if isinstance(res, dict) and res.get("res_model") == "stock.backorder.confirmation":
    ctx = dict(res.get("context") or {})
    wiz = ex("stock.backorder.confirmation", "create", {"pick_ids": [(6, 0, [PK])]}, context=ctx)
    ex("stock.backorder.confirmation", "process", [wiz], context=ctx)   # process() = créer le backorder
```

Résultat : le backorder passe `done` avec le produit livré, un **nouveau backorder `assigned`**
est créé pour le reste. `process_cancel_backorder()` à la place de `process()` = pas de backorder.

## Cas B — Produit livré en trop, ou mauvais produit physiquement sorti

Il faut **reprendre du stock** → créer un **retour** (le BL d'origine reste, on l'inverse).

1. Wizard `stock.return.picking` — `default_get` ne pré-remplit PAS `product_return_moves` en
   XML-RPC, il faut construire les lignes à la main depuis les `stock.move` du picking d'origine :
   ```python
   return_lines = [(0, 0, {"product_id": m["product_id"][0], "quantity": m["quantity"],
                           "move_id": m["id"], "uom_id": m["product_uom"][0], "to_refund": True})
                   for m in moves_a_reprendre]
   wiz = ex("stock.return.picking", "create",
            {"picking_id": PK_ORIGINE, "product_return_moves": return_lines})
   res = ex("stock.return.picking", "action_create_returns", [wiz])  # Odoo 17+
   new_pid = res["res_id"]
   ```
2. Sur le picking retour : set `quantity` des move.line puis `button_validate([new_pid])`.
3. Renvoyer ensuite le bon produit via une nouvelle livraison si besoin.

(Détail wizards : [[feedback_odoo_xmlrpc_pitfalls]].)

## Pièges à connaître

- **`quantity` se met sur la `stock.move.line`**, pas sur `stock.move` (computed depuis les lignes).
- **`picked=True`** sur la (les) ligne(s) à livrer avant `button_validate`.
- **Facture** : si `sale.order.invoice_status == 'invoiced'`, livrer/backorder **n'a aucun impact
  facture** (déjà facturé). Si une correction de facturation est nécessaire (produit facturé faux,
  surfacturation), c'est un **avoir** séparé (`account.move.reversal`), jamais en touchant le picking.
- **Email client** : vérifier qu'aucune notif n'est déjà partie (`mail.mail` vers le partenaire) ;
  les `mail.message type=notification subj=False` sont des **logs internes**, pas des envois. La
  notif tracking/reliquat MyLab part au cron du soir → corriger avant.
- **Reliquat sur le PDF du BL** : il est calculé au **niveau commande** (`order_line` :
  commandé − livré, hors services), pas par picking — sinon il est vide (Odoo réduit la demande
  du move au moment du backorder). Voir [[bons-livraison-cartons]].
- **Marshalling None** : Odoo 18 lève `cannot marshal None` sur les méthodes qui retournent None
  (`button_validate`, `mail.mail.send`…) alors que le travail est fait → catcher ce Fault.

## Note pour Hermes — transformer ce document en skill

- **But** : sur demande (« corrige le BL X, le produit Y est à tort en reliquat »), faire le
  diagnostic, montrer l'état, et appliquer le Cas A ou B.
- **Garde-fou écriture 2 temps OBLIGATOIRE** : d'abord un **aperçu read-only** (état des pickings,
  ce qui sera livré / gardé en reliquat / retourné), attendre **« confirme »**, **puis** écrire.
- **Toujours re-vérifier après** : relire `sale.order.line` (livré/reste) + les pickings, et le
  confirmer à l'utilisateur. Ne jamais déclarer corrigé sans la vérif.
- **Ne jamais** forcer `state` d'un picking done. Si la demande est « dé-valider », expliquer que
  ce n'est pas possible proprement et proposer Cas A / Cas B.
- **Creds** : `ODOO_*` depuis `os.environ` (le `.env` Hermes les a déjà).
