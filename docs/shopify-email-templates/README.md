# Shopify email notifications — MY.LAB branding

Les templates d'email Shopify (confirmation de commande, shipping, facture, etc.) ne sont **pas dans le thème** — ils vivent dans **Shopify Admin → Paramètres → Notifications**. Ce dossier documente les customisations MY.LAB pour les garder sous git.

## Approche

Plutôt que réécrire chaque template (fragile, Shopify les met à jour), on **remplace deux blocs ciblés** dans chaque template :

1. **`<head>` + `<style>`** — applique la DA (fonts Cormorant Garamond + DM Sans, palette `--ml-*`, boutons noirs, liens sans accent color).
2. **Footer** — footer sombre cohérent avec le site (logo MY.LAB, contact, socials).

Le reste du template (logique `line_items`, adresses, totaux, split cart, etc.) est intact.

## Fichiers

| Fichier | Usage |
|---------|-------|
| `order-confirmation-mylab-head.liquid` | Bloc `<head>` à coller dans "Confirmation de commande" |
| `order-confirmation-mylab-footer.liquid` | Bloc `<table class="row footer">` à coller dans "Confirmation de commande" |

## Procédure d'application

1. `Shopify Admin → Paramètres → Notifications`
2. Choisir la notification (ex. *Confirmation de commande*) → **Modifier le code**
3. Dans l'éditeur :
   - Sélectionner du `<head>` au `</head>` → remplacer par le contenu de `order-confirmation-mylab-head.liquid`
   - Sélectionner du `<table class="row footer">` au `</table>` de fermeture → remplacer par le contenu de `order-confirmation-mylab-footer.liquid`
4. **Aperçu** → **Envoyer un test** (à toi-même) → vérifier le rendu sur Gmail + Apple Mail
5. Enregistrer

## Réutilisation sur les autres notifications

Les deux blocs sont réutilisables quasi à l'identique sur :
- Shipping confirmation
- Out for delivery
- Delivered
- Order invoice (factures sur draft orders)
- Order refund
- Cancelled order
- Abandoned checkout

Le seul bloc à adapter est le wording, pas le style.

## Limites email-safe

- **Outlook desktop** ignore les webfonts Google → fallbacks Georgia (titres) et Helvetica/Arial (body)
- **Dark mode Apple Mail** peut inverser les couleurs du footer — testé OK avec `#111111` qui reste sombre
- Les `<link rel="preconnect">` sont ignorés par la plupart des clients mais ne cassent rien
- L'accent color Shopify (`shop.email_accent_color`) est **volontairement ignoré** pour forcer la cohérence avec le site

## Tokens DA (source `assets/mylab-product.css`)

```
--ml-white:  #FFFFFF
--ml-off:    #F5F4F2
--ml-black:  #111111
--ml-mid:    #555555
--ml-light:  #AAAAAA
--ml-muted:  #888888
--ml-green:  #2D4A2D  (discount tag)
```

Fonts : `Cormorant Garamond` (titres) + `DM Sans` (body).
