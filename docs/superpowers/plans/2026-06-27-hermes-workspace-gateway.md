# Passerelle workspace Hermes local (via n8n) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Donner à Hermes local (Qwen) un accès lecture + écriture à Google Workspace, Airtable et n8n via UN seul outil (une passerelle webhook n8n), sans réintroduire le bloat d'outils MCP qui dégrade le routage du modèle local.

**Architecture:** Un workflow n8n `hermes-gateway` expose un webhook POST sécurisé par token. Hermes appelle un script unique `n8n_gateway.py` qui POST `{capability, params}` ; un nœud Switch route vers la branche service (nœuds natifs Gmail/Calendar/Drive/Airtable portant l'OAuth) ; la réponse est un JSON normalisé `{ok, data, error}`. Côté Hermes : un skill `workspace` (catalogue de capacités) + une ligne dans le routeur `SOUL.md`.

**Tech Stack:** n8n (REST API + nœuds natifs, instance `https://n8n.startec-paris.com`), Python 3.11 (`requests`/`urllib`), Hermes agent (skills + SOUL.md + config.yaml + .env).

## Global Constraints

- Instance n8n cible : **`https://n8n.startec-paris.com`**. API : header `X-N8N-API-KEY: $N8N_API_KEY`. Webhooks : `https://n8n.startec-paris.com/webhook/<path>`.
- Clés déjà présentes dans `C:\Users\MyLab\AppData\Local\hermes\.env` : `N8N_BASE_URL`, `N8N_API_KEY`, `AIRTABLE_API_KEY`. (NB : la ref skill mentionne `N8N_KEY` — la vraie variable est `N8N_API_KEY`.)
- **L'agent Hermes ne peut PAS lire `.env`** (protégé) et `terminal.env_passthrough: []` est vide. Tout secret dont un script lancé par l'agent a besoin DOIT être ajouté explicitement à `terminal.env_passthrough` dans `config.yaml`.
- Hôte n8n = non secret → peut être en dur dans le script. Seul `HERMES_GW_TOKEN` est secret.
- Convention scripts Hermes (leçon `draft-creator`) : **pas d'emoji dans `print()`** (console Windows cp1252 → crash), **exit 0 = succès / exit ≠ 0 = échec réel** (jamais d'exit code menteur).
- Skills Hermes : `C:\Users\MyLab\AppData\Local\hermes\skills\<nom>\SKILL.md` (frontmatter `name`/`description`/`trigger`), scripts sous `skills/<nom>/scripts/`.
- `$HERMES_HOME` est un repo git (whitelist `.gitignore`, secrets exclus) — commits via `cd $HERMES_HOME && git add -A && git commit`.
- Règle email préservée : **Gmail = lecture seule** via la passerelle ; l'écriture mail reste sur himalaya/draft-creator « brouillon only ». Pas de capacité `gmail.send` dans ce plan.
- Catalogue v1 (9 capacités) : `gmail.search`, `gmail.get`, `calendar.list`, `calendar.create`, `calendar.update`, `drive.search`, `drive.get`, `airtable.query`, `airtable.upsert`.

---

### Task 1: Recon & prérequis (instance, credentials, token)

But : rassembler les faits instance-spécifiques que les tâches suivantes consomment, et générer le secret. Aucun code applicatif ; produit un bloc de faits.

**Files:**
- Create: `C:\Users\MyLab\AppData\Local\hermes\skills\workspace\NOTES-prereqs.md` (scratch, versionné — faits de build)

**Interfaces:**
- Produces : `WEBHOOK_PATH = "hermes-gateway"`, `WEBHOOK_URL = "https://n8n.startec-paris.com/webhook/hermes-gateway"`, `HERMES_GW_TOKEN` (valeur générée), et un mapping `CRED_IDS = { google: <id>, calendar: <id>, drive: <id>, airtable: <id> }` (IDs des credentials OAuth/API existants dans n8n).

- [ ] **Step 1: Vérifier l'accès API n8n et lister les credentials existants**

