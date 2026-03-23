# MY.LAB — Checklist de tests : Configurateur Gros Volumes

**Date :** 23 mars 2026
**URL :** https://mylab-shop-3.myshopify.com/pages/commande-gros-volumes
**Version :** v1.0

---

## 1. Tests fonctionnels

### Étape 1 — Sélection des formules

| # | Test | Résultat | Notes |
|---|------|----------|-------|
| 1.1 | Les 10 gammes apparaissent dans les filtres avec la bonne couleur | ☐ | Nourrissante=#d4a574, Volume=#a8c5a0, etc. |
| 1.2 | Le filtre "Gamme" masque les produits des autres gammes | ☐ | |
| 1.3 | Le filtre "Type" masque les produits des autres types | ☐ | Shampoings, Masques, Crèmes, Sprays, Sérums, Huiles |
| 1.4 | Les filtres Gamme + Type se combinent correctement | ☐ | Ex: Gamme Volume + Type Masque → 1 résultat |
| 1.5 | Le bouton "Toutes" / "Tous" réinitialise le filtre | ☐ | |
| 1.6 | Cliquer une card la sélectionne (bordure colorée + check vert) | ☐ | |
| 1.7 | Re-cliquer une card la dé-sélectionne | ☐ | |
| 1.8 | Le compteur dans la barre fixe se met à jour en temps réel | ☐ | |
| 1.9 | Les chips dans la barre fixe correspondent aux formules sélectionnées | ☐ | |
| 1.10 | Cliquer le × d'un chip retire la sélection de la card | ☐ | |
| 1.11 | Le bouton "Étape suivante" est désactivé sans sélection | ☐ | |
| 1.12 | Le bouton "Étape suivante" est actif avec ≥1 sélection | ☐ | |
| 1.13 | La barre fixe slide-up quand une formule est sélectionnée | ☐ | |
| 1.14 | La barre fixe disparaît quand on dé-sélectionne tout | ☐ | |
| 1.15 | Les 27 formules s'affichent (10 gammes) | ☐ | |
| 1.16 | Chaque card affiche : % naturel, actifs en tags, labels (vegan, etc.) | ☐ | |
| 1.17 | Le message "Aucune formule ne correspond" s'affiche si filtres sans résultat | ☐ | |

### Étape 2 — Choix du format

| # | Test | Résultat | Notes |
|---|------|----------|-------|
| 2.1 | Toutes les formules sélectionnées apparaissent | ☐ | |
| 2.2 | Seuls les formats disponibles sont affichés (ex: spray → 200ml uniquement) | ☐ | |
| 2.3 | Cliquer un format le met en surbrillance (couleur gamme) | ☐ | |
| 2.4 | Le prix indicatif "À partir de X,XX € HT/unité" apparaît | ☐ | |
| 2.5 | Le prix change quand on change de format | ☐ | |
| 2.6 | Note packaging 200/500ml : "bouteille ambrée + bouchon/pompe" | ☐ | |
| 2.7 | Note packaging 1000ml : "bouchon blanc + pompe en option 0,45€" | ☐ | |
| 2.8 | Note packaging 5000ml : "packaging à votre charge" | ☐ | |
| 2.9 | Avec uniquement des formats ≤1000ml → question Takemoto optionnelle | ☐ | |
| 2.10 | "Non, garder le standard" → saute à l'étape 4 | ☐ | |
| 2.11 | "Oui, personnaliser" → va à l'étape 3 | ☐ | |
| 2.12 | Avec au moins un format 5000ml → notice rouge + étape 3 obligatoire | ☐ | |
| 2.13 | Le bouton "Suivant" ne fonctionne pas tant que tous les formats ne sont pas choisis | ☐ | |

### Étape 3 — Flacons Takemoto

