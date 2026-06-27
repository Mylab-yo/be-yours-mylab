# Design — Passerelle workspace Hermes local via n8n

**Date :** 2026-06-27
**Auteur :** Yoann + Claude
**Statut :** validé, prêt pour plan d'implémentation

## Problème

Hermes local (agent NousResearch, backend Qwen via llama-swap) doit pouvoir
accéder à la suite workspace de travail : **Google Workspace (Gmail, Calendar,
Drive), Airtable, et n8n**. L'utilisateur veut un accès **lecture + écriture
complète**.

Contrainte directrice (cf. mémoire `hermes-local-setup`) : le modèle local est
**faible**. Rebrancher 3 gros MCP (~60 outils cumulés) sur Qwen recrée
exactement le **bloat d'outils** qui dégrade le routage — raison pour laquelle
les MCP ont été retirés (`mcp_servers: {}`). Le précédent MCP Gmail était en
plus instable (« Premature close »). Le principe acté : **surface d'outils
petite, précision déportée sur des scripts/sources déterministes**.

## Solution retenue : n8n comme passerelle (1 seul outil)

Hermes ne voit qu'**un seul mécanisme** (« appeler la passerelle workspace »).
n8n — qui porte déjà l'OAuth natif Google + Airtable — fait toute
l'orchestration multi-service. Les secrets et la complexité restent dans n8n ;
Qwen ne route que l'intention.

Variante de granularité retenue : **A — webhook unique + vocabulaire de
capacités** (un seul workflow n8n avec un nœud Switch sur le champ `capability`).
Écartées : B (un workflow/webhook par capacité — trop d'URLs à maintenir) et
C (n8n MCP Server Trigger — réintroduit un client MCP dans Hermes, ce qui a été
désactivé exprès et s'était montré instable).

## Architecture (flux)

```
Qwen (intention) → script n8n_gateway.py → POST webhook (token secret)
   → n8n "hermes-gateway" [Switch sur capability]
        ├─ gmail.*    (nœud Gmail natif)
        ├─ calendar.* (nœud Google Calendar natif)
        ├─ drive.*    (nœud Google Drive natif)
        └─ airtable.* (nœud Airtable natif)
   → Respond to Webhook : {ok, data, error} → script → modèle
```

## Composants

1. **Workflow n8n `hermes-gateway`**
   - Trigger : Webhook `POST`, sécurisé par header `X-Hermes-Token`.
   - Corps attendu : `{ "capability": "<nom>", "params": { ... } }`.
   - Nœud **Switch** sur `capability` → une branche par préfixe de service.
   - Chaque branche utilise le nœud natif n8n correspondant (Gmail / Google
     Calendar / Google Drive / Airtable), qui porte les credentials OAuth.
   - Nœud **Respond to Webhook** renvoyant systématiquement un JSON normalisé
     `{ ok: bool, data: any, error: string|null }`.
   - Les OAuth Google et Airtable **restent confinés dans n8n**.

2. **Script `n8n_gateway.py`** (côté Hermes, nouveau skill `workspace`)
   - POST le payload `{capability, params}` vers le webhook.
   - Lit le token depuis l'**environnement** (jamais dans le contexte du modèle).
   - Renvoie le JSON brut de n8n ; convertit timeout / HTTP ≠ 200 / erreur
     réseau en message lisible.
   - **Exit code honnête** : 0 = succès, ≠ 0 = échec réel (leçon `draft-creator` :
     pas d'exit code menteur). Pas d'emoji dans les `print()` (console Windows
     cp1252).

3. **Skill `workspace`** (Hermes)
   - Documente le **catalogue de capacités** : pour chaque capacité, son nom,
     ses params attendus, un exemple d'appel.
   - C'est l'**offload de précision** : le modèle remplit les params en lisant
     le skill, pas en devinant des schémas MCP.

4. **Routeur `SOUL.md`** (toujours en contexte)
   - Quelques lignes intention → capacité, ex :
     - « chercher un mail / fil client » → `gmail.search`
     - « dispo / événements agenda » → `calendar.list`
     - « créer un RDV » → `calendar.create`
     - « trouver un fichier Drive » → `drive.search`
     - « lire / écrire une fiche Airtable » → `airtable.query` / `airtable.upsert`

## Catalogue de capacités v1

Lecture + écriture complète :

| Capacité | Service | Type |
|----------|---------|------|
| `gmail.search` | Gmail | lecture |
| `gmail.get` | Gmail | lecture |
| `calendar.list` | Calendar | lecture |
| `calendar.create` | Calendar | écriture |
| `calendar.update` | Calendar | écriture |
| `drive.search` | Drive | lecture |
| `drive.get` | Drive | lecture |
| `airtable.query` | Airtable | lecture |
| `airtable.upsert` | Airtable | écriture |

**Exception Gmail (règle existante préservée) :** l'**envoi** de mail ne passe
PAS par la passerelle. Gmail reste en **lecture seule** via la passerelle ;
l'écriture/rédaction d'email continue via le chemin existant
**himalaya / draft-creator « brouillon only, jamais d'envoi »** (cf. mémoire
`hermes-local-email-drafts`). La passerelle ne court-circuite pas cette règle.

## Gestion d'erreur

- n8n renvoie toujours `{ok:false, error:"..."}` plutôt que de planter la
  requête (branche d'erreur / `Respond to Webhook` en sortie d'erreur).
- Le script `n8n_gateway.py` convertit timeout / HTTP ≠ 200 en message lisible
  et exit code ≠ 0.
- Succès = exit 0 (pas d'exit code menteur).

## Sécurité

- Token webhook obligatoire (header `X-Hermes-Token`) — sinon `401`.
- Secrets / OAuth Google + Airtable confinés dans n8n, **jamais exposés au
  modèle**.
- Token Hermes lu depuis l'environnement, pas dans le prompt ni le repo
  (`$HERMES_HOME` a un `.gitignore` en liste blanche excluant les secrets).
- Webhook n8n non listé publiquement.

## Tests

- Par branche n8n : `prepare_test_pin_data` + exécution du workflow pour valider
  chaque capacité (entrée → sortie normalisée).
- Bout-en-bout : un appel réel `n8n_gateway.py` par capacité du catalogue v1,
  en vérifiant le JSON `{ok,data,error}` et l'exit code.
- Cas d'erreur : token absent → 401 lisible ; capacité inconnue → `{ok:false}`.

## Hors périmètre (YAGNI)

- Odoo (déjà câblé via scripts XML-RPC, `scripts/odoo/`).
- Envoi de mail via la passerelle (reste himalaya « brouillon only »).
- Délégation au modèle fort VPS (option écartée pour cette itération).
- Pagination / streaming de gros résultats — à voir si un besoin réel émerge.