```bash
# Depuis un shell ayant N8N_BASE_URL + N8N_API_KEY (cd $HERMES_HOME ; charger .env)
curl -s -H "X-N8N-API-KEY: $N8N_API_KEY" "https://n8n.startec-paris.com/api/v1/credentials/schema/googleApi" >/dev/null && echo "API OK"
curl -s -H "X-N8N-API-KEY: $N8N_API_KEY" "https://n8n.startec-paris.com/api/v1/workflows?limit=1" | head -c 200
```

Expected : `API OK` puis un JSON de workflow (preuve que la clé marche).

- [ ] **Step 2: Identifier les credentials Google + Airtable déjà configurés dans n8n**

Dans l'UI n8n (ou via un workflow existant qui utilise Gmail/Calendar/Drive/Airtable), relever les **credential IDs** des connexions OAuth Google (Gmail, Calendar, Drive) et de la connexion Airtable (Personal Access Token / OAuth). Les noter dans `NOTES-prereqs.md`.

Expected : 4 IDs (ou moins si une même cred Google couvre Gmail+Calendar+Drive). Si une cred manque → la créer dans l'UI n8n AVANT de continuer (hors scope script ; action manuelle one-shot).

- [ ] **Step 3: Générer le token de passerelle**

```bash
python -c "import secrets; print('HERMES_GW_TOKEN=' + secrets.token_urlsafe(32))"
```

Copier la ligne produite. Expected : `HERMES_GW_TOKEN=<44 chars>`.

- [ ] **Step 4: Consigner les faits**

Écrire dans `NOTES-prereqs.md` : `WEBHOOK_URL`, `WEBHOOK_PATH`, les `CRED_IDS`, et une note « token stocké dans .env (Task 6), jamais ici ». **Ne PAS écrire la valeur du token dans ce fichier** (il est versionné).

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/MyLab/AppData/Local/hermes" && git add skills/workspace/NOTES-prereqs.md && git commit -m "chore(workspace): prereqs passerelle n8n (instance, cred IDs)"
```

---

### Task 2: Squelette du workflow n8n `hermes-gateway` (webhook + token + switch + respond)

But : un workflow qui reçoit un POST, refuse sans token, route sur `capability`, et répond `{ok,data,error}` — avec une branche `ping` factice pour prouver le bout-en-bout AVANT de câbler les services.

**Files:**
- Create (n8n) : workflow `hermes-gateway` (via REST API POST `/workflows`, ou n8n MCP `create_workflow_from_code` si le connecteur cible bien `n8n.startec-paris.com`).
- Create : `C:\Users\MyLab\AppData\Local\hermes\skills\workspace\scripts\build_gateway_workflow.py` (script idempotent qui construit/MAJ le workflow via REST API).

**Interfaces:**
- Consumes : `WEBHOOK_PATH`, `CRED_IDS` (Task 1).
- Produces : workflow actif joignable à `WEBHOOK_URL` ; contrat I/O = entrée `{capability:string, params:object}`, sortie `{ok:bool, data:any, error:string|null}` ; capacité `ping` → `{ok:true, data:"pong", error:null}`.

- [ ] **Step 1: Écrire le test (script de vérif bout-en-bout) qui DOIT échouer**

```python
# skills/workspace/scripts/test_gateway_ping.py
import json, os, urllib.request
URL = "https://n8n.startec-paris.com/webhook/hermes-gateway"
TOKEN = os.environ["HERMES_GW_TOKEN"]
def call(payload, token=TOKEN):
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(),
        headers={"Content-Type":"application/json","X-Hermes-Token":token})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, json.loads(r.read().decode())
if __name__ == "__main__":
    s, body = call({"capability":"ping","params":{}})
    assert s == 200 and body["ok"] is True and body["data"] == "pong", body
    # token absent => 401
    try:
        call({"capability":"ping","params":{}}, token="")
        raise SystemExit("ERREUR: 401 attendu sans token")
    except urllib.error.HTTPError as e:
        assert e.code == 401, e.code
    print("[OK] ping + auth")
