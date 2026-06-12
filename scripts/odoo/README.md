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
python -m scripts.odoo.step02_init_carton_capacity
# → ouvrir scripts/odoo/init_carton_capacity.csv pour vérif manuelle
# → corriger exceptions dans l'UI Odoo

# 3. Déployer l'action serveur
python -m scripts.odoo.step03_create_server_action

# 4. Déployer le template PDF + action report
python -m scripts.odoo.step04_create_bl_report

# 5. Ajouter le bouton dans la vue picking
python -m scripts.odoo.step05_add_picking_button
```

Tous les scripts sont **idempotents** : relançables sans effet de bord.

## Fichiers de code

- `_client.py` : helper XML-RPC partagé
- `server_action_code.py` : code Python de l'action "Répartir en cartons" (lu par step03_)
- `templates/bl_deliveryslip.xml` : source QWeb du BL (lu par step04_)

Pour modifier l'action ou le template, éditer le fichier source puis relancer le script de déploiement correspondant.

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
