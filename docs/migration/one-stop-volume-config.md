# Migration paliers volume → One Stop Volume Discounts — Package clé-en-main

Date : 2026-06-22. Boutique : mylab-shop-3 (plan Grow). App publique → fonctionne sur Grow, applique les prix au checkout.

## Runbook (ordre à suivre)

1. **(Optionnel) Stand-by** : Boutique en ligne → Préférences → activer le mot de passe (le temps de la config, ~15 min).
2. **Vérifier BSS OFF** : règle `mylab10` désactivée (déjà fait) ; aucune autre règle BSS active. One Stop devient le seul moteur de prix.
3. **Créer les 17 offres** dans One Stop (détail ci-dessous) : pour chaque groupe, sélectionner les produits listés + entrer les paliers (type **Fixed price**), éligibilité **All customers**.
4. **−10 % pour 4 clients** : voir section dédiée en bas.
5. **Tester au checkout** : Bain Miraculeux 12 u. → doit facturer **8,05 €/u (96,60 €)**. Tester 6 / 24 u.
6. **Corriger le drawer MyLab** (lecture du vrai panier `/cart.js`) — me redemander, je le fais sur dev puis push.
7. **Désinstaller l'app `volume-discount`** (fonction custom inutilisable sur Grow).
8. **Vérifier Odoo** : 1 commande test → la remise descend bien en `sale.order.line.discount` (workflow n8n existant).

## Les 17 offres à créer

Pour chaque offre : **prix de base** = prix normal du produit (déjà le prix Shopify, ne rien changer). Les **paliers** ci-dessous = « à partir de N unités, prix fixe X ».

### Offre 1 — 8 produits
**Produits :** shampoing-nourrissant, shampoing-boucles, shampoing-lissant, shampoing-ha-repulpe, shampoing-volume, shampoing-purifiant, shampoing-protecteur-de-couleur, shampoing-gel-douche
**Prix de base (qté 6+) :** 7,00 € _(prix normal, ne pas changer)_
**Paliers à configurer :** 12+ → **6,65 €** | 24+ → **6,30 €** | 48+ → **5,60 €** | 96+ → **5,00 €** | 250+ → **3,90 €** | 500+ → **3,60 €**

### Offre 2 — 8 produits
**Produits :** shampoing-nourrissant-500ml, shampoing-boucles-500ml, shampoing-lissant-500ml, shampoing-ha-repulpe-500ml, shampoing-volume-500ml, shampoing-purifiant-500ml, shampoing-protecteur-de-couleur-500ml, shampoing-gel-douche-500ml
**Prix de base (qté 6+) :** 14,90 € _(prix normal, ne pas changer)_
**Paliers à configurer :** 12+ → **13,40 €** | 24+ → **12,65 €** | 48+ → **11,90 €** | 96+ → **10,65 €** | 100+ → **7,90 €** | 200+ → **7,30 €**

### Offre 3 — 8 produits
**Produits :** shampoing-nourrissant-1000ml, shampoing-boucles-1000ml, shampoing-lissant-1000ml, shampoing-ha-repulpe-1000ml, shampoing-volume-1000ml, shampoing-purifiant-1000ml, shampoing-protecteur-de-couleur-1000ml, shampoing-gel-douche-1000ml
**Prix de base (qté 1+) :** 24,90 € _(prix normal, ne pas changer)_
**Paliers à configurer :** 3+ → **23,65 €** | 6+ → **21,00 €** | 12+ → **18,65 €** | 50+ → **14,50 €** | 100+ → **13,40 €**

### Offre 4 — 6 produits
**Produits :** masque-nourrissant, masque-boucles, masque-lissant, masque-ha-repulpe, masque-volume, masque-protecteur-de-couleur
**Prix de base (qté 6+) :** 9,50 € _(prix normal, ne pas changer)_
**Paliers à configurer :** 12+ → **9,00 €** | 24+ → **8,55 €** | 48+ → **7,60 €** | 96+ → **6,80 €** | 250+ → **5,70 €** | 500+ → **5,40 €**

### Offre 5 — 6 produits
**Produits :** masque-nourrissant-400ml, masque-boucles-400ml, masque-lissant-400ml, masque-ha-repulpe-400ml, masque-volume-400ml, masque-protecteur-de-couleur-400ml
**Prix de base (qté 6+) :** 16,90 € _(prix normal, ne pas changer)_
**Paliers à configurer :** 12+ → **15,90 €** | 24+ → **15,20 €** | 48+ → **13,50 €** | 96+ → **12,10 €**

### Offre 6 — 6 produits
**Produits :** masque-nourrissant-1000ml, masque-boucles-1000ml, masque-lissant-1000ml, masque-ha-repulpe-1000ml, masque-volume-1000ml, masque-protecteur-de-couleur-1000ml
**Prix de base (qté 1+) :** 32,90 € _(prix normal, ne pas changer)_
**Paliers à configurer :** 3+ → **31,25 €** | 6+ → **27,90 €** | 12+ → **24,65 €** | 50+ → **22,50 €** | 100+ → **21,40 €**

### Offre 7 — 6 produits
**Produits :** shampoing-coloristeur-blond-soleil, shampoing-coloristeur-blond-vanille, shampoing-coloristeur-chocolat, shampoing-coloristeur-cuivre, shampoing-coloristeur-marron-noisette, shampoing-dejaunisseur-platine
**Prix de base (qté 6+) :** 7,50 € _(prix normal, ne pas changer)_
**Paliers à configurer :** 12+ → **7,10 €** | 24+ → **6,75 €** | 48+ → **6,00 €** | 96+ → **5,40 €**