```

- [ ] **Step 2: Lancer le test → échec attendu**

Run : `python skills/workspace/scripts/test_gateway_ping.py`
Expected : échec (HTTP 404 « webhook not registered » — le workflow n'existe pas encore).

- [ ] **Step 3: Construire le workflow squelette**

`build_gateway_workflow.py` POST ce graphe via l'API n8n (`POST /api/v1/workflows` puis activer) :
- **Webhook** (`n8n-nodes-base.webhook`, typeVersion 2) : `path:"hermes-gateway"`, `httpMethod:"POST"`, `responseMode:"responseNode"`.
- **IF token** (`n8n-nodes-base.if`) : condition `{{$json.headers["x-hermes-token"]}}` **égal** `={{$env.HERMES_GW_TOKEN}}`. Faux → **Respond 401** (`n8n-nodes-base.respondToWebhook`, `responseCode:401`, body `{"ok":false,"data":null,"error":"unauthorized"}`).
- **Switch** (`n8n-nodes-base.switch`, mode `rules`) sur `={{$json.body.capability}}` : règle `ping` → branche ping ; règle par défaut (fallback) → **Respond** `{"ok":false,"data":null,"error":"unknown capability"}`.
- **Branche ping** : **Set** `data="pong"` → **Respond** `{{ {ok:true,data:$json.data,error:null} }}`.

Le script lit `CRED_IDS`/`WEBHOOK_PATH` depuis `NOTES-prereqs.md` ou des constantes en tête. Idempotent : si un workflow nommé `hermes-gateway` existe, faire `PUT` au lieu de `POST`.

- [ ] **Step 4: Activer + relancer le test → succès**

```bash
python skills/workspace/scripts/build_gateway_workflow.py   # crée/MAJ + active
HERMES_GW_TOKEN=<valeur Task1.Step3> python skills/workspace/scripts/test_gateway_ping.py
```
Expected : `[OK] ping + auth`.

- [ ] **Step 5: Commit**

```bash
cd "C:/Users/MyLab/AppData/Local/hermes" && git add skills/workspace/scripts/build_gateway_workflow.py skills/workspace/scripts/test_gateway_ping.py && git commit -m "feat(workspace): squelette passerelle n8n (webhook+token+switch+ping)"
```

---

### Task 3: Branche Gmail (lecture seule) — `gmail.search`, `gmail.get`

**Files:**
- Modify (n8n) : workflow `hermes-gateway` via `build_gateway_workflow.py` (ajout branches).
- Modify : `skills/workspace/scripts/build_gateway_workflow.py`
- Create : `skills/workspace/scripts/test_gateway_gmail.py`

**Interfaces:**
- Consumes : contrat I/O + `CRED_IDS.google` (Task 1/2).
- Produces : `gmail.search` (params `{query:string, limit?:int}` → `data:[{id,threadId,from,subject,date,snippet}]`) ; `gmail.get` (params `{id:string}` → `data:{id,from,to,subject,date,body}`).

- [ ] **Step 1: Écrire le test (échec attendu)**

```python
# skills/workspace/scripts/test_gateway_gmail.py — réutilise call() de test_gateway_ping
from test_gateway_ping import call
s, b = call({"capability":"gmail.search","params":{"query":"newer_than:30d","limit":3}})
assert b["ok"] and isinstance(b["data"], list), b
if b["data"]:
    one = b["data"][0]["id"]
    s2, b2 = call({"capability":"gmail.get","params":{"id":one}})
    assert b2["ok"] and b2["data"]["id"] == one, b2