| # | Test | Résultat | Notes |
|---|------|----------|-------|
| 3.1 | Un onglet par formule nécessitant un flacon | ☐ | |
| 3.2 | Les flacons sont pré-filtrés par contenance compatible | ☐ | |
| 3.3 | Les flacons sont pré-filtrés par type de fermeture adapté | ☐ | |
| 3.4 | Le filtre "Matériau" fonctionne (PET, rPET, PCR, verre) | ☐ | |
| 3.5 | Le filtre "Couleur" fonctionne | ☐ | |
| 3.6 | Le filtre "Éco-responsable uniquement" fonctionne | ☐ | |
| 3.7 | L'option "Packaging MY.LAB Standard" est en première position | ☐ | |
| 3.8 | L'option standard a le badge "Inclus" vert | ☐ | |
| 3.9 | Les flacons éco ont le badge "Éco" | ☐ | |
| 3.10 | Les flacons compatibles ont le badge "Recommandé" | ☐ | |
| 3.11 | Cliquer un flacon le sélectionne (bordure + highlight) | ☐ | |
| 3.12 | La check ✓ apparaît sur l'onglet quand un flacon est choisi | ☐ | |
| 3.13 | Le mini-récap sidebar affiche le status de chaque formule | ☐ | |
| 3.14 | "À choisir" en rouge si pas de flacon sélectionné | ☐ | |
| 3.15 | Le lien "Voir sur Takemoto" ouvre dans un nouvel onglet | ☐ | |
| 3.16 | Le message "Contactez-nous pour un packaging sur-mesure" est visible | ☐ | |
| 3.17 | Le message vide apparaît si tous les flacons sont filtrés | ☐ | |

### Étape 4 — Quantité et tarifs

| # | Test | Résultat | Notes |
|---|------|----------|-------|
| 4.1 | Chaque formule configurée a un bloc avec résumé (gamme + format + flacon) | ☐ | |
| 4.2 | La quantité minimum est 50 kg | ☐ | |
| 4.3 | Le sélecteur de tranche affiche "50 litres minimum" et "100 à 200 litres" | ☐ | |
| 4.4 | Le prix unitaire change quand on change de tranche | ☐ | |
| 4.5 | Saisir ≥100 kg bascule automatiquement sur la tranche 100-200kg | ☐ | |
| 4.6 | Saisir <100 kg bascule automatiquement sur la tranche 50kg | ☐ | |
| 4.7 | Le calcul nb flacons = (kg × 1000) / format est affiché et correct | ☐ | |
| 4.8 | Le tableau de décomposition montre : Formule + Remplissage + Packaging + Étiquette | ☐ | |
| 4.9 | La ligne "Pompe (option 1L)" apparaît pour les masques/crèmes en 1000ml | ☐ | |
| 4.10 | La ligne "Pompe" n'apparaît PAS pour les shampoings en 1000ml | ☐ | |
| 4.11 | La ligne "Flacon Takemoto" apparaît si flacon custom sélectionné | ☐ | |
| 4.12 | La ligne "Packaging" disparaît si flacon custom sélectionné | ☐ | |
| 4.13 | La ligne "Total HT" est la somme correcte de toutes les lignes | ☐ | |
| 4.14 | Le bloc "Total général" en noir affiche la somme de toutes les formules | ☐ | |
| 4.15 | Le nombre total de flacons est correct | ☐ | |
| 4.16 | Les 4 notes conditions sont affichées (marge ±3%, délai, règlement, transport) | ☐ | |

### Étape 5 — Récapitulatif et devis

| # | Test | Résultat | Notes |
|---|------|----------|-------|
| 5.1 | Le numéro de devis est généré (format MYLAB-GV-YYYYMMDD-XXXX) | ☐ | |
| 5.2 | La date est au format français | ☐ | |
| 5.3 | La mention "Devis valable 3 mois" est visible | ☐ | |
| 5.4 | Le tableau récap affiche toutes les formules avec les bonnes données | ☐ | |
| 5.5 | Le sous-total HT est correct | ☐ | |
| 5.6 | La TVA 20% est calculée correctement | ☐ | |
| 5.7 | Le total TTC = sous-total + TVA | ☐ | |
| 5.8 | Les 6 conditions commerciales sont listées | ☐ | |
| 5.9 | Le formulaire client a tous les champs (Prénom, Nom, Société, Email, Tel, Ville, Notes) | ☐ | |
| 5.10 | Les champs Prénom, Nom, Société, Email sont obligatoires | ☐ | |
| 5.11 | Le bouton "Télécharger le devis PDF" génère un fichier PDF | ☐ | |
| 5.12 | Le PDF contient le tableau récap (pas les boutons ni le formulaire) | ☐ | |
| 5.13 | Le bouton "Envoyer le devis par email" envoie les données | ☐ | |
| 5.14 | Un message de succès vert s'affiche après l'envoi | ☐ | |
| 5.15 | Le formulaire et les boutons disparaissent après l'envoi | ☐ | |

