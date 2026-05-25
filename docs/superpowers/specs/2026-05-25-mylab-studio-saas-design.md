# MY.LAB Studio — Spec v2.1

**Date** : 2026-05-25
**Auteur** : Yoann Durand + Claude
**Statut** : v2.1 — V2 Yoann + 6 corrections d'attention review, prête pour plan d'implémentation Sprint 0
**Type** : Nouveau produit (extension verticale du funnel MY.LAB)

---

## 0. Changelog

### 0.1 v2 → v2.1 (cette révision — intègre la review de la V2)

Ajustements introduits par la review pour durcir les zones les plus risquées. Aucun pivot d'architecture, six précisions chirurgicales.

| # | Précision | Section |
|---|---|---|
| **A1 — R1b durci** | Réévalué Moyenne-Haute / Critique (au lieu de Moyenne / Élevé) avec un **gating explicite Sprint 0/1** : si le test compositing bout-en-bout (3-5 flacons réels variés) ne donne pas un résultat acceptable, C1 entier est à reconsidérer (fallback LoRA partiel ou approche hybride). | §10, §13 |
| **A2 — QA détourage** | Le détourage produit est un point de défaillance silencieux (verre transparent, reflets, ombres complexes). Ajout d'un **écran de validation client du PNG alpha** + **fallback détourage manuel Yoann** pour les ~10-15 % de photos difficiles. À budgéter dans les 2-4 h/client onboarding. | §6.2, §8 |
| **A3 — SP2 réévalué** | Avec dispatcher + failover cloud + image Docker partagée PC/cloud, **3-4 sem réalistes (pas 2)**. Le freelance recommandé (D3) doit couvrir **SP2 + SP6 + SP7**, pas juste SP6/SP7. | §1.4, §9, D3 |
| **A4 — VRAM benchmark Sprint 0** | Pipeline compositing complet en VRAM = ~17-20 GB simultané (SDXL + ControlNet ×2 + IP-Adapter + relight + détourage). 24 GB de la 3090 passe mais serre. Benchmark explicite **dès Sprint 0** pour éviter une mauvaise surprise en Sprint 1. | §6.1, §9 |
| **A5 — Compositing limite certains templates** | Templates "flacon flou bokeh", "flacon comme élément de scène (étagère bondée)" sont plus durs en compositing qu'en pure génération. **Ne tue pas C1**, mais restreint le repertoire R&D et peut nécessiter la LoRA en complément sur certains templates créatifs. | §4.2, §6.2 |
| **A6 — ETP partiel Phase 2 dans P&L** | Onboarding 2-4 h/client × 50 clients = 100-200 h/mois ≈ 1 ETP partiel à budgéter dès Phase 2. Le setup 890 € absorbe (44 K€/an à 50 clients), mais ça doit apparaître dans le P&L sinon mauvaise surprise. | §3.3, §8 |

### 0.2 v1 → v2 (la révision Yoann — pour mémoire)

| # | Changement | Pourquoi |
|---|---|---|
| **C1 — Pipeline produit** | Le **compositing du vrai flacon** remplace la LoRA-par-flacon comme technique *primaire* de cohérence packaging. La LoRA devient optionnelle/secondaire. | La LoRA approxime le flacon (texte d'étiquette mangé, géométrie floue) → déclenche directement le risque critique R1. En e-commerce le produit affiché doit être *exactement* le produit livré. Le compositing garantit la fidélité à 100 %. |
| **C2 — Compute jetable + failover** | Le PC est **compute pur, sans état**. Toutes les sorties partent au cloud immédiatement. Ajout d'un **pool de workers cloud GPU serverless** en burst/failover. | Un seul GPU 24/7 en résidentiel = panne unique existentielle. Et contrainte utilisateur : le PC n'est **ni serveur ni NAS**. |
| **C3 — Stockage cloud-only** | Nouveau **§7bis : modèle de localisation des données**. Aucune donnée client ne persiste sur le PC. | Contrainte explicite : images/vidéos stockées dans le cloud. |
| **C4 — Économie corrigée** | Objectif MRR réaligné (incohérence 12 K€ vs 7,8 K€ corrigée), mix de tiers réaliste, **CAC ajouté** comme métrique de pilotage #1. | §1.2 et §3.3 V1 se contredisaient. CAC totalement absent. |
| **C5 — Métriques de succès** | North star = **"visuel publié / client encore actif à M3"**, pas "5 visuels générés". WTP post-pilote ajoutée. | Générer est gratuit et ludique → ne prouve aucune valeur. La seule question : le client *publie-t-il* et *re-paie-t-il* ? |

Corrections mineures héritées de la V2 : justification SDXL/Flux complétée (§6.3), fausse précision anti-collision retirée (§4.3), coût électricité corrigé (R10), "Nouveautés visuelles" sortie du MVP (§5.2), effort humain/onboarding réaliste (§8).

---

## 1. Contexte & objectifs

### 1.1 Problème
MY.LAB Shop accompagne ses clients B2B cosmétiques sur la formulation, le packaging, l'étiquette et le flacon (parcours création de marque en production). Une fois la marque livrée, le client se retrouve seul face à la mise en marché : site e-commerce, contenu visuel régulier (Instagram, TikTok), présence digitale cohérente.

Persona typique : **un créateur de marque qui veut mettre son énergie sur les réseaux et le commercial**, pas sur la technique d'un site ou la production visuelle pro. Ni le temps, ni l'envie, ni les compétences.

### 1.2 Objectif business
Étendre le funnel vers le **digital "brand-in-a-box"** :
- **Rétention** : prolonger la valeur livrée aux clients packaging via un service collant et récurrent.
- **Acquisition** : utiliser l'offre site + IA comme aimant marketing différenciant.

**Cible 12 mois (réaliste — voir §3.3) :** la cible volume reste ~50 clients abonnés, ce qui représente **~6,5 K€ MRR** avec un mix réaliste (pas 12 K€). Atteindre 12 K€ exige ~90 clients ou un mix plus riche. On pilote sur le volume client et on laisse le MRR suivre le mix réel observé en pilote.

### 1.3 Solution
**MY.LAB Studio** combine :
1. Un **site Shopify clé-en-main** livré paramétré (theme MY.LAB mono-marque cosmétique).
2. Un **dashboard web** de génération self-service de visuels et vidéos courtes, quota mensuel par tier.
3. Une **bibliothèque de templates** en évolution permanente (~6 nouveaux/mois).
4. Un **système de cohérence + anti-collision** : flacon réel incrusté (fidélité garantie) + Brand DNA + variations seedées.

Setup one-shot (~890 €) + abo mensuel (49 / 149 / 299 €), résiliable. Le client garde son Shopify s'il part.

### 1.4 Périmètre — 8 sous-projets

| # | Sous-projet | Effort | Dépend de |
|---|---|---|---|
| **SP1** | Pipeline IA local — **compositing-first** (ComfyUI + SDXL + ControlNet + détourage/relight + IP-Adapter ; LoRA optionnelle) + wrapper API local | 4-6 sem | — |
| **SP2** | API Gateway + Queue (FastAPI VPS + Redis) **+ pool worker cloud failover + image Docker partagée PC/cloud** | **3-4 sem** *(A3 : revu à la hausse avec failover)* | SP1 |
| **SP3** | Dashboard client (Next.js + Vercel + Supabase Auth + UI génération) | 6-8 sem | SP2 |
| **SP4** | Bibliothèque templates (30 au lancement, prompts paramétriques) | 3-4 sem | SP1 |
| **SP5** | Template Shopify clé-en-main (theme config-driven) | 2-3 sem | — |
| **SP6** | Onboarding flow (Stripe → Supabase → Shopify dev store → transfer) | 2-3 sem | SP3 + SP5 |
| **SP7** | Billing + quotas (Stripe subscriptions + usage-based) | 2 sem | SP2 |
| **SP8** | Ops compute (PC compute jetable + worker cloud + monitoring + backups assets cloud) | 1 sem | — |

Chemin critique : **SP1 → SP2 → SP3 → SP6 ≈ 18 sem** vers MVP (voir §9 pour la timeline réelle).

### 1.5 Hors périmètre v1
❌ Vidéos longues/tutos (>30s) · ❌ Gestion publication réseaux · ❌ Photos réelles shooting physique · ❌ Modifs site illimitées · ❌ Multi-langue dashboard (FR only) · ❌ Plateforme e-commerce propriétaire (Shopify only) · ❌ Sous-domaine MY.LAB fallback (domaine custom obligatoire) · ❌ Influenceur/Ads management · ❌ Templates Shopify multiples · ❌ Mode prompt libre Midjourney-style · ❌ Section "Nouveautés visuelles" dynamique sur le site → Phase 2.

---

## 2. Personas & cas d'usage

### 2.1 Persona principal : "Le créateur réseaux"
25-45 ans, créateur cosmétique débutant/intermédiaire · déjà client packaging MY.LAB ou en parcours · actif Insta/TikTok (canal #1) · zéro envie de gérer un site · budget digital 100-300 €/mois → sweet spot tier **Pro 149 €**.

### 2.2 Cas d'usage récurrents
| # | Cas d'usage | Fréquence | Outil |
|---|---|---|---|
| 1 | "Visuel salle de bain bohème pour mon shampoing" | 2-3×/sem | Template → ajustement palette → génération |
| 2 | "3 visuels Halloween la semaine prochaine" | Saisonnier | Templates saisonniers → 3 variations |
| 3 | "Reel court flacon ambiance soir cosy" | 1-2×/sem | Template vidéo → vidéo 5s |
| 4 | "Mettre à jour mon site après ajout produit" | 1-2×/mois | Theme Editor Shopify (client seul) |

*(UC5 "site pull dynamique des visuels" retiré du MVP — voir §1.5.)*

---

## 3. Offre commerciale

### 3.1 Pricing
| Composant | Prix | Détail |
|---|---|---|
| **Setup clé-en-main** | 890 € one-shot (payable 1× ou 3×) | Brand DNA + Shopify dev store + theme + import catalogue (12 produits max) + pack lancement (8 visuels + 2 reels) + visio 30 min |
| **Starter** | 49 €/mois | 20 visuels + 2 reels/mois |
| **Pro** (recommandé) | 149 €/mois | 80 visuels + 8 reels/mois |
| **Studio** | 299 €/mois | 250 visuels + 25 reels/mois + vidéo qualité |
| **Add-on** | 0,50 €/visuel ; 5 €/reel | Dépassement quota |
| **Modifs site avancées** | 80 €/h | Au-delà du Theme Editor |

### 3.2 Engagement
**3 mois minimum** puis mensuel résiliable d'1 mois à l'autre · garantie satisfait 30 j (refait ou remboursement abo, pas setup) · hébergement Shopify payé séparément par le client (~32-36 €/mois Basic).
**Shopify Partner referral (vérifié) :** 20 % de l'abo Shopify du marchand, **récurrent à vie**, via *client transfer store* (exactement le flux d'onboarding §8 → éligible). Bonus, pas le moteur économique.

### 3.3 Économie unitaire (corrigée v2 + précisée v2.1)

**Hypothèse de mix réaliste** (à valider en pilote) : 40 % Starter / 50 % Pro / 10 % Studio → **~124 €/client/mois** en moyenne.

| Métrique | Phase 1 (10 cl.) | Phase 2 (50 cl.) | Phase 3 (200 cl.) |
|---|---|---|---|
| MRR abos (mix réaliste) | ~1 240 € | ~6 200 € | ~24 800 € |
| MRR Shopify referral (20 % × ~36 € × n) | ~72 € | ~360 € | ~1 440 € |
| **MRR total** | **~1 310 €** | **~6 560 €** | **~26 240 €** |
| Coût infra mensuel | 30-50 € | 50-90 € | 90-150 € |
| **Coût humain mensuel (A6)** | ~20-40h (early, SAV onboarding lourd) | **~100-200h ≈ ~1 ETP partiel à budgéter** | ~200-400h ≈ 1-2 ETP |
| Setup fees (annuel) | ~9 K€ | ~45 K€ | ~180 K€ |

**A6 — ETP partiel Phase 2** : à 2-4 h/client onboarding en early × 50 clients = 100-200 h/mois. Le setup 890 € absorbe largement (44 K€/an à 50 clients couvre un ETP partiel chargé), **mais cette ligne doit apparaître explicitement dans le P&L** sinon surprise en Phase 2. Recrutement à anticiper avant d'atteindre 30 clients actifs.

**Le CAC (le trou de la v1) :**
- **Acquisition chaude** (base MY.LAB existante, pilote) : CAC quasi nul (email + relation existante). C'est le terrain de chasse du MVP.
- **Acquisition froide** (scale 50+) : CAC **inconnu, à mesurer dès le launch**. C'est le risque business #1.
- **Garde-fou conseillé :** tant que **CAC < setup fee (890 €)**, chaque acquisition est *cash-flow positive dès J0* et l'abonnement devient pure marge. À surveiller comme métrique de gating avant de dépenser en acquisition.

---

## 4. UX produit — dashboard de génération

### 4.1 Choix d'UX : Option D — Templates + ajustements
Bibliothèque de compositions/ambiances pré-cuisinées, **3-4 paramètres ajustables** (couleur dominante, ambiance, saison, texte overlay optionnel). Le système assemble le prompt sous le capot.
Pourquoi pas prompt libre : tue le persona. Pourquoi pas templates purs : lassitude → churn. Option D = micro-création + qualité garantie + extensible.

### 4.2 Bibliothèque templates
**30 au lancement** : 20 core (4 ambiances × 5 variantes), 6 saisonniers rotatifs, 4 trending. **+6/mois** post-lancement (veille tendances 30 min/sem). Communication : email mensuel + badge "NEW" 14 j.

**A5 — Limitation compositing à connaître au R&D :** certains templates créatifs sont plus durs à réaliser en compositing pur (ex. *"flacon flou en bokeh d'arrière-plan"*, *"flacon comme un élément parmi d'autres sur une étagère bondée"*, *"flacon vu de loin dans une scène"*). Pour ces templates :
- **Privilégier la LoRA en complément** (re-introduction ciblée), ou
- **Adapter la composition** pour mettre le produit en avant (où le compositing excelle)

Documenter ce trade-off pendant SP4 et ne pas survendre la palette créative au lancement.

### 4.3 Cohérence & anti-collision (3 leviers réels)

1. **Produit réel incrusté** (cœur de C1) : le vrai flacon détouré est composité dans chaque scène → fidélité packaging garantie, et deux marques différentes n'ont jamais le même produit. Le levier anti-collision le plus fort, gratuit.
2. **Brand DNA injecté automatiquement** : palette + textures + accents extraits à l'onboarding, appliqués en système (prompt + IP-Adapter sur mood board de marque) → deux marques sur le même template ont des ambiances visiblement distinctes.
3. **Seed unique + variations "soft"** par génération (angle, lumière, heure, accessoires) → variation de composition.

**Risque résiduel honnête :** la collision n'est plus "pixel-identique" (rendue impossible par produit réel + Brand DNA) mais "**ambiance similaire**" entre deux marques sur un template populaire. Mitigé par Brand DNA strict ; détecteur de quasi-doublon en Phase 2 si besoin.

---

## 5. Site Shopify clé-en-main

### 5.1 Approche : un seul template excellent, config-driven
Un seul theme dérivé du theme MY.LAB actuel (base Be Yours customisée), adapté mono-marque cosmétique.

### 5.2 Personnalisation par client
| Élément | Source |
|---|---|
| Palette (3 couleurs) | Brand DNA onboarding |
| Logo + favicon | Upload client |
| 3-4 photos hero | Générées au setup (pack lancement) |
| Textes (Accueil, À propos, Contact) | IA-générés, validés client |
| Structure menu | 5 entrées max |
| ~~Section "Nouveautés visuelles"~~ | **Retiré du MVP → Phase 2** |

### 5.3 Pages incluses (5)
Accueil, Catalogue, Fiche produit (template), À propos, Contact.

### 5.4 Catalogue
12 produits max au setup (+5 €/mois par lot de 5 au-delà). Import CSV ou saisie manuelle. Descriptions IA validées client.

### 5.5 Modifs post-setup
Theme Editor en self-service (texte, photos, sections). Modifs design avancées 80 €/h. Guide self-help fourni, pas de SAV technique récurrent inclus.

### 5.6 Pré-configurations livrées
Stripe connecté · DPD pré-configuré (tarifs 2026 MY.LAB) · TVA UE (HT + TVA au checkout) · DNS guidé vers domaine custom (3 chemins, §8).

---

## 6. Pipeline IA local — **compositing-first**

### 6.1 Hardware
| Composant | Spec | Note |
|---|---|---|
| GPU | RTX 3090 24 GB (MSI Trio) | Tient ~300 clients ; **VRAM à benchmarker dès Sprint 0 — voir A4 ci-dessous** |
| CPU | Ryzen 9 9900X | ✅ |
| RAM | 32 Go DDR5 6000 CL30 | ⚠️ → 64 Go après Phase 1 |
| Stockage | NVMe Lexar EQ790 2 To | ✅ (cache modèles uniquement, voir §7bis) |
| Alim | Corsair RM1200X 1200W | ✅ |
| **Add-on** | UPS Eaton 5E / APC (~120 €) | Sprint 0 — protège un job en cours, pas un rôle serveur |

**A4 — Benchmark VRAM Sprint 0 (critique).** Le pipeline compositing complet en VRAM simultané :
- SDXL base : ~7 GB
- ControlNet (Depth + Canny, 2 instances) : ~5 GB
- IP-Adapter : ~1 GB
- Relight model (IC-Light ou équivalent) : ~3-5 GB
- Détourage (BiRefNet/SAM si gardé en VRAM) : ~1-2 GB
- **Total simultané : ~17-20 GB**

Sur 24 GB de la 3090 ça passe **mais ça serre.** Si on dépasse, soit on offload partiellement (latence +20-40 %), soit on chaîne les étapes sans tout charger en même temps (architecturalement plus propre mais plus de latence I/O). À benchmarker **dès Sprint 0** sur 3-5 cas réels pour valider le headroom — pas en Sprint 1 sinon on découvre le problème trop tard.

> **Note C2 :** l'UPS ne sert plus à garantir un uptime 24/7 (le failover cloud s'en charge), mais juste à ne pas corrompre un job/training en cours lors d'une micro-coupure. Le PC peut être éteint sans casser le service.

### 6.2 Pipeline de génération image — la nouvelle approche

**Principe : générer la scène où SDXL excelle, puis incruster le VRAI produit.** On ne demande plus au modèle de "dessiner le flacon" (là où il échoue), on lui demande de dessiner un *monde* autour d'un produit réel.

```
1. Génération de scène     SDXL + ControlNet (Depth/Canny pour la compo)
                           + Brand DNA (prompt + IP-Adapter sur mood board marque)
                           → arrière-plan / ambiance, avec zone réservée au produit
2. Insertion produit       Photo réelle du flacon détourée (PNG alpha, faite à l'onboarding)
                           placée dans la scène à l'échelle/position voulue
3. Harmonisation           Relight + ombrage + color grade pour intégrer le produit
                           (candidats à benchmarker Sprint 1 : IC-Light, inpainting
                           de bords, génération d'ombre)
4. Upscale + finition       RealESRGAN x2
```

**Bénéfices vs LoRA-primaire :**
- **Fidélité produit 100 %** (le flacon affiché = le flacon livré) → désamorce le risque critique R1.
- **Onboarding plus rapide et déterministe** : "détourer N photos produit" remplace "entraîner N LoRA × 20 min sans QA".
- **Anti-collision renforcé** gratuitement (produit réel = unique par marque).

**A2 — QA du détourage = point de défaillance silencieux à industrialiser.** Selon la qualité des photos uploadées par le client, le détourage automatique (BiRefNet/SAM/rembg) peut bavé sur :
- Verre transparent / liquide visible → frontière mal détectée
- Reflets sur surface brillante → intégrés au PNG alpha
- Ombre portée importante au sol → souvent gardée comme partie du produit
- Bouchon de couleur similaire au fond → frontière manquante

**Pipeline anti-bavure obligatoire :**
1. Détourage auto (BiRefNet par défaut, SAM en fallback selon photo)
2. **Écran de validation client** dans l'onboarding : "Voici votre flacon détouré, est-ce bien net ?" (avant/après, zoom 200%, possibilité de re-upload une meilleure photo)
3. **Si re-upload ne résout pas** : ticket auto pour détourage manuel par Yoann (~5 min/photo dans Photoshop ou alternative) sur 10-15 % des cas attendus
4. Stockage du PNG alpha validé dans Supabase Storage (cf. §7bis)

Ne pas négliger ce point : un détourage approximatif tue C1 entier (le client voit son flacon "découpé aux ciseaux").

**A5 — Limitation créative à assumer.** Le compositing excelle quand le produit est central et net dans la scène. Pour les compositions "flacon en arrière-plan flou", "flacon parmi d'autres objets", "flacon vu de loin", la LoRA reste pertinente en complément (re-introduction ciblée Phase 2 ou pour des templates spécifiques).

**La LoRA devient secondaire/optionnelle :** utile uniquement pour l'imagerie "univers de marque" sans produit central, ou en Phase 2 pour des styles signature, ou pour certains templates créatifs (A5). Elle sort du chemin critique de l'onboarding.

### 6.3 Modèles IA — choix final
| Usage | Modèle | Latence (3090) | Licence |
|---|---|---|---|
| Image base (scène) | **SDXL 1.0** | ~10s | CreativeML Open RAIL++, commercial OK |
| Composition fixée | **SDXL ControlNet** (Depth + Canny) | +2s | Open |
| Détourage produit | **rembg / BiRefNet / SAM** (à benchmarker S0) | ~1-3s | À confirmer (candidats open) |
| Harmonisation/relight | **IC-Light ou équivalent** (à benchmarker S1) | +3-8s | À benchmarker Sprint 1 |
| Cohérence ambiance marque | **IP-Adapter** | +1s | Open |
| Cohérence produit | **Compositing photo réelle** (C1) | inclus | n/a (photo client) |
| LoRA produit (optionnel) | **LoRA SDXL** (Kohya) | training ~20 min | Open |
| Vidéo courte (tous tiers) | **LTX-Video** (5s, 768×512) | ~50s | Open commercial |
| Vidéo qualité (Studio) | **HunyuanVideo** (3s, 480p, offload) | ~5 min | Open commercial |

**Rationale SDXL :** le vrai critère est la **maturité de l'écosystème ControlNet / IP-Adapter / LoRA / relight**, nettement supérieure sur SDXL — décisif pour un pipeline de compositing. Note : FLUX.1 [schnell] est Apache 2.0 (commercial OK), une licence commerciale FLUX.1 [dev] s'achète en self-serve, et FLUX.2 [dev] est sorti fin 2025 — mais l'écosystème compositing y est encore plus pauvre. **À ré-évaluer en Phase 2** quand les outils Flux matureront.

### 6.4 Capacité — 1 RTX 3090 tient jusqu'à ~300 clients
| Phase | Clients | Volume/mois | GPU util. |
|---|---|---|---|
| 1 | 10 | ~800 visuels + 100 reels | 2 % |
| 2 | 50 | ~4 000 + 500 | 10 % |
| 3 | 200 | ~16 000 + 2 000 | 40 % |

### 6.5 Orchestration locale
ComfyUI (workflows JSON versionnés, API HTTP) + wrapper FastAPI local qui : lit un job Redis, sélectionne le workflow selon le template, injecte Brand DNA + produit réel + ajustements, **upload le résultat sur R2 puis supprime le local** (voir §7bis), retourne l'URL signée. Cloudflare Tunnel expose le PC au VPS sans IP fixe.

---

## 7. Architecture technique globale

```
┌─────────────────────────────────────────────────────────────┐
│   Dashboard client (Next.js + Tailwind, Vercel)             │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS REST
                           ▼
┌─────────────────────────────────────────────────────────────┐
│   API Gateway (FastAPI, VPS startec-paris)                  │
│   - Auth Supabase JWT, quotas, Stripe webhooks, Shopify API │
│   - DISPATCHER : route le job vers PC ou worker cloud       │
└──────────────────────────┬──────────────────────────────────┘
                           │ Redis Queue (survit aux reboots)
              ┌────────────┴─────────────┐
              ▼                          ▼
┌──────────────────────────┐  ┌──────────────────────────────┐
│ Worker PRIMAIRE (PC)     │  │ Worker FAILOVER/BURST (cloud)│
│ ComfyUI, compute pur     │  │ GPU serverless (RunPod/Modal/│
│ SANS ÉTAT, Cloudflare    │  │ Replicate). Scale-to-zero.   │
│ Tunnel                   │  │ Même image, même contrat.    │
└────────────┬─────────────┘  └───────────────┬──────────────┘
             │  upload direct + suppression locale            │
             └──────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│   Cloudflare R2 — SOURCE DE VÉRITÉ des sorties              │
│   visuels + vidéos + LoRA + assets. URLs signées 24h.       │
└─────────────────────────────────────────────────────────────┘

┌──────────────────────┐  ┌──────────────────────┐  ┌─────────────────────┐
│ Supabase             │  │ Stripe               │  │ Shopify (Partner)   │
│ Auth + Postgres +    │  │ Subscriptions +      │  │ Theme via Admin API │
│ Storage (assets)     │  │ usage-based + hooks  │  │ Transfer au client  │
└──────────────────────┘  └──────────────────────┘  └─────────────────────┘
```

### 7.1 Dispatcher — logique de routage
Le VPS route chaque job selon :
- **PC en bonne santé** (heartbeat < N s) **et** queue peu profonde → **PC** (coût ~électricité).
- **PC injoignable** (reboot, panne, éteint, FAI down) → **worker cloud**.
- **Queue au-dessus d'un seuil** (pic) → **débordement vers cloud** en parallèle du PC.
- **Job prioritaire** (reel Studio payant, pack onboarding) → cloud si le PC est saturé.

Le worker cloud utilise **la même image conteneur** que le PC (ComfyUI + modèles), tire la LoRA/le produit depuis R2, génère, upload R2, rend l'URL signée — **contrat identique**. Serverless = **~0 € à l'idle**, facturé à la seconde uniquement en burst/failover.

### 7.2 Stack — récapitulatif
| Couche | Choix | Hébergement | Coût/mois |
|---|---|---|---|
| Dashboard | Next.js 14 + Tailwind + shadcn/ui | Vercel | 0 → 20 € |
| Auth | Supabase Auth (magic link + Google) | Supabase | Inclus Pro |
| DB | Supabase Postgres | Supabase | 25 € (Pro) |
| Storage assets | Supabase Storage | Supabase | Inclus Pro |
| **Storage sorties** | **Cloudflare R2 (source de vérité)** | Cloudflare | ~10 € (10 To) |
| API Gateway | FastAPI | VPS startec-paris | 0 € additionnel |
| Queue | Redis | VPS | 0 € (déjà là) |
| Worker primaire | ComfyUI custom | **PC (compute jetable)** | Électricité |
| **Worker failover** | **Même image** | **Cloud GPU serverless** | ~0 € idle, à l'usage |
| Tunnel PC↔VPS | Cloudflare Tunnel | Cloudflare | 0 € |
| Billing | Stripe | Stripe | 1,4 % + 0,25 €/tx |
| Email | Resend | Resend | 0 → 20 € |
| Monitoring | Uptime Kuma + Sentry | VPS + Sentry free | 0 € |
| **TOTAL infra** | | | **~50-90 €/mois** |

### 7.3 Choix structurants
Supabase (auth+DB+storage en 1) · API Gateway sur VPS (uptime même si PC down) · Redis (jobs survivent aux reboots) · R2 (egress 10× moins cher que S3) · Cloudflare Tunnel · **+ worker cloud failover** (supprime la panne unique).

---

## 7bis. Modèle de localisation des données

**Règle d'or : aucune donnée client ne persiste sur le PC. Le PC est jetable et réimageable à tout moment sans perte.**

| Donnée | Où vit-elle (source de vérité) | Persiste sur le PC ? |
|---|---|---|
| OS, ComfyUI, code worker | PC | Oui — infra pure, re-déployable |
| Modèles de base (SDXL, ControlNet, IP-Adapter, relight, upscaler) | PC (cache) + R2 (backup) | Cache, re-téléchargeable — pas de la donnée client |
| LoRA par client (si utilisée) | **R2** | Cache LRU éphémère uniquement |
| Photos produit détourées (PNG alpha) | **Supabase Storage** | Non — tirées au job, supprimées après |
| Brand DNA / assets onboarding | **Supabase Storage** | Non |
| **Visuels & vidéos générés (sorties client)** | **Cloudflare R2** | **NON — générés en tmpfs, push R2, suppression immédiate** |
| Métadonnées génération, quotas, historique galerie | **Supabase Postgres** | Non |

**Implémentation :**
- Le worker écrit ses sorties dans un **répertoire éphémère (tmpfs/RAM disk ou /tmp)**, les **upload vers R2**, puis **supprime le local** dans le même handler de job.
- Un **janitor** purge `/tmp` à la fin de chaque job et au boot (filet de sécurité).
- Conséquence directe : **le PC n'est ni serveur ni NAS.** Pas de RAID, pas d'obligation 24/7, pas de fichiers clients qui s'accumulent. S'il est éteint, les jobs partent au cloud. S'il meurt, on en branche un autre et il re-télécharge les modèles — zéro donnée perdue.
- Le client ne télécharge **jamais** depuis le PC : il télécharge depuis R2 via URL signée. Le PC n'est jamais exposé au client.

---

## 8. Onboarding client end-to-end

```
J0      Client paie setup + 1er mois (Stripe Checkout)
        → Compte Supabase auto + magic link → Notif Yoann

J0+1h   Onboarding guidé (4 écrans)
        1. Brand DNA — 6 questions visuelles (palette, ambiance, ton, style)
        2. Produits — upload photos flacon par produit (3-5 typique)
            → DÉTOURAGE auto (secondes)
            → ÉCRAN DE VALIDATION CLIENT : "Voici votre flacon détouré, est-ce net ?"
            → Si NON : re-upload (meilleure photo) ou fallback ticket Yoann (~5 min/photo)
        3. Catalogue — import CSV ou saisie (max 12 produits)
        4. Domaine — wizard 3 chemins (A: déjà un domaine / B: achat Shopify Domains / C: conseil de nom → B)

J0+1h   Background auto (après validation détourage) :
        - Stockage PNG alpha validés dans Supabase Storage
        - Génération pack lancement (8 visuels + 2 reels) par compositing
        - Provisioning Shopify dev store (compte Partner Yoann)
        - Theme MY.LAB Studio configuré avec Brand DNA

J+1     Yoann : valide les 8 visuels, polish dev store, déclenche le transfer
J+2     Visio onboarding 30 min (Cal.com) → site live, dashboard activé

Total : 2-3 jours du paiement à la mise en ligne
```

**Effort humain réaliste (A6) :** la V1 disait "45 min/client". En early, prévois **2-4 h/client** :
- SAV DNS des clients non-techniques (chemin A = générateur de tickets)
- Reprises de génération
- Ajustements Brand DNA
- **Détourages manuels** sur 10-15 % des photos difficiles (A2)
- Visio 30 min

La marge du setup (890 €) l'absorbe largement, mais **ne base pas l'argument de scalabilité sur 45 min**. À 50 clients = 100-200 h/mois ≈ 1 ETP partiel à budgéter explicitement (cf. §3.3).

**Scale :** la visio 30 min ne scale pas au-delà de ~30 clients (R5). Phase 2 → onboarding asynchrone (Loom + chat), visio optionnelle premium. **Mais ne promets pas un onboarding "100 % auto sans intervention humaine" :** le transfert de store Shopify exige une action du client (accepter la propriété + ajouter un moyen de paiement). Vise un onboarding *fortement automatisé avec un point de contact humain léger*, pas "zéro humain".

---

## 9. Plan de bataille — 10 sprints

| Sprint | Durée | Contenu | Livrable testable |
|---|---|---|---|
| **0** | **1,5 sem** *(A4)* | Setup PC : UPS, ComfyUI, drivers, **benchmark VRAM pipeline compositing complet**, **premier test compositing bout-en-bout** (scène SDXL + flacon réel incrusté + relight) sur 3-5 flacons variés | "Je génère 1 visuel avec mon vrai flacon incrusté en local, **et je connais le headroom VRAM précis**" |
| **1** | 3 sem | SP1 — **Pipeline compositing core** : workflows ComfyUI (scène + ControlNet + détourage + relight + upscale) + API wrapper local + upload R2/suppression locale. **Benchmark relight + décision modèle vidéo + GATING A1 : si compositing pas acceptable, escalade plan B.** | "Génération HTTP localhost → image compositée → URL R2 ; rien ne reste sur le PC ; qualité jugée acceptable sur 5 flacons variés" |
| **2** | **3-4 sem** *(A3)* | SP2 — API Gateway VPS + Redis + 1 worker PC **+ dispatcher avec failover cloud + image Docker partagée PC/cloud** | "Requête VPS → image sur PC OU cloud si PC down → URL signée R2" |
| **3** | 3 sem | SP3 p1 — Auth Supabase + onboarding 4 écrans **+ écran validation détourage** + galerie | "Je crée un compte, fais l'onboarding (sans Shopify), valide le détourage de mes flacons, vois mes générations" |
| **4** | 2 sem | SP4 p1 — 10 premiers templates (3 par ambiance) avec Brand DNA + compositing | "10 templates utilisables, Brand DNA + produit réel appliqués" |
| **5** | 3 sem | SP3 p2 — Écran génération (browse + sliders + génération asynchrone + download) | "Je choisis un template, ajuste, génère, télécharge depuis R2" |
| **6** | 2 sem | SP5 — Theme Shopify config-driven + scripts provisioning *(sans section Nouveautés)* | "Je provisionne un dev store paramétré via API + theme installé" |
| **7** | 2 sem | SP6 + SP7 min — Onboarding Stripe + transfer Shopify (semi-manuel OK MVP) | "Client paye → compte créé → transfer manuel → accès dashboard" |
| **🎯 MVP** | — | **5-10 pilotes MY.LAB (gratuit ou 49 €) — 4-6 sem de feedback structuré, mesure du taux de publication** | — |
| **8** | 2 sem | Quotas Stripe usage-based + Brand DNA raffiné | "Quotas temps réel, overages facturés auto" |
| **9** | 3 sem | 20 templates de plus (total 30) + onboarding fortement automatisé (transfer assisté, pas 100 % auto) | "30 templates, onboarding minimal-touch sauf transfer + visio" |
| **🚀 Launch** | — | **Tarif public, marketing, mesure du CAC, scale** | — |

**Timeline — réalité :** ~24-25 sem solo à 20-30 h/sem (compte ×1,5 à ×2 vs estimation théorique). Le provisioning/transfert Shopify (Admin API) et le billing usage-based Stripe **plus le dispatcher cloud failover** sont notoirement plus longs que "2 sem chacun". La bonne réponse n'est **pas** de compresser le temps mais de **couper le scope MVP** (déjà fait : compositing > LoRA simplifie l'onboarding, "Nouveautés visuelles" retirée, transfer semi-manuel assumé au MVP).

**Recommandation A3 mise à jour :** **1 freelance dev mid-senior** ciblé sur **SP2 (dispatcher cloud) + SP6 (Shopify) + SP7 (Stripe)** — c'est là que le solo se noie. ~20-30 K€ pour 8-10 semaines de freelance, accélère ×~2 sur le chemin critique.

---

## 10. Risques & mitigations

| # | Risque | Prob. | Impact | Mitigation |
|---|---|---|---|---|
| R1 | **Qualité visuels insuffisante / "AI slop", flacon mal rendu** | Moyenne | **Critique** | **Compositing du flacon réel (C1) → fidélité produit garantie.** Brand DNA strict. Validation Yoann 4 sem pilote. La barre cosmétique est haute → métrique "publié" (§11) comme juge de paix. |
| **R1b** | **Harmonisation compositing ratée** (produit "collé", lumière incohérente, ombres absentes) | **Moyenne-Haute** *(A1)* | **Critique** *(A1)* | **Gating Sprint 0/1 : si test compositing bout-en-bout ne donne pas résultat acceptable sur 3-5 flacons variés, C1 entier à reconsidérer (plan B = approche hybride scène-par-template avec LoRA en complément).** Benchmark relight Sprint 1 (IC-Light + ombrage), itération templates avec zones de lumière maîtrisées, fallback LoRA pour cas durs. |
| **R1c** | **Détourage produit raté** (verre transparent, reflets, ombres complexes) *(A2)* | Élevée *(toutes les photos clients ne sont pas pro)* | Élevé | **Pipeline obligatoire : auto + écran validation client + re-upload + fallback manuel Yoann ~5 min/photo sur 10-15 % des cas.** Budgété dans 2-4 h/client onboarding. |
| R2 | **Collision d'ambiance entre clients** | Faible-Moyenne | Élevé | Produit réel unique + Brand DNA distinct → collision pixel impossible. Détecteur quasi-doublon Phase 2 si besoin. |
| R3 | **PC instable / mort GPU** | Moyenne | ~~Élevé~~ → **Faible** | **Failover cloud (C2) : PC down ⇒ jobs routés au cloud, service continu.** PC jetable, zéro donnée dessus (§7bis), remplaçable sans perte. UPS protège juste le job en cours. |
| R4 | **Lassitude templates** | Élevée | Élevé | +6/mois min, email + badge NEW, veille active. |
| R5 | **Onboarding visio ne scale pas >30 clients** | Certaine | Moyen | Phase 2 → async Loom + chat. *(Mais pas "100 % auto" — transfer Shopify exige le client.)* |
| R6 | **Shopify réduit la commission Partner** | Faible | Faible | Referral = bonus, pas le moteur. Plan viable sans. |
| R7 | **Concurrent Wix+IA / outil compositing US** | Élevée | Moyen | Différenciation = niche cosmétique B2B + **fidélité produit par compositing** + Brand DNA spécifique cosmétique. Dur à copier sans connaître le métier. |
| R8 | **Time-to-market trop long** | Moyenne | Moyen | Scope MVP coupé + freelance ciblé SP2/SP6/SP7. |
| R9 | **Effort R&D templates sous-estimé** | Élevée | Moyen | Workflow IA-assisté, freelance designer si bouchon. **Plus : A5 limite certains templates créatifs en compositing → re-budgétiser.** |
| R10 | **Coût électricité PC** | Faible | Faible | ~18 €/mois système complet en charge active. Avec failover, PC pas obligé de tourner 24/7. |
| **R11** | **CAC froid inconnu** | Moyenne | **Élevé** | Mesurer dès le launch. Garde-fou : CAC < 890 € (setup) ⇒ acquisition cash-flow positive J0. Privilégier la base MY.LAB chaude tant que le CAC froid n'est pas prouvé. |
| **R12** | **VRAM 24 GB insuffisante pour pipeline compositing complet** *(A4)* | Faible-Moyenne | Moyen | **Benchmark dès Sprint 0** sur cas réels. Si dépassement, soit offload partiel (latence +20-40 %), soit chaînage étapes sans tout charger simultané. Pas un blocker, juste une contrainte d'architecture. |
| **R13** | **ETP partiel non-budgété Phase 2** *(A6)* | Certaine si ignoré | Moyen | **Inscrire ~100-200 h/mois support/onboarding dans le P&L Phase 2.** Anticiper recrutement avant 30 clients actifs. |

