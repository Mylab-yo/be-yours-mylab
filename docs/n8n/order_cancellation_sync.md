# Workflow n8n — Shopify Orders/Cancelled -> Odoo SO Cancel

## Identifiants

| Champ | Valeur |
|-------|--------|
| **Workflow ID** | `zM9bKHtl5N5KewfA` |
| **Nom** | MY.LAB — Shopify Orders/Cancelled -> Odoo SO Cancel |
| **Statut initial** | `active: false` — a activer manuellement |
| **Lien direct** | https://n8n.startec-paris.com/workflow/zM9bKHtl5N5KewfA |

## URL Webhook

```
https://n8n.startec-paris.com/webhook/shopify-order-cancelled
```

Cette URL n'est active qu'une fois le workflow active (bouton toggle dans l'UI n8n).

## Architecture du workflow

```
[Webhook POST /shopify-order-cancelled]
         |
[Extract Order]         -- extrait order.id du payload Shopify (rawBody)
         |
[Odoo Cancel SO]        -- cherche la SO + annule si possible
```

### Noeud 1 : Webhook Shopify Order Cancelled

- Path : `shopify-order-cancelled`
- Method : POST
- responseMode : `onReceived` (reponse 200 immediate avant traitement)
- rawBody : true (meme convention que workflow Xj8T `orders/paid`)

### Noeud 2 : Extract Order

Extrait l'objet `order` du payload Shopify. Shopify peut envoyer le body soit
sous `input.body` (quand rawBody est active), soit a plat. Le noeud normalise
les deux cas. Pas de verification HMAC — meme bypass que le workflow reference
`Xj8T5a7aO8drZk5v` (HMAC bypass temporaire documente en memoire).

### Noeud 3 : Odoo Cancel SO

Logique XML-RPC Odoo (meme helpers que Xj8T) :

1. **Recherche** : `sale.order.search_read` avec filtre `[client_order_ref = String(order.id), company_id = 3]`
2. **Cas no_match** : aucune SO trouvee → log et fin (pas d'erreur bloquante)
3. **Cas already_cancelled** : SO deja annulee → no-op
4. **Cas skipped_done** : SO en etat `done` → impossible d'annuler auto, note dans le resultat pour traitement manuel
5. **Cas normal** : appel `sale.order.action_cancel([so_id])` → libere les reservations de stock

## Logique de matching SO

Le champ utilise est `client_order_ref = String(order.id)` (ID numerique Shopify, ex: `"6789012345678"`).

**Pourquoi ce champ ?** Inspecte dans le noeud "Create Sale Order" du workflow
`Xj8T5a7aO8drZk5v` (ligne 133 / 139) : la SO est creee avec
`client_order_ref: String(order.id)`. C'est donc la cle de jointure canonique
entre Shopify et Odoo dans ce projet.

Le champ `origin` contient `Shopify #1234` (numero lisible) mais n'est pas utilise
pour le matching car il n'est pas indexe de la meme facon.

## HMAC

Pas de verification HMAC — meme comportement que le workflow `orders/paid`
(`Xj8T5a7aO8drZk5v`), ou le noeud "Verify HMAC" ne fait en realite qu'extraire
le payload sans valider la signature. Documente comme "HMAC bypass temporaire".

Si besoin d'activer la verification HMAC a terme, ajouter un noeud Code entre
le webhook et Extract Order avec `crypto.createHmac('sha256', SECRET).update(rawBody).digest('base64')`.

## Configuration cote Shopify

1. Aller dans **Admin Shopify → Settings → Notifications**
2. Scroll jusqu'a la section **Webhooks**
3. Cliquer **Create webhook**
4. Remplir :
   - **Event** : `Order cancellation` (ou `orders/cancelled`)
   - **Format** : JSON
   - **URL** : `https://n8n.startec-paris.com/webhook/shopify-order-cancelled`
   - **Webhook API version** : laisser la version par defaut (2024-01 ou plus recente)
5. Sauvegarder
6. Cliquer **Send test notification** pour valider (le workflow doit etre actif)

## Etapes pour activer

### Option A — via l'UI n8n

1. Ouvrir https://n8n.startec-paris.com/workflow/zM9bKHtl5N5KewfA
2. Cliquer le toggle **Inactive → Active** en haut a droite
3. Deplacer le workflow dans le folder **Yo** via "Move to folder" (l'API n8n ne
   supporte pas le placement de folder a la creation)

### Option B — via l'API n8n

```bash
curl -X PATCH \
  -H "X-N8N-API-KEY: <your-key>" \
  -H "Content-Type: application/json" \
  -d '{"active": true}' \
  "https://n8n.startec-paris.com/api/v1/workflows/zM9bKHtl5N5KewfA"
```

## Resultats possibles du noeud Odoo Cancel SO

| `result` | Description |
|----------|-------------|
| `cancelled` | SO trouvee et annulee, reservations de stock liberees |
| `already_cancelled` | SO deja en etat cancel, pas d'action |
| `skipped_done` | SO en etat done (livraison faite), annulation manuelle requise |
| `no_match` | Aucune SO Odoo avec ce `client_order_ref` (ex: commande creee avant la mise en place du workflow) |

## Notification Gmail (optionnelle)

Non incluse dans le workflow initial pour garder la configuration simple.
Si souhaite, ajouter un noeud **Gmail** apres "Odoo Cancel SO" avec :
- Credential : `Z9P00eLPPJyWM08T` (Gmail account YO)
- To : `yoann@mylab-shop.com`
- Subject : `[MY.LAB] Annulation commande Shopify {{$json.shopify_order_name}}`
- Body : inclure `result`, `so_name`, `partner`, `shopify_order_id`

## Script de creation

Le script Python qui a cree ce workflow est conserve dans :
`scripts/n8n/create_order_cancelled_workflow.py`