print("[OK] gmail.search + gmail.get")
```

- [ ] **Step 2: Lancer → échec** (`unknown capability`).
Run : `python skills/workspace/scripts/test_gateway_gmail.py` — Expected : AssertionError (ok=False).

- [ ] **Step 3: Ajouter les branches Gmail**

Dans le Switch, ajouter règles `gmail.search` et `gmail.get` →
- `gmail.search` : nœud **Gmail** (`n8n-nodes-base.gmail`, resource `message`, operation `getAll`), `filters.q = ={{$json.body.params.query}}`, `limit = ={{$json.body.params.limit || 10}}`, credential = `CRED_IDS.google`. Puis **Set/Code** pour normaliser en `[{id,threadId,from,subject,date,snippet}]` → **Respond** `{ok:true,data,error:null}`.
- `gmail.get` : nœud **Gmail** (operation `get`), `messageId = ={{$json.body.params.id}}` → normaliser → Respond.

- [ ] **Step 4: Rebuild + test → succès**
```bash
python skills/workspace/scripts/build_gateway_workflow.py && python skills/workspace/scripts/test_gateway_gmail.py
```
Expected : `[OK] gmail.search + gmail.get`.

- [ ] **Step 5: Commit**
```bash
cd "C:/Users/MyLab/AppData/Local/hermes" && git add -A && git commit -m "feat(workspace): branche Gmail lecture (search+get)"
```

---

### Task 4: Branche Calendar (lecture + écriture) — `calendar.list`, `calendar.create`, `calendar.update`

**Files:**
- Modify (n8n) : workflow via `build_gateway_workflow.py`.
- Create : `skills/workspace/scripts/test_gateway_calendar.py`

**Interfaces:**
- Consumes : `CRED_IDS.calendar` (= `CRED_IDS.google` si cred unique).
- Produces : `calendar.list` (params `{timeMin?,timeMax?,limit?}` → `data:[{id,summary,start,end}]`) ; `calendar.create` (params `{summary,start,end,description?,attendees?}` → `data:{id,htmlLink}`) ; `calendar.update` (params `{id, ...champs}` → `data:{id,htmlLink}`).

- [ ] **Step 1: Test (échec attendu)** — crée un event de test, le met à jour, le liste, puis nettoie.

```python
# skills/workspace/scripts/test_gateway_calendar.py
from test_gateway_ping import call
c = call({"capability":"calendar.create","params":{
    "summary":"TEST hermes-gateway","start":"2026-07-01T10:00:00+02:00",
    "end":"2026-07-01T10:30:00+02:00"}})[1]
assert c["ok"] and c["data"]["id"], c
eid = c["data"]["id"]
u = call({"capability":"calendar.update","params":{"id":eid,"summary":"TEST maj"}})[1]
assert u["ok"], u
l = call({"capability":"calendar.list","params":{"timeMin":"2026-07-01T00:00:00+02:00","timeMax":"2026-07-02T00:00:00+02:00"}})[1]
assert l["ok"] and any(e["id"]==eid for e in l["data"]), l
print("[OK] calendar list/create/update")  # NB: supprimer l'event de test à la main
```

- [ ] **Step 2: Lancer → échec** (`unknown capability`).

- [ ] **Step 3: Ajouter les branches Calendar**

Règles Switch `calendar.list|create|update` → nœud **Google Calendar** (`n8n-nodes-base.googleCalendar`) :
- `list` : operation `getAll`, `timeMin/timeMax` depuis params, `limit = ={{$json.body.params.limit || 20}}` → normaliser `[{id,summary,start,end}]`.
- `create` : operation `create`, `start`/`end`/`summary`/`description` depuis params → `{id,htmlLink}`.
- `update` : operation `update`, `eventId = ={{$json.body.params.id}}` + champs présents → `{id,htmlLink}`.
Chacune → **Respond** `{ok:true,data,error:null}`. Credential = `CRED_IDS.calendar`.

- [ ] **Step 4: Rebuild + test → succès**
```bash
python skills/workspace/scripts/build_gateway_workflow.py && python skills/workspace/scripts/test_gateway_calendar.py
```
Expected : `[OK] calendar list/create/update`. Supprimer l'event « TEST … » créé.

- [ ] **Step 5: Commit**
```bash
cd "C:/Users/MyLab/AppData/Local/hermes" && git add -A && git commit -m "feat(workspace): branche Calendar list/create/update"
```

---

### Task 5: Branche Drive (lecture) — `drive.search`, `drive.get`

**Files:**
- Modify (n8n) via `build_gateway_workflow.py`.
- Create : `skills/workspace/scripts/test_gateway_drive.py`

**Interfaces:**
- Consumes : `CRED_IDS.drive`.
- Produces : `drive.search` (params `{query:string, limit?:int}` → `data:[{id,name,mimeType,modifiedTime,webViewLink}]`) ; `drive.get` (params `{id:string}` → `data:{id,name,mimeType,webViewLink}`).

- [ ] **Step 1: Test (échec attendu)**
```python
# skills/workspace/scripts/test_gateway_drive.py
from test_gateway_ping import call
s,b = call({"capability":"drive.search","params":{"query":"name contains 'mylab'","limit":3}})
assert b["ok"] and isinstance(b["data"],list), b
if b["data"]:
    g = call({"capability":"drive.get","params":{"id":b["data"][0]["id"]}})[1]
    assert g["ok"] and g["data"]["id"], g
