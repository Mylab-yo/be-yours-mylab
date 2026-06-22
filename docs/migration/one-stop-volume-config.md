# Migration paliers volume → One Stop Volume Discounts — Package clé-en-main (v2)

Date : 2026-06-22. mylab-shop-3 (Grow). App publique → applique au checkout, marche sur Grow.

## ⚙️ Comment créer une offre dans One Stop
- Onglet **Général** : *Type d'offre* = **Remise uniquement** ; *L'offre s'applique à* = **Produits spécifiques** → sélectionner les produits du groupe.
- Onglet **Paliers de prix** : un « Offre #N » par palier. *Quantité minimale* + *Type de remise* = **Remise fixe par unité** + *Remise par article* (le montant € ci-dessous).
- 1er palier (qté minimale 1) = **Aucune remise** (prix standard).
- Enregistrer.

## Runbook
1. (Optionnel) stand-by : Boutique en ligne → Préférences → mot de passe (le temps de config).
2. Vérifier BSS OFF (règle mylab10 désactivée).
3. Créer les 17 offres ci-dessous (Remise fixe par unité).
4. Activer l'embed d'app One Stop (éditeur de thème → Enregistrer). Laisser le bloc d'app (doublon MyLab).
5. Tester checkout : Bain Miraculeux 12u → 96,60 € (8,05/u). Tester 24/48/96.
6. −10 % 4 clients (tag remise-10) : via One Stop si éligibilité tag, sinon BSS flat.
7. Désinstaller l'app custom volume-discount.
8. Vérifier Odoo (remise → sale.order.line.discount).

## Les 17 offres (Remise fixe par unité = montant € retiré / unité)

### Offre 1 — 8 produit(s) — base 7,00 € (qté 6+, aucune remise)
**Produits :** shampoing-nourrissant, shampoing-boucles, shampoing-lissant, shampoing-ha-repulpe, shampoing-volume, shampoing-purifiant, shampoing-protecteur-de-couleur, shampoing-gel-douche
**Paliers :**
  - qté **12+** → remise **0,35 €/unité**  (→ 6,65 €)
  - qté **24+** → remise **0,70 €/unité**  (→ 6,30 €)
  - qté **48+** → remise **1,40 €/unité**  (→ 5,60 €)
  - qté **96+** → remise **2,00 €/unité**  (→ 5,00 €)
  - qté **250+** → remise **3,10 €/unité**  (→ 3,90 €)
  - qté **500+** → remise **3,40 €/unité**  (→ 3,60 €)

### Offre 2 — 8 produit(s) — base 14,90 € (qté 6+, aucune remise)
**Produits :** shampoing-nourrissant-500ml, shampoing-boucles-500ml, shampoing-lissant-500ml, shampoing-ha-repulpe-500ml, shampoing-volume-500ml, shampoing-purifiant-500ml, shampoing-protecteur-de-couleur-500ml, shampoing-gel-douche-500ml
**Paliers :**
  - qté **12+** → remise **1,50 €/unité**  (→ 13,40 €)
  - qté **24+** → remise **2,25 €/unité**  (→ 12,65 €)
  - qté **48+** → remise **3,00 €/unité**  (→ 11,90 €)
  - qté **96+** → remise **4,25 €/unité**  (→ 10,65 €)
  - qté **100+** → remise **7,00 €/unité**  (→ 7,90 €)
  - qté **200+** → remise **7,60 €/unité**  (→ 7,30 €)

### Offre 3 — 8 produit(s) — base 24,90 € (qté 1+, aucune remise)
**Produits :** shampoing-nourrissant-1000ml, shampoing-boucles-1000ml, shampoing-lissant-1000ml, shampoing-ha-repulpe-1000ml, shampoing-volume-1000ml, shampoing-purifiant-1000ml, shampoing-protecteur-de-couleur-1000ml, shampoing-gel-douche-1000ml
**Paliers :**
  - qté **3+** → remise **1,25 €/unité**  (→ 23,65 €)
  - qté **6+** → remise **3,90 €/unité**  (→ 21,00 €)
  - qté **12+** → remise **6,25 €/unité**  (→ 18,65 €)
  - qté **50+** → remise **10,40 €/unité**  (→ 14,50 €)
  - qté **100+** → remise **11,50 €/unité**  (→ 13,40 €)

