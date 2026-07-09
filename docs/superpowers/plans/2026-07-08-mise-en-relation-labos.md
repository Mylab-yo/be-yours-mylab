# Mise en relation labos partenaires — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transformer la carte « Hors périmètre » de la home en offre de mise en relation avec les labos partenaires : page `/pages/projet-sur-mesure` avec formulaire → webhook n8n → table Airtable « Leads sur-mesure » + mail notif Yoann + accusé de réception client.

**Architecture:** Clone du pattern « Formulaire catalogue » existant : section Liquid autonome (form JS → POST JSON webhook n8n + backup `/contact` Shopify), workflow n8n dédié (Webhook → Respond 200 → Airtable create → Gmail ×2), table dans la base Airtable existante. Transmission aux labos = manuelle (aucun envoi automatique à un tiers).

**Tech Stack:** Liquid (thème Be Yours), n8n REST API (JWT), Airtable (MCP claude.ai + credential n8n existante), Shopify Admin REST (PUT assets, POST pages).

**Spec:** `docs/superpowers/specs/2026-07-08-mise-en-relation-labos-design.md`

## Global Constraints

- Réponses et copy en **français**. Aucune mention de commission côté client — la mise en relation est présentée « gratuite et sans engagement ».
- Thème : pousser sur le **thème dev** d'abord (PUT REST par asset, jamais CLI `--only`) ; live **uniquement** sur « PUSH LIVE » explicite de Yoann. Jamais de full-PUT de `templates/index.json` live sans partir de la version LIVE fraîchement récupérée (le Theme Editor peut avoir dérivé).
- Tokens : Shopify themes/pages = `.env.local` **ligne 46** (`shpat_c78…`) ; n8n = JWT **ligne 39** de `.env.local` (ligne brute sans nom de variable, regex `^eyJ…`). Ne JAMAIS afficher ni committer ces valeurs. `.env.local` = `d:\Configurateur Designs MyLab\mylab-configurateur\.env.local`.
- n8n : jsCode/JSON versionnés dans `scripts/n8n/projet_sur_mesure/`, credentials existantes réutilisées par ID (jamais recréées), pas de secret en dur dans le workflow.
- Airtable : base « Espace de travail mylab » `appdWBkaxdGnJAqxU`, credential n8n `airtableTokenApi` nommée « Catalogue Shopify x Mylab YO ».
- Git : travail sur branche `feat/mise-en-relation-labos`, commits fréquents, PR vers master à la fin (pattern du 08/07 audit home).
- Webhook n8n de référence (workflow catalogue à imiter) : `r9EqKKnyQepCx8t3` — dump JSON complet déjà sauvegardé en scratchpad (`wf_catalogue_r9EqKKnyQepCx8t3.json`) ; sinon le re-télécharger via GET `/api/v1/workflows/r9EqKKnyQepCx8t3`.

---

### Task 1: Table Airtable « Leads sur-mesure »

**Files:** aucun (Airtable uniquement — noter le `tableId` produit pour Task 2)

**Interfaces:**
- Consumes: base `appdWBkaxdGnJAqxU` (existe, contient « Prospects catalogue » `tblN9mp2iFCwDwXCX`)
- Produces: `TABLE_ID` de « Leads sur-mesure » (format `tblXXXXXXXXXXXXXX`) + noms de champs EXACTS ci-dessous, consommés par le mapping Airtable du workflow n8n (Task 2)

- [ ] **Step 1: Créer la table via MCP Airtable** (outil `mcp__claude_ai_Airtable__create_table`, à charger via ToolSearch si session subagent)

