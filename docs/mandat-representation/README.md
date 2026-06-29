# Envoi automatique du mandat de représentation

Envoi du **mandat de Personne Responsable (Règlement CE 1223/2009)** aux clients ayant **payé** le service « Création du dossier cosmétologique » (`product.product` Odoo id=2313).

> **État : 🟢 automatisé et LIVE depuis le 2026-06-29.** Un cron tourne sur le VPS toutes les 15 min. L'envoi manuel (CLI) reste disponible pour les renvois et cas particuliers.

## Architecture

```
┌──────────────────────────────┐        ┌────────────────────────────┐
│ VPS — cron */15 (flock)       │        │ CLI manuel (renvoi /        │
│ auto_send_mandats.py  (poll)  │        │ cas particulier)            │
│  chemin AUTO (LIVE)           │        │ send_mandat_representation   │
└───────────────┬──────────────┘        └──────────────┬─────────────┘
                │ factures éligibles                    │
                │ (posted + paid + produit 2313 +       │
                │  invoice_date >= cutoff +             │
                │  x_mandat_sent_at vide)               │
                └───────────────┬──────────────────────┘
                                ▼
                 send_mandat_representation.process_invoice()
                                │  Docs/Drive API (service account)
                                ▼
                 ┌────────────────────────────────┐
                 │  Google Drive                  │
                 │  - Template Doc (id 1eCm…)     │ → copie + placeholders → PDF
                 │  - Dossier "Mandats envoyés"   │
                 └───────────────┬────────────────┘
                                 ▼
                 ┌────────────────────────────────┐
                 │  Odoo (account.move)           │
                 │  - PDF en pièce jointe          │
                 │  - mail.mail → client           │
                 │  - log chatter                  │
                 │  - x_mandat_sent_at tamponné    │
                 └───────────────┬────────────────┘
                                 ▼
                      Ping Telegram (bot Hermes)
```

## Les deux chemins d'envoi

Les deux appellent la même fonction `process_invoice()` ; elles partagent donc le même tampon d'idempotence.

| | AUTO (LIVE) | MANUEL |
|---|---|---|
| Script | `auto_send_mandats.py` (poll) | `send_mandat_representation.py` (CLI) |
| Déclenchement | cron VPS `*/15` | lancé à la main par Yoann/Claude |
| Sélection | factures éligibles (voir ci-dessous) | `--invoice FAC/2026/00XXX` |
| Usage | nominal, sur paiement | renvoi, cas particulier, backlog |

**Manuel :**
```bash
python -m scripts.odoo.send_mandat_representation --invoice FAC/2026/00XXX [--force] [--to test@exemple.fr] [--dry-run]
```
- `--force` : bypass la vérification `payment_state=paid`
- `--to` : redirige le mail vers une autre adresse (test)
- `--dry-run` : affiche les placeholders + destinataire sans rien envoyer

## Pipeline (`process_invoice`)

1. Lit la facture + le partner depuis Odoo, **vérifie la présence du produit 2313**.
2. Construit les placeholders depuis les données partner.
3. Garde-fous : email présent ? `payment_state == paid` (sauf `--force`) ?
4. **Copie le template Google Doc** → remplace les placeholders → nomme par **n° de facture**.
5. **Exporte en PDF**.
6. **Attache le PDF** à la facture Odoo (`ir.attachment`).
7. **Envoie l'email** via `mail.mail` — corps HTML codé en dur dans `build_email_body()` (⚠️ **pas** un `mail.template` Odoo).
8. **Log chatter** sur la facture.
9. **Tamponne `x_mandat_sent_at`** (idempotence).

## Idempotence & garde anti-rafale

- **Idempotence** : champ custom `account.move.x_mandat_sent_at` (Datetime), créé une fois via `setup_mandat_field.py`. Tamponné **uniquement à l'envoi réussi** (auto **et** manuel). Vide = pas encore envoyé → jamais de double envoi.
- **Cutoff** : `MANDAT_AUTO_SINCE` (défaut `2026-06-29`). L'auto n'envoie que les factures dont `invoice_date >= cutoff` → les factures pré-existantes sont **exclues de l'auto** (traitées à la main). Pour étendre l'auto à du plus ancien : baisser cette date.