print("[OK] drive search/get")
```

- [ ] **Step 2: Lancer → échec** (`unknown capability`).

- [ ] **Step 3: Ajouter les branches Drive** — nœud **Google Drive** (`n8n-nodes-base.googleDrive`) : `search` (operation `fileFolder`/`search`, `q` depuis params, limit) → normaliser ; `get` (operation `download`/`share` metadata via `fileId`) → normaliser. Credential = `CRED_IDS.drive`. → Respond.

- [ ] **Step 4: Rebuild + test → succès**
```bash
python skills/workspace/scripts/build_gateway_workflow.py && python skills/workspace/scripts/test_gateway_drive.py
```
Expected : `[OK] drive search/get`.

- [ ] **Step 5: Commit**
```bash
cd "C:/Users/MyLab/AppData/Local/hermes" && git add -A && git commit -m "feat(workspace): branche Drive search/get"
```

---

### Task 6: Branche Airtable (lecture + écriture) — `airtable.query`, `airtable.upsert`

**Files:**
- Modify (n8n) via `build_gateway_workflow.py`.
- Create : `skills/workspace/scripts/test_gateway_airtable.py`

**Interfaces:**
- Consumes : `CRED_IDS.airtable`.
- Produces : `airtable.query` (params `{base:string, table:string, filterByFormula?:string, limit?:int}` → `data:[{id,fields}]`) ; `airtable.upsert` (params `{base, table, records:[{id?,fields}]}` → `data:[{id,fields}]`).

- [ ] **Step 1: Test (échec attendu)** — utiliser une base/table de test choisie dans `NOTES-prereqs.md`.
```python
# skills/workspace/scripts/test_gateway_airtable.py
from test_gateway_ping import call
BASE, TABLE = "appXXXX", "Tests"  # à renseigner depuis NOTES-prereqs.md
q = call({"capability":"airtable.query","params":{"base":BASE,"table":TABLE,"limit":2}})[1]
assert q["ok"] and isinstance(q["data"],list), q
up = call({"capability":"airtable.upsert","params":{"base":BASE,"table":TABLE,
    "records":[{"fields":{"Name":"hermes-gateway test"}}]}})[1]
