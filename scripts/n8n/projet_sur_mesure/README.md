# Workflow n8n — Projet sur-mesure (mise en relation labos)

Reçoit les soumissions du formulaire `/pages/projet-sur-mesure` (section `ml-partner-request.liquid`), crée le lead dans Airtable, notifie Yoann et envoie l'accusé de réception client.

## Références

| Élément | Valeur |
|---|---|
| Workflow n8n | `MY.LAB — Projet sur-mesure (mise en relation)` — id `c2jg5izEjB9o7fNq` |
| Webhook prod | `https://n8n.startec-paris.com/webhook/projet-sur-mesure` (POST JSON) |
| Base Airtable | « Espace de travail mylab » `appdWBkaxdGnJAqxU` |
| Table | « Leads sur-mesure » `tbl3G5YkoG9g1Hw3l` |
| Credentials réutilisées | `gmailOAuth2` « Gmail account », `airtableTokenApi` « Catalogue Shopify x Mylab YO » (lues dynamiquement sur le wf catalogue `r9EqKKnyQepCx8t3`) |

## Chaîne

Webhook → Répondre 200 → Créer lead Airtable (statut « Nouveau ») → Notif Yoann (`yoann@mylab-shop.com` + `contact@homecosmetiques.com` — Cindy Granier) → AR client (48 h ouvrées).

La transmission aux labos partenaires est **manuelle** (Yoann qualifie puis transmet) — le workflow ne contacte aucun tiers.

## Payload attendu

```json
{"prenom": "", "nom": "", "email": "", "telephone": "", "marque": "",
 "type_projet": "", "categorie": "", "quantites": "", "echeance": "",
 "description": "", "consent": "oui", "source": "", "page_url": ""}
```

Les valeurs de `type_projet`, `categorie`, `quantites`, `echeance` doivent matcher EXACTEMENT les options des selects Airtable (sinon erreur « Insufficient permissions to create new select option ») — elles sont définies à l'identique dans le formulaire Liquid.

## Déployer / re-déployer

```bash
python scripts/n8n/projet_sur_mesure/create_workflow.py   # idempotent (upsert par nom + activate)
```

## Tester

⚠️ Depuis Windows, ne PAS tester avec `curl -d` (payload CP1252 → mojibake → erreur select Airtable). Utiliser Python `requests` (UTF-8) :

```bash
python - <<'EOF'
import requests
payload = {"prenom": "Test", "nom": "Canari", "email": "yoann@mylab-shop.com",
  "telephone": "0600000000", "marque": "TEST-DELETE-ME",
  "type_projet": "Création de formule sur-mesure", "categorie": "Capillaire",
  "quantites": "500 – 1 000 u", "echeance": "3 – 6 mois",
  "description": "Test technique — à supprimer", "consent": "oui",
  "source": "test", "page_url": "https://test"}
print(requests.post('https://n8n.startec-paris.com/webhook/projet-sur-mesure', json=payload, timeout=30).text)
EOF
```

Puis vérifier l'exécution (`GET /api/v1/executions?workflowId=c2jg5izEjB9o7fNq`), la ligne Airtable, les 2 mails — et **supprimer la ligne de test**.