```json
{
  "baseId": "appdWBkaxdGnJAqxU",
  "name": "Leads sur-mesure",
  "description": "Demandes de mise en relation labos partenaires (formulaire /pages/projet-sur-mesure). Pipeline commission géré par Yoann.",
  "fields": [
    { "name": "Prénom", "type": "singleLineText" },
    { "name": "Nom", "type": "singleLineText" },
    { "name": "Email", "type": "email" },
    { "name": "Téléphone", "type": "phoneNumber" },
    { "name": "Marque / société", "type": "singleLineText" },
    { "name": "Type de projet", "type": "singleSelect", "options": { "choices": [
      { "name": "Modification de formule existante" },
      { "name": "Création de formule sur-mesure" },
      { "name": "Formulation à façon" },
      { "name": "Études cliniques" },
      { "name": "Autre" } ] } },
    { "name": "Catégorie produit", "type": "singleSelect", "options": { "choices": [
      { "name": "Capillaire" }, { "name": "Soin visage" }, { "name": "Corps" },
      { "name": "Hygiène" }, { "name": "Autre" } ] } },
    { "name": "Quantités envisagées", "type": "singleSelect", "options": { "choices": [
      { "name": "< 500 u" }, { "name": "500 – 1 000 u" }, { "name": "1 000 – 5 000 u" },
      { "name": "> 5 000 u" }, { "name": "Je ne sais pas encore" } ] } },
    { "name": "Échéance", "type": "singleSelect", "options": { "choices": [
      { "name": "< 3 mois" }, { "name": "3 – 6 mois" }, { "name": "6 – 12 mois" },
      { "name": "Pas de date" } ] } },
    { "name": "Description", "type": "multilineText" },
    { "name": "Date de soumission", "type": "dateTime", "options": { "timeZone": "Europe/Paris", "dateFormat": { "name": "european" }, "timeFormat": { "name": "24hour" } } },
    { "name": "Source", "type": "singleLineText" },
    { "name": "Statut", "type": "singleSelect", "options": { "choices": [
      { "name": "Nouveau" }, { "name": "Qualifié" }, { "name": "Transmis labo" },
      { "name": "Devis en cours" }, { "name": "Projet validé" },
      { "name": "Commission facturée" }, { "name": "Sans suite" } ] } },
    { "name": "Labo partenaire", "type": "singleLineText" },
    { "name": "CA projet (€)", "type": "currency", "options": { "precision": 2, "symbol": "€" } },
    { "name": "% commission", "type": "percent", "options": { "precision": 1 } },
    { "name": "Notes", "type": "multilineText" }
  ]
}
```

- [ ] **Step 2: Ajouter le champ formule « Commission due (€) »** via `mcp__claude_ai_Airtable__create_field` : type `formula`, formula `{CA projet (€)} * {% commission}`. Si l'API refuse le type formula → le noter dans le récap final pour création manuelle par Yoann dans l'UI Airtable (30 s), NE PAS bloquer.

- [ ] **Step 3: Vérifier** via `mcp__claude_ai_Airtable__list_tables_for_base` : la table apparaît avec les 17-18 champs. **Noter le `tableId`** → utilisé Task 2.

---

### Task 2: Workflow n8n « MY.LAB — Projet sur-mesure (mise en relation) »

**Files:**
- Create: `scripts/n8n/projet_sur_mesure/create_workflow.py`
- Create: `scripts/n8n/projet_sur_mesure/README.md` (webhook URL, wf id, tableId, comment tester)

**Interfaces:**
- Consumes: `TABLE_ID` (Task 1) ; credentials n8n existantes lues dynamiquement sur le workflow catalogue `r9EqKKnyQepCx8t3` (`gmailOAuth2` « Gmail account », `airtableTokenApi` « Catalogue Shopify x Mylab YO »)
- Produces: webhook prod `https://n8n.startec-paris.com/webhook/projet-sur-mesure` (POST JSON) — consommé par la section Liquid (Task 3). Payload attendu : `{prenom, nom, email, telephone, marque, type_projet, categorie, quantites, echeance, description, consent, source, page_url}`

- [ ] **Step 1: Écrire `create_workflow.py`** — script idempotent (cherche le wf par nom avant de créer) :

```python
# -*- coding: utf-8 -*-
"""Crée + active le workflow n8n 'MY.LAB — Projet sur-mesure (mise en relation)'.
Réutilise les credentials du workflow catalogue r9EqKKnyQepCx8t3. Idempotent."""
import re, sys, json, requests

sys.stdout.reconfigure(encoding='utf-8')
TABLE_ID = 'REMPLACER_PAR_TABLE_ID_TASK_1'  # ex. tblXXXXXXXXXXXXXX
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
     "sendTo": "yoann@mylab-shop.com",
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
r.raise_for_status()
wf_id = r.json()['id']
print(f'✓ Workflow {wf_id} créé/à jour')
ra = requests.post(f'{BASE}/workflows/{wf_id}/activate', headers=H, timeout=20)
ra.raise_for_status()
print(f'✓ Activé — webhook prod: https://n8n.startec-paris.com/webhook/projet-sur-mesure')
```

