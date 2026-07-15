# Scripts Odoo MyLab

Scripts Python XML-RPC pour customisations Odoo (déploiement de champs, actions, vues, reports).

## Prérequis
- Python 3.11+
- `pip install python-dotenv`
- `.env.local` (dans le repo mylab-configurateur) avec `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_API_KEY`

## Ordre d'exécution (first-time setup du BL cartons)

```bash
# 1. Créer le champ x_carton_capacity
python -m scripts.odoo.step01_create_carton_field

# 2. Initialiser les valeurs depuis les noms produits
#    ⚠️ PÉRIMÉ — exige --force, et le rejouer casserait le colisage actuel.
#    Ne fait plus partie du parcours normal. Voir la section "Colisage" ci-dessous.
python -m scripts.odoo.step02_init_carton_capacity

# 3. Déployer l'action serveur
python -m scripts.odoo.step03_create_server_action

# 4. Déployer le template PDF + action report
python -m scripts.odoo.step04_create_bl_report

# 5. Ajouter le bouton dans la vue picking
python -m scripts.odoo.step05_add_picking_button
```

Tous les scripts sont **idempotents** : relançables sans effet de bord.

## Colisage (x_carton_capacity)

**La capacité carton est une propriété du FLACON, pas de la gamme commerciale.** Deux produits
qui partagent le même contenant partagent le même carton — et donc la même famille dans
l'action « Répartir en cartons », quitte à se mélanger dans un carton de bord de famille.
C'est voulu.

Trois sources, par ordre de priorité :

| Source | Portée |
| ------ | ------ |
| `PARTNER_PRODUCT_CARTON` dans `server_action_code.py` | Colisage négocié pour **un client × un produit** (prioritaire) |
| `x_carton_capacity` sur `product.template` | Colisage par défaut, **tous clients** |
| — (0) | Produit non colisé → carton « Divers » |

Familles actuelles : 69 (verre ambré 50ml) · 63 (100ml) · 40 (crème/shampoing 200ml) ·
35 (coloristeur/gloss 200ml, flacon pompe) · 24 (masque 200/400ml) · 23 (500ml) · 12 (1L).
Les libellés vivent dans `FAMILY_LABELS` — **ajouter une capacité sans son libellé** produit
un carton « Carton 35u » au lieu d'un nom lisible.

```bash
# Rejouer le colisage flacons pompe 35 / verre ambré 69 (idempotent, --dry-run dispo)
python -m scripts.odoo.set_carton_capacity_flacons_pompes --dry-run

# Répartir en cartons sur un BL précis (rejouable, purge + reconstruit, ne valide rien)
# execute("ir.actions.server", "run", [[774]],
#         {"context": {"active_model": "stock.picking", "active_ids": [pid], "active_id": pid}})
```

⚠️ `step02_init_carton_capacity` déduit la capacité du **nom** du produit. Ce modèle est faux
(il ne voit pas le flacon) et le script est désormais bloqué derrière `--force`. Les gammes
marque blanche (silver care 54, hydratant/silver glow 80) et les 100ml n'ont aucune règle qui
les couvre : il les écraserait.

## Fichiers de code

- `_client.py` : helper XML-RPC partagé
- `server_action_code.py` : code Python de l'action "Répartir en cartons" (lu par step03_)
- `templates/bl_deliveryslip.xml` : source QWeb du BL (lu par step04_)

Pour modifier l'action ou le template, éditer le fichier source puis relancer le script de déploiement correspondant.

⚠️ **Le champ `code` de l'action serveur est éditable depuis l'UI Odoo et dérive.** Avant tout
redéploiement, rapatrier le LIVE et differ contre le repo, sinon on clobbere une édition UI
(c'est arrivé : l'override CENDREE et le tri par produit ont vécu 8 jours en LIVE seulement).

## Paiement en ligne devis (step20-step24)

Setup pour permettre aux clients de payer leur devis depuis le portail Odoo (lien email) — Stripe (CB) + virement bancaire, avec acompte conditionnel selon montant.

```bash
# 20. Diagnostic read-only de l'instance (already run, see output in chat)
python -m scripts.odoo.step20_probe_payment_setup
python -m scripts.odoo.step20b_probe_stripe_module
python -m scripts.odoo.step20c_probe_prepayment
python -m scripts.odoo.step20d_probe_providers_and_company

# 21. Installer le module payment_stripe (15-30s, irreversible-ish)
python -m scripts.odoo.step21_install_payment_stripe

# 22. Créer le provider Virement bancaire (state=disabled, à activer manuellement)
python -m scripts.odoo.step22_create_wire_transfer_provider

# 23. Règle automatisée acompte conditionnel
#     < 1000 € → prepayment_percent = 100%
#     ≥ 1000 € → prepayment_percent = 50%
python -m scripts.odoo.step23_acompte_threshold_rule

# 24. Test : crée 2 devis dummy (500€ + 2000€), vérifie, supprime
python -m scripts.odoo.step24_test_thresholds
```

