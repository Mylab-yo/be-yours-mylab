# Shopify Webhook Setup — orders/paid → n8n

## Création du webhook

1. Ouvrir Shopify admin : https://mylab-shop-3.myshopify.com/admin
2. Settings (roue crantée en bas à gauche) → Notifications → scroll vers "Webhooks"
3. Cliquer "Create webhook"
4. Remplir :
   - **Event** : `Order payment` (équivalent `orders/paid`)
   - **Format** : `JSON`
   - **URL** : `https://n8n.startec-paris.com/webhook/mylab-shopify-order`
   - **API version** : la plus récente stable disponible
5. Enregistrer

## Récupération du HMAC secret

Après création du premier webhook de la boutique, Shopify affiche une section "Webhook signing secret" avec une valeur style `shpss_xxxxxxxxxxxxx`.

**Copier cette valeur** — elle servira à vérifier la signature HMAC SHA256 côté n8n.

## Stockage côté n8n

Dans n8n → Credentials → New credential → "Generic Credential Type" (ou custom) :
- Nom : `Shopify Webhook HMAC Secret`
- Field : `secret` = valeur du webhook signing secret Shopify

Ou, plus simple : stocker en variable d'environnement n8n (`SHOPIFY_WEBHOOK_SECRET` dans le docker-compose/env file sur le VPS), et y accéder via `$env.SHOPIFY_WEBHOOK_SECRET` dans les Code nodes.

## Test de base

Une fois le webhook créé, Shopify permet d'envoyer un test :
- Sur la ligne du webhook créé → "Send test notification"
- n8n doit recevoir un POST avec un payload d'exemple (une fausse commande).
- Vérifier dans les logs n8n que le workflow s'exécute et log correctement (même si il "skip" parce que la fake commande a un id étrange).
