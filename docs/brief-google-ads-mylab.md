# Brief stratégique — Campagne Google Ads MY.LAB

> Document destiné à Claude Cowork (ou toute agence / freelance SEA) pour construire la stratégie et la campagne Google Ads de MY.LAB.
> **Version :** 2026-04-22 · **Contact :** Yoann Durand — yoann@mylab-shop.com

---

## 1. L'entreprise

| Champ | Valeur |
|-------|--------|
| Raison sociale | **SARL STARTEC** (capital variable 300 000 €) |
| SIRET | 499 500 668 00060 |
| RCS | Avignon |
| Marque commerciale | **MY.LAB** (anciennement MyLab Shop) |
| Siège | 231 Avenue de la Voguette, 84300 Cavaillon |
| Dirigeant | Yoann Durand |
| Site e-commerce | mylab-shop-3.myshopify.com (domaine primaire `mylab-shop.com` à rebrancher) |
| Instagram | [@mylab.france](https://www.instagram.com/mylab.france/) |
| Facebook | [/mylabfrance](https://www.facebook.com/mylabfrance) |

---

## 2. Business model

MY.LAB est un **coordinateur de filière cosmétique française, spécialisé capillaire**. Depuis la fermeture de son labo propre de Velaux, la production est sous-traitée à **plusieurs laboratoires façonniers français**, chacun sélectionné pour son expertise (shampoings, masques, crèmes, sérums).

MY.LAB reste :
- **Responsable qualifié** au sens du règlement CE 1223/2009 (CPNP + PIF 10 ans)
- Coordinateur formulation, conditionnement, expédition
- Interlocuteur unique client B2B

**Positionnement :** Made in France, 96% naturel, sans tests animaux, filière française qualifiée.

> ⚠️ **Claims à ne PAS utiliser dans les annonces :** "notre laboratoire", "2 600 m² ECOCERT", "labo propre", ni affirmation directe de certifications ISO 22716 / Cosmos / Ecocert tant qu'elles ne sont pas vérifiées par façonnier.
>
> ✅ **Claims autorisés :** "Made in France", "96% naturel", "sans tests animaux", "filière française qualifiée", "CPNP inclus".

---

## 3. Cible B2B (cœur de campagne)

| Segment | Profil | Besoin principal |
|---------|--------|------------------|
| **Salons de coiffure indépendants** | 1-5 bacs, patron-coiffeur, France | Revente en marque propre, marge, exclusivité locale |
| **Coiffeurs à domicile / freelances** | SASU / micro-entreprise | Petites quantités récurrentes, marque personnelle |
| **Réseaux / franchises capillaires** | 5-50 salons | Volumes moyens, MDD cohérente |
| **Créateurs de marque cosmétique** | DNVB, influenceurs beauté, entrepreneurs | Formules custom + étiquettes personnalisées, gros volumes |
| **Distributeurs pro / grossistes** | France + Europe (DE, BE, ES, IT) | Gros volumes, tarifs dégressifs |
| **Revendeurs spa / instituts** | Spas, hôtels, centres bien-être | Lignes d'accueil + revente |

**Zones géographiques prioritaires :** France (PACA, Paris, Lyon, Aix-en-Provence, Marseille) → puis Europe (Belgique, Allemagne, Espagne, Italie — via DPD).

**À exclure du ciblage :** particuliers B2C (pas de vente à consommateurs finaux en petites unités).

---

## 4. Proposition de valeur (arguments campagne)

1. **Créez votre propre marque de cosmétique capillaire** — formulation, étiquettes personnalisées, CPNP inclus
2. **Made in France** via façonniers sélectionnés
3. **96% d'ingrédients naturels**, non testés sur animaux
4. **Pas de minimum de commande** sur le catalogue standard
5. **Frais de port offerts dès 500 € HT** France
6. **Tarifs dégressifs** automatiques par palier de contenance
7. **Délais réassort 15-20 jours**
8. **Livraison Europe** via DPD (8 zones configurées)
9. **Dossier cosmétologique complet** fourni (CPNP, PIF 10 ans)
10. **Paiement fractionné ALMA** disponible

---

## 5. Gamme produits

- ~162 références Shopify (~150 vendables Odoo)
- **Familles :** shampoings, après-shampoings, masques, crèmes de coiffage, sérums, huiles, sprays, soins spécifiques (platine, cuivre, brillance, détox, volume)
- **Contenances :** 200 ml / 500 ml / 1000 ml (testeurs disponibles)
- **Packs :** duo, trio, coffret, pack pro 10 kg
- **Étiquettes personnalisables** : modèles prêts-à-l'emploi + designs custom
- **Gros volumes :** 8 familles de fermetures flacons (pump, spray, flip-top, dropper, nozzle, disc, twist-cap, screw-cap), 4 matériaux, min 50 kg/référence en custom

### Noms commerciaux courants
Les clients utilisent souvent des noms commerciaux différents des noms techniques — bon à connaître pour la négation et les termes de recherche :

| Nom commercial | Produit |
|---|---|
| brillance | protecteur/protectrice de couleur |
| blond polaire / platine | déjaunisseur platine |
| blond cuivré / cuivré | coloristeur cuivre |
| spray volume / spray détox | spray texturisant |

---

## 6. Pricing / économie

- **Tarifs dégressifs** codés par contenance (pricelist Odoo "TARIFS DEGRESSIFS MYLAB", id=3, 527 items)
- **Paliers 200 / 500 / 1000 ml** automatiques en front
- **Gros volumes custom** : devis via configurateur 5 étapes → email HTML automatique au client (workflow n8n `sQ3XQo0HuzmCizbr`)
- **Paiement B2B** : CB Shopify, virement, ALMA (paiement fractionné)
- **Panier moyen cible :** > 500 € HT (seuil franco port France)

---

## 7. Landing pages disponibles

| Intention | URL / handle |
|-----------|--------------|
| Catalogue général | `/collections/la-boutique-my-lab` |
| Testeurs (1ère commande) | `/collections/boutique-testeurs` |
| Catalogue + formules | `/pages/catalogue-prix-et-formules-mylab` |
| Commande express | `/pages/commande-express` |
| **Gros volumes (configurateur)** | `/pages/vous-cherchez-a-commander-en-gros-volume-cest-par-ici` |
| Créer sa marque — étapes | `/pages/etapes-creation` |
| Personnalisation | `/pages/personnalisation` |
| Étiquettes (modèles) | `/pages/modeles-etiquettes` |
| Étiquettes (designs) | `/pages/designs-etiquettes` |
| Configurateur étiquette | `/pages/configurateur` |
| FAQ (11 Q/R FR) | `/pages/faq` |
| Réalisations (preuve sociale) | `/pages/nos-realisations` |
| Témoignages (Aurélien, Amandine, Minh) | `/pages/temoignages` |
| SEO local | `/pages/marseille`, `/pages/lyon`, `/pages/aix-en-provence`, `/pages/paca` |
| Dossier cosmétologique | `/pages/creation-du-dossier-cosmetologique` |
| Prise de RDV commercial | `/pages/prise-de-rendez-vous` |
| Jeu concours (lead magnet) | `/pages/jeu-concours` |

---

## 8. Pistes de mots-clés (à valider via DataForSEO avant de lancer)

### Intention "créer sa marque" — forte valeur, intention commerciale haute
- créer sa marque de cosmétique
- créer sa marque de shampoing
- créer sa marque de produits capillaires
- fabricant cosmétique marque blanche
- laboratoire cosmétique marque propre
- façonnier cosmétique France
- cosmétique marque blanche personnalisée
- shampoing marque blanche personnalisé
- private label cosmetics France
- OEM cosmétique capillaire

### Intention "pro / salon"
- grossiste cosmétique coiffure
- fournisseur produits capillaires salon
- shampoing professionnel grossiste
- produits coiffure pro gros volume
- distributeur cosmétique capillaire France
- marque blanche salon de coiffure
- produits capillaires B2B France

### Intention "made in France / naturel"
- shampoing naturel made in France
- cosmétique bio française grossiste
- produits capillaires naturels 96%
- shampoing sans sulfates grossiste
- cosmétique capillaire vegan France

### Intention locale
- laboratoire cosmétique PACA
- laboratoire cosmétique Provence
- fabricant cosmétique Cavaillon
- fabricant cosmétique Marseille / Lyon / Aix-en-Provence

### Negative keywords recommandés
`amazon · aliexpress · carrefour · monoprix · sephora · gratuit · échantillon gratuit · emploi · recrutement · stage · MSC MyLab · laboratoire d'analyse · labo médical · ingrédients bruts · matière première cosmétique · MLM · réseau de vente · chien · animal · vétérinaire`

---

## 9. Concurrents probables à benchmarker

**Labos FR / façonniers :**
- Laboratoire Expanscience
- Gravier
- Sicaf
- Natura-Tec
- Cosmepack
- Cosmétiques Création

**Revendeurs pro (cible salon) :**
- Generik
- Beauty Coiffure
- Coiffeur.com
- CoiffShop

À benchmarker : angle d'accroche, offre d'appel, packaging prix affiché, délais, zone de livraison.

---

## 10. Objectifs de campagne recommandés

### Phase 1 — Acquisition ciblée B2B (3 mois)
| Campagne | Type | Destination |
|---|---|---|
| "Créer sa marque cosmétique" | Search | `/pages/etapes-creation` |
| "Grossiste capillaire / salon" | Search | `/collections/la-boutique-my-lab` |
| "Gros volumes / marque blanche" | Search | `/pages/vous-cherchez-a-commander-en-gros-volume-cest-par-ici` |
| Catalogue shopping | Performance Max | Feed Shopify |
| Remarketing visiteurs | Display + Search | `/collections/boutique-testeurs` (porte d'entrée petit panier) |
| Local PACA | Search géociblé | `/pages/marseille`, `/pages/paca` |

### KPI cibles
- **Objectif macro :** demandes de devis (configurateur gros volume + formulaire contact) + 1ère commande testeur
- **Panier moyen visé :** > 500 € HT (franco port)
- **CPA cible à définir selon phase :**
  - Lead qualifié (form contact / RDV) : **30–80 €**
  - 1ère commande testeur : **80–150 €**
  - 1ère commande gros volume (> 500 €HT) : **150–250 €**
- **LTV B2B indicative :** cycle de réassort 15-20j → potentiel 6-12 commandes/an/client actif

---

## 11. Tracking à vérifier avant lancement

- [ ] Google Tag / GA4 posé sur Shopify (via Theme + Google & YouTube app)
- [ ] Conversions Shopify natives (achat, ajout panier, début checkout)
- [ ] **Événement custom "Demande devis gros volume"** → à brancher sur submit du webhook `https://n8n.startec-paris.com/webhook/bulk-order-quote`
- [ ] **Événement custom "Formulaire contact"** → submit formulaire contact
- [ ] **Événement custom "Prise de RDV"** → submit page `/pages/prise-de-rendez-vous`
- [ ] Remarketing audiences : visiteurs 30j, panier abandonné, vus produit, vus page gros volume
- [ ] Google Merchant Center : feed Shopify synchronisé + validation EAN/GTIN
- [ ] Données structurées Product + Offer déjà en place dans le thème

---

## 12. Bémols à corriger AVANT dépenser en SEA

### 🔴 Critique (à faire avant lancement payant)
1. **Brancher `mylab-shop.com` comme domaine primaire** (Admin Shopify → Settings → Domains). Sans ça :
   - Autorité SEO mal attribuée (mylab-shop-3.myshopify.com capte les liens entrants)
   - Chaque euro dépensé en SEA construit de l'autorité sur une URL qui sera migrée plus tard
   - Les annonces Google Ads afficheront `.myshopify.com` = signal "site peu sérieux" pour un acheteur B2B
2. **Crédibilité "laboratoire" sous-étayée** :
   - Pas de photos labo / équipe / production
   - Pas de certifications tierces affichées (ISO 22716, Ecocert, Cosmos)
   - Impact fort sur le taux de conversion du trafic froid qui compare plusieurs labos

### 🟡 Recommandé (non bloquant)
- Compte LinkedIn MY.LAB à créer (cible B2B → `sameAs` schema + campagnes LinkedIn Ads plus tard)
- Avis Google My Business à collecter (quelques clients ambassadeurs)
- Trustpilot ou équivalent (crédibilité B2B)
- Chiffres clés publics : nb clients, nb références, années d'activité, pays livrés

---

## 13. Contraintes & règles d'or pour le brief créa

- ❌ **Jamais :** "notre labo à Velaux", "2 600 m² ECOCERT", "labo propre", "nous fabriquons"
- ✅ **Toujours :** "nous coordonnons une filière française", "Made in France", "façonniers français sélectionnés", "96% naturel", "sans tests animaux"
- Certifications ISO 22716 / Ecocert : ne pas affirmer que MY.LAB les possède — à re-vérifier par façonnier avant tout claim
- Ton : **pro B2B français, chaleureux, concret, pas de buzzwords US**, tutoiement/vouvoiement à aligner sur le site (site = vouvoiement)
- Respecter la charte couleur du site (à extraire depuis le thème live)
- Mentions obligatoires annonces : SARL STARTEC ou MY.LAB, pas "MyLab Shop" (nom legacy)

---

## 14. Ressources disponibles côté MY.LAB

- **Catalogue produits** : `assets/ml-product-map.json` (source de vérité tarifs dégressifs)
- **Feed Google Shopping** : natif Shopify via app "Google & YouTube"
- **Pixel Meta** : à vérifier
- **Base clients Odoo** : ~150 produits vendables, SARL STARTEC company_id=3
- **Workflows n8n devis** : déjà en place (configurateur gros volume + email manuel + email automatique)
- **Configurateur 5 étapes** : opérationnel en prod (`/pages/vous-cherchez-a-commander-en-gros-volume-cest-par-ici`)

---

## 15. Questions ouvertes / à valider avec Yoann

- Budget mensuel Google Ads envisagé ?
- Priorité phase 1 : **créer sa marque** ou **revente salon** ou **gros volumes** ?
- Zones Europe prioritaires (ordre de déploiement) ?
- Un commercial peut-il traiter les leads entrants rapidement (<24h) ?
- Photos labo / équipe disponibles rapidement ou à planifier ?
- Certifications vérifiables par façonnier à remonter ?

---

*Brief consolidé depuis 3 audits UX + 1 audit SEO + inventaire complet catalogue/workflows. Toutes les URLs, IDs et chiffres sont valides au 2026-04-22.*
