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