---

## 2. Tests de calcul — Cas concrets

### Cas 1 : Shampoing Nourrissant, 500ml, 50kg, standard

| Donnée | Attendu | Réel | OK ? |
|--------|---------|------|------|
| Tranche | 50kg | | ☐ |
| Prix formule | 6,50 € | | ☐ |
| Prix remplissage | 0,60 € | | ☐ |
| Prix packaging | 0,60 € | | ☐ |
| Prix étiquette | 0,20 € | | ☐ |
| **Prix unitaire** | **7,90 €** | | ☐ |
| Nb flacons | (50×1000)/500 = **100** | | ☐ |
| **Total HT** | 100 × 7,90 = **790,00 €** | | ☐ |

### Cas 2 : Masque Lissant, 200ml, 150kg, standard

| Donnée | Attendu | Réel | OK ? |
|--------|---------|------|------|
| Tranche | 100-200kg (auto) | | ☐ |
| Prix formule | 4,00 € | | ☐ |
| Prix remplissage | 0,50 € | | ☐ |
| Prix packaging | 0,70 € | | ☐ |
| Prix étiquette | 0,20 € | | ☐ |
| **Prix unitaire** | **5,40 €** | | ☐ |
| Nb flacons | (150×1000)/200 = **750** | | ☐ |
| **Total HT** | 750 × 5,40 = **4 050,00 €** | | ☐ |

### Cas 3 : Crème Volume, 5000ml, 50kg, flacon Takemoto

| Donnée | Attendu | Réel | OK ? |
|--------|---------|------|------|
| Tranche | 50kg | | ☐ |
| Prix formule | 90,00 € | | ☐ |
| Prix remplissage | 1,30 € | | ☐ |
| Prix packaging | 0 € (custom) | | ☐ |
| Prix étiquette | 0,20 € | | ☐ |
| Flacon Takemoto | prix variable | | ☐ |
| Nb bidons | (50×1000)/5000 = **10** | | ☐ |
| **Total HT formule** | 10 × 91,50 = **915,00 €** + flacons | | ☐ |

### Cas 4 : Masque Nourrissant, 1000ml, 100kg, standard (avec pompe)

| Donnée | Attendu | Réel | OK ? |
|--------|---------|------|------|
| Tranche | 100-200kg (auto) | | ☐ |
| Prix formule | 20,00 € | | ☐ |
| Prix remplissage | 0,50 € | | ☐ |
| Prix packaging | 0,70 € | | ☐ |
| Prix étiquette | 0,20 € | | ☐ |
| **Pompe (option)** | **0,45 €** | | ☐ |
| **Prix unitaire** | **21,85 €** | | ☐ |
| Nb flacons | (100×1000)/1000 = **100** | | ☐ |
| **Total HT** | 100 × 21,85 = **2 185,00 €** | | ☐ |

### Cas 5 : Multi-formules (2 produits)

| Formule | Format | Kg | Tranche | Unitaire | Nb | Total |
|---------|--------|----|---------|----------|----|-------|
| Shampoing Boucles | 200ml | 50 | 50kg | 3,90 € | 250 | 975,00 € |
| Masque Boucles | 200ml | 50 | 50kg | 5,70 € | 250 | 1 425,00 € |
| | | | | | **Total HT** | **2 400,00 €** |
| | | | | | TVA 20% | 480,00 € |
| | | | | | **Total TTC** | **2 880,00 €** |

---

## 3. Tests de navigation