Avant d'exécuter : remplacer `TABLE_ID`. ⚠️ Si l'API n8n rejette un paramètre Gmail/Airtable (format de champ), comparer avec le dump du wf catalogue (`GET /workflows/r9EqKKnyQepCx8t3`) et aligner les noms de paramètres sur ce que fait le node équivalent.

- [ ] **Step 2: Exécuter** — `python scripts/n8n/projet_sur_mesure/create_workflow.py` → attendu : `✓ Workflow <id> créé/à jour` + `✓ Activé`.

- [ ] **Step 3: Test de bout en bout (canari)** — payload factice avec l'email de Yoann en client :

```bash
curl -s -X POST https://n8n.startec-paris.com/webhook/projet-sur-mesure \
  -H "Content-Type: application/json" \
  -d '{"prenom":"Test","nom":"Canari","email":"yoann@mylab-shop.com","telephone":"0600000000","marque":"TEST-DELETE-ME","type_projet":"Création de formule sur-mesure","categorie":"Capillaire","quantites":"500 – 1 000 u","echeance":"3 – 6 mois","description":"Test technique — à supprimer","consent":"oui","source":"test curl","page_url":"https://test"}'
```

Attendu : `{"ok": true}`. Vérifier : (1) ligne « TEST-DELETE-ME » dans Airtable avec statut Nouveau et selects bien mappés, (2) mail notif reçu par Yoann, (3) mail AR reçu (canari). Puis **supprimer la ligne de test** Airtable.

- [ ] **Step 4: README + commit**

```bash
git checkout -b feat/mise-en-relation-labos
git add scripts/n8n/projet_sur_mesure/
git commit -m "feat(n8n): workflow projet sur-mesure (webhook -> Airtable + notif + AR client)"
```

---

### Task 3: Section `ml-partner-request.liquid` + template de page

**Files:**
- Create: `sections/ml-partner-request.liquid` (clone adapté de `sections/ml-catalogue-request.liquid`)
- Create: `templates/page.projet-sur-mesure.json`

**Interfaces:**
- Consumes: webhook prod Task 2 (dans `webhook_url` du template) ; payload JSON défini Task 2
- Produces: section schema `ml-partner-request` + template suffix `projet-sur-mesure` (consommé par la page Shopify Task 4)