assert up["ok"] and up["data"][0]["id"], up
print("[OK] airtable query/upsert")  # NB: supprimer la ligne de test à la main
```

- [ ] **Step 2: Lancer → échec** (`unknown capability`).

- [ ] **Step 3: Ajouter les branches Airtable** — nœud **Airtable** (`n8n-nodes-base.airtable`) : `query` (operation `search`/`list`, `base`/`table`/`filterByFormula`/`limit` depuis params) → `[{id,fields}]` ; `upsert` (operation `upsert` ou `create`, `records` depuis params) → `[{id,fields}]`. Credential = `CRED_IDS.airtable`. → Respond.

- [ ] **Step 4: Rebuild + test → succès**
```bash
python skills/workspace/scripts/build_gateway_workflow.py && python skills/workspace/scripts/test_gateway_airtable.py
```
Expected : `[OK] airtable query/upsert`. Supprimer la ligne de test.

- [ ] **Step 5: Commit**
```bash
cd "C:/Users/MyLab/AppData/Local/hermes" && git add -A && git commit -m "feat(workspace): branche Airtable query/upsert"
```

---

### Task 7: Client Hermes — `n8n_gateway.py` + câblage env

But : le script unique que l'agent appelle, + exposer le token au terminal de l'agent.

**Files:**
- Create : `skills/workspace/scripts/n8n_gateway.py`
- Modify : `C:\Users\MyLab\AppData\Local\hermes\.env` (ajout `HERMES_GW_TOKEN=`)
- Modify : `C:\Users\MyLab\AppData\Local\hermes\config.yaml` (`terminal.env_passthrough`)

**Interfaces:**
- Consumes : `WEBHOOK_URL` (en dur), `HERMES_GW_TOKEN` (env).
- Produces : CLI `python n8n_gateway.py <capability> '<params-json>'` → imprime sur stdout le JSON `{ok,data,error}` ; **exit 0 si `ok=true`, exit 1 sinon**.

- [ ] **Step 1: Écrire le script**

```python
# skills/workspace/scripts/n8n_gateway.py
import json, os, sys, urllib.request, urllib.error
WEBHOOK_URL = "https://n8n.startec-paris.com/webhook/hermes-gateway"

def gateway(capability, params):
    token = os.environ.get("HERMES_GW_TOKEN")
    if not token:
        return {"ok": False, "data": None, "error": "HERMES_GW_TOKEN absent de l'environnement (env_passthrough config.yaml)"}
    body = json.dumps({"capability": capability, "params": params}).encode()
    req = urllib.request.Request(WEBHOOK_URL, data=body,
        headers={"Content-Type": "application/json", "X-Hermes-Token": token})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"ok": False, "data": None, "error": f"HTTP {e.code}: {e.read().decode()[:200]}"}
    except Exception as e:
        return {"ok": False, "data": None, "error": f"reseau: {e}"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "data": None, "error": "usage: n8n_gateway.py <capability> [params-json]"}))
        sys.exit(2)
    cap = sys.argv[1]
    params = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    res = gateway(cap, params)
    print(json.dumps(res, ensure_ascii=False))
    sys.exit(0 if res.get("ok") else 1)
```

- [ ] **Step 2: Ajouter le token à `.env`**

Ajouter en fin de `C:\Users\MyLab\AppData\Local\hermes\.env` (section `# n8n`) :
```
HERMES_GW_TOKEN=<valeur générée Task 1, Step 3>
```

- [ ] **Step 3: Exposer le token au terminal de l'agent**

Dans `config.yaml`, remplacer `env_passthrough: []` par :
```yaml
  env_passthrough: ["HERMES_GW_TOKEN"]
```

- [ ] **Step 4: Redémarrer la gateway + test bout-en-bout réel**

```bash
hermes gateway restart
# puis, dans un shell où HERMES_GW_TOKEN est exporté :
python "C:/Users/MyLab/AppData/Local/hermes/skills/workspace/scripts/n8n_gateway.py" ping '{}'
echo "exit=$?"
```
Expected : `{"ok": true, "data": "pong", "error": null}` et `exit=0`.
Test échec : `python n8n_gateway.py inconnue '{}'` → `{"ok": false, ... "unknown capability"}` et `exit=1`.

- [ ] **Step 5: Commit** (le token est dans `.env`, exclu par `.gitignore` whitelist — vérifier `git status` ne le montre pas)
```bash
cd "C:/Users/MyLab/AppData/Local/hermes" && git status --porcelain | grep -q "\.env" && echo "ATTENTION .env tracké — STOP" || (git add skills/workspace/scripts/n8n_gateway.py config.yaml && git commit -m "feat(workspace): client n8n_gateway.py + env_passthrough token")
```

---

### Task 8: Skill `workspace` (catalogue) + routeur SOUL.md

But : apprendre au modèle quand et comment utiliser la passerelle, surface minimale.

**Files:**
- Create : `skills/workspace/SKILL.md`
- Create : `skills/workspace/references/capabilities.md`
- Modify : `C:\Users\MyLab\AppData\Local\hermes\SOUL.md` (table routeur)

