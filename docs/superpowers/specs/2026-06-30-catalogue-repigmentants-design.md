# Design — Section « Repigmentants / Coloristeur » du catalogue MY.LAB

Date : 2026-06-30 · Branche : `feat/catalogue-repigmentants`

## But

Ajouter au catalogue PDF MY.LAB (`Catalogue mylab/MY.LAB_catalogue_2025_V1.pdf`, 51 pages, A4 paysage) une **nouvelle gamme « Repigmentants / Coloristeur »**, mise en page **exactement comme les autres gammes**. Ce sont les produits **Coloristeur** déjà existants (mêmes formules, mêmes prix que dans `assets/ml-product-map.json`) ; ici on les présente dans le catalogue commercial, là où ils manquent.

**On ne touche pas au site Shopify.** Livrable = PDF uniquement.

## Livrables

1. **`Catalogue mylab/MY.LAB_repigmentants_section.pdf`** — la section seule, 3 pages A4 paysage.
2. **`Catalogue mylab/MY.LAB_catalogue_2025_V2.pdf`** — le catalogue complet, section insérée **après la page 31** (juste après les Déjaunisseurs, dans la logique « soin de la couleur »).
3. **Source HTML/CSS** versionnée dans `docs/catalogue/repigmentants/` (réutilisable pour les prochaines gammes).

## Système de design (relevé sur le catalogue existant)

- **Format** : A4 paysage, 297 × 210 mm, pages simples (pas de double-page), fond blanc.
- **Typo** : sans-serif ; titres de gamme **CAPITALES espacées** (« LES … ») ; corps de texte lisible, interligne aéré (~1.5) ; libellés d'actifs en petites capitales.
- **Gabarit par gamme = 3 pages** :
  1. **Divider** : grand titre « LES [GAMME] », ligne des types de produits (SHAMPOING · MASQUE) avec le **% d'ingrédients naturels** sous chaque produit, visuel produit.
  2. **Propriétés & actifs** : titre « PROPRIÉTÉS & AUTRES ACTIFS », paragraphe d'usage/bénéfices, liste d'actifs principaux, mention « sans sulfate · sans paraben · sans silicone », bloc « Actifs principaux », badge « GAMME [NOM] » en pied.
  3. **Tarifs** : titre « TARIFS [GAMME] », tableaux 3 colonnes (format / paliers ×6 ×12 ×24 ×48 ×96 / prix), points de conduite (dotted leaders), mention « Prix HT et à l'unité ».
- **Couleur d'accent** : chaque gamme a sa teinte. La couleur exacte sera **relevée visuellement** sur 2–3 pages du PDF avant le build. Pour les Repigmentants on retiendra une teinte cohérente avec la famille « couleur » (déjaunisseur = violet/lavande adjacent) ; à confirmer au build.
- **Photo produit** : flacon sur fond blanc, cadrage standardisé.

## Contenu de la section Repigmentants (3 pages)

### Particularité : la gamme a **6 teintes**
Contrairement aux autres gammes (1 formule), les Repigmentants existent en 6 teintes. La section intègre donc un **nuancier** sur la page Propriétés.

Teintes (toutes incluses, platine compris — décision utilisateur « tout ensemble ») et visuels (Shopify CDN, depuis `assets/bulk-product-images.json`, on demandera `_800x800`) :

| Teinte | Handle shampoing | Handle masque |
|---|---|---|
| Blond Soleil | `shampoing-coloristeur-blond-soleil` | `masque-coloristeur-blond-soleil` |
| Blond Vanille | `shampoing-coloristeur-blond-vanille` | `masque-coloristeur-blond-vanille` |
| Chocolat | `shampoing-coloristeur-chocolat` | `masque-coloristeur-chocolat` |
| Cuivre (Intense) | `shampoing-coloristeur-cuivre` | `masque-coloristeur-cuivre` |
| Marron Noisette | `shampoing-coloristeur-marron-noisette` | `masque-coloristeur-marron-noisette` |
| Platine | `shampoing-dejaunisseur-platine` | `masque-dejaunisseur-platine` |

