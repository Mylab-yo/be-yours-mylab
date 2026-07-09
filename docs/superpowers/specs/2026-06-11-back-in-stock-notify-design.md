# Back in stock — e-mail automatique au retour de stock (SP2)

**Date :** 2026-06-11
**Statut :** design validé (Yoann, « GO »)
**Dépend de :** SP1 (`2026-06-11-rupture-stock-backorder-design.md`) — table Airtable `back-in-stock` + workflow capture déjà en place et opérationnels.

## Objectif

Quand un produit en rupture (pour lequel des clients ont demandé « prévenez-moi ») **revient en stock**, leur envoyer automatiquement un e-mail les invitant à commander.

## Décisions verrouillées

| Sujet | Décision |
|---|---|
| Déclencheur | **Poll planifié** n8n — **toutes les heures** (pas de webhook Shopify) |
| Détection retour stock | `inventory_quantity > 0` via Shopify Admin API (PAS `available`, qui reste vrai en backorder) |
| Envoi | **Automatique** (notif transactionnelle) |
| Expéditeur | **`contact@mylab-shop.com`** (alias « Envoyer en tant que » vérifié sur le compte `yoann@mylab-shop.com` connecté dans n8n) |
| Signature | MY.LAB (`docs/signature-email.html`) |
| Stockage | Airtable `back-in-stock` (base `appdWBkaxdGnJAqxU`, table `tblbBvfe1tgri0AyO`) |

## Architecture

Un seul workflow n8n **« Back in stock — notify »**, indépendant du workflow de capture (SP1). Folder Yo (`Z2t5yT17QDhgf2XO`), projet `HUgJsuxI2uJxkLLk`.

### Flux

1. **Schedule Trigger** — toutes les heures.
2. **Airtable Search** — lignes `status = pending` de `back-in-stock` (champs : email, handle, variant_id, product_title).
3. **Dédup** (Code) :
   - liste des `variant_id` distincts (1 check stock par variant) ;
   - dédup `email+variant_id` (évite d'envoyer 2 fois au même client pour le même produit).
4. **Check stock** (HTTP Request, par variant distinct) — `GET /admin/api/2024-07/variants/{variant_id}.json?fields=id,inventory_quantity` avec le token `shpat_5768…` (scope inventory). `back_in_stock = inventory_quantity > 0`.
5. **Filtre** — ne garder que les lignes dont le variant est `back_in_stock`.
6. Par ligne retenue :
   - **Gmail Send** (auto) → `to = email`, **from = contact@mylab-shop.com** (alias), objet + corps HTML FR + lien `https://mylab-shop.com/products/{handle}` + signature MY.LAB.
   - **Airtable Update** — `status → notified` (uniquement **après** envoi réussi).
7. Variants encore en rupture → lignes laissées `pending` (re-checkées à H+1).

### E-mail

- **Objet :** `Bonne nouvelle — {product_title} est de nouveau disponible`
- **Corps (HTML) :**
  > Bonjour,
  > Le produit **{product_title}** que vous souhaitiez commander est de nouveau **en stock** sur mylab-shop.com.
  > [ Commander maintenant → ] (lien vers la fiche produit)
  > — puis la signature MY.LAB (`docs/signature-email.html`).

## Identifiants / credentials n8n

- **Airtable** : credential token `mylab` (`patP8tmW7YtfVBtqE`, data.records:write) — celle réparée en SP1.
- **Gmail** : credential du compte `yoann@mylab-shop.com` ; envoi via l'alias `contact@mylab-shop.com` (réglage From/sendAs du nœud Gmail).
- **Shopify** : token `shpat_5768…` (read inventory/products) — via HTTP Request (header `X-Shopify-Access-Token`) ou credential Shopify n8n existante.

## Gestion d'erreurs / idempotence

- Échec du check stock d'un variant → on saute ce variant (reste `pending`, retry H+1).
- Échec d'envoi Gmail d'une ligne → on ne passe **pas** `notified` (retry H+1).
- Le flag `notified` garantit **aucun renvoi** (idempotent). L'ordre est strict : envoi → puis update statut.
- Un échec sur une ligne ne doit pas bloquer les autres (continue-on-fail par item).

## Tests / vérification

1. Sur une ligne `pending` de test pointant un variant **réapprovisionné** (`inventory_quantity > 0`) → exécution manuelle du workflow → e-mail reçu (from contact@, signature, lien produit) + ligne passée `notified`.
2. Ligne `pending` sur variant **encore en rupture** → aucun e-mail, reste `pending`.
3. Re-run immédiat → la ligne `notified` n'est PAS renvoyée (idempotent).
4. Deux lignes même email+variant → un seul e-mail (dédup).
5. From = `contact@mylab-shop.com` bien appliqué (pas yoann@).

## Hors scope (YAGNI)

- Pas de relance/multi-rappel.
- Pas de lien de désinscription dédié (réponse à contact@ suffit ; alias surveillé).
- Pas de webhook temps réel (poll horaire suffit en B2B).
- Purge des lignes `notified` : laissée pour plus tard (historique utile).