### Offre 4 — 6 produit(s) — base 9,50 € (qté 6+, aucune remise)
**Produits :** masque-nourrissant, masque-boucles, masque-lissant, masque-ha-repulpe, masque-volume, masque-protecteur-de-couleur
**Paliers :**
  - qté **12+** → remise **0,50 €/unité**  (→ 9,00 €)
  - qté **24+** → remise **0,95 €/unité**  (→ 8,55 €)
  - qté **48+** → remise **1,90 €/unité**  (→ 7,60 €)
  - qté **96+** → remise **2,70 €/unité**  (→ 6,80 €)
  - qté **250+** → remise **3,80 €/unité**  (→ 5,70 €)
  - qté **500+** → remise **4,10 €/unité**  (→ 5,40 €)

### Offre 5 — 6 produit(s) — base 16,90 € (qté 6+, aucune remise)
**Produits :** masque-nourrissant-400ml, masque-boucles-400ml, masque-lissant-400ml, masque-ha-repulpe-400ml, masque-volume-400ml, masque-protecteur-de-couleur-400ml
**Paliers :**
  - qté **12+** → remise **1,00 €/unité**  (→ 15,90 €)
  - qté **24+** → remise **1,70 €/unité**  (→ 15,20 €)
  - qté **48+** → remise **3,40 €/unité**  (→ 13,50 €)
  - qté **96+** → remise **4,80 €/unité**  (→ 12,10 €)

### Offre 6 — 6 produit(s) — base 32,90 € (qté 1+, aucune remise)
**Produits :** masque-nourrissant-1000ml, masque-boucles-1000ml, masque-lissant-1000ml, masque-ha-repulpe-1000ml, masque-volume-1000ml, masque-protecteur-de-couleur-1000ml
**Paliers :**
  - qté **3+** → remise **1,65 €/unité**  (→ 31,25 €)
  - qté **6+** → remise **5,00 €/unité**  (→ 27,90 €)
  - qté **12+** → remise **8,25 €/unité**  (→ 24,65 €)
  - qté **50+** → remise **10,40 €/unité**  (→ 22,50 €)
  - qté **100+** → remise **11,50 €/unité**  (→ 21,40 €)

### Offre 7 — 6 produit(s) — base 7,50 € (qté 6+, aucune remise)
**Produits :** shampoing-coloristeur-blond-soleil, shampoing-coloristeur-blond-vanille, shampoing-coloristeur-chocolat, shampoing-coloristeur-cuivre, shampoing-coloristeur-marron-noisette, shampoing-dejaunisseur-platine
**Paliers :**
  - qté **12+** → remise **0,40 €/unité**  (→ 7,10 €)
  - qté **24+** → remise **0,75 €/unité**  (→ 6,75 €)
  - qté **48+** → remise **1,50 €/unité**  (→ 6,00 €)
  - qté **96+** → remise **2,10 €/unité**  (→ 5,40 €)

### Offre 8 — 6 produit(s) — base 28,90 € (qté 1+, aucune remise)
**Produits :** shampoing-1000ml-coloristeur-blond-soleil, shampoing-1000ml-coloristeur-blond-vanille, shampoing-1000ml-coloristeur-chocolat, shampoing-1000ml-coloristeur-cuivre, shampoing-1000ml-coloristeur-marron-noisette, shampoing-1000ml-dejaunisseur-platine
**Paliers :**
  - qté **3+** → remise **1,45 €/unité**  (→ 27,45 €)
  - qté **6+** → remise **4,40 €/unité**  (→ 24,50 €)
  - qté **12+** → remise **7,30 €/unité**  (→ 21,60 €)

### Offre 9 — 6 produit(s) — base 9,60 € (qté 6+, aucune remise)
**Produits :** masque-coloristeur-blond-soleil, masque-coloristeur-blond-vanille, masque-coloristeur-chocolat, masque-coloristeur-cuivre, masque-coloristeur-marron-noisette, masque-dejaunisseur-platine
**Paliers :**
  - qté **12+** → remise **0,50 €/unité**  (→ 9,10 €)
  - qté **24+** → remise **1,00 €/unité**  (→ 8,60 €)
  - qté **48+** → remise **1,95 €/unité**  (→ 7,65 €)
  - qté **96+** → remise **2,70 €/unité**  (→ 6,90 €)

### Offre 10 — 6 produit(s) — base 34,90 € (qté 1+, aucune remise)
**Produits :** masque-1000ml-coloristeur-blond-soleil, masque-1000ml-coloristeur-blond-vanille, masque-1000ml-coloristeur-chocolat, masque-1000ml-coloristeur-cuivre, masque-1000ml-coloristeur-marron-noisette, masque-1000ml-dejaunisseur-platine
**Paliers :**
  - qté **3+** → remise **1,75 €/unité**  (→ 33,15 €)
  - qté **6+** → remise **5,25 €/unité**  (→ 29,65 €)
  - qté **12+** → remise **8,75 €/unité**  (→ 26,15 €)

