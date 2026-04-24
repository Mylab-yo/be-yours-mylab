# Brief design — page "Créons ensemble votre marque"

> Brief prêt à coller dans `/frontend-design` (ou toute autre commande design).
> **Avant de lancer** : attache 3-5 screenshots (hero, étape 2, étape 3, récap, mobile 375px) en plus de ce brief.

---

## 1. Contexte produit

**Entreprise :** MY.LAB (coordonnée par STARTEC) — coordinateur de marques cosmétiques capillaires B2B, fabrication française via un réseau de façonniers qualifiés.

**Audience :** professionnels du capillaire (coiffeurs indépendants, instituts, salons, marques émergentes DNVB) qui veulent créer ou étendre leur propre gamme. Décideurs pressés, souvent consultés mobile entre deux rendez-vous, avec un besoin dual : **projection** (ça ressemble à quoi une marque pro ?) et **rassurance** (qui fait le dossier réglementaire ? combien ça coûte ? quels délais ?).

**Promesse de la page :** unifier en un seul parcours ce qui était éclaté avant — dossier réglementaire, choix d'étiquette (3 tiers), abonnement impression, composition de la gamme produits, récap/devis. L'utilisateur doit sentir qu'**on s'occupe de tout, il garde la vision**.

**Ton :** premium accessible, expertise française, pas corporate froid, pas agence creative non plus. Style éditorial haut de gamme qui inspire confiance à un pro qui va investir 3 000 à 15 000 €.

---

## 2. État actuel — URL et source

- **URL live :** https://mylab-shop-3.myshopify.com/pages/creons-ensemble-votre-marque
- **Fichier source :** [sections/ml-creons-ensemble-votre-marque.liquid](../sections/ml-creons-ensemble-votre-marque.liquid) (1773 lignes, CSS inline dans `{% style %}`)
- **Template :** [templates/page.creons-ensemble-votre-marque.json](../templates/page.creons-ensemble-votre-marque.json)

**Structure actuelle (top → bottom) :**
1. **Hero** — vidéo/image plein écran 88vh, eyebrow or, titre Cormorant italique, 2 CTAs (gold + ghost), 3 trust items
2. **Étape 1 "Dossier cosmétologique"** — fond cream, 3 piliers (DIP / CPNP / Tests), details expansible, hint délai
3. **Étape 2 "Étiquette"** — fond blanc, 3 cartes options (Design MY.LAB gratuit / Modèles 99 € / Sur mesure 390 €+) avec CTA par carte
4. **Étape 2.5 "Forfait impression"** — fond blanc, 3 piliers (1 an / Tacite / 2 formules), callout forfait auto-déterminé
5. **Étape 3 "Produits"** — fond cream-2, tabs de filtre, grid cartes produits avec paliers de volume + prix dégressifs
6. **Étape 4 "Récap"** — fond noir profond, timeline steps, box récapitulatif, 2 CTAs (valider + RDV expert)
7. **Sticky sidebar desktop** (1200px+) + **bottom bar mobile** — récap permanent, total HT, bouton finaliser
8. **Modal configurateur** — iframe Vercel plein écran pour Option 02 / 03

---

## 3. Design DNA — NE PAS RÉINVENTER

Le site MY.LAB a déjà une identité visuelle cohérente. La page doit rester cohérente avec les autres pages du site (home, modèles, étiquettes, profit-calculator).

### Palette
```css
--cem-gold:      #c5a467;   /* accent principal — eyebrows, em italique, boutons or */
--cem-gold-dark: #755a25;   /* gradient bouton gold + hover */
--cem-dark:      #1a1a1a;   /* texte + fond étape récap + bouton primaire */
--cem-cream:     #f5f0eb;   /* fond étape dossier + surfaces calmes */
--cem-cream-2:   #fefaf7;   /* fond étape produits (cream très clair) */
--cem-line:      #e5e5e5;   /* bordures neutres */
--cem-mid:       #555;      /* texte secondaire */
--cem-muted:     #888;      /* texte tertiaire */
--cem-success:   #2d7a45;   /* état validé / ajouté au panier */
```

### Typographie
- **`Cormorant Garamond`** (weight 500-600, italic) → tous les H1/H2/H3, les `<em>` d'accent dans les titres, les prix affichés en gros, les totaux
- **`DM Sans`** (400-700) → body, UI, boutons, labels, paragraphes
- **Eyebrows** : ALL-CAPS, `letter-spacing: 0.14-0.18em`, couleur or, 0.74-0.85rem

