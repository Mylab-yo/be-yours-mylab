# -*- coding: utf-8 -*-
"""Crée + active le workflow n8n 'MY.LAB — Projet sur-mesure (mise en relation)'.
Réutilise les credentials du workflow catalogue r9EqKKnyQepCx8t3. Idempotent."""
import re, sys, json, requests

sys.stdout.reconfigure(encoding='utf-8')
TABLE_ID = 'tbl3G5YkoG9g1Hw3l'  # Leads sur-mesure (base appdWBkaxdGnJAqxU)
WF_NAME = 'MY.LAB — Projet sur-mesure (mise en relation)'
BASE = 'https://n8n.startec-paris.com/api/v1'

key = None
with open(r'd:\Configurateur Designs MyLab\mylab-configurateur\.env.local', encoding='utf-8') as f:
    for line in f:
        if re.match(r'^eyJ[A-Za-z0-9._-]+$', line.strip()):
            key = line.strip(); break
assert key, 'JWT n8n introuvable (.env.local ligne ~39)'
H = {'X-N8N-API-KEY': key, 'Content-Type': 'application/json'}

# Credentials depuis le wf catalogue (jamais en dur)
cat = requests.get(f'{BASE}/workflows/r9EqKKnyQepCx8t3', headers=H, timeout=20).json()
creds = {}
for n in cat['nodes']:
    for ctype, c in (n.get('credentials') or {}).items():
        creds[ctype] = c
assert 'gmailOAuth2' in creds and 'airtableTokenApi' in creds, f'credentials manquantes: {list(creds)}'

W = "={{ $('Webhook').item.json.body."  # helper préfixe expression
nodes = [
  {"name": "Webhook", "type": "n8n-nodes-base.webhook", "typeVersion": 2,
   "position": [0, 0],
   "parameters": {"httpMethod": "POST", "path": "projet-sur-mesure",
                  "responseMode": "responseNode", "options": {}}},
  {"name": "Répondre 200", "type": "n8n-nodes-base.respondToWebhook", "typeVersion": 1.1,
   "position": [220, 0],
   "parameters": {"respondWith": "json", "responseBody": "{\"ok\": true}", "options": {}}},
  {"name": "Créer lead Airtable", "type": "n8n-nodes-base.airtable", "typeVersion": 2.1,
   "position": [440, 0], "credentials": {"airtableTokenApi": creds['airtableTokenApi']},
   "parameters": {
     "base": {"__rl": True, "value": "appdWBkaxdGnJAqxU", "mode": "id"},
     "table": {"__rl": True, "value": TABLE_ID, "mode": "id"},
     "operation": "create",
     "columns": {"mappingMode": "defineBelow", "value": {
        "Prénom": W + "prenom }}", "Nom": W + "nom }}",
        "Email": W + "email }}", "Téléphone": W + "telephone }}",
        "Marque / société": W + "marque }}",
        "Type de projet": W + "type_projet }}",
        "Catégorie produit": W + "categorie }}",
        "Quantités envisagées": W + "quantites }}",
        "Échéance": W + "echeance }}",
        "Description": W + "description }}",
        "Date de soumission": "={{ $now.toISO() }}",
        "Source": W + "source }}",
        "Statut": "Nouveau"},
      "matchingColumns": [], "schema": []},
     "options": {}}},
  {"name": "Notif Yoann", "type": "n8n-nodes-base.gmail", "typeVersion": 2.1,
   "position": [660, 0], "credentials": {"gmailOAuth2": creds['gmailOAuth2']},
   "parameters": {
     "sendTo": "yoann@mylab-shop.com, contact@homecosmetiques.com",
     "subject": "=🧪 Nouveau projet sur-mesure — {{ $('Webhook').item.json.body.marque || $('Webhook').item.json.body.nom }}",
     "message": "=<p><strong>Nouveau lead mise en relation labos</strong></p><ul><li>Nom : {{ $('Webhook').item.json.body.prenom }} {{ $('Webhook').item.json.body.nom }}</li><li>Email : {{ $('Webhook').item.json.body.email }}</li><li>Téléphone : {{ $('Webhook').item.json.body.telephone }}</li><li>Marque : {{ $('Webhook').item.json.body.marque }}</li><li>Type : {{ $('Webhook').item.json.body.type_projet }}</li><li>Catégorie : {{ $('Webhook').item.json.body.categorie }}</li><li>Quantités : {{ $('Webhook').item.json.body.quantites }}</li><li>Échéance : {{ $('Webhook').item.json.body.echeance }}</li></ul><p><strong>Projet :</strong><br>{{ $('Webhook').item.json.body.description }}</p><p>→ Ligne créée dans Airtable « Leads sur-mesure » (statut Nouveau). À qualifier puis transmettre au labo.</p>",
     "options": {}}},
  {"name": "AR client", "type": "n8n-nodes-base.gmail", "typeVersion": 2.1,
   "position": [880, 0], "credentials": {"gmailOAuth2": creds['gmailOAuth2']},
   "parameters": {
     "sendTo": "={{ $('Webhook').item.json.body.email }}",
     "subject": "Votre projet sur-mesure — MY.LAB",
     "message": "=<p>Bonjour {{ $('Webhook').item.json.body.prenom }},</p><p>Nous avons bien reçu la description de votre projet. Notre équipe l'étudie et revient vers vous <strong>sous 48 h ouvrées</strong> pour vous mettre en relation avec le laboratoire partenaire le plus adapté.</p><p>La mise en relation est gratuite et sans engagement.</p><p>À très vite,<br>L'équipe MY.LAB<br><a href=\"https://mylab-shop.com\">mylab-shop.com</a></p>",
     "options": {}}},
]
connections = {
  "Webhook": {"main": [[{"node": "Répondre 200", "type": "main", "index": 0}]]},
  "Répondre 200": {"main": [[{"node": "Créer lead Airtable", "type": "main", "index": 0}]]},
  "Créer lead Airtable": {"main": [[{"node": "Notif Yoann", "type": "main", "index": 0}]]},
  "Notif Yoann": {"main": [[{"node": "AR client", "type": "main", "index": 0}]]},
}

existing = requests.get(f'{BASE}/workflows', headers=H, params={'limit': 100}, timeout=20).json()['data']
match = [w for w in existing if w['name'] == WF_NAME]
body = {"name": WF_NAME, "nodes": nodes, "connections": connections, "settings": {"executionOrder": "v1"}}
if match:
    wf_id = match[0]['id']
    r = requests.put(f'{BASE}/workflows/{wf_id}', headers=H, json=body, timeout=20)
else:
    r = requests.post(f'{BASE}/workflows', headers=H, json=body, timeout=20)
if r.status_code >= 400:
    print('ERREUR', r.status_code, r.text[:800]); sys.exit(1)
wf_id = r.json()['id']
print(f'✓ Workflow {wf_id} créé/à jour')
ra = requests.post(f'{BASE}/workflows/{wf_id}/activate', headers=H, timeout=20)
if ra.status_code >= 400:
    print('ERREUR activation', ra.status_code, ra.text[:800]); sys.exit(1)
print('✓ Activé — webhook prod: https://n8n.startec-paris.com/webhook/projet-sur-mesure')
