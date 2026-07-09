# MY.LAB Studio — Spec V3

**Date** : 2026-07-08
**Auteur** : Yoann Durand + Claude
**Statut** : Design validé en brainstorming, prêt pour implementation plan
**Remplace** : Spec V2.2 (`2026-05-25-mylab-studio-saas-design.md`) sur l'architecture et le périmètre. Les sections V2.2 sur le pricing récurrent et le dashboard self-service restent la référence pour la Phase 2.

---

## 0. Le pivot V2.2 → V3

| Sujet | V2.2 | V3 |
|---|---|---|
| Génération image/vidéo | Pipeline local (ComfyUI + SDXL + compositing sur RTX 3090) + failover cloud | **Appels API via fal.ai : Nano Banana Pro (image), Seedance 2.0 (vidéo)**. Les modèles locaux ne sont pas au niveau. |
| Nature du produit | SaaS autonome (dashboard + abonnements) | **Funnel d'accompagnement intégré au site MyLab**, de l'arrivée du client jusqu'au site livré. Le dashboard self-service récurrent part en Phase 2 (spec dédiée). |
| Fidélité produit | Compositing du vrai flacon (détourage PNG alpha) | Photos du vrai flacon comme **images de référence** Nano Banana Pro. Plus de pipeline de détourage. Porte de validation à passer (Lot 0). |
| Infra | SP1/SP2/SP8 (worker local, dispatcher, ops compute), repo `mylab-studio-worker` | **Obsolètes, abandonnés.** L'app existante `mylab-configurateur` (Next.js + Postgres) devient le backend/frontend Studio. |
| Prix setup | 890 € | **~1900 € HT**, sur devis. Facturation possiblement via une structure juridique dédiée hors MyLab (décision ouverte, hors scope technique). |

## 1. Objectif

Créer un funnel continu qui prend le client MyLab à son arrivée sur le site et l'amène jusqu'à un **site e-commerce Shopify livré clé en main** intégrant sa gamme de produits MyLab :

> dossier cosmétologique → **① choix des produits** → **② choix du modèle d'étiquette** → **③ suivi de la création d'étiquette jusqu'à validation (BAT)** → **④ onboarding Studio** → génération du pack de lancement → **livraison du site**