### Page 1 — Divider « LES REPIGMENTANTS »
- Titre « LES REPIGMENTANTS » (sous-titre / kicker « Coloristeur »).
- Types : **SHAMPOING · MASQUE**, avec % naturel sous chaque (valeur à confirmer — défaut : aligné sur l'ADN marque « 96 % naturel, vegan » ; ⚠️ à valider).
- Visuel héros : alignement des flacons / aperçu des teintes.

### Page 2 — Propriétés & actifs + Nuancier
- Paragraphe d'usage : raviver et intensifier la couleur, neutraliser les reflets indésirables, entretenir la couleur entre deux colorations, prolonger l'éclat.
- Actifs principaux + mention « sans sulfate · sans paraben · sans silicone ».
  - ⚠️ Copy/actifs réels à récupérer depuis les fiches produit live (`/products/{handle}.js`) au build ; fallback = formulation cohérente marque.
- **Nuancier** : 6 vignettes (teinte + nom + flacon).
- Badge « GAMME REPIGMENTANTS » en pied.

### Page 3 — Tarifs Repigmentants
Source : `assets/ml-product-map.json` (coloristeur) + PDF tarifs `docs/pricing/…Repigmentant-Coloristeur.pdf`. Prix HT, à l'unité.

**Shampoing Repigmentant**
- 200 ml — ×6 7,50 € · ×12 7,10 € · ×24 6,75 € · ×48 6,00 € · ×96 5,40 €
- 1000 ml — ×1 28,90 € · ×3 27,45 € · ×6 24,50 € · ×12 21,60 €

**Masque Repigmentant**
- 200 ml — ×6 9,60 € · ×12 9,10 € · ×24 8,60 € · ×48 7,65 € · ×96 6,90 €
- 400 ml — ×4 16,90 € · ×8 15,90 €
- 1000 ml — ×1 34,90 € · ×3 33,15 € · ×6 29,65 € · ×12 26,15 €

## Pipeline de fabrication (vérifié)

1. **HTML/CSS** : 3 pages, `@page { size: 297mm 210mm; margin: 0 }`, polices web (sans-serif proche de l'existant), images teintes en `_800x800`.
2. **Rendu PDF** : Chrome headless local — `chrome --headless --disable-gpu --no-pdf-header-footer --print-to-pdf` (testé OK : sortie 841.9 × 595 pts = A4 paysage). Pas de blocage Device Guard sur Chrome. Fallback : rendu sur le VPS si besoin.
3. **Fusion** : `pypdf 6.8.0` (dispo) — pages 1–31 du V1 + 3 pages section + pages 32–51 → `…_V2.pdf`.
4. **Contrôle** : ouverture du V2, vérif insertion au bon endroit, comptage 54 pages, rendu des teintes.

## Relevé V1 (2026-06-30)
- **Couleur d'accent : `#7365AC`** (violet color-care, échantillonné sur les puces « TARIFS » de la p.31 ; on l'adopte pour les Repigmentants → cohérence avec la famille couleur adjacente).
- **Insertion confirmée : après la page 31.** p.31 = « TARIFS DÉJAUNISSEUR » (dernière page Déjaunisseurs), p.32 = « LE MASQUE RÉPARATEUR » (gamme suivante).
- **Gabarit relevé** :
  - *Divider* : colonne image lifestyle à gauche (~30 %), titre bold MAJUSCULES en haut à droite, ligne « SHAMPOING · MASQUE » grise espacée, flacons au centre, 2 **badges ronds %** « X % d'ingrédients d'origine naturelle », **cercle violet** débordant le bord droit.
  - *Propriétés* : 2 petites photos en haut-gauche, bloc « GAMME [NOM] » (nom en accent) + « Actifs principaux » (liste à puces), « 200ml/500ml », mention « sans sulfate · sans paraben · sans silicone », titre « PROPRIÉTÉS & AUTRES ACTIFS » + 2 paragraphes + rangée de pictos.
  - *Tarifs* : **3 puces rondes violettes** + « TARIFS / [NOM] » (bold MAJ) + filet horizontal + « Prix HT et à l'unité » à droite ; 2 colonnes SHAMPOING | MASQUE ; sous-titres « 200 ML / 1000 ML » ; lignes « x 6 …… 7,50 € » (quantité **bold**, dotted leader, prix gris) ; filet en pied.
  - Les **prix Déjaunisseur (p.31) sont identiques aux prix Repigmentant** → la page Tarifs reprend exactement ce gabarit (+ ligne 400 ml masque).
- **Typo** : titres bold MAJUSCULES sans-serif géométrique (≈ Montserrat/Poppins ExtraBold) ; corps sans-serif léger. Build : charger **Montserrat** (400/600/800) via Google Fonts, fallback `Arial, sans-serif`.

## Points encore à trancher au build
- % d'ingrédients naturels par produit (sinon claim section « jusqu'à 96 % d'origine naturelle »).
- Copy actifs/propriétés (idéalement tirée des fiches produit live ; sinon bénéfices génériques honnêtes).
- Nom exact en couverture : défaut « LES REPIGMENTANTS », kicker « Coloristeur ».

## Hors périmètre
- Aucune modification du thème Shopify, du product-map, des collections ou du checkout.
- Pas de refonte des autres pages du catalogue.