### Offre 11 — 5 produit(s) — base 8,50 € (qté 6+, aucune remise)
**Produits :** creme-boucles, creme-ha-repulpe, creme-lissante, creme-nourrissante, creme-volume
**Paliers :**
  - qté **12+** → remise **0,45 €/unité**  (→ 8,05 €)
  - qté **24+** → remise **0,85 €/unité**  (→ 7,65 €)
  - qté **48+** → remise **1,70 €/unité**  (→ 6,80 €)
  - qté **96+** → remise **2,40 €/unité**  (→ 6,10 €)
  - qté **250+** → remise **3,40 €/unité**  (→ 5,10 €)
  - qté **500+** → remise **3,70 €/unité**  (→ 4,80 €)

### Offre 12 — 2 produit(s) — base 9,50 € (qté 6+, aucune remise)
**Produits :** serum-finition-ultime, serum-barbe
**Paliers :**
  - qté **12+** → remise **0,50 €/unité**  (→ 9,00 €)
  - qté **24+** → remise **1,00 €/unité**  (→ 8,50 €)
  - qté **48+** → remise **1,90 €/unité**  (→ 7,60 €)
  - qté **96+** → remise **2,70 €/unité**  (→ 6,80 €)

### Offre 13 — 2 produit(s) — base 8,50 € (qté 6+, aucune remise)
**Produits :** bain-miraculeux, huile-a-barbe
**Paliers :**
  - qté **12+** → remise **0,45 €/unité**  (→ 8,05 €)
  - qté **24+** → remise **0,85 €/unité**  (→ 7,65 €)
  - qté **48+** → remise **1,70 €/unité**  (→ 6,80 €)
  - qté **96+** → remise **2,40 €/unité**  (→ 6,10 €)

### Offre 14 — 1 produit(s) — base 17,90 € (qté 6+, aucune remise)
**Produits :** creme-boucles-500ml
**Paliers :**
  - qté **14+** → remise **2,40 €/unité**  (→ 15,50 €)
  - qté **28+** → remise **3,50 €/unité**  (→ 14,40 €)
  - qté **42+** → remise **4,30 €/unité**  (→ 13,60 €)

### Offre 15 — 1 produit(s) — base 9,90 € (qté 6+, aucune remise)
**Produits :** masque-reparateur-sans-rincage
**Paliers :**
  - qté **12+** → remise **0,50 €/unité**  (→ 9,40 €)
  - qté **24+** → remise **1,00 €/unité**  (→ 8,90 €)
  - qté **48+** → remise **2,00 €/unité**  (→ 7,90 €)
  - qté **96+** → remise **2,80 €/unité**  (→ 7,10 €)

### Offre 16 — 1 produit(s) — base 7,90 € (qté 6+, aucune remise)
**Produits :** spray-texturisant
**Paliers :**
  - qté **12+** → remise **0,40 €/unité**  (→ 7,50 €)
  - qté **24+** → remise **0,90 €/unité**  (→ 7,00 €)
  - qté **48+** → remise **1,40 €/unité**  (→ 6,50 €)
  - qté **96+** → remise **1,90 €/unité**  (→ 6,00 €)
  - qté **196+** → remise **2,60 €/unité**  (→ 5,30 €)

### Offre 17 — 1 produit(s) — base 9,50 € (qté 6+, aucune remise)
**Produits :** masque-intense
**Paliers :**
  - qté **12+** → remise **0,50 €/unité**  (→ 9,00 €)
  - qté **24+** → remise **0,95 €/unité**  (→ 8,55 €)
  - qté **48+** → remise **1,90 €/unité**  (→ 7,60 €)
  - qté **96+** → remise **2,70 €/unité**  (→ 6,80 €)

## −10 % pour 4 clients (tag `remise-10`)
- Si One Stop gère l'éligibilité par tag client → 2ᵉ jeu d'offres −10 % sur tag `remise-10`.
- Sinon BSS « Tarification personnalisée » flat −10 % ciblant les 4 clients (tester cumul avec One Stop).

## Décommissionnement
- Désinstaller app `volume-discount` (custom, Plus-only, inutilisable sur Grow).
- Garder désactivées : promo Shopify `mylab10` + règle BSS `mylab10`.