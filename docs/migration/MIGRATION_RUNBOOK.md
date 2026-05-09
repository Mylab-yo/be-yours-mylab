# MY.LAB Migration Runbook — WP → Shopify

**Cutover window** : Samedi 9 → Lundi 11 mai 2026
**Domain** : `mylab-shop.com` (actuellement WP, basculer sur Shopify dimanche 10/05)
**Registrar / DNS** : **PlanetHoster** (panel N0C, NS = `nsa/nsb/nsc.n0c.com`)
**Hébergeur WP actuel** : PlanetHoster — IP `46.105.115.38`
**Theme live Shopify** : `theme-export-be-yours` (id 184014340430)
**Stratégie d'import** : DELTA samedi (pas full re-import — orders + customers depuis **2026-02-26** confirmé par Yoann)

---

## ✅ Bugs résolus avant cutover

### Bug 1 : Footer — lien `/pages/faq` 404 ✅ RÉSOLU 2026-05-06

- Yoann a renommé le handle Shopify `faq-my-lab` → `faq`. Le footer `sections/footer-group.json:45` pointe vers `/pages/faq` et résout désormais.
- TODO post-cutover : créer un redirect `/pages/faq-my-lab → /pages/faq` au cas où des liens externes pointaient vers l'ancien handle.

### Bug 2 : Redirect cassé `creer-sa-marque...` ✅ RÉSOLU 2026-05-05

- Redirect id `1678942208334` modifié pour pointer vers `/pages/les-etapes-de-creation-de-marque`. URL ranké à 125 clics/16 mois préservée.

---

## 📅 Planning J-3 → J+1

### J-3 (Jeu 7/05)
- [x] **Yoann** : Installer Matrixify sur Shopify (installé, abonnement payant à activer le jour J)
- [x] **Yoann** : Outils d'export WP en place (plugin "Advanced Order Export For WooCommerce" déjà utilisé pour les CSV forfait — Matrixify n'a pas de companion WP, c'est une app Shopify only)
- [ ] **Yoann** : Sortir le mapping `wp_handle, shopify_handle` pour produits/collections (CSV) — sinon je reste sur le fuzzy match
- [x] **Yoann** : Corriger les 2 bugs ci-dessus dans l'admin Shopify
- [ ] **Claude** : Vérifier le mapping et compléter `redirect_plan.csv` avec les corrections

### J-2 (Ven 8/05)
- [ ] **Claude** : Dry-run de `apply_redirects.py` (mode lecture seule)
- [ ] **Yoann** : Valider le rapport dry-run
- [ ] **Yoann (avec Claude)** : Exécuter `apply_redirects.py --apply --priority P1_HOT,P2_RANKED,P3_INDEXED` (les 49 entrées prioritaires)
- [ ] **Yoann** : Réduire le TTL DNS chez le PlanetHoster (panel N0C) (3600s → 300s) — préparation pour cutover dimanche

### Volet configurateur Vercel + nouveau thème Shopify (parallèle migration)

Side-track hors WP→Shopify mais à coordonner sur la même fenêtre. Source : findings consolidés PR configurateur 2026-05-06.

| # | Action | Quand | Où |
|---|---|---|---|
| 1 | Tester le preview Vercel de la PR configurateur (wizard, studio, refinement) | Avant merge | URL preview du PR |
| 2 | Merger la PR configurateur | Quand le preview est validé | GitHub PR #1 du repo configurateur |
| 3 | Vérifier env vars Vercel prod (`N8N_LEAD_WEBHOOK_URL`, optionnellement `GEMINI_DAILY_MAX_*`) | Avant samedi | Vercel Dashboard → Settings → Env Variables |
| 4 | Activer la section "MyLab — Info visuels" dans le customizer du **nouveau** thème Shopify | Avant ou pendant samedi | Shopify Admin → Themes → Customize → page customers/account → Add section |
| 5 | Activer le nouveau thème Shopify en prod (= bascule visuelle) | Samedi (avant ou après l'import Matrixify selon ton ordre) | Shopify Admin → Themes → Activate |

**Notes** :
- Le webhook lead capture (n8n workflow `83JGhapLmLlBjR30`) est **inbound**, donc la migration WP→Shopify ne le casse pas. Aucune action n8n nécessaire. Source : `validate-design/route.ts:165` consomme `N8N_LEAD_WEBHOOK_URL` → vérifier juste que la var est set.
- La section [sections/mylab-visuals-notice.liquid](sections/mylab-visuals-notice.liquid) est untracked en local — elle existe déjà dans le nouveau thème Shopify (2146 bytes confirmés par l'audit), mais devra être commitée dans le repo dans la consolidation post-cutover.
- Issues non-bloquantes notées (à traiter post-cutover) :
  - Vitest config probablement à fixer avec `pool: "forks"` (isolation worker entre fichiers)
  - `.gitignore` doublon `.vercel` (ligne 38 ou 74) — cosmétique

✅ **Ordre acté (Yoann 2026-05-06)** : **Activation nouveau thème Shopify AVANT l'import Matrixify**.

Donc déroulé samedi :

1. (matin) Désactiver Staff Notifications + 6 Flows
2. **Activer le nouveau thème Shopify** (Themes → Activate)
3. **Activer la section "MyLab — Info visuels"** dans le customizer du nouveau thème
4. Lancer `samedi_run.ps1` → générer les 3 CSV
5. Import Matrixify : Customers → Orders → tags abo (en MERGE)
6. Réactiver Flows + Staff Notifications

### J-1 (Sam 9/05)
- [x] **Yoann** : Abonnement Matrixify payant actif (confirmé 2026-05-06)
- [ ] **Yoann** : Backup CSV Customers Shopify (Customers → Export → All) — filet de sécurité avant tagging
- [ ] **Yoann** : **DÉSACTIVER les Staff Order Notifications** (Shopify Admin → Settings → Notifications → Staff Order Notifications → décocher tous les destinataires) — sinon 112+ emails "nouvelle commande" reçus pendant l'import. Réactiver après le live import.
- [ ] **Yoann** : **DÉSACTIVER les 6 Shopify Flows** (Apps → Flow → chaque flow → "Désactiver le flux de travail") pour éviter retag/events parasites pendant l'import
- [ ] **Yoann** : Exporter le delta WC depuis le plugin "Advanced Order Export For WooCommerce" (filtre `created_after >= 2026-02-26`)
- [ ] **Claude** : Pré-remplir la colonne `Tags` du CSV Matrixify Customers selon mapping flows → tags (cf. section "Mapping flows → tags" ci-dessous)
- [ ] **Yoann** : Importer le delta dans Shopify via Matrixify (mode "draft" d'abord pour vérif)
- [ ] **Yoann** : Vérifier ligne par ligne sur 5-10 commandes test
- [ ] **Yoann** : Promouvoir l'import en "live"
- [ ] **Yoann** : **RÉACTIVER les 6 Shopify Flows**
- [ ] **Claude** : Audit count par tag avant/après — confirmer que `dossier-valide` et `pro` matchent les attendus
- [ ] **Claude** : Préparer les sitemaps à soumettre dimanche

### J0 (Dim 10/05) — CUTOVER
- [ ] **05h00** Sauvegarde finale WP (export complet en CSV via Matrixify, au cas où rollback)
- [ ] **06h00** Mode maintenance sur WP (plugin "Coming Soon" ou .htaccess 503)
- [ ] **06h15** Réduire encore TTL DNS si pas fait (300s → 60s, pour propag rapide)
- [ ] **06h30** **DNS cutover** : changer A/CNAME de `mylab-shop.com` chez le PlanetHoster (panel N0C) vers Shopify
  - Voir détails dans `dns_cutover_steps.md` (ci-dessous)
- [ ] **07h00** Vérifier propagation : `dig mylab-shop.com` depuis 3 endroits différents
- [ ] **07h30** Smoke tests sur les 14 P1_HOT URLs (curl chaque, vérifier 200 ou 301 vers Shopify)
- [ ] **08h00** Vérifier SSL est actif (Shopify auto-renouvelle via Let's Encrypt — peut prendre 1h)
- [ ] **08h30** **Claude** : Soumettre les sitemaps à GSC + Bing
- [ ] **10h00** Test commande end-to-end (commander un produit, vérifier email confirmation arrive)
- [ ] **18h00** Surveillance fin de journée des erreurs 404 + emails non délivrés

### J+1 (Lun 11/05) — Monitoring
- [ ] **Claude** : Surveiller les 404s remontés par GSC (rapport "Couverture")
- [ ] **Claude** : Patcher les redirects manquants au fur et à mesure
- [ ] **Yoann** : Communiquer aux clients sur les paniers WP en cours (email "votre panier a été migré")
- [ ] **Claude + Yoann** : Bilan 24h post-launch

---

## 🏷️ Mapping Shopify Flows → tags clients (vérifié 2026-05-06)

État courant des flows actifs (Apps → Flow) :

| Flow | Trigger | Condition | Tags écrits |
|---|---|---|---|
| Tag dossier cosmétologique | Order paid | "Si achat dossier cosmétologique" (filtre Liquid sur line items) | **`dossier-valide`, `pro`** |
| Tag abo forfait d'impression couleur | Subscription Created | `Lines product id == gid://shopify/Product/10898488426830` (handle `forfait-dimpression`) | `abo-impression-couleur` |
| Tag abo forfait d'impression noire | Subscription Created | `Lines product id == gid://shopify/Product/10898488492366` (handle `forfait-dimpression-standard`) | `abo-impression-noire` |
| suppression Tag abo forfait d'impression couleur annulé | Subscription Cancelled | (même produit couleur) | retire `abo-impression-couleur` |
| suppression Tag abo forfait d'impression noire annulé | Subscription Cancelled | (même produit noire) | retire `abo-impression-noire` |
| Récupérer le paiement abandonné | Customer abandons checkout | — | (pas de tag — email présumé) |

### Distribution actuelle des tags (952 clients Shopify, snapshot 2026-05-06)

- `customer` : 543 (default)
- `pro` : 348 (manuel B2B + co-ajouté avec dossier-valide)
- `dossier-valide` : 75 (⊂ pro)
- `administrator`, `Login with Shop`, `Shop`, `shop_manager` : bruit technique (≤ 8 chacun)
- `abo-impression-noire` / `abo-impression-couleur` : **0 clients** côté Shopify aujourd'hui (les flows n'ont jamais matché — abos pas encore migrés sur Appstle)

### Règles de tagging à appliquer dans le CSV Matrixify Customers (samedi)

Le tagging se fait via un **CSV séparé** dédié uniquement aux abos (post-import principal). Voir `matrixify_customers_tags_abo.csv` (23 clients).

⚠️ Avant import : **désactiver les 6 flows** pour éviter retag/events parasites sur les Order paid importées. Réactiver après vérif.

#### Fichier `matrixify_customers_tags_abo.csv` (généré 2026-05-06)

- **Format** : 3 colonnes `Email, Tags, Tags Command`
- **Mode** : `Tags Command = MERGE` → les tags `dossier-valide`, `pro`, `customer` existants sont préservés ; on ajoute juste `abo-impression-noire` ou `abo-impression-couleur`
- **Source** : 2 exports plugin "Advanced Order Export For WooCommerce" filtrés sur les produits "Forfait d'impression standard" (product_id WP 300181) et "Forfait d'impression couleur"
- **Filtres appliqués** :
  - Statut WP "réel" uniquement : `completed`, `delivered`, `shipped`, `partial-shipped`, `processing` (pas les `ywraq-pending`/`ywraq-new` = devis non payés, pas les `cancelled`/`failed`)
  - Filtre temporel "abo annuel" : achat ≤ 365 jours (cutoff 2025-05-06). Aucun client n'est tombé sous ce filtre au 2026-05-06 (le plus ancien = 274j).
  - Exclusion manuelle : `fev.vieiraa@gmail.com` (statut `on-hold` depuis 274j, virement bancaire jamais reçu)
- **Détail** : 8 clients `+abo-impression-noire`, 15 clients `+abo-impression-couleur`, aucun cumul

#### Mode d'emploi import

1. **Après** l'import principal Matrixify (orders+customers WC delta), vérifier que les 2 nouveaux clients existent bien sur Shopify :
   - `jade.pratberthomier@gmail.com` (forfait noire)
   - `mariam.aboudou.bikele@gmail.com` (forfait couleur)
   Si absent : refaire l'import principal ou créer manuellement avant de continuer.
2. Dans Shopify Admin → Apps → Matrixify → **Import** → Upload `matrixify_customers_tags_abo.csv`
3. Sélectionner le format Customers / vérifier la preview (23 lignes détectées avec colonne Tags Command = MERGE)
4. Lancer l'import (mode "Live", pas dry-run)
5. Vérifier le rapport : 23/23 lignes traitées, 0 error
6. Audit final : query GraphQL `customers(query:"tag:abo-impression-noire")` → doit renvoyer 8 clients ; même pour `couleur` → 15 clients

### Pipeline import principal Orders+Customers (samedi)

**Outil source WP** : WebToffee Pro (Import Export Suite for WooCommerce). Pas de companion Matrixify côté WP.

**Pipeline samedi matin** :

```
WP (WebToffee Pro export CSV)  →  transform_wc_to_matrixify.py  →  CSV Matrixify  →  Upload Shopify
```

**Étapes côté Yoann** :

1. WP Admin → WebToffee → Export → **WooCommerce Orders** → format CSV → **TOUTES colonnes par défaut** (ne pas désélectionner) → date filter optionnel (le script Python re-filtre `>= 2026-02-26`). Sauvegarder dans `Téléchargements`.
2. WP Admin → WebToffee → Export → **WooCommerce Users** → format CSV → toutes colonnes par défaut. Sauvegarder dans `Téléchargements`.
3. Lancer le runner one-click `samedi_run.ps1` (clic-droit → Exécuter avec PowerShell, ou via terminal) :
   ```powershell
   powershell -ExecutionPolicy Bypass -File "d:\be-yours-mylab\docs\migration\samedi_run.ps1"
   ```
   Le script trouve auto les 2 CSV les plus récents dans Downloads, crée un dossier daté `runs/<timestamp>/`, lance le transform, copie le CSV abo, et ouvre Explorer sur le résultat.

   Alternative manuelle si besoin :
   ```
   python d:/be-yours-mylab/docs/migration/transform_wc_to_matrixify.py \
     --orders "C:/Users/startec/Downloads/order_export_*.csv" \
     --users  "C:/Users/startec/Downloads/user_export_*.csv" \
     --out    "d:/be-yours-mylab/docs/migration/runs/manual/" \
     --shopify-existing-orders "#3356,#3357"
   ```
4. Vérifier `run_samedi/transform_log.txt` (compteurs imported / skipped / unmapped statuses)
5. Shopify Admin → Apps → Matrixify → Import → upload `matrixify_customers.csv` → **Dry Run** → 0 erreur attendue → puis Import live
6. Idem pour `matrixify_orders.csv` (Customers d'abord, Orders après — pour que les line items orders matchent un customer)
7. Upload `matrixify_customers_tags_abo.csv` (= les 23 abos) en dernier

**Script comportement** :
- Filtre `order_date >= 2026-02-26` (cutoff)
- Skip statuts : `ywraq-pending`, `ywraq-new`, `trash`
- Skip Names déjà présents sur Shopify (paramètre `--shopify-existing-orders`)
- Mapping statuts WC → Shopify Financial/Fulfillment :
  - `completed`/`shipped`/`delivered` → `paid` + `fulfilled`
  - `partial-shipped` → `paid` + `partial`
  - `processing`/`en-cours-de-prepa` → `paid` + `unfulfilled`
  - `on-hold`/`pending` → `pending` + `unfulfilled`
  - `cancelled`/`failed` → `voided`
  - `refunded` → `refunded`
- Tag `imported-from-wc` ajouté à chaque commande pour traçabilité (mode MERGE)
- Transactions générées en sub-row (`Line: Type = Transaction`) avec gateway + transaction_id WC

**Validation dry-run 2026-05-06** : sur sample 170 orders, 112 importés (46 hors fenêtre, 12 ywraq/trash, 0 collision).

### Mécanisme d'expiration annuelle (BACKLOG post-cutover)

Les flows actuels gèrent uniquement `Subscription Created/Cancelled` (events Appstle). Il n'existe **aucun mécanisme natif d'expiration temporelle**. À prévoir post-cutover :
- Soit un cron quotidien qui untag les clients dont l'achat forfait remonte à >365j
- Soit un Shopify Flow `Schedule trigger` (daily) avec condition sur metafield `last_forfait_purchase_at`
- Sans ça, les 23 tags taggés samedi resteront indéfiniment, même après expiration de l'abo annuel.

---

## 📋 Email DNS records à configurer chez le PlanetHoster (panel N0C)

Pour que les emails Shopify (commandes, factures, marketing) ne tombent pas en spam après cutover, ajouter ces records DNS :

### SPF (existant à modifier)
```
TYPE: TXT
HOST: @
VALUE: "v=spf1 include:_spf.google.com include:shops.shopify.com ~all"
```
⚠️ Si tu as déjà un SPF Google Workspace, **fusionner** avec `include:shops.shopify.com` — ne pas créer 2 records SPF.

### DKIM Shopify (récupérés 2026-05-06)

Deux CNAME à ajouter chez le PlanetHoster (panel N0C) :
```
TYPE: CNAME
HOST: dkim1._domainkey
VALUE: dkim1.b4e6d605f98c.p571.email.myshopify.com.
TTL: 3600

TYPE: CNAME
HOST: dkim2._domainkey
VALUE: dkim2.b4e6d605f98c.p571.email.myshopify.com.
TTL: 3600
```
⚠️ Le `.` final fait partie de la valeur (FQDN). Selon le PlanetHoster (panel N0C) (OVH notamment), il peut être omis ou auto-ajouté — vérifier après save que le record résout bien (`dig dkim1._domainkey.mylab-shop.com CNAME`).

### DMARC (recommandé)
```
TYPE: TXT
HOST: _dmarc
VALUE: "v=DMARC1; p=quarantine; rua=mailto:dmarc@mylab-shop.com; pct=100"
```
Démarre en `p=quarantine` pour 2 semaines, puis passer à `p=reject` une fois validé que tout fonctionne.

---

## 🌐 DNS cutover steps (Sam 9/05 soir → Dim 10/05 matin)

### Étape 1 — Vendredi soir : réduire TTL
Chez ton PlanetHoster (panel N0C), modifier le TTL des records `mylab-shop.com` :
```
A     @     [IP WP actuelle]    TTL: 300s (au lieu de 3600s)
CNAME www   mylab-shop.com.     TTL: 300s
```
Attendre 1h pour propagation.

### Étape 2 — Dimanche matin : swap
Changer les records vers Shopify :
```
A     @     23.227.38.65         TTL: 300s
CNAME www   shops.myshopify.com  TTL: 300s
```
(IP officielle Shopify : 23.227.38.65 — vérifier sur https://help.shopify.com/en/manual/online-store/domains)

### Étape 3 — Connecter le domaine côté Shopify
Admin → Settings → Domains → "Connect existing domain" → entrer `mylab-shop.com`
Shopify va vérifier les records et activer le SSL (Let's Encrypt) automatiquement.

### Étape 4 — Définir comme primary
Admin → Settings → Domains → mettre `mylab-shop.com` en **Primary** (au lieu de `mylab-shop-3.myshopify.com`).
Toutes les URLs canoniques utiliseront désormais le domaine principal.

### Étape 5 — Forcer HTTPS
Admin → Settings → Domains → "Force HTTPS" enabled.

### Rollback (si désastre)
Re-modifier les records DNS chez le PlanetHoster (panel N0C) pour repointer vers l'IP WP ancienne. Avec TTL 300s, tout sera remis en ordre en 5-10 min.

---

## 📤 Sitemaps à soumettre J0

### Google Search Console
1. Vérifier que la propriété `mylab-shop.com` est bien validée
2. Aller dans **Sitemaps** → soumettre :
   - `https://mylab-shop.com/sitemap.xml` (sitemap principal Shopify)
   - `https://mylab-shop.com/sitemap_products_1.xml` (auto-généré)
   - `https://mylab-shop.com/sitemap_pages_1.xml`
   - `https://mylab-shop.com/sitemap_collections_1.xml`

### Bing Webmaster Tools
1. Vérifier la propriété (méta-tag déjà déployée pour Google fonctionne pas pour Bing — refaire l'opération avec le code Bing)
2. Soumettre `https://mylab-shop.com/sitemap.xml`

### Indexnow (bonus)
Shopify supporte IndexNow nativement (envoie auto les nouvelles URLs à Bing/Yandex).
Vérifier dans Admin → Online Store → Preferences que c'est activé.

---

## 🚨 Checks post-cutover (Lun 11/05)

Tous les jours pendant 1 semaine :
1. **GSC → Couverture → Erreurs** : surveiller les 404 et 5xx
2. **GSC → Performances** : vérifier que les top URLs continuent à recevoir des clics
3. **Shopify Admin → Reports → Sales** : confirmer que les commandes arrivent
4. **Email deliverability** : envoyer un test depuis Shopify (commande test) et vérifier qu'il arrive dans Inbox + non spam (mail-tester.com)
5. **Console navigateur** : ouvrir 5 pages clés et vérifier qu'aucune erreur JS ne casse le rendu

---

## 📁 Fichiers générés pour cette migration

- `wp_inventory.csv` — 219 URLs WP crawlées du sitemap
- `shopify_inventory.json` — 130 produits + 21 collections + 39 pages + 124 redirects
- `wp_to_shopify_mapping.csv` — premier mapping brut (pre-fuzzy)
- `product_fuzzy_match.csv` — mapping fuzzy des 128 produits WP
- `category_match.csv` — mapping des 36 catégories
- `page_match.csv` — mapping des 30 pages
- `redirect_plan.csv` — **plan d'exécution final** (218 entrées, par priorité)
- `apply_redirects.py` — script idempotent (dry-run par défaut)
- `MIGRATION_RUNBOOK.md` — ce fichier