---

## 11. Métriques de succès

### 11.1 Pilote (5-10 clients, 4-6 sem)
- **North star — Taux de publication** : % de visuels générés **effectivement téléchargés ET publiés** par le client. *C'est la seule preuve de valeur.* Cible : >50 % des générations menant à une publication.
- **Rétention d'usage S4-S8** : le client génère-t-il **encore** à un mois ? Indicateur avancé du churn. Cible : >60 % encore actifs à S6.
- **Activation** : % qui complètent l'onboarding **et téléchargent leur 1er visuel** (pas "génèrent 5"). Cible : >80 %.
- **Willingness-to-pay** : % de pilotes qui passent au **plein tarif** après le pilote. *Le vrai test.* Cible : >40 %.
- **Qualité** : taux de régénération comme proxy + sondage explicite "posteriez-vous ce visuel ?" sur un échantillon. Cible regen <30 %.
- **Qualité détourage** *(A2)* : % de photos client validées au 1er détourage auto. Cible : >70 % auto, <15 % fallback manuel Yoann.
- **Stabilité** : uptime *service* (PC+failover) > 99,5 %, erreurs API < 1 %.

### 11.2 Launch (6-12 mois)
- **MRR** : ~3 K€ à 6 mois, ~6,5 K€ à 12 mois *(cible réaliste ; 12 K€ = ~90 clients ou mix plus riche)*.
- **Nouveaux clients/mois** : 5-10.
- **Churn mensuel** : < 5 % (la métrique qui compte vraiment).
- **CAC** : mesuré, maintenu **< 890 €** (garde-fou). LTV/CAC > 3×.
- **Setup conversion** : 15-25 % des prospects.

---

## 12. Décisions ouvertes

| # | Décision | Statut | Échéance |
|---|---|---|---|
| D1 | Modèle vidéo Phase 2 (HunyuanVideo / Wan 2.x / Veo open) | Benchmark Sprint 1 | Avant Sprint 4 |
| D1b | **Modèle de relight/harmonisation compositing** (IC-Light vs alternatives) | Benchmark Sprint 1 | Sprint 1 |
| D1c | **Modèle de détourage par défaut** (BiRefNet vs SAM vs rembg, qualité sur photos cosmétiques) *(A2)* | Benchmark Sprint 0 | Sprint 0 |
| D2 | Mode hybride (contenu manuel premium ?) | Après pilote | Phase 2 |
| D3 | **Freelance dev** sur SP2 + SP6 + SP7 *(A3 — élargi)* | À arbitrer (recommandé) | Avant Sprint 2 |
| D4 | Quotas/prix exacts par tier | Strawman validé, ajuster après pilote | Phase 2 |
| D5 | Provider cloud GPU failover (RunPod / Modal / Replicate) | Benchmark coût/latence | Sprint 2 |
| D6 | App Shopify "MY.LAB Content" | Phase 3 | 12+ mois |
| D7 | Internationalisation EN | Hors v1 | Phase 3 |
| D8 | 2e GPU | Pas avant 300 clients | Phase 3 |
| D9 | Favoris/collections dashboard | Nice-to-have | Phase 2 |
| D10 | Édition post-génération (recadrage, overlay éditable) | Nice-to-have | Phase 2 |
| **D11** | **Recrutement support/onboarding Phase 2** *(A6)* | À anticiper avant 30 clients actifs | Phase 2 |

---

## 13. Prochaines étapes immédiates

1. **Valider cette v2.1** (arbitrage compositing-first §6, failover cloud §7, et les 6 corrections d'attention §0.1).
2. **Décider D3** (freelance dev élargi à SP2 + SP6 + SP7) et **D5** (provider cloud GPU).
3. **Écrire le plan d'implémentation Sprint 0** (skill `writing-plans`) — qui contiendra :
   - Setup hardware (UPS, drivers, etc.)
   - Installation ComfyUI + modèles
   - **Benchmark VRAM** *(A4)* avec critère de succès chiffré
   - **Test compositing bout-en-bout** *(A1)* sur 3-5 flacons réels variés, avec critère d'acceptabilité défini ex-ante
   - **Benchmark détourage** *(D1c)* sur photos cosmétiques réelles
   - Gating : si A1 ou A4 échoue, escalade plan B avant Sprint 1
4. **Préparer 5-10 pilotes MY.LAB chauds**, avec briefing de l'offre et mesure du taux de publication dès J1.

---

**Fin de spec v2.1 — corrections C1-C5 (V2) + A1-A6 (review V2.1) intégrées, prête pour plan d'implémentation Sprint 0.**