- [ ] **Step 1: Cloner la base** — copier `ml-catalogue-request.liquid` → `ml-partner-request.liquid` puis, dans le nouveau fichier : remplacer TOUTES les occurrences `ml-cat` → `ml-partner` et `CatalogueForm-` → `PartnerForm-`. Supprimer : le champ Ville + son autocomplete (bloc HTML `ml-partner__autocomplete` + tout le JS geo.api.gouv.fr, de `/* ── Autocomplete ville via API Geo Gouv ── */` à la fin de l'IIFE — garder la fermeture `})();`), le sélecteur Activité (`{%- if section.settings.show_activity -%}...{%- endif -%}` + son setting schema), le node Drive n'existe pas ici (rien à faire côté Liquid).

- [ ] **Step 2: Hero + colonne gauche** — remplacer les defaults du hero et le contenu gauche :

```liquid
{%- comment -%} ====== HERO ====== {%- endcomment -%}
<div class="ml-partner__hero">
  <div class="ml-partner__badge">{{ section.settings.badge | default: 'MY.LAB & ses laboratoires partenaires' }}</div>
  <h1 class="ml-partner__title">{{ section.settings.heading | default: 'Votre projet sur-mesure, avec nos laboratoires partenaires' }}</h1>
  <p class="ml-partner__subtitle">{{ section.settings.subtitle | default: 'Formule sur-mesure, modification de formule, formulation à façon ou études cliniques : décrivez votre projet, nous vous mettons en relation avec le laboratoire français adapté. Gratuit et sans engagement.' }}</p>
</div>
```

Colonne gauche : garder la structure `features` (blocks) — les 3 étapes passent dans les blocks du template (Step 4 ci-dessous). Encadré « Pourquoi ces informations ? » default :

```liquid
<p class="ml-partner__why-text">{{ section.settings.why_text | default: 'Votre description nous permet de sélectionner le laboratoire partenaire le plus pertinent pour votre projet. Vos informations ne sont transmises qu’au laboratoire retenu, avec votre accord.' }}</p>
```

⚠️ Apostrophes typographiques `’` (U+2019) obligatoires dans les defaults Liquid entre quotes simples — une apostrophe droite `'` casserait la string (idem partout dans les defaults du schema).

```liquid
```

- [ ] **Step 3: Champs du formulaire** — remplacer le bloc `<div id="{{ form_id }}-fields">` (les champs après Prénom/Nom/Email/Téléphone qui sont conservés tels quels, `salon`/`ville`/`activite` supprimés) :

```liquid
<div class="ml-partner__field">
  <label class="ml-partner__label" for="{{ form_id }}-marque">Marque / société</label>
  <input class="ml-partner__input" type="text" id="{{ form_id }}-marque" name="marque"
         autocomplete="organization" placeholder="Ma Marque">
</div>

<div class="ml-partner__field-row">
  <div class="ml-partner__field">
    <label class="ml-partner__label" for="{{ form_id }}-type">Type de projet <span>*</span></label>
    <select class="ml-partner__input ml-partner__select" id="{{ form_id }}-type" name="type_projet" required>
      <option value="" disabled selected>Sélectionnez</option>
      <option value="Modification de formule existante">Modification de formule existante</option>
      <option value="Création de formule sur-mesure">Création de formule sur-mesure</option>
      <option value="Formulation à façon">Formulation à façon</option>
      <option value="Études cliniques">Études cliniques</option>
      <option value="Autre">Autre</option>
    </select>
  </div>
  <div class="ml-partner__field">
    <label class="ml-partner__label" for="{{ form_id }}-categorie">Catégorie produit <span>*</span></label>
    <select class="ml-partner__input ml-partner__select" id="{{ form_id }}-categorie" name="categorie" required>
      <option value="" disabled selected>Sélectionnez</option>
      <option value="Capillaire">Capillaire</option>
      <option value="Soin visage">Soin visage</option>
      <option value="Corps">Corps</option>
      <option value="Hygiène">Hygiène</option>
      <option value="Autre">Autre</option>
    </select>
  </div>
</div>

<div class="ml-partner__field-row">
  <div class="ml-partner__field">
    <label class="ml-partner__label" for="{{ form_id }}-quantites">Quantités envisagées</label>
    <select class="ml-partner__input ml-partner__select" id="{{ form_id }}-quantites" name="quantites">
      <option value="" disabled selected>Sélectionnez</option>
      <option value="< 500 u">Moins de 500 unités</option>
      <option value="500 – 1 000 u">500 à 1 000 unités</option>
      <option value="1 000 – 5 000 u">1 000 à 5 000 unités</option>
      <option value="> 5 000 u">Plus de 5 000 unités</option>
      <option value="Je ne sais pas encore">Je ne sais pas encore</option>
    </select>
  </div>
  <div class="ml-partner__field">
    <label class="ml-partner__label" for="{{ form_id }}-echeance">Échéance souhaitée</label>
    <select class="ml-partner__input ml-partner__select" id="{{ form_id }}-echeance" name="echeance">
      <option value="" disabled selected>Sélectionnez</option>
      <option value="< 3 mois">Moins de 3 mois</option>
      <option value="3 – 6 mois">3 à 6 mois</option>
      <option value="6 – 12 mois">6 à 12 mois</option>
      <option value="Pas de date">Pas de date précise</option>
    </select>
  </div>
</div>

<div class="ml-partner__field">
  <label class="ml-partner__label" for="{{ form_id }}-description">Décrivez votre projet <span>*</span></label>
  <textarea class="ml-partner__input" id="{{ form_id }}-description" name="description" rows="5" required
            placeholder="Type de produit, texture recherchée, actifs souhaités, contraintes, références existantes…"></textarea>
</div>

<div class="ml-partner__field" style="margin-top:0.4rem;">
  <label class="ml-partner__checkbox">
    <input type="checkbox" name="consent" value="oui" required>
    <span>J'accepte que MY.LAB transmette ces informations à ses laboratoires partenaires pour l'étude de mon projet.
      {%- if section.settings.privacy_url != blank -%}
        <a href="{{ section.settings.privacy_url }}" target="_blank">Politique de confidentialité</a>
      {%- endif -%}
    </span>
  </label>
</div>
```

Ajouter au CSS cloné (le textarea n'existait pas) :

```css
textarea.ml-partner__input { resize: vertical; min-height: 110px; font-family: inherit; }
```

- [ ] **Step 4: Payload JS** — remplacer l'objet `payload` et le backup dans le script cloné :

```javascript
var payload = {
  prenom      : get('prenom'),
  nom         : get('nom'),
  email       : get('email'),
  telephone   : get('telephone'),
  marque      : get('marque'),
  type_projet : get('type_projet'),
  categorie   : get('categorie'),
  quantites   : get('quantites'),
  echeance    : get('echeance'),
  description : get('description'),
  consent     : get('consent'),
  source      : 'Shopify — page projet sur-mesure',
  page_url    : window.location.href
};
```

et le corps du backup `/contact` :

```javascript
var backupBody =
  'Projet sur-mesure — ' + payload.source + '\n' +
  'Marque : '     + payload.marque + '\n' +
  'Type : '       + payload.type_projet + '\n' +
  'Catégorie : '  + payload.categorie + '\n' +
  'Quantités : '  + payload.quantites + '\n' +
  'Échéance : '   + payload.echeance + '\n' +
  'Téléphone : '  + payload.telephone + '\n' +
  'Description :\n' + payload.description + '\n' +
  'Page : '       + payload.page_url;
```

(`get('consent')` : la fonction `get` clonée lit `.value` — pour une checkbox non cochée le `required` bloque la soumission, donc toujours "oui" ici.)

- [ ] **Step 5: Schema** — adapter le schema cloné : `"name": "ML Projet sur-mesure"`, `"class": "ml-partner-section"`, defaults des settings = textes des Steps 2-3, retirer `show_activity`, garder `webhook_url`, `privacy_url`, `success_title` default `"Votre projet a bien été envoyé !"`, `success_text` default `"Nous revenons vers vous sous 48 h ouvrées avec le laboratoire adapté à votre projet."`, `submit_label` default `"Envoyer mon projet"`, `form_heading` default `"Décrivez votre projet"`, `form_desc` default `"2 minutes suffisent — nous nous chargeons du reste."`. Block `feature` renommé label `"Étape / argument"`.

- [ ] **Step 6: Template de page** — créer `templates/page.projet-sur-mesure.json` :

```json
{
  "sections": {
    "main": {
      "type": "ml-partner-request",
      "blocks": {
        "step_1": { "type": "feature", "settings": {
          "title": "1. Décrivez votre projet",
          "description": "Formule, texture, actifs, quantités : plus c'est précis, mieux c'est." } },
        "step_2": { "type": "feature", "settings": {
          "title": "2. MY.LAB sélectionne le bon laboratoire",
          "description": "Nous qualifions votre demande et identifions le partenaire français adapté." } },
        "step_3": { "type": "feature", "settings": {
          "title": "3. Mise en relation sous 48 h",
          "description": "Vous échangez directement avec le laboratoire, accompagné par MY.LAB." } },
        "arg_1": { "type": "feature", "settings": {
          "title": "Laboratoires français",
          "description": "Partenaires sélectionnés pour leur expertise cosmétique." } },
        "arg_2": { "type": "feature", "settings": {
          "title": "Gratuit et sans engagement",
          "description": "La mise en relation ne vous coûte rien." } }
      },
      "block_order": ["step_1", "step_2", "step_3", "arg_1", "arg_2"],
      "settings": {
        "content_heading": "Comment ça marche",
        "padding_top": 60,
        "padding_bottom": 60,
        "webhook_url": "https://n8n.startec-paris.com/webhook/projet-sur-mesure",
        "privacy_url": "shopify://policies/privacy-policy"
      }
    }
  },
  "order": ["main"]
}
```

⚠️ Vérifier que `shopify://policies/privacy-policy` est accepté par un setting `url` (le template catalogue live à comparer) ; sinon mettre `/policies/privacy-policy` en dur.

- [ ] **Step 7: Lint local** — vérifier qu'il ne reste AUCUNE occurrence `ml-cat`, `CatalogueForm`, `catalogue` dans le nouveau fichier : `grep -in "ml-cat\|CatalogueForm\|catalogue" sections/ml-partner-request.liquid` → attendu : aucune ligne (sauf éventuel commentaire d'origine à réécrire).

- [ ] **Step 8: Commit**

```bash
git add sections/ml-partner-request.liquid templates/page.projet-sur-mesure.json
git commit -m "feat(theme): section + template page projet sur-mesure (mise en relation labos)"
```

---

### Task 4: Page Shopify + push thème dev + QA

**Files:** aucun nouveau (API Shopify uniquement)

**Interfaces:**
- Consumes: token `.env.local` ligne 46 (`shpat_c78…`, scopes themes + content) ; template suffix `projet-sur-mesure` (Task 3)
- Produces: page live `https://mylab-shop.com/pages/projet-sur-mesure` (rendra le template seulement sur les thèmes qui l'ont) ; assets poussés sur le thème DEV

- [ ] **Step 1: Créer la page** — POST REST (script Python scratchpad, token jamais affiché) :

```python
# POST /admin/api/2024-10/pages.json
{"page": {"title": "Projet sur-mesure", "handle": "projet-sur-mesure",
          "template_suffix": "projet-sur-mesure", "published": True,
          "body_html": ""}}
```

Attendu : 201 + `"handle": "projet-sur-mesure"`. Si 403 (scope write_content manquant sur ligne 46) : essayer les autres tokens de `.env.local` (lignes 23/37) ; si aucun ne passe → demander à Yoann de créer la page dans l'admin (titre « Projet sur-mesure », thème template `projet-sur-mesure`) et continuer.

- [ ] **Step 2: Identifier le thème dev** — GET `/admin/api/2024-10/themes.json` → prendre `role == "development"` (sinon `unpublished` le plus récent ; l'audit du 08/07 utilisait `199873429838`). Noter `DEV_THEME_ID`.

- [ ] **Step 3: Pousser les 2 assets sur le thème DEV** — pattern PUT REST fiable (jamais CLI `--only`) :

```python
# PUT /admin/api/2025-04/themes/{DEV_THEME_ID}/assets.json
{"asset": {"key": "sections/ml-partner-request.liquid", "value": "<contenu du fichier>"}}
{"asset": {"key": "templates/page.projet-sur-mesure.json", "value": "<contenu du fichier>"}}
```

Attendu : 200 sur les deux.

- [ ] **Step 4: QA rendu (sans navigateur)** — pattern curl preview (domaine PRINCIPAL, jamais myshopify qui perd le param) :

```bash
curl -sL -c /tmp/jar -b /tmp/jar "https://mylab-shop.com/pages/projet-sur-mesure?preview_theme_id=DEV_THEME_ID" -o page.html
grep -c "ml-partner__" page.html          # attendu > 0 (section rendue)
grep -c "type_projet" page.html           # attendu ≥ 1 (champ présent)
grep -ci "laboratoires partenaires" page.html   # attendu ≥ 2 (hero + consentement)
grep -ci "commission" page.html           # attendu 0 (JAMAIS côté client)
grep -c "n8n.startec-paris.com/webhook/projet-sur-mesure" page.html  # attendu 1
```

Confirmer que c'est bien le thème dev : `grep -o "Shopify.theme[^;]*" page.html | head -1` doit contenir `DEV_THEME_ID` et `"role":"development"`.

- [ ] **Step 5: Test formulaire réel (canari)** — depuis le HTML rendu, rejouer ce que ferait le JS : re-curl le webhook (déjà validé Task 2) ; le vrai test navigateur sera fait par Yoann à la validation. Rien à committer.

---

### Task 5: Carte home « Projet sur-mesure ? »

**Files:**
- Modify: `templates/index.json` (bloc `col_exclude` de la section `perimeter_columns`, ~lignes 362-380)

**Interfaces:**
- Consumes: version LIVE de `templates/index.json` (GET asset sur le thème role=main — le repo peut avoir dérivé du Theme Editor)
- Produces: `templates/index.json` modifié poussé sur le thème DEV + committé sur la branche

- [ ] **Step 1: Récupérer le index.json LIVE** — GET `/admin/api/2025-04/themes/{LIVE_ID}/assets.json?asset[key]=templates/index.json` (LIVE_ID via role=main, attendu `184014340430`). Sauvegarder en scratchpad. Vérifier que le bloc `col_exclude` contient bien `"title": "<em>Hors périmètre</em>"` — si le contenu diffère du repo, PARTIR DE LA VERSION LIVE.

- [ ] **Step 2: Modification chirurgicale** — dans la copie live, remplacer UNIQUEMENT les 4 settings du bloc `col_exclude` :

```json
"title": "<em>Projet sur-mesure ?</em>",
"text": "<p>Ces projets dépassent notre catalogue — nos laboratoires partenaires les réalisent. Nous vous mettons en relation gratuitement :</p><ul><li>Modification de formule existante</li><li>Création de formule sur-mesure</li><li>Formulation à façon</li><li>Études cliniques personnalisées</li></ul>",
"button_label": "Décrivez-nous votre projet",
"button_link": "shopify://pages/projet-sur-mesure"
```

Tout le reste du fichier strictement identique à la version live (diff avant push : seul le bloc `col_exclude` change).

- [ ] **Step 3: PUT sur le thème DEV** (`templates/index.json`) → 200.

- [ ] **Step 4: QA home dev** :

```bash
curl -sL -c /tmp/jar -b /tmp/jar "https://mylab-shop.com/?preview_theme_id=DEV_THEME_ID" -o home.html
grep -c "Projet sur-mesure ?" home.html            # attendu ≥ 1
grep -c "Décrivez-nous votre projet" home.html      # attendu ≥ 1
grep -c "/pages/projet-sur-mesure" home.html        # attendu ≥ 1
grep -c "Hors périmètre" home.html                  # attendu 0
```

- [ ] **Step 5: Reporter la modif dans le repo + commit** — appliquer le même changement (mêmes 4 settings) dans `templates/index.json` local via Edit chirurgical, puis :

```bash
git add templates/index.json
git commit -m "feat(home): carte Hors perimetre -> Projet sur-mesure (mise en relation labos)"
git push -u origin feat/mise-en-relation-labos
```

---

### Task 6: Validation Yoann + mise en live

**Files:** aucun (déploiement + PR)

- [ ] **Step 1: Récap à Yoann** — lui donner : URL preview home + page (`https://mylab-shop.com/...?preview_theme_id=DEV_THEME_ID`), rappel du test canari réussi (Airtable + 2 mails), et la question restante éventuelle (champ formule Airtable si non créé par API). **ATTENDRE son « PUSH LIVE » explicite.**

- [ ] **Step 2 (après GO): Push live** — PUT des 3 assets sur le thème LIVE (role=main, attendu `184014340430`) : `sections/ml-partner-request.liquid`, `templates/page.projet-sur-mesure.json`, `templates/index.json` (⚠️ re-GET la version live JUSTE AVANT, réappliquer le patch chirurgical, puis PUT — le Theme Editor peut avoir bougé entre-temps).

- [ ] **Step 3: QA live** — mêmes greps que Tasks 4-5 sans `preview_theme_id`. Vérifier `grep -ci "commission"` = 0 sur les deux pages.

- [ ] **Step 4: PR + merge**

```bash
gh pr create --title "feat: mise en relation labos partenaires (home + page + n8n/Airtable)" --body "Carte home 'Hors périmètre' → 'Projet sur-mesure ?' + page /pages/projet-sur-mesure (formulaire qualifiant, consentement RGPD, backup /contact) + workflow n8n webhook → Airtable 'Leads sur-mesure' + notif Yoann + AR client 48h. Spec : docs/superpowers/specs/2026-07-08-mise-en-relation-labos-design.md. QA curl preview OK, test canari n8n/Airtable/mails OK, zéro mention commission côté client.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

- [ ] **Step 5: Mémoire** — créer `project_mise_en_relation_labos.md` (memory) : webhook URL, wf id n8n, tableId Airtable, ce qui est live, pipeline commission = géré main dans Airtable ; + ligne dans MEMORY.md.
