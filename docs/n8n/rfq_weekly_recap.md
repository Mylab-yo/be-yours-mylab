# Workflow n8n — RFQ Récap Lundi

## Informations générales

| Champ | Valeur |
|-------|--------|
| **Workflow ID** | `R1VW6r00aJ4jTW2I` |
| **Nom** | MY.LAB — RFQ Récap Lundi |
| **Créé le** | 2026-05-20 |
| **Statut** | Inactif (à activer manuellement) |
| **Fuseau horaire** | Europe/Paris |
| **Dossier cible** | Yo (placement manuel requis — voir ci-dessous) |

## Déclencheur

- **Type** : Schedule Trigger (cron)
- **Expression** : `0 8 * * 1`
- **Signification** : Chaque **lundi à 8h00** (Europe/Paris)

## Structure des nœuds

```
[1] Chaque Lundi 8h00  (scheduleTrigger)
          ↓
[2] Odoo — Fetch RFQs Draft  (code / XML-RPC)
          ↓
[3] Format — Compose Email HTML  (code)
          ↓
[4] Gmail — Send RFQ Recap  (gmail)
```

### Nœud 2 — Odoo Fetch RFQs

- Interroge `purchase.order` via XML-RPC (`execute_kw → search_read`)
- Filtre : `state = 'draft'` ET `date_order >= NOW - 7 jours`
- Champs récupérés : `id`, `name`, `partner_id`, `date_order`, `amount_total`
- Retourne `{ rfq_list: [...], fetched_at, since }`

### Nœud 3 — Format Email

- Si `rfq_list.length === 0` : sujet = `[MyLab] Pas de réappro à faire cette semaine`
- Sinon : sujet = `[MyLab] N RFQ à valider — récap lundi`
- Corps HTML : liste des RFQs groupées par fournisseur, liens cliquables vers Odoo
- Signature MY.LAB (depuis `docs/signature-email.html`) toujours appendée

### Nœud 4 — Gmail Send

- Destinataire : `yoann@mylab-shop.com`
- Credential : `Gmail account YO` (id `Z9P00eLPPJyWM08T`)
- Expéditeur affiché : `MY.LAB`
- Reply-To : `yoann@mylab-shop.com`

## Activer le workflow

### Via l'UI n8n

1. Ouvrir [n8n.startec-paris.com](https://n8n.startec-paris.com)
2. Rechercher "RFQ Récap Lundi"
3. Cliquer le toggle "Active" en haut à droite

### Via l'API

```bash
curl -X POST \
  https://n8n.startec-paris.com/api/v1/workflows/R1VW6r00aJ4jTW2I/activate \
  -H "X-N8N-API-KEY: <JWT_TOKEN>"
```

## Déplacer dans le dossier Yo

L'API v1 de n8n ne supporte pas le déplacement de workflows entre dossiers (aucun endpoint `/move` ou `/transfer` fonctionnel pour les folders). Procéder via l'UI :

1. Ouvrir n8n → liste des workflows
2. Clic droit sur "MY.LAB — RFQ Récap Lundi"
3. Sélectionner "Move to folder" → choisir **Yo**

## Dry-run Odoo (test du 2026-05-20)

- Requête : RFQs en draft depuis 7 jours
- Résultat : **0 RFQs** (aucune commande fournisseur en draft cette semaine — normal)
- Connexion Odoo XML-RPC : OK

## Notes

- Le workflow est **inactif par défaut** — à activer après review de Yoann
- Si le nœud Gmail montre "credential missing" à l'ouverture, c'est cosmétique : le credential `Gmail account YO` est correctement référencé par son ID `Z9P00eLPPJyWM08T`
- La date de référence "7 jours" est recalculée à chaque exécution (pas de stateful memory)
