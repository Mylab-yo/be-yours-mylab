# Parcours 4 étapes, site en option, Studio dans le profil client

Date : 2026-07-10 · Repo : be-yours-mylab (thème Shopify live mylab-shop-3)

## Contexte et intention

Deux clarifications produit de Yoann :

1. **La création du site internet est facultative et indépendante** du parcours de commande. Elle ne doit plus apparaître comme une étape du parcours ni laisser croire qu'elle démarre automatiquement après la commande.
2. **Le SaaS d'étiquettes sur-mesure (MyLab Studio, espace de travail réel : BAT, retours graphiste↔client)** se découvre dans le **compte client Shopify natif**, uniquement après une commande payée contenant l'étiquette sur-mesure ET le forfait d'impression. Le Studio en mode inspiration sur l'étape étiquette du parcours reste inchangé (outil inspirationnel, libre).

## Lot A — Parcours 4 étapes, page site standalone

- **Stepper** (`snippets/ml-parcours-shell.liquid`) : supprimer l'étape 5 « Votre site » ; compteurs mobile « Étape 0X / 04 » ; retirer le case `votre-site-internet` du CTA mobile. Le lien externe « Suivi · Votre projet ↗ » reste.
- **JS** (`assets/ml-parcours.js`) : retirer `site` de `stepOrder`, `paths` et `currentStep()`.
- **theme.liquid** : retirer `page.handle == 'votre-site-internet'` de la condition de rendu du shell (la page sort du parcours).
- **Section** (`sections/ml-parcours-site.liquid`) : charge elle-même `{{ 'ml-parcours.css' | asset_url | stylesheet_tag }}` (la page reste stylée sans le shell). Copy :
  - kicker « Étape 05 / 05 — Votre site internet » → « Option · Site clé en main »
  - note CTA « Cette étape démarre automatiquement après votre commande… » → texte disant que c'est une option indépendante de la commande, sur devis, activable quand le client veut.
  - lien retour « Retour au récap » conservé.
- **Récap** (`sections/ml-parcours-recap.liquid`) : le CTA/lien vers `/pages/votre-site-internet` n'est plus présenté comme étape suivante mais comme bloc optionnel en fin de page : « Envie d'une boutique en ligne pour votre marque ? Option indépendante, sur devis. »

## Lot B — Bloc « Mon projet MY.LAB » dans le compte client

**Révision 10/07 (demande Yoann)** : le suivi de projet (BAT, échanges graphiste, validations) doit vivre dans le compte client, pas dans le parcours — et pour **tout** client ayant un projet, pas seulement le sur-mesure. Gating final : commande payée **non annulée** contenant le dossier cosmétologique (= un projet existe côté configurateur). Le texte mentionne le Studio si le client a aussi acheté le sur-mesure. La version initiale ci-dessous (gating sur-mesure + forfait) est remplacée.

### Version initiale (remplacée)

- Nouveau snippet `snippets/ml-account-studio.liquid`, rendu depuis la section `main-account` (modification minimale de la section Be Yours, ou section dédiée ajoutée au template `customers/account.json` — choisir la voie la plus propre au moment du plan).
- **Gating (option 1 retenue — Liquid pur)** : parcourir `customer.orders` ; le bloc s'affiche si au moins une commande avec `financial_status == 'paid'` contient :
  - le produit étiquette sur-mesure (variant 55418346242382), ET
  - un forfait d'impression (handle `forfait-dimpression-standard` ou `forfait-dimpression`).
  Les deux peuvent être dans des commandes différentes (deux drapeaux indépendants).
- **Contenu du bloc** : titre « Mes étiquettes sur-mesure », texte « Retrouvez les échanges avec votre graphiste, vos BAT et vos validations », bouton vers `https://mylab-configurateur.vercel.app/projet` (connexion par email de commande, mécanisme existant).
- **Limites assumées** : gating d'affichage seulement (la sécurité réelle reste côté configurateur) ; un achat en invité avec un email différent du compte ne matchera pas. Si ce cas devient fréquent, bascule prévue vers un metafield client posé par le webhook `orders/paid` (option 2, hors scope ici).

## Lot C — Parcours conscient de l'état du client connecté (ajout 10/07)

Pour un client **connecté**, le parcours s'adapte à ses achats passés (commandes payées) :

- **Dossier cosmétologique déjà acheté** (commande payée contenant `creation-du-dossier-cosmetologique`, toute date) : le parcours ne l'auto-ajoute plus au panier ; la validation du récap considère l'exigence dossier satisfaite ; le drawer récap affiche « Déjà réglé ✓ ».
- **Étiquette sur-mesure déjà achetée** (commande payée contenant le variant 55418346242382) : la carte Sur-mesure affiche « Déjà acquis ✓ » et sa sélection ajoute le marqueur 0 € (`frais-dimpression-etiquettes`) avec la propriété `Type étiquette: Sur-mesure (design existant)` au lieu de refacturer 390 €. La distinction de carte sélectionnée se fait par la propriété `Type étiquette` (le marqueur est partagé avec la carte Import).
- **Forfait d'impression ajouté d'office** : à la sélection d'une carte étiquette, si aucun forfait n'est « actif » sur le compte (= commande payée contenant un forfait datant de **moins de 12 mois**), le forfait correspondant est ajouté automatiquement au panier — Standard → `forfait-dimpression-standard` (99 €/an), Modèles / Sur-mesure / J'ai mes étiquettes → `forfait-dimpression` (250 €/an couleur). Changer de carte permute le forfait. Si un forfait est actif, rien n'est ajouté.
- **Invité (non connecté)** : comportement actuel inchangé (tout est facturé). Les drapeaux sont calculés en Liquid dans `ml-parcours-shell.liquid` et exposés via `window.MylabParcours.customerState` + `forfaitVariants`.

## Hors scope

- Aucune modification du configurateur (l'espace projet /projet montre déjà les retours graphiste↔client).
- Pas de galerie d'étiquettes/photos intégrée au compte (éventuel lot ultérieur).
- Studio inspiration de l'étape étiquette : inchangé.

## Critères de succès

1. Le stepper du parcours affiche 4 étapes partout, aucune référence « 05 » restante.
2. `/pages/votre-site-internet` est stylée sans le shell parcours, copy « option » cohérente.
3. Le récap propose le site comme option, pas comme étape.
4. Un client connecté avec commande payée contenant sur-mesure + forfait voit le bloc Studio dans `/account` ; un client sans ces achats ne le voit pas.
5. Déploiement : push des fichiers modifiés sur le thème live via `npx @shopify/cli theme push --only …`, vérification live (avec cookie panier pour bypasser le cache HTML anonyme).