### Motifs UI récurrents
- **Boutons** : pill radius `999px`, min-height 44-52px, trois variantes (`--primary` noir, `--gold` gradient, `--ghost` border dark)
- **Cartes** : radius `14-18px`, bordure 1-1.5px line, hover → `translateY(-2px à -4px)` + border or + ombre dorée subtile
- **Badges** : pill, cream background + text gold-dark, uppercase 0.7rem
- **Séparateurs prix** : dashed 1px line
- **Icônes** : SVG stroke 1.8-2, containers circulaires 48px cream
- **`<em>` dans les titres** : italique Cormorant or (rupture typographique qui rythme les H2)
- **Sections** : padding vertical 5-7rem, max-width interne 68rem

---

## 4. Ce que j'aimerais améliorer

> **Audit réalisé par analyse du code source** — note 0-10 par zone, suivi de gaps concrets à corriger.
> Valide, supprime ou nuance chaque point avant d'envoyer au designer.

### 4.1 Hero — **4/10** *(révisé après capture live)*

**Ce qui marche** : clamp responsive du titre, eyebrow + italique or cohérents avec la DA, CTAs pill radius correct.

**Gaps à corriger :**

- **BLOCKER : fond hero complètement noir** sur la version live — aucune vidéo ni image chargée. Le hero doit accueillir un visuel (vidéo lab, photo flacon éditoriale, macro texture) — à choisir et charger avant redesign
- **Asymétrie maladroite** : titre à gauche en colonne étroite (chaque mot presque sur sa propre ligne : "Créons" / "ensemble votre" / "marque" / "capillaire") + trust items à droite qui flottent dans le vide. Donne l'impression d'un layout cassé, pas d'une intention éditoriale
- **Trust items isolés** à droite, verticaux, sans rapport spatial avec le titre → on dirait qu'ils ont été posés là faute de mieux
- **Zéro identité MY.LAB** hors du texte — pas de logo-mark stylisé, pas d'ornement éditorial (filet, initiale drop-cap, numéro d'édition, millésime, ligne de signature)
- CTA "Commençons notre projet" gold + CTA "Prendre rendez-vous" ghost → **tension 50/50** qui trahit l'hésitation produit (vendre ou prendre RDV ?). Décider quelle action domine visuellement
- Sous-titre "On s'occupe de la formulation, de la réglementation et de l'impression. Vous gardez la vision." → punchline forte **noyée en 1.15rem opacity 0.92** — devrait être traitée comme un manifesto, pas comme un paragraphe

### 4.2 Étape 1 "Dossier cosmétologique" — **7/10**

**Ce qui marche** : fond cream qui calme après le hero sombre, piliers clairs, details expansible élégant, hint délai en italique.

**Gaps à corriger :**

- Les **3 cartes à border-top 3px gold** sont un pattern Bootstrap-era, pas éditorial. Un traitement plus haut de gamme : filet fin 1px + numéro 01 · 02 · 03 en gros Cormorant à l'arrière
- **Icônes circulaires cream sur carte blanche** → pas de contraste, les SVG flottent. Soit on assume un fond sombre pour les icônes, soit on supprime le cercle
- Le titre "Le dossier cosmétologique, *on s'en occupe*" est fort mais **pas mis en scène** — on pourrait faire du "on s'en occupe" un bloc visuel dédié (overlay, tamponnage, typographie XXL)
- **Aucune preuve visuelle** du sérieux réglementaire : pas de logo ANSM, pas de sceau CPNP, pas de signature du pharmacien toxicologue, pas de photo du pilote qualité. C'est 100 % texte → l'argument "on gère le réglementaire" manque de matière

### 4.3 Étape 2 "Options étiquette" — **5/10**

**Ce qui marche** : 3 cartes bien rangées, badge or cream + `em` italique dans le titre, preview post-design élégante.

**Gaps à corriger :**

- **Aucune hiérarchie commerciale** entre les 3 options. La carte du milieu (Modèles 99 €) est probablement ton sweet-spot business, mais rien ne la signale : pas de badge "Le plus choisi", pas de scale +1.05, pas de fond cream, pas de shadow marquée
- **Prix affichés sans tension** — "99 € / modèle" vs "390 € de brief" vs "Gratuit" n'ont pas de rapport comparable. Mettre un micro-tableau de positionnement (délai / exclusivité / budget) aiderait à faire le choix
- Les **3 cartes ont la même silhouette** → le Sur mesure à 390 € ne se distingue pas visuellement d'un template gratuit. Un traitement premium (fond dark, accent or liseré, badge "Collection privée") communiquerait la valeur
- Le pseudo-badge `::after "✓ Sélectionné"` en haut à droite sur `data-selected="true"` → **trop proche visuellement du badge option-badge en haut à gauche**, ça se chamaille à l'œil
- Liens `.ml-cem__option-more` en bas ("En savoir plus sur X →") sont **sous-dimensionnés** (0.85rem), traités comme un default underline. Soit on en fait un CTA secondaire légitime, soit on les vire
- **Toutes les options saignent des dollars cognitifs** (prix + meta + best-for + preview + CTA + more link = 6 couches). Sur mobile, carte fait 500-600px de haut → friction scroll énorme

### 4.4 Étape 2.5 "Forfait impression" — **4/10**

**Ce qui marche** : le callout forfait avec 3 états (empty / active / skipped) est une bonne idée fonctionnelle.

**Gaps à corriger :**

- **Répétition du pattern pilier-avec-icône-cercle** immédiatement après étape 1 → la page devient "template" au lieu d'"éditorial". Les étapes doivent se différencier visuellement, pas se copier-coller
- **Fond blanc comme étape 2** → deux sections blanches consécutives aplatissent le rythme de couleur (cream → blanc → blanc → cream-2 → dark). Besoin d'une rupture : fond texture, fond cream-2, illustration pleine largeur, photo macro d'étiquette imprimée
- La section vend un **produit physique** (impression d'étiquettes) mais est **100 % typographique** — aucune photo de flacon avec étiquette, aucun close-up de qualité d'impression, aucune comparaison noir/couleur
- Le callout "Votre forfait : À déterminer selon votre choix d'étiquette" en état empty → texte négatif, passif, anxiogène. Retournement UX nécessaire : célébrer le fait qu'on va déterminer *pour* l'utilisateur
- FAQ details en bas → fonctionnel mais **identique au details de l'étape 1** (même pattern `+` rotation). Manque de variation

### 4.5 Étape 3 "Produits" — **5/10**

**Ce qui marche** : paliers de volume avec badge `-X %`, grid responsive 1→2→3 col, CTA add-to-cart clair, fond cream-2 qui apaise la densité.

**Gaps à corriger :**

- **Grid de 150 produits max** → c'est un catalogue, pas une curation. "Composons *votre ligne*" promet une création, on livre un rayon supermarché
- **Tabs de filtre en pills neutre/dark** (9 options) → sur mobile ça wrap en 4 lignes, visuellement lourd. Un pattern chip horizontal scroll serait plus premium
- Les **tier buttons 62px min-width** sont cramped — 5 paliers sur mobile = 1 rangée serrée, texte 0.95rem qty + 0.62rem unités, difficile à toucher
- Image produit `aspect-ratio: 1` + `object-fit: cover` sur fond cream → **visuel e-commerce générique**. Besoin de lifestyle, macro texture, flacon sur fond éditorial
- **Aucune progression visible** : l'utilisateur ajoute 3 produits, rien ne célèbre "ta ligne compte 3 références" (sauf le sticky sidebar desktop qu'on voit pas en 1024px)
- Pas de **panier récapitulatif inline** en bas de section — l'utilisateur doit scroller à l'étape 4 pour voir ce qu'il a pris. Perte de contexte
- Titre de produit Cormorant 1.3rem → **pas différencié du titre de carte étape 2** (Cormorant 2rem italique). La hiérarchie typographique s'écrase

### 4.6 Étape 4 "Récap" — **6/10**

**Ce qui marche** : rupture fond dark bienvenue après 3 sections claires, timeline étapes done/pending, total en Cormorant 2.4rem blanc fort.

**Gaps à corriger :**

- Le titre "Votre marque *prend forme*" annonce une **célébration visuelle**, la section livre un **résumé checkout**. Gap de promesse énorme
- **Aucune preview du projet assemblé** : pas de thumbnail du label choisi, pas de vignettes produits alignés comme une gamme, pas de rendu "à quoi votre marque va ressembler". C'est le moment où il faut donner de la fierté
- Timeline `ml-cem__tl-step` à 3 étapes statiques (dossier done, label, products) → **pas de remontée live** des choix effectués. Statique donc sans valeur
- Recap box `rgba(white,.05)` sur dark → la box **se fond** dans le fond, manque de présence. Besoin d'un traitement plus "diplôme" / "bon de commande signé"
- Les 2 CTAs "Valider notre projet" (blanc → dark) + "Réserver 15 min avec un expert" (ghost) → **tension décisionnelle identique au hero**. L'utilisateur qui arrive ici veut probablement valider, pas recommencer l'hésitation
- **Rien ne raconte la suite** : qu'est-ce qui se passe après clic "Valider" ? Délai ? Interlocuteur ? Étapes ? L'utilisateur B2B qui va mettre 3-15K€ a besoin de visibilité post-clic

### 4.7 Sticky sidebar desktop (1200 px+) — **6/10**

- 280 px fixe à droite, filet or à gauche, total Cormorant 1.4rem → **respectable mais statique**
- **Aucune animation** à l'ajout d'un produit (pas de pulse, pas de flash du total, pas de mini-toast) → l'utilisateur ne sent pas le feedback
- **Display toggle uniquement à 1200 px+** → les laptops 1366×768 la voient mais les tablettes portrait non. Seuil trop haut
- Circles steps `18×18` → microscopiques, rendent le composant illisible à distance

### 4.8 Bottom bar mobile — **5/10**

- Mange **~70 px de viewport** permanent + `box-shadow` au-dessus → sur iPhone 12 (390×844), ça laisse ~750 px de contenu utile
- Label "1/3 étape" **ambigu** — est-ce "étape 1 sur 3 en cours" ou "1 étape sur 3 complétée" ?
- Bouton "Finaliser" en gold gradient → **brillant mais sans distinction d'état**. Devrait rester ghost tant que le projet est incomplet, devenir gold à la complétion

### 4.9 Cross-cutting (toute la page) — **5/10**

- **Aucune animation de scroll** : les sections apparaissent sèches. Un IntersectionObserver avec `opacity: 0 → 1` + `translateY(20px → 0)` stagger sur les cartes changerait l'expérience sans alourdir
- **Rythme de couleur bancal** : `cream → blanc → blanc → cream-2 → dark`. Les 2 blancs consécutifs (étapes 2 + 2.5) aplatissent le milieu. Swap possible : étape 2 blanc, étape 2.5 cream, étape 3 blanc, étape 4 dark
- **Zéro humain sur la page** alors que le service c'est "on coordonne des façonniers français qualifiés". Pas de photo de lab, pas de signature d'Yoann, pas de photo d'un façonnier au travail → la "rassurance" promise dans le brief audience reste un vœu
- **Zéro preuve sociale** : pas de testimonial, pas de logo-wall "ils nous ont fait confiance", pas de nombre (X marques lancées, Y produits en rayon). Pour du B2B à 3-15K€, c'est un gap majeur
- **Pas de mockup "voici votre produit fini"** → le promesse de la page c'est de créer une marque, la page ne montre jamais à quoi ressemble une marque MY.LAB finie sur une étagère

### 4.10 Objectifs mesurables à atteindre

- [ ] **Scroll-depth étape 4** : passer de ~? % à 60 %+ (GA4 à brancher)
- [ ] **Taux de clic** "Valider notre projet" > "Prendre RDV" (mesure actions divergentes)
- [ ] **Friction mobile réduite** : temps moyen de scroll jusqu'au premier add-to-cart < 30 s
- [ ] **Identité éditoriale propre** : page screenshotable et reconnaissable comme MY.LAB, pas comme un template Shopify B2B générique
- [ ] **Preuve matérielle** : au moins 3 visuels de produits finis / lab / façonnier intégrés

---

## 5. Contraintes techniques — NON NÉGOCIABLES

- **Shopify Liquid** — pas de build step, pas de Tailwind, pas de JSX, pas de React
- **CSS dans `{% style %}` inline** à l'intérieur du fichier section — pas de fichier CSS externe (ou alors ajout dans `assets/ml-*.css` chargé via `{{ 'file.css' | asset_url | stylesheet_tag }}`)
- **JS vanilla dans IIFE** déjà en place (l 1170+) — pas de framework, pas de module ES
- **Préfixe de classe `ml-cem__`** obligatoire (BEM) pour ne pas polluer le thème Be Yours
- **Fonts déjà chargées** dans `layout/theme.liquid` : Cormorant Garamond + DM Sans (ne pas réimporter)
- **Mobile-first impératif** — audience B2B consultée depuis portable entre 2 RDV
- **Cohérence avec le reste du site** : regarder la home, `/pages/modeles-etiquettes`, `/pages/profit-calculator` pour rester dans la même DA
- **Performance** : pas de lib externe lourde (AOS, GSAP, Framer-like). Micro-animations CSS ou Web Animations API uniquement.

---

## 6. Références visuelles

> Refs sélectionnées pour coller à la DA MY.LAB (gold + Cormorant italic + cream + dark).
> **Coche / barre** avant envoi au designer. Mieux vaut 3 refs validées que 10 tièdes.

### 6.1 Socles DA — signature éditoriale cosméto (proche Cormorant + or)

- [ ] **Officine Universelle Buly 1803** — <https://www.buly1803.com/>
  **Pourquoi** : la référence absolue pour l'italique serif + tons chauds + traitement éditorial 19e siècle. Regarder les pages produit (typo XXL italique, numérotation, filets fins, apothicaire) et leur page "Maisons" pour l'asymétrie
- [ ] **Oribe** — <https://www.oribe.com/> — *la ref la plus proche de ta DA actuelle*
  **Pourquoi** : dark + or + italiques serif, produits capillaires premium, hero éditoriaux, preuve matérielle (photos backstage, studios). Regarder <https://www.oribe.com/products> pour les vignettes et le récit
- [ ] **Kevin.Murphy** — <https://kevinmurphy.com.au/>
  **Pourquoi** : DA dark + or, storytelling lab visible, hiérarchie claire catégories/produits/rituels
- [ ] **La Bouche Rouge Paris** — <https://laboucherougeparis.com/>
  **Pourquoi** : dark luxe avec cuir + or + italiques, et surtout la page "L'Atelier" — exactement le ton "coordination artisanale" qu'il te faut pour "on s'occupe des façonniers"

### 6.2 Configurateurs / parcours composition — UX étape par étape

- [ ] **Function of Beauty** — <https://www.functionofbeauty.com/hair-quiz-landing>
  **Pourquoi** : parcours de composition d'une gamme capillaire personnalisée. Regarder la célébration en fin de quiz (preview produit + récap) — exactement ce qui manque à ton étape 4
- [ ] **Prose** — <https://prose.com/>
  **Pourquoi** : configurateur B2C hair, mais leur page de landing consultation pro montre très bien le passage "composition → rassurance labo"
- [ ] **Haeckels** — <https://www.haeckels.co.uk/>
  **Pourquoi** : dark botanical + typo serif + storytelling fabrication. Regarder les pages produit pour les compositions INCI éditoriales (ton dossier cosmétologique pourrait s'inspirer de leur traitement des ingrédients)

### 6.3 Preuve matérielle — photos lab, façonniers, produit fini

- [ ] **Davines** — <https://www.davines.com/en/sustainability>
  **Pourquoi** : ils montrent leur chaîne de fabrication (photos d'usine, portraits de chimistes, lab). Exactement ce qu'il te manque pour "façonniers français"
- [ ] **Pangaia Science** — <https://thepangaia.com/pages/science>
  **Pourquoi** : traitement éditorial de la matière première + photo macro texture + stamps de certifications. Référence pour ton étape 1 (dossier cosmétologique) et son besoin de preuve
- [ ] **Aesop** — <https://www.aesop.com/fr/fr/c/skin/ingredients/>
  **Pourquoi** : démonstration que la typo seule suffit à évoquer le sérieux. Respirations énormes, italique Garamond, filets fins — modèle pour refroidir les 2 sections blanches consécutives (étape 2 + 2.5)

### 6.4 Bonus — éditorial magazine (rythme + respiration)

- [ ] **Kinfolk** — <https://www.kinfolk.com/>
  **Pourquoi** : rythme éditorial, grid asymétrique, respirations, portraits — pour casser le feeling "template" des étapes 1 + 2.5
- [ ] **Cereal Magazine** — <https://readcereal.com/>
  **Pourquoi** : typographie éditoriale minimaliste + photo produit/lieu — peut inspirer le récap étape 4 sous forme "page de magazine"

### 6.5 Ce qu'on ne veut PAS

- Design agency showcase creux (parallax gratuits, curseurs custom, heros à animation lourde)
- Cosméto DTC grand public clicheux (pastel rose, emojis, confettis, "glow up")
- E-commerce Shopify générique (templates Dawn/Impulse sans travail éditorial)
- B2B SaaS dataviz (gradients mauve/cyan, illustrations isométriques, bento cards)
- "Bio-natural" générique feuilles vertes + fond kraft

### 6.6 Comment utiliser ces refs dans le brief

Quand tu envoies à `/frontend-design`, précise **quel aspect de chaque ref** tu retiens.  
Exemple : *"Comme Oribe pour la palette dark+or et la hiérarchie produits, comme Buly pour la typographie éditoriale des étapes 1 et 4, comme Function of Beauty pour la célébration du récap."*  
Sans ce filtrage, le designer risque de cumuler tous les styles.

---

## 7. Must-keep — NE PAS CASSER

Ces éléments fonctionnels doivent **continuer à marcher à l'identique** après le redesign. Le CSS peut changer, les data-attributes et la logique JS non.

### Structure HTML / data-attributes
- `data-label-option="standard|modeles|sur-mesure"` sur les 3 cartes étape 2
- `data-variant-id`, `data-price-cents` sur chaque carte option et produit
- `data-tier-data="6:700,12:665,..."` sur chaque carte produit étape 3 (format `qty:prixCentimes`)
- `data-option-add`, `data-product-add`, `data-validate` sur les CTAs
- `data-preview`, `data-preview-thumb`, `data-preview-ref`, `data-preview-label`, `data-preview-edit` sur les blocs preview post-design
- `data-forfait-callout`, `data-forfait-name`, `data-forfait-price` sur le callout forfait
- `data-recap-lines`, `data-recap-label`, `data-recap-products`, `data-recap-total` sur la box récap
- `data-sticky-total`, `data-bottombar-steps` sur la sidebar + bottombar
- `data-modal`, `data-modal-iframe`, `data-modal-close`, `data-modal-loader`, `data-modal-error` sur la modal configurateur

### Logique JS (l. 1170-fin)
- Gating forfait auto selon option étiquette choisie (`FORFAITS` map)
- `customerHasTag()` pour skipper le forfait si déjà abonné (tags `abo-impression-noire` / `abo-impression-couleur`)
- postMessage `design:ready` depuis l'iframe configurateur → preview card
- Line-item properties Shopify transmises au cart
- Paliers de volume : recalcul unit price + total sur click tier
- Add-to-cart AJAX via `/cart/add.js` + propagation event `cart:updated`
- Smooth-scroll vers `#etape-*` sur CTAs `data-smooth`

### Intégrations externes
- Iframe Vercel `https://mylab-configurateur.vercel.app/configurateur` (étapes 2.2 & 2.3)
- Cal.eu lien RDV `https://cal.eu/yoann-durand-xyj75z/etude-projet-marque-capillaire`
- Appstle Subscriptions (sellingPlanId 690138743118 / 690138775886)

### Variant IDs hardcodés (à garder tels quels)
```
Dossier cosmétologique : 59234431041870 / 389,90 €
Design MY.LAB (std)    : 59231350554958 / gratuit
Modèles graphiques     : 55418309083470 / 99 €
Sur mesure             : 55418346242382 / 390 €
Forfait noir           : 55418362003790, plan 690138743118, 99 €
Forfait couleur        : 55418356793678, plan 690138775886, 250 €
```

---

## 8. Livrables attendus

1. **Le fichier `sections/ml-creons-ensemble-votre-marque.liquid` modifié** — uniquement bloc `{% style %}` et ajustements HTML marginaux (classes supplémentaires, wrappers) si nécessaire. **Ne pas toucher au JS ni aux data-attributes.**
2. **Un résumé des changements** dans une réponse : zones retouchées, rationale de chaque décision DA, points où tu as hésité entre 2 options.
3. **Pas de commit** — je pousserai moi-même après validation visuelle via `shopify theme push --development --nodelete`.

---

## 9. Commande recommandée

```
/frontend-design Applique ce brief sur le fichier sections/ml-creons-ensemble-votre-marque.liquid.
Règles absolues :
- Ne touche QUE au bloc {% style %} et aux classes HTML
- Ne modifie JAMAIS les data-attributes, le JS, la structure sémantique, les IDs
- Respecte strictement la palette et la typo de la section 3 (design DNA)
- Travaille mobile-first
- Produis des diffs atomiques par zone (hero / étape 1 / étape 2 / ...) pour que je puisse reviewer pas à pas
```