**Interfaces:**
- Consumes : la CLI `n8n_gateway.py <capability> <params-json>` (Task 7).
- Produces : déclenchement par intention (mots-clés agenda / drive / fichier / Airtable / RDV / mail-lecture).

- [ ] **Step 1: Écrire `SKILL.md`**

```markdown
---
name: workspace
description: "Accès Google Workspace (Gmail lecture, Calendar, Drive), Airtable et n8n via la passerelle n8n hermes-gateway. Use when: agenda, calendrier, RDV, événement, disponibilité, Google Drive, fichier Drive, Airtable, base Airtable, fiche, lire un mail (recherche)."
trigger: agenda, calendrier, rendez-vous, RDV, événement, disponibilité, planning, drive, google drive, fichier, airtable, base airtable, fiche airtable
---

# Workspace (passerelle n8n)

Un seul outil pour Google Workspace / Airtable. Tu appelles TOUJOURS via :

    python "C:/Users/MyLab/AppData/Local/hermes/skills/workspace/scripts/n8n_gateway.py" <capability> '<params-json>'

La sortie est un JSON `{ok, data, error}`. Si `ok:false`, lis `error` et corrige les params (catalogue dans `references/capabilities.md`).

## Règles
- **Gmail = lecture seule ici** (`gmail.search`, `gmail.get`). Pour RÉPONDRE/écrire un mail → skill `mylab-email-rules` (himalaya, brouillon only). NE PAS chercher à envoyer via cette passerelle.
- Dates Calendar au format ISO 8601 avec fuseau (`2026-07-01T10:00:00+02:00`).
- Toujours vérifier `ok` avant d'annoncer un résultat à Yoann.

## Capacités
Voir `references/capabilities.md` (nom + params + exemple).
```

- [ ] **Step 2: Écrire `references/capabilities.md`** (le catalogue — params exacts + exemple par capacité)