### Offre 8 — 6 produits
**Produits :** shampoing-1000ml-coloristeur-blond-soleil, shampoing-1000ml-coloristeur-blond-vanille, shampoing-1000ml-coloristeur-chocolat, shampoing-1000ml-coloristeur-cuivre, shampoing-1000ml-coloristeur-marron-noisette, shampoing-1000ml-dejaunisseur-platine
**Prix de base (qté 1+) :** 28,90 € _(prix normal, ne pas changer)_
**Paliers à configurer :** 3+ → **27,45 €** | 6+ → **24,50 €** | 12+ → **21,60 €**

### Offre 9 — 6 produits
**Produits :** masque-coloristeur-blond-soleil, masque-coloristeur-blond-vanille, masque-coloristeur-chocolat, masque-coloristeur-cuivre, masque-coloristeur-marron-noisette, masque-dejaunisseur-platine
**Prix de base (qté 6+) :** 9,60 € _(prix normal, ne pas changer)_
**Paliers à configurer :** 12+ → **9,10 €** | 24+ → **8,60 €** | 48+ → **7,65 €** | 96+ → **6,90 €**

### Offre 10 — 6 produits
**Produits :** masque-1000ml-coloristeur-blond-soleil, masque-1000ml-coloristeur-blond-vanille, masque-1000ml-coloristeur-chocolat, masque-1000ml-coloristeur-cuivre, masque-1000ml-coloristeur-marron-noisette, masque-1000ml-dejaunisseur-platine
**Prix de base (qté 1+) :** 34,90 € _(prix normal, ne pas changer)_
**Paliers à configurer :** 3+ → **33,15 €** | 6+ → **29,65 €** | 12+ → **26,15 €**

### Offre 11 — 5 produits
**Produits :** creme-boucles, creme-ha-repulpe, creme-lissante, creme-nourrissante, creme-volume
**Prix de base (qté 6+) :** 8,50 € _(prix normal, ne pas changer)_
**Paliers à configurer :** 12+ → **8,05 €** | 24+ → **7,65 €** | 48+ → **6,80 €** | 96+ → **6,10 €** | 250+ → **5,10 €** | 500+ → **4,80 €**

### Offre 12 — 2 produits
**Produits :** serum-finition-ultime, serum-barbe
**Prix de base (qté 6+) :** 9,50 € _(prix normal, ne pas changer)_
**Paliers à configurer :** 12+ → **9,00 €** | 24+ → **8,50 €** | 48+ → **7,60 €** | 96+ → **6,80 €**

### Offre 13 — 2 produits
**Produits :** bain-miraculeux, huile-a-barbe
**Prix de base (qté 6+) :** 8,50 € _(prix normal, ne pas changer)_
**Paliers à configurer :** 12+ → **8,05 €** | 24+ → **7,65 €** | 48+ → **6,80 €** | 96+ → **6,10 €**

### Offre 14 — 1 produits
**Produits :** creme-boucles-500ml
**Prix de base (qté 6+) :** 17,90 € _(prix normal, ne pas changer)_
**Paliers à configurer :** 14+ → **15,50 €** | 28+ → **14,40 €** | 42+ → **13,60 €**

### Offre 15 — 1 produits
**Produits :** masque-reparateur-sans-rincage
**Prix de base (qté 6+) :** 9,90 € _(prix normal, ne pas changer)_
**Paliers à configurer :** 12+ → **9,40 €** | 24+ → **8,90 €** | 48+ → **7,90 €** | 96+ → **7,10 €**

### Offre 16 — 1 produits
**Produits :** spray-texturisant
**Prix de base (qté 6+) :** 7,90 € _(prix normal, ne pas changer)_
**Paliers à configurer :** 12+ → **7,50 €** | 24+ → **7,00 €** | 48+ → **6,50 €** | 96+ → **6,00 €** | 196+ → **5,30 €**

### Offre 17 — 1 produits
**Produits :** masque-intense
**Prix de base (qté 6+) :** 9,50 € _(prix normal, ne pas changer)_
**Paliers à configurer :** 12+ → **9,00 €** | 24+ → **8,55 €** | 48+ → **7,60 €** | 96+ → **6,80 €**

## −10 % pour les 4 clients spécifiques

Deux options selon ce que One Stop permet :
- **Si One Stop gère l'éligibilité par tag client** : créer une 2ᵉ série d'offres (ou un mode) ciblant le tag `remise-10`, à −10 % sur le prix palier. (à vérifier dans l'UI)
- **Sinon, via BSS** (le module flat qu'on a vu) : règle Tarification personnalisée → Ciblage = les 4 clients → −10 %. ⚠️ Vérifier que ça se cumule proprement avec les paliers One Stop (tester au checkout).

## Décommissionnement
- App `volume-discount` (fonction custom) : **désinstaller** — inutilisable sur Grow (cf. mémoire `feedback_shopify_functions_require_plus_for_custom_apps`).
- Metafield `mylab.volume_tiers` : peut rester (source de vérité réutilisable) ou être nettoyé plus tard.
- Promo Shopify `mylab10` + règle BSS `mylab10` : garder désactivées.