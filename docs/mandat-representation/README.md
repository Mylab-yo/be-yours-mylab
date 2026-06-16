# Envoi automatisé du mandat de représentation

Automatisation de l'envoi du **mandat de Personne Responsable (Règlement CE 1223/2009)** aux clients ayant acheté le service "Création du dossier cosmétologique" (product.product Odoo id=2313).

## Architecture

```
                                          ┌────────────────────────────────┐
                                          │  Google Drive                  │
                                          │  - Template Doc (modèle)       │
                                          │  - Dossier "Mandats envoyés"   │
                                          └─────────────┬──────────────────┘
                                                        │ Docs/Drive API
                                                        │ (service account)
                                                        ▼
  ┌──────────────────┐    bouton manuel   ┌────────────────────────────┐
  │ Odoo (facture)   │ ─────────────────► │ scripts/odoo/              │
  │ "Envoyer mandat" │                    │ send_mandat_representation │
  └──────────────────┘                    └──────────────┬─────────────┘
         ▲                                               │
         │  pj PDF + log chatter                         │
         └───────────────────────────────────────────────┤
                                                         ▼
                                          ┌────────────────────────────────┐
                                          │  Email envoyé au client        │
                                          │  via mail.template Odoo        │
                                          │  (apparait dans le chatter)    │
                                          └────────────────────────────────┘
```

## Mapping des placeholders

Champs **pré-remplis** depuis Odoo :

| Placeholder dans le Doc | Source Odoo |
|---|---|
| `[Raison sociale du Client]` | `res.partner.commercial_company_name` (fallback `name`) |
| `[ville]` (RCS) | `res.partner.city` |
| `[SIREN]` | extrait du `res.partner.vat` (FR + 11 chiffres → 9 derniers) |
| `[le cas échéant]` (TVA intracom) | `res.partner.vat` |
| `[adresse complète]` | `street, zip city, country` |
| Date "29 mai 2026" → date du jour | `datetime.today()` formatée FR |

Champs **laissés en blanc** (client remplit/signe) :
- `[Forme juridique]`, `[montant]` (capital), `[Civilité, Nom, Prénom]`, `[fonction]`
- `[Nom de marque]`, `[Nom du représentant]`, `[Fonction]` (bloc signature)
- Ville de signature ("Fait à ___")
- Annexe 1 (liste des Produits)

## Setup initial (à faire UNE FOIS par Yoann)

### 1. Créer un service account Google Cloud

1. Aller sur https://console.cloud.google.com/iam-admin/serviceaccounts
2. Choisir un projet (ou en créer un, ex : `mylab-mandat-automation`)
3. **CREATE SERVICE ACCOUNT** :
   - Name : `mandat-representation-sender`
   - Description : "Service account pour générer + envoyer les mandats de représentation aux clients dossier cosméto"
4. Donner le rôle **Editor** (ou plus restrictif si tu veux : juste les rôles Drive/Docs)
5. **Keys → ADD KEY → Create new key → JSON** : télécharge un fichier `mandat-representation-XXXX.json`
6. **Garder l'email du service account** (du genre `mandat-representation-sender@<project>.iam.gserviceaccount.com`) — affiché dans la liste des SA

### 2. Activer les APIs Google nécessaires

Dans le même projet Cloud, activer :
- **Google Docs API** : https://console.cloud.google.com/apis/library/docs.googleapis.com
- **Google Drive API** : https://console.cloud.google.com/apis/library/drive.googleapis.com

### 3. Partager le template + créer le dossier "Mandats envoyés"

1. Sur Google Drive, créer un dossier **"Mandats envoyés"** (ou choisir un dossier existant)
2. Partager ce dossier avec l'email du service account → permission **Éditeur**
3. Partager le template Doc (`1eCmScLGtG1XS9B2v90srZRVoY--55iVDr35WwJ6oIYo`) avec le service account → permission **Lecteur** suffit
4. Noter l'**ID du dossier "Mandats envoyés"** (visible dans l'URL : `drive.google.com/drive/folders/<ID>`)

### 4. Stocker les credentials

Placer le JSON téléchargé dans :
```
d:\Configurateur Designs MyLab\mylab-configurateur\.env.local\..\secrets\google-service-account-mandat.json
```

Et ajouter dans `.env.local` :
```
GOOGLE_SA_JSON=d:\Configurateur Designs MyLab\mylab-configurateur\secrets\google-service-account-mandat.json
MANDAT_TEMPLATE_DOC_ID=1eCmScLGtG1XS9B2v90srZRVoY--55iVDr35WwJ6oIYo
MANDAT_SENT_FOLDER_ID=<id du dossier Mandats envoyés>
```

### 5. Tester le script

```bash
python -m scripts.odoo.send_mandat_representation --invoice INV/2026/XXXX --dry-run
```

Le `--dry-run` affiche ce qui serait fait (placeholders fusionnés, destinataires) sans rien envoyer.

Puis sans `--dry-run` pour envoyer pour de vrai.

## Phase 2 : action serveur Odoo

Une fois le script validé sur 2-3 factures réelles, on crée :
1. Un `ir.actions.server` Python qui appelle le script via subprocess ou logique inline
2. Visible comme bouton "Envoyer mandat de représentation" sur la fiche facture
3. Filtré pour n'apparaître que sur les factures contenant le produit 2313

## Phase 3 (futur) : automation sur paiement

Un `base.automation` sur `account.move` :
- Trigger : `payment_state` change to `paid`
- Filtre : au moins une ligne avec `product_id == 2313`
- Filtre : pas encore envoyé (champ custom `x_mandat_sent_at` à créer)
- Action : appelle l'action serveur de l'étape 2