## Nommage des fichiers

`Mandat Personne Responsable - {Raison sociale} - {FAC-2026-NNNNN}` (le `/` du n° de facture devient `-`). Le PDF suit la même règle. Le **n° de facture sert de clé unique** → deux mandats ne peuvent plus porter le même nom (même client / même jour / deux factures).

## Le template Google Doc

- Doc id `1eCmScLGtG1XS9B2v90srZRVoY--55iVDr35WwJ6oIYo`, nommé `MANDAT_Personne_Responsable_VEGETAL_ORIGIN`.
- ⚠️ **Le corps est copié verbatim** par client ; seuls les placeholders `[...]` sont remplacés. **Aucun texte non-placeholder « brouillon » ne doit rester dans le corps** (un ancien marqueur « — MODÈLE — » fuyait dans les mandats clients ; retiré le 2026-06-29).
- Le contenu juridique s'édite **directement dans le Google Doc**, pas dans le code.

### Mapping des placeholders

Champs **pré-remplis** depuis Odoo :

| Placeholder dans le Doc | Source Odoo |
|---|---|
| `[Raison sociale du Client]` | `res.partner.commercial_company_name` (fallback `name`) |
| `[ville]` (RCS) | `res.partner.city` |
| `[SIREN]` | extrait du `res.partner.vat` (9 derniers chiffres) |
| `[le cas échéant]` (TVA intracom) | `res.partner.vat` |
| `[adresse complète]` | `street, zip city, country` |
| Date « 29 mai 2026 » → date du jour | `date.today()` formatée FR |

Champs **laissés en blanc** (le client remplit / signe) :
- `[Forme juridique]`, `[montant]` (capital), `[Civilité, Nom, Prénom]`, `[fonction]`
- `[Nom de marque]`, `[Nom du représentant]`, `[Fonction]` (bloc signature)
- Ville de signature (« Fait à ___ »)
- Annexe 1 (liste des Produits)

## Setup initial (déjà fait — référence)

### 1. Service account Google Cloud
- Projet GCP : `api-relais-colis-dpd`
- Compte de service : `mandat-representation-sender@api-relais-colis-dpd.iam.gserviceaccount.com`
- Clé JSON téléchargée (Keys → ADD KEY → JSON). ⚠️ Le SA ne voit **que ce qui lui est partagé**.

### 2. APIs Google activées
- **Google Docs API** + **Google Drive API** sur le même projet.

### 3. Partages Drive
- Dossier **« Mandats envoyés »** partagé avec le SA en **Éditeur** (le script y dépose les copies).
- Template Doc partagé avec le SA (**Lecteur** suffit, le script le copie).

### 4. Credentials locaux (`.env.local`)
```
GOOGLE_SA_JSON=<chemin du JSON service account>
MANDAT_TEMPLATE_DOC_ID=1eCmScLGtG1XS9B2v90srZRVoY--55iVDr35WwJ6oIYo
MANDAT_SENT_FOLDER_ID=<id du dossier "Mandats envoyés">
```

## Déploiement VPS (cron auto)

Idempotent, via paramiko/SFTP :
```bash
python -m scripts.odoo.vps_deploy_mandat_automation
```
Crée `/root/mandat-automation/` : scripts + venv (`google-api-python-client`, `google-auth`, `python-dotenv`) + `.env` (Odoo + Google + Telegram) + `secrets/google-sa-mandat.json` (chmod 600) + `run.sh` + cron `*/15` avec `flock` + `logs/mandat.log`. Le token Telegram est **lu côté serveur** dans `/root/.hermes/.env` (jamais loggé). Notifications via le **bot Hermes** (chat_id `7760145552`).

> ⚠️ Tout changement de `send_mandat_representation.py` ou `auto_send_mandats.py` nécessite de **relancer ce déploiement** pour que le worker auto en bénéficie.

## Legacy (superseded)

L'ancienne approche — bouton serveur Odoo « Envoyer mandat » + `mail.activity.type` id=8 + worker local `process_mandat_queue.py` — ne faisait que **mettre en file** (aucun cron ne lançait le worker). **Abandonnée** au profit du poll cron VPS ci-dessus ; laissée en place mais plus branchée.
