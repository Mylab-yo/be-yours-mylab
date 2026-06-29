---
name: mylab-rag
description: "Interroge la base de connaissances documentaire MyLab (RAG AnythingLLM) : retrouve les passages pertinents dans les documents uploadés (procédures, fiches techniques, specs fournisseurs, notes internes, contrats). Use when: cherche dans la base de connaissances, que dit la doc sur, consulte la KB, base documentaire, retrouve l'info sur, documentation MyLab, fiche technique, procédure documentée, what does the doc say, RAG."
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [rag, knowledge-base, anythingllm, documentation, mylab]
---

# MyLab RAG — Recherche dans la base de connaissances documentaire

## Runtime (Hermes)

Tu tournes dans l'agent Hermes (VPS). Les credentials sont déjà dans l'environnement
(`/opt/data/.env` → `os.environ`) — **ne jamais les hardcoder ni les afficher** :
`ANYTHINGLLM_URL`, `ANYTHINGLLM_API_KEY`, `ANYTHINGLLM_WORKSPACE`. `requests` est disponible.

## Quand l'utiliser

Quand la question porte sur le **contenu de documents MyLab** uploadés dans la base
(procédures, specs produit, fiches/contrats fournisseurs, notes internes…).

- **NE PAS** utiliser pour des données live Shopify/Odoo (commandes, clients, stock,
  factures) → c'est `check-order` / `check-customer` / les autres skills métier.
- **NE PAS** utiliser pour ce que tu sais déjà via ta mémoire courte.

## Principe : récupération, pas génération externe

La base renvoie les **passages pertinents** des documents. C'EST TOI (Hermes) qui rédiges
la réponse à partir de ces passages, en **citant le document source**. Tu restes le cerveau —
tu ne délègues pas la rédaction. N'invente rien qui ne soit pas dans les passages renvoyés.

## Procédure

### Étape 1 — Recherche vectorielle dans la base

```python
import os, requests

BASE = os.environ['ANYTHINGLLM_URL'].rstrip('/')
KEY  = os.environ['ANYTHINGLLM_API_KEY']
WS   = os.environ['ANYTHINGLLM_WORKSPACE']

query = "..."  # la question de l'utilisateur reformulée en requête de recherche (mots-clés + intention)

r = requests.post(
    f"{BASE}/api/v1/workspace/{WS}/vector-search",
    headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    json={"query": query, "topN": 6},
    timeout=30,
)
data = r.json() if r.ok else {}
results = data.get("results", []) if isinstance(data, dict) else []
```

### Étape 2 — Extraire les passages + leur source

Chaque résultat ressemble à `{"text": "...", "score": 0.xx}`. Le `text` commence souvent par
un bloc `<document_metadata>` qui contient `sourceDocument:` (le nom du fichier) — sers-t'en
comme **citation**.

```python
passages = []
for res in results:
    txt = res.get("text", "") or ""
    src = "document"
    if "sourceDocument:" in txt:
        src = txt.split("sourceDocument:", 1)[1].split("\n", 1)[0].strip()
    body = txt.split("</document_metadata>", 1)[-1].strip() if "</document_metadata>" in txt else txt
    passages.append({"source": src, "score": res.get("score"), "text": body})
```

### Étape 3 — Répondre

- **Si `passages` non vide** : rédige une réponse concise en français **à partir des passages
  uniquement**, et cite la/les source(s) (`source`). Si plusieurs passages se contredisent,
  signale-le plutôt que de trancher au hasard.
- **Si vide** : dis clairement que la base de connaissances ne contient rien sur ce sujet.
  Elle est peut-être encore vide — les documents s'uploadent dans le workspace **« MyLab KB »**
  sur https://rag.mylab-shop.com (UI AnythingLLM).

## Variante — réponse déjà rédigée par la RAG (optionnel)

Si l'utilisateur veut explicitement une réponse synthétisée par la base elle-même
(modèle Gemini du workspace, avec ses propres citations) plutôt que les passages bruts :

```python
r = requests.post(
    f"{BASE}/api/v1/workspace/{WS}/chat",
    headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    json={"message": query, "mode": "query"},   # mode "query" = répond UNIQUEMENT depuis les docs
    timeout=60,
)
answer = r.json().get("textResponse", "") if r.ok else ""
```

Par défaut **préfère `vector-search`** (Étapes 1–3) : tu gardes le contrôle de la rédaction et
de la langue. N'utilise `/chat` que sur demande explicite d'une réponse « clé en main ».