Bénéfices attendus : rétention (le client reste dans l'écosystème MyLab après le packaging), acquisition (« on vous livre votre site » comme différenciant), revenu setup ~1900 € HT + referral Shopify Partner 20 % à vie.

## 2. Décisions structurantes (issues du brainstorming)

1. **Les produits AVANT l'étiquette.** Le client fige sa gamme (étape ①) avant la création d'étiquette : le graphiste ne décline le design que sur les références réellement commandées. Conséquence : interversion des étapes 02/03 du parcours multi-pages Shopify existant. Le forfait impression reste couplé au choix d'étiquette.
2. **Le client paie avant la créa.** Le checkout Shopify (dossier + produits + modèle d'étiquette + forfait) intervient à la fin de l'étape ② ; le paiement (`orders/paid`) déclenche la demande d'étiquette. Pas de checkout différé.
3. **La maquette est produite par un graphiste**, pas par le client. Le design du configurateur sert de brief ; le livrable de production est un fichier Illustrator (contrainte impression). L'amélioration de l'éditeur self-service est un chantier reporté.
4. **L'app `mylab-configurateur` devient l'app Studio** : espace client « Mon projet » en pleine page (magic link NextAuth, Postgres = source de vérité de l'état du funnel, Cloudinary pour les assets, Resend pour les emails). Cible : sous-domaine dédié type `studio.mylab-shop.fr`. Pas d'iframe pour les écrans authentifiés (cookies tiers fragiles) — l'iframe reste uniquement pour le configurateur en étape ②, comme aujourd'hui.
5. **Évolution du parcours existant, pas de refonte.** Les pages parcours Shopify restent la colonne vertébrale des étapes ①-② ; le stepper s'étend pour afficher ③ et ④ et pointer vers l'app.
6. **Génération via un agrégateur unique (fal.ai)** : une API, une facture, swap de modèle facile si mieux sort.
7. **Livraison = modèle V2.2 conservé** : dev store provisionné sur le compte Shopify Partner de Yoann → configuration automatique → polish manuel → transfer au client (qui prend l'abo Shopify à sa charge ; referral 20 % récurrent pour MyLab).
8. **Paiement Studio découplé du funnel** : sur devis (~1900 € HT), facturation manuelle (Odoo ou structure dédiée à créer). Aucun paiement en ligne Studio dans la V3.

## 3. Architecture

```
Site Shopify (be-yours-mylab)                    App Studio (mylab-configurateur étendu)
┌─────────────────────────────────┐              ┌──────────────────────────────────────┐
│ Landing parcours + dossier       │              │ Espace client « Mon projet »         │
│ ① parcours-produits              │   webhook    │ ③ Suivi BAT (client + back-office)   │
│ ② parcours-etiquette             │  orders/paid │ ④ Onboarding 3 écrans                │
│    (configurateur en iframe)     │ ───────────► │ Galerie pack + suivi livraison       │
│ Stepper étendu (①→④) ──liens────►│              │ Postgres = état du funnel            │
└─────────────────────────────────┘              └──────┬───────────┬───────────┬───────┘
                                                        │           │           │
                                                   fal.ai API   Shopify     Resend /
                                                   (NBP image,  Partner API Cloudinary
                                                   Seedance     (dev store,
                                                   vidéo)       transfer)
```

- **Site Shopify** : vitrine, pédagogie, achats. Aucune nouvelle logique d'état au-delà du stepper étendu (le panier reste l'état des étapes ①-② comme aujourd'hui, via `ml-parcours.js`).
- **App Studio** : tout l'état durable (projet, BAT, onboarding, génération, livraison). Rôles : client, graphiste, admin (Yoann).
- **Orchestration** : côté app (API routes + queue simple en Postgres pour les jobs fal.ai). Pas de n8n dans le chemin critique — il peut consommer les mêmes webhooks pour les notifications annexes si besoin.

## 4. Le funnel étape par étape

### 4.0 Landing + dossier cosmétologique (inchangé)
La landing `/pages/creons-ensemble-votre-marque` et l'auto-add du dossier (389,90 €) fonctionnent comme aujourd'hui. Seul le stepper change : il affiche désormais 4 étapes + « votre site », les étapes ③/④ pointant vers l'app.

### 4.1 Étape ① — Choix des produits (déplacée avant l'étiquette)
`/pages/parcours-produits` passe en étape 02 du parcours (interversion avec l'étiquette). Fonctionnement inchangé (tabs catégories, paliers volume, add-to-cart). La gamme au panier définit les références que le graphiste devra décliner.

### 4.2 Étape ② — Choix du modèle d'étiquette
`/pages/parcours-etiquette` passe en étape 02. Le configurateur Vercel reste en iframe/modale. Deux ajouts :
- La demande envoyée depuis le configurateur **embarque la liste des références** de la gamme (lue depuis le panier Shopify, transmise via le postMessage existant ou en query param).
- À la soumission, l'app crée (ou rattache) le **compte client** (magic link) et un **`Project`** en base.
Le checkout Shopify (dossier + produits + étiquette + forfait) clôt cette étape. Le webhook `orders/paid` fait passer le projet en « payé » et active la demande d'étiquette côté graphiste.

### 4.3 Étape ③ — Suivi de la création d'étiquette jusqu'au BAT validé
Remplace les allers-retours email actuels. Dans l'app, côté client et côté back-office.

**Machine à états (par demande)** :
`Demande reçue → En création (graphiste) → BAT vN envoyé → Gamme validée ✓`
« Modifications demandées » sur un BAT renvoie en « En création » et incrémente la version (v1, v2, …).

**Règles** :
- **Validation par référence** : chaque référence (produit × contenance) a son statut propre ; la demande est « Gamme validée » quand toutes les références le sont. Bouton « Tout valider ».
- **Chaque transition notifie par email** (Resend) : BAT envoyé → client ; modifications demandées → graphiste ; gamme validée → Yoann + déblocage de l'étape ④.
- **Fichiers** : le graphiste uploade des aperçus BAT (PNG/PDF basse définition, filigranés) visibles par le client. Les fichiers Illustrator de production restent internes (stockage privé), transmis à l'impression après validation.
- **Back-office** : file des demandes (statut, références validées/total, dernière action), fiche demande (brief configurateur, gamme, fil de commentaires par référence, upload BAT en sélectionnant les références couvertes, historique des versions).

### 4.4 Étape ④ — Onboarding Studio (3 écrans)
Débloquée à la validation de la gamme. Simplifiée vs V2.2 : l'import catalogue disparaît (la gamme vient de la commande, les visuels d'étiquettes des BAT).

1. **Brand DNA** — 6 questions visuelles (palette **pré-remplie depuis l'étiquette validée**, ambiance, ton, style, univers, cible).
2. **Photos produits** — 1 à 3 photos par référence du vrai flacon étiqueté. Images de référence pour Nano Banana Pro ; pas de détourage ni d'écran de validation PNG alpha.
3. **Société, prix, domaine, contenus** :
   - Infos société (raison sociale, forme juridique, SIRET, adresse, contact) → pages légales et footer.
   - **Prix publics par référence**, avec suggestion pré-calculée (prix B2B × coefficient conseillé, cohérent avec le calculateur de marges du site).
   - Wizard domaine 3 chemins (A : domaine existant / B : achat Shopify Domains / C : conseil de nom → B).
   - 2-3 questions « histoire de marque » (pourquoi, pour qui, promesse) → matière première des textes IA.
   - **« Vos éléments existants » (optionnel)** : upload libre de photos, vidéos, textes, logo, charte… Ces éléments sont priorisés sur le contenu généré (une vraie photo de la fondatrice vaut mieux qu'un visuel IA) et versés au brief de génération.

### 4.5 Génération du pack de lancement
Au submit de l'onboarding, l'app enfile les jobs fal.ai :
- **~12 visuels** (Nano Banana Pro ; prompts = templates × Brand DNA, photos produit en référence) — le client en sélectionne 8 dans une galerie « Mon projet ».
- **2 reels courts** (Seedance 2.0).
- Assets stockés sur Cloudinary ; coûts par asset tracés (colonne coût sur le job).
**Revue Yoann obligatoire avant exposition au client** : écran admin pour écarter/relancer les ratés (c'est là que la fidélité étiquette se contrôle). Idem pour les textes IA (home, descriptions produits).

### 4.6 Livraison du site
| Quand | Qui | Quoi |
|---|---|---|
| J0 | Auto | Provisioning dev store (API Partner), thème MyLab Studio installé, settings Brand DNA injectés, produits créés (gamme, prix publics, photos + visuels étiquette) |
| J+1 | Yoann | Revue pack + textes, polish du dev store |
| J+1 | Client | Sélection des 8 visuels dans la galerie |
| J+2 | Yoann + client | Transfer du store (le client accepte la propriété + prend l'abo Shopify + active Shopify Payments — KYC), branchement domaine, visio 30 min. **Site en ligne.** Facturation setup sur devis. |

**Checklist du site livré** : thème configuré (Brand DNA) · home complète (hero + histoire de marque + mise en avant gamme + réassurance, textes IA validés, éléments client prioritaires) · boutique prête (produits, prix, descriptions) · pages légales FR (mentions légales, CGV, confidentialité, retours — templates pré-rédigés remplis avec les infos société) · zones/tarifs de livraison simples · emails transactionnels aux couleurs de la marque · domaine branché.

Le provisioning peut être **semi-manuel au début** (scripts + checklist) et s'automatiser lot par lot — comme assumé en V2.2.

## 5. Modèle de données (app Studio, Postgres/Prisma)

```
Project        1/client/marque : statuts du funnel, customer, lien commande Shopify (order_id)
├── LabelRequest      brief configurateur (design id, mode), forfait, statut global
│   ├── LabelReference   produit, contenance, statut (en création / BAT envoyé / validée)
│   ├── BatVersion       n° version, fichier aperçu, note graphiste, références couvertes
│   └── Comment          auteur (client|graphiste), texte, référence concernée, timestamps
├── Onboarding        réponses Brand DNA, infos société, prix par référence, domaine,
│                     histoire de marque, uploads « éléments existants »
├── GenerationJob     type (image|video|texte), prompt/template, statut, coût, asset Cloudinary
└── Delivery          dev store id, checklist, statut transfer, domaine, date visio
```

Rôles utilisateur : `client`, `graphiste`, `admin`. Le graphiste ne voit que le back-office BAT.

## 6. Intégrations

| Intégration | Usage | Notes |
|---|---|---|
| Webhook Shopify `orders/paid` | Crée/active la demande d'étiquette, lie la commande au Project | Filtrage : commandes contenant le dossier ou des items parcours |
| fal.ai | Nano Banana Pro (image), Seedance 2.0 (vidéo) | Webhooks de complétion → update GenerationJob ; budget par projet tracé |
| API LLM (Claude) | Textes home + descriptions produits + suggestions de nom de domaine | Passe par la revue Yoann, jamais direct client |
| Shopify Partner API | Provisioning dev store, installation thème, création produits, transfer | Semi-manuel accepté au MVP |
| Resend | Notifications transactionnelles (BAT, validation, livraison) | Déjà intégré à l'app |
| Cloudinary | Aperçus BAT, photos produits, assets générés | Déjà intégré ; fichiers Illustrator sur stockage privé séparé |

## 7. Risques & portes de validation

| # | Risque | Mitigation |
|---|---|---|
| R1 | **Fidélité étiquette insuffisante** en génération (texte mangé, logo déformé) — hérité V2.2, toujours LE risque critique | **Lot 0 = porte GO/NO-GO** : test sur 3-5 vrais flacons avec photos de référence avant toute construction du Lot 4. Plan B : pack limité aux compositions sûres (packshots, produit central) + photos réelles client |
| R2 | Fidélité produit en **vidéo** (Seedance) encore plus dure | Testée au Lot 0 ; fallback : reels construits sur les visuels validés (montage animé) plutôt que génération pleine |
| R3 | Coûts API par projet mal connus | Mesurés au Lot 0, tracés par job ensuite ; marge setup ~1900 € très confortable a priori |
| R4 | Charge graphiste = goulot d'étranglement | Le workflow BAT rend la charge visible (file, délais) ; la gamme réduite aux références commandées la limite by design |
| R5 | Transfer Shopify exige des actions client (propriété, abo, KYC Payments) | Jamais promettre « 100 % auto » ; accompagnement en visio de livraison (inchangé V2.2) |
| R6 | Structure juridique / facturation Studio non décidée | Hors scope technique ; le funnel aboutit à un devis, la facturation reste manuelle |

## 8. Hors scope V3

❌ Dashboard de génération self-service + abonnements récurrents (Phase 2, spec dédiée) · ❌ Amélioration de l'éditeur d'étiquettes self-service (chantier reporté « quand les outils le permettront ») · ❌ Paiement en ligne du setup Studio · ❌ Automatisation complète du provisioning dès le MVP · ❌ Multi-langue · ❌ Gestion de publication réseaux sociaux.

## 9. Phasage — 6 lots livrables indépendamment

| Lot | Contenu | Valeur livrée |
|---|---|---|
| **0 — Spike** | Compte fal.ai ; test fidélité 3-5 vrais flacons (Nano Banana Pro) + 1 test Seedance ; mesure des coûts par asset | **GO/NO-GO** sur le volet visuel |
| **1 — Fondations** | Interversion produits/étiquette dans le parcours Shopify ; modèle `Project` ; webhook `orders/paid` ; espace « Mon projet » minimal | Le funnel réordonné tourne, chaque commande crée un projet |
| **2 — BAT** | Workflow complet (back-office graphiste, BAT multi-références, commentaires, versions, notifications) | Remplace les allers-retours email actuels — utile seul |
| **3 — Onboarding** | Les 3 écrans + upload éléments existants + déblocage à la validation de gamme | Collecte client structurée |
| **4 — Génération** | Intégration fal.ai (queue Postgres), pack visuels/reels, galerie de sélection, écran de revue admin | Le pack de lancement sort tout seul |
| **5 — Livraison** | Provisioning dev store, injection thème/produits/légal/home, textes IA, checklist transfer + visio | **Funnel complet de bout en bout** |

Ordre imposé : 0 → 1 → 2 → 3 → 4 → 5 (le Lot 0 peut tourner en parallèle de 1-2 ; le Lot 4 ne démarre pas sans GO du Lot 0).

## 10. Critères de succès

- Un client passe du panier à la « Gamme validée » sans un seul email de BAT.
- Un projet complet (paiement → site en ligne) tient en ≤ 2-3 jours ouvrés côté MyLab, avec ≤ 2-4 h de travail humain (hors graphiste).
- Le graphiste ne produit que les références commandées, jamais la gamme entière.
- Le pack de lancement présenté au client ne contient aucun visuel où l'étiquette est illisible ou déformée (revue Yoann systématique).
- Le site livré est vendable le jour du transfer : produits, prix, légal, home, domaine, paiement actif.
- Le stepper du site Shopify reflète l'état réel du projet à chaque étape (Shopify ↔ app cohérents).
