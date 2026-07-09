# Documents Shopify — harmonisation visuelle MY.LAB

Ce dossier centralise les snippets de **branding email** + la procédure pour aligner **tous les documents générés par Shopify** sur la grammaire visuelle MY.LAB (DM Sans body + Cormorant Garamond titres + ink `#111`/`#1a1a1a` + cream `#f5f0eb`).

> La grammaire de référence est celle du **bordereau d'expédition** (`docs/shopify-packing-slip.liquid`) et du **BL Odoo** (`scripts/odoo/templates/bl_deliveryslip.xml`).

## Documents harmonisés

| Document | Fichier source | Où l'appliquer |
| --- | --- | --- |
| ✅ **Bordereau d'expédition** (packing slip) | [`../shopify-packing-slip.liquid`](../shopify-packing-slip.liquid) | Settings → Expédition et livraison → Modifier le modèle de bordereau d'expédition |
| ✅ **Carte cadeau** (gift card) | [`../../templates/gift_card.liquid`](../../templates/gift_card.liquid) | Déjà poussé via thème (override CSS inline dans `<head>`) |
| 🔧 **Notifications email** (×9) | `mylab-email-*.liquid` (ce dossier) | Settings → Notifications → chaque template → Modifier le code |

## Notifications email à harmoniser (9 templates)

Les 4 fichiers `mylab-email-*.liquid` de ce dossier sont **universels** : ils s'appliquent à toutes les notifications listées ci-dessous, sans adaptation.

| Notification | Catégorie Shopify | Priorité |
| --- | --- | --- |
| Confirmation de commande | Commandes | ⭐ Critique |
| Confirmation d'expédition | Livraison | ⭐ Critique |
| En cours de livraison | Livraison | Moyen |
| Livré | Livraison | Moyen |
| Commande annulée | Commandes | ⭐ Critique |
| Commande remboursée | Commandes | Moyen |
| Brouillon de commande (devis) | Commandes | ⭐ Critique |
| Facture sur draft order | Commandes | ⭐ Critique |
| Panier abandonné | Récupération | Moyen |

## Approche

Plutôt que réécrire chaque template entier (fragile, Shopify met à jour la structure), on **remplace 2 à 4 blocs ciblés** dans chacun. Le reste (logique `line_items`, adresses, totaux, split cart, etc.) reste intact.

## Fichiers

| Fichier | Rôle | Obligatoire ? |
| --- | --- | --- |
| `mylab-email-head.liquid` | Bloc `<head>` complet : fonts, palette, boutons, totals, footer, mobile | ✅ Oui |
| `mylab-email-footer.liquid` | Footer sombre (logo + contact + socials + mentions) | ✅ Oui |
| `mylab-email-logo-block.liquid` | Override de `<td class="shop-name__cell">` — logo MY.LAB avec fallbacks | Optionnel |
| `mylab-email-header-block.liquid` | Variante : logo centré + numéro commande dessous (au lieu de gauche/droite) | Optionnel |

## Procédure d'application (pour chaque notification)

### 1. Ouvrir le template

`Shopify Admin → Settings → Notifications → Customer notifications` → cliquer sur la notification → bouton **Edit code**.

### 2. Remplacer le `<head>` (obligatoire)

Sélectionner du `<head>` jusqu'au `</head>` inclus → remplacer par le contenu de [`mylab-email-head.liquid`](./mylab-email-head.liquid).

### 3. Remplacer le footer (obligatoire)

Chercher `<table class="row footer">` près de la fin du template → sélectionner jusqu'au `</table>` de fermeture → remplacer par le contenu de [`mylab-email-footer.liquid`](./mylab-email-footer.liquid).

> Si le template n'a pas de `<table class="row footer">`, coller le bloc juste avant `</body>`.

### 4. (Optionnel) Logo centré

Pour centrer le logo au lieu du layout gauche/droite Shopify : remplacer le bloc `<table class="row">` du header par le contenu de [`mylab-email-header-block.liquid`](./mylab-email-header-block.liquid).

### 5. Tester

Bouton **Preview** → puis **Send test email** à toi-même → vérifier le rendu sur :

- Gmail web (Chrome)
- Gmail mobile (iOS / Android)
- Apple Mail (dark mode actif)
- Outlook desktop (si client B2B sur Office)

### 6. Enregistrer

Cliquer sur **Save** en bas de page.

## Notes email-safe

- **Outlook desktop** ignore les webfonts Google → fallbacks Georgia (titres) + Helvetica/Arial (body) activés
- **Apple Mail dark mode** peut inverser les couleurs du footer → testé OK avec `#111111` qui reste sombre
- Les `<link rel="preconnect">` sont ignorés par la plupart des clients mais ne cassent rien
- L'accent color Shopify (`shop.email_accent_color`) est **volontairement ignoré** pour forcer la cohérence avec le site
- `display: none` sur `.button__cell--shop-app` cache le bouton "Track with Shop App" (clients B2B FR ne l'utilisent pas)

## Tokens DA (référence)

Fonts :

- **Titres** : `Cormorant Garamond` (fallback Georgia)
- **Body** : `DM Sans` (fallback Helvetica/Arial)

Palette :

```text
--ml-ink     #111111 / #1a1a1a   (texte principal, boutons)
--ml-cream   #f5f0eb              (background gift card, accents parcours)
--ml-off     #F5F4F2              (background email body)
--ml-white   #FFFFFF              (cartes content)
--ml-grey    #f0f0f0              (badges, headers tableau)
--ml-mid     #555555              (texte secondaire)
--ml-muted   #888888              (texte tertiaire, variantes)
--ml-border  #e5e0d0              (séparateurs)
--ml-green   #2D4A2D              (tags discount uniquement)
```

## Voir aussi

- [`docs/signature-email.html`](../signature-email.html) — signature email Yoann (à coller en bas des Gmail draft)
- [`docs/shopify-packing-slip.liquid`](../shopify-packing-slip.liquid) — packing slip (BL)
- [`scripts/odoo/templates/bl_deliveryslip.xml`](../../scripts/odoo/templates/bl_deliveryslip.xml) — BL Odoo (référence visuelle)