**Étapes manuelles complémentaires** (UI Odoo, après step21+22) :
1. Coller les clés Stripe live (`pk_live_...` / `sk_live_...`) sur le provider Stripe → State = Enabled
2. Vérifier l'IBAN dans le pending_msg du provider Virement → State = Enabled
3. Settings → Sales : cocher *Online Payment* + *Online Signature*

## Note origine export Suisse sur facture (step40)

Ajoute automatiquement sur les factures dont **l'adresse de livraison est en Suisse**
(`o.partner_shipping_id.country_id.code == 'CH'`) une note douanière : numéro EORI,
déclaration d'origine préférentielle CE, mention « PRODUITS CERTIFIÉS SANS COV » et
signature Joseph DURAND, avec « Fait à Cavaillon, le `<date du jour d'édition>` ».

```bash
# Sonde l'arch du template facture standard (read-only) pour vérifier l'anchor xpath
python -m scripts.odoo.probe_invoice_report_arch

# Déploie la vue QWeb héritée (idempotent, upsert par key)
python -m scripts.odoo.step40_create_invoice_ch_note

# Vérifie le rendu : force une livraison CH en transaction + rollback (aucune modif DB)
python -m scripts.odoo.verify_invoice_ch_note_render
```

- Source QWeb : `templates/invoice_ch_origin_note.xml` (vue héritée de `account.report_invoice_document`,
  injectée via xpath après le bloc `name="comment"`).
- Date dynamique via `context_timestamp(datetime.datetime.now())` → figée par le cache PDF
  des factures *posted* à la 1ère génération (comportement voulu pour un document douanier).

## PDP / Facturation électronique 2026 — mise à jour Odoo + rollback

**Contexte** : la réforme impose la *réception* de factures électroniques au **1er sept. 2026**
et l'*émission* au **1er sept. 2027** (MY.LAB = PME). Odoo est **Plateforme Agréée (PA)** et
fournit un module gratuit "French e-invoicing" (recherche "PDP"), compatible Community 18.
Mais l'image du VPS (`18.0-20260324`) est **antérieure** à la sortie du module (juin 2026) :
il faut donc d'abord bumper l'image `odoo:18.0`, puis installer le module + KYC/KYB.

Egress vers `iap.odoo.com` vérifié OK (prérequis PA pour une instance self-hosted).

### Procédure (fenêtre calme, aucun import n8n Shopify→Odoo en cours)

```bash
# 1. Backup intégral (sûr, lecture seule sur la prod) → /root/odoo-backups/<ts>/
python -m scripts.odoo.pdp_step01_backup

# 2. Voir le plan sans rien toucher
python -m scripts.odoo.pdp_step02_update

# 3. Exécuter le bump + -u all (downtime ~2-5 min)
python -m scripts.odoo.pdp_step02_update --apply
```

Puis dans l'UI Odoo : Apps → *Update Apps List* → installer "French e-invoicing" (PDP) →
Comptabilité → Config → Paramètres → *Facturation électronique française* → procédure KYC/KYB.

### Rollback si un rapport custom casse ou la migration plante

Les artefacts sont dans `/root/odoo-backups/<timestamp>/` (DB dump, filestore, compose,
config, addons, `IMAGE_DIGEST.txt`).

**Rollback image seule** (la DB n'a pas encore été migrée par `-u all`) :
```bash
# Pin le compose sur le digest d'avant (1re ligne de IMAGE_DIGEST.txt)
#   image: odoo@sha256:<digest>
cd /root/odoo && nano docker-compose.yml   # remplacer "image: odoo:18.0"
docker compose up -d web
```

**Rollback complet** (la DB a été migrée et est cassée) :
```bash
cd /root/odoo
docker compose stop web
# restaurer la base dans une copie neuve puis basculer, OU droper/recréer OdooYJ :
docker exec -i odoo-db-1 dropdb -U odoo OdooYJ
docker exec -i odoo-db-1 createdb -U odoo OdooYJ
docker cp /root/odoo-backups/<ts>/OdooYJ.dump odoo-db-1:/tmp/OdooYJ.dump
docker exec odoo-db-1 pg_restore -U odoo -d OdooYJ --no-owner /tmp/OdooYJ.dump
# restaurer le filestore
docker cp /root/odoo-backups/<ts>/filestore.tgz odoo:/tmp/filestore.tgz
docker exec odoo bash -c 'cd /var/lib/odoo/.local/share/Odoo && tar xzf /tmp/filestore.tgz'
# re-pin l'image au digest d'avant (voir rollback image seule), puis :
docker compose up -d web
```

Idempotence : `pdp_step01_backup` crée un dossier horodaté à chaque run (n'écrase rien).
`pdp_step02_update` sans `--apply` est un dry-run pur.