```markdown
# Catalogue de capacités — passerelle workspace

| capability | params | retour (data) |
|---|---|---|
| `gmail.search` | `{query, limit?}` | `[{id,threadId,from,subject,date,snippet}]` |
| `gmail.get` | `{id}` | `{id,from,to,subject,date,body}` |
| `calendar.list` | `{timeMin?,timeMax?,limit?}` | `[{id,summary,start,end}]` |
| `calendar.create` | `{summary,start,end,description?,attendees?}` | `{id,htmlLink}` |
| `calendar.update` | `{id, ...champs}` | `{id,htmlLink}` |
| `drive.search` | `{query, limit?}` | `[{id,name,mimeType,modifiedTime,webViewLink}]` |
| `drive.get` | `{id}` | `{id,name,mimeType,webViewLink}` |
| `airtable.query` | `{base,table,filterByFormula?,limit?}` | `[{id,fields}]` |
| `airtable.upsert` | `{base,table,records:[{id?,fields}]}` | `[{id,fields}]` |

## Exemples
- Dispo cette semaine : `n8n_gateway.py calendar.list '{"timeMin":"2026-06-29T00:00:00+02:00","timeMax":"2026-07-05T23:59:59+02:00"}'`
- Créer un RDV : `n8n_gateway.py calendar.create '{"summary":"Appel client X","start":"2026-07-02T14:00:00+02:00","end":"2026-07-02T14:30:00+02:00"}'`
- Chercher un fichier : `n8n_gateway.py drive.search '{"query":"name contains '\''devis'\''","limit":5}'`
- Lire une base : `n8n_gateway.py airtable.query '{"base":"appXXXX","table":"Clients","limit":10}'`
```

- [ ] **Step 3: Ajouter la ligne au routeur `SOUL.md`**

Dans la table « Où aller selon la demande », ajouter (après la ligne Workflows n8n) :
```markdown
| Agenda, RDV, dispo / Google Drive, fichier / Airtable, fiche / lire un mail (recherche) | skill `workspace` (passerelle n8n — `n8n_gateway.py`) |
```

- [ ] **Step 4: Redémarrer + test d'intention (modèle)**

```bash
hermes gateway restart
```
Puis via Telegram/CLI Hermes : « Hermes, quelles sont mes dispos le 1er juillet ? » → le modèle doit choisir le skill `workspace` et appeler `calendar.list`. Vérifier la réponse.
Expected : Hermes appelle `n8n_gateway.py calendar.list ...` et restitue les events (ou « aucun »).

- [ ] **Step 5: Commit**
```bash
cd "C:/Users/MyLab/AppData/Local/hermes" && git add skills/workspace/SKILL.md skills/workspace/references/capabilities.md SOUL.md && git commit -m "feat(workspace): skill catalogue + routeur SOUL.md"
```

---

### Task 9: Recette bout-en-bout + mémoire

But : valider chaque capacité depuis Hermes en conditions réelles et capitaliser.

**Files:**
- Modify : (aucun code) — éventuellement `skills/workspace/NOTES-prereqs.md` (résultats recette).
- Create : `C:\Users\MyLab\.claude\projects\d--Projets-mylab-vs-code-be-yours-mylab\memory\hermes-workspace-gateway.md` (+ ligne dans `MEMORY.md`).

**Interfaces:**
- Consumes : tout ce qui précède.

- [ ] **Step 1: Recette des 9 capacités**

Lancer chaque test bout-en-bout (réutiliser les `test_gateway_*.py`) avec le token exporté :
```bash
for t in ping gmail calendar drive airtable; do python skills/workspace/scripts/test_gateway_$t.py || echo "ECHEC $t"; done
```
Expected : tous `[OK]`, aucun `ECHEC`. Nettoyer les données de test (event Calendar, ligne Airtable).

- [ ] **Step 2: Vérifier la non-régression du routage Qwen**

Poser 3 demandes non-workspace à Hermes (stock, email-réponse, OF) et confirmer qu'il route encore correctement (le nouveau skill n'a pas cannibalisé les intentions existantes). Si collision → resserrer les `trigger` de `SKILL.md`.

- [ ] **Step 3: Écrire la mémoire**

Créer `memory/hermes-workspace-gateway.md` (type `reference`) : archi passerelle, `WEBHOOK_URL`, où vit le token (`.env` + `env_passthrough`), catalogue v1, pièges (cred IDs, `responseMode:responseNode`, Gmail lecture-only). Lier `[[hermes-local-setup]]` et `[[hermes-local-email-drafts]]`. Ajouter la ligne d'index dans `MEMORY.md`.

- [ ] **Step 4: Commit final Hermes**
```bash
cd "C:/Users/MyLab/AppData/Local/hermes" && git add -A && git commit -m "test(workspace): recette bout-en-bout passerelle v1" && git push
```

---

## Self-Review (couverture spec)

- Google Workspace + Airtable + n8n, lecture + écriture → Tasks 3-6 (Gmail lecture, Calendar r/w, Drive lecture, Airtable r/w). ✔
- Passerelle 1 outil / pas de bloat MCP → un seul script `n8n_gateway.py` + 1 ligne SOUL.md (Tasks 7-8). ✔
- Secrets confinés n8n + token webhook → Task 2 (IF token/401), Task 7 (`.env` + `env_passthrough`). ✔
- JSON normalisé `{ok,data,error}` + exit code honnête → contrat posé Task 2, appliqué partout. ✔
- Gmail lecture-only / envoi reste himalaya → contrainte globale + SKILL.md règle (Task 8). ✔
- Tests par branche + bout-en-bout → un `test_gateway_*.py` par service + recette Task 9. ✔
- Pièges Windows (emoji print, exit code) → contrainte globale + script Task 7. ✔

**Note d'exécution :** Task 1 (recon credentials + instance n8n) débloque tout le reste — à faire en premier, manuellement si besoin. Les nœuds n8n natifs exigent les `CRED_IDS` réels ; si une cred Google/Airtable manque dans n8n, la créer dans l'UI avant Task 3+.
