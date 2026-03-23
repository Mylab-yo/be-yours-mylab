# MY.LAB — API Commande Gros Volumes

Deux options pour transformer un devis en Draft Order Shopify.

## Option A — Cloudflare Worker (recommandé pour la prod)

### Déploiement

```bash
# Installer Wrangler
npm install -g wrangler

# Se connecter
wrangler login

# Configurer les secrets
wrangler secret put SHOPIFY_STORE_URL    # mylab-shop-3.myshopify.com
wrangler secret put SHOPIFY_ACCESS_TOKEN # shpat_xxx
wrangler secret put NOTIFICATION_EMAIL   # yoann@mylab-shop.com
wrangler secret put ALLOWED_ORIGIN       # https://mylab-shop-3.myshopify.com

# Déployer
wrangler deploy api/bulk-order-worker.js --name mylab-bulk-order
```

### Token API Shopify

1. Admin > Paramètres > Applications > Développer des applications
2. Créer une application "MyLab Bulk Order API"
3. Configurer les portées API Admin :
   - `write_draft_orders`
   - `read_draft_orders`
   - `write_customers`
   - `read_customers`
4. Installer l'application
5. Copier le token "Admin API access token"

### Utilisation

```
POST https://mylab-bulk-order.your-subdomain.workers.dev/
Content-Type: application/json

{ client: {...}, items: [...], ref: "MYLAB-GV-..." }
```

---

## Option B — n8n Webhook (recommandé pour démarrer)

### Déploiement

1. Ouvrir n8n (n8n.startec-paris.com)
2. Importer le workflow : `api/n8n-bulk-order-workflow.json`
3. Configurer les credentials :
   - **Shopify** : créer un credential HTTP Header Auth avec `X-Shopify-Access-Token: shpat_xxx`
   - **Email** : configurer SMTP (ou Gmail OAuth2)
4. Activer le workflow
5. Copier l'URL de production du webhook
6. Dans le Theme Editor Shopify : section "Commande Gros Volumes" > coller l'URL webhook

### Flux

```
Client remplit devis → POST webhook n8n
→ Validation des données
→ Création Draft Order Shopify
→ Email notification à yoann@mylab-shop.com
→ Email confirmation au client
→ Réponse JSON au frontend
```

---

## Sécurité

| Mesure | Option A | Option B |
|--------|----------|----------|
| Validation données | ✅ Serveur | ✅ n8n |
| Recalcul prix serveur | ✅ | ⚠️ (à ajouter) |
| Rate limiting | ✅ 5/h/IP | ⚠️ (via n8n settings) |
| CORS | ✅ | ✅ (via n8n) |
| Token API sécurisé | ✅ Env vars | ✅ Credentials n8n |

## Variables d'environnement

| Variable | Valeur | Obligatoire |
|----------|--------|-------------|
| `SHOPIFY_STORE_URL` | `mylab-shop-3.myshopify.com` | Oui |
| `SHOPIFY_ACCESS_TOKEN` | `shpat_xxx` | Oui |
| `NOTIFICATION_EMAIL` | `yoann@mylab-shop.com` | Oui |
| `ALLOWED_ORIGIN` | `https://mylab-shop-3.myshopify.com` | Option A |
