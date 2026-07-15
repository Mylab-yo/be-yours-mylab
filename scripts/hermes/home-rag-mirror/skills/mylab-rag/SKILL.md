---
name: mylab-rag
description: "Interroge la base de connaissances documentaire MyLab (RAG AnythingLLM) : retrouve les passages pertinents dans les documents (procédures, fiches techniques, specs fournisseurs, notes internes, contrats). Use when: cherche dans la base de connaissances, que dit la doc sur, consulte la KB, base documentaire, retrouve l'info sur, documentation MyLab, fiche technique, procédure documentée, what does the doc say, RAG."
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [rag, knowledge-base, anythingllm, documentation, mylab]
---

# MyLab RAG — Recherche dans la base de connaissances documentaire

## Runtime (Hermes)

Les credentials sont dans l'environnement (`os.environ`) — **ne jamais les hardcoder ni les
afficher** : `ANYTHINGLLM_URL`, `ANYTHINGLLM_API_KEY`, `ANYTHINGLLM_WORKSPACE`. `requests` dispo.

> Sur ce Hermes maison, `ANYTHINGLLM_URL` pointe sur ton AnythingLLM **local**
> (ex. `http://127.0.0.1:3001`), tenu en miroir du VPS par `mirror_from_vps.py`.

## Quand l'utiliser

Quand la question porte sur le **contenu de documents MyLab** (procédures, specs, fiches/contrats
fournisseurs, notes internes). PAS pour des données live Shopify/Odoo, ni pour ta mémoire courte.

## Principe : récupération, pas génération externe

La base renvoie les **passages pertinents**. C'EST TOI qui rédiges la réponse à partir de ces
passages, en **citant le document source**. N'invente rien hors des passages renvoyés.

## Procédure

### Étape 1 — Recherche vectorielle

```python
import os, requests
BASE = os.environ['ANYTHINGLLM_URL'].rstrip('/')
KEY  = os.environ['ANYTHINGLLM_API_KEY']
WS   = os.environ['ANYTHINGLLM_WORKSPACE']
query = "..."  # la question reformulée en requête de recherche

r = requests.post(
    f"{BASE}/api/v1/workspace/{WS}/vector-search",
    headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    json={"query": query, "topN": 6},
    timeout=30,
)
data = r.json() if r.ok else {}
results = data.get("results", []) if isinstance(data, dict) else []
```

### Étape 2 — Extraire passages + source

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

- **Si `passages`** : réponds en français à partir des passages **uniquement**, en citant la/les source(s).
- **Si vide** : dis que la base ne contient rien sur ce sujet (elle est peut-être encore vide / le
  miroir n'a pas tourné — lance `mirror_from_vps.py`).