| # | Test | Résultat | Notes |
|---|------|----------|-------|
| N.1 | Le stepper affiche l'étape active en noir | ☐ | |
| N.2 | Les étapes passées affichent un check vert | ☐ | |
| N.3 | Les étapes futures sont grisées | ☐ | |
| N.4 | Le bouton "Précédent" ramène à l'étape précédente | ☐ | |
| N.5 | Le bouton "Précédent" est désactivé à l'étape 1 | ☐ | |
| N.6 | Le bouton "Suivant" est désactivé à l'étape 5 | ☐ | |
| N.7 | Revenir à l'étape 1 conserve les sélections | ☐ | |
| N.8 | Revenir à l'étape 2 conserve les formats choisis | ☐ | |
| N.9 | Skip Takemoto (étape 3) → "Précédent" depuis étape 4 ramène à étape 2 | ☐ | |
| N.10 | La page scroll en haut à chaque changement d'étape | ☐ | |

---

## 4. Tests responsive

| # | Test | Breakpoint | Résultat | Notes |
|---|------|-----------|----------|-------|
| R.1 | Stepper : labels visibles | Desktop 1440px | ☐ | |
| R.2 | Stepper : labels masqués, numéros seuls | Mobile 375px | ☐ | |
| R.3 | Cards formules : 3 colonnes | Desktop 1440px | ☐ | |
| R.4 | Cards formules : 2 colonnes | Tablette 768px | ☐ | |
| R.5 | Cards formules : 1 colonne | Mobile 375px | ☐ | |
| R.6 | Barre sélection fixe visible et fonctionnelle | Mobile 375px | ☐ | |
| R.7 | Chips sélection masqués sur mobile | Mobile 375px | ☐ | |
| R.8 | Format pills accessibles (touch target ≥44px) | Mobile 375px | ☐ | |
| R.9 | Tableau quantité scrollable horizontalement | Mobile 375px | ☐ | |
| R.10 | Flacons : grille 3 colonnes | Desktop 1440px | ☐ | |
| R.11 | Flacons : grille 2 colonnes | Mobile 375px | ☐ | |
| R.12 | Récap sidebar : à droite | Desktop 1440px | ☐ | |
| R.13 | Récap sidebar : en bas | Mobile 375px | ☐ | |
| R.14 | Takemoto choice : boutons côte à côte | Desktop | ☐ | |
| R.15 | Takemoto choice : boutons empilés | Mobile 375px | ☐ | |
| R.16 | Formulaire client : 2 colonnes | Desktop | ☐ | |
| R.17 | Formulaire client : 1 colonne | Mobile 375px | ☐ | |
| R.18 | Boutons PDF/Email : côte à côte | Desktop | ☐ | |
| R.19 | Boutons PDF/Email : pleine largeur empilés | Mobile 375px | ☐ | |
| R.20 | Total général lisible et bien cadré | Mobile 320px | ☐ | |

---

## 5. Tests navigateur

| Navigateur | Version | Desktop | Mobile | Notes |
|-----------|---------|---------|--------|-------|
| Chrome | Dernier | ☐ | ☐ Android | |
| Firefox | Dernier | ☐ | — | |
| Safari | Dernier | ☐ | ☐ iOS | |
| Edge | Dernier | ☐ | — | |
| Samsung Internet | — | — | ☐ | |

---

## 6. Tests de performance

| # | Test | Résultat | Notes |
|---|------|----------|-------|
| P.1 | Chargement données JSON < 2s | ☐ | |
| P.2 | Pas de lag au clic/filtrage avec 27 cards | ☐ | |
| P.3 | Pas de layout shift au chargement | ☐ | |
| P.4 | Génération PDF < 5s | ☐ | |
| P.5 | Envoi formulaire < 3s | ☐ | |

---

## 7. Tests de sécurité

| # | Test | Résultat | Notes |
|---|------|----------|-------|
| S.1 | Les prix sont recalculés côté serveur (pas de confiance au frontend) | ☐ | Option A uniquement |
| S.2 | Rate limiting : 6ème requête en 1h → erreur 429 | ☐ | Option A uniquement |
| S.3 | CORS : requête depuis un autre domaine → bloquée | ☐ | |
| S.4 | XSS : injection HTML dans les champs client → échappée | ☐ | |
| S.5 | Le token API Shopify n'est jamais exposé au frontend | ☐ | |

---

## Signature

| Rôle | Nom | Date | Signature |
|------|-----|------|-----------|
| Testeur | | | |
| Développeur | Claude Opus 4.6 | 23/03/2026 | ✓ |
| Validateur | | | |
