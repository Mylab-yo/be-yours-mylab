# Session 13/07/2026 — Hermes : abo Max impossible, vrai coupable = Opus, MAJ v0.18.2

## Point de départ

Yoann voulait « brancher son abonnement Claude Max » sur Hermes pour arrêter de payer l'API au token
(~230 $ sur 1,5 mois — ce qui l'avait fait débrancher l'agent le 23/06).

## Verdict : impossible, et refusé

- Hermes = agent **NousResearch** (container `hermes-gateway`), **pas** Claude Code. Il tape l'API
  Anthropic en direct avec une **clé API** (`x-api-key`, `config.yaml` → `model.api_key`).
- Un **abonnement Max n'est pas une clé API** : il ne fonctionne que dans les apps Claude + Claude Code.
  Vrai aussi **en local**, et **via OpenRouter** (qui *revend* l'accès Anthropic avec marge, et exige une
  clé API même en « BYOK »).
- Seul « pont » technique : router un token OAuth Claude Code (`claude setup-token`) en
  `Authorization: Bearer` via un proxy type `claude-code-router`. **Refusé** : violation des CGU +
  risque de suspension du compte Anthropic. Tourner en local ne cache rien côté serveur.
- Anthropic n'offre **aucun abonnement API à tarif fixe**. API = au token, point.

## La vraie découverte : c'était Opus, pas Sonnet

Console → Coût, clé `hermes-agent-vps`, mois écoulé : **230,75 $ dont ~85 % en Claude Opus 4.6**
(journées à 70 / 37 / 42 $ les 13-17 juin). Yoann croyait tourner sur Sonnet. Déjà corrigé en amont :
la config était repassée sur `claude-sonnet-4-6`.

Ratios (les 3 modèles ont le même rapport in/out 1:5 → multiplicateur exact quel que soit le mix) :

| Modèle | in/out /M | Même usage |
|---|---|---|
| Opus 4.6 (ce qui était facturé) | $5 / $25 | ~231 $ |
| **Sonnet 4.6** (actuel) | $3 / $15 | **~138 $ (−40 %)** |
| Haiku 4.5 (tout basculé) | $1 / $5 | ~46 $ (−80 %) — mais perte de qualité, à réserver à l'auxiliaire |

## Prompt caching : bloqué en v0.16.0, débloqué en v0.18.2

- **v0.16.0** routait Anthropic via l'endpoint **OpenAI-compat** (`/v1/chat/completions`, SDK OpenAI) à
  cause d'un « routing bug » — d'où le workaround `.env` `OPENAI_API_KEY = clé Anthropic`. Cet endpoint
  **n'expose pas `cache_control`** → **aucun caching possible**.
- **v0.18.2** (2026.7.7) — vérifiée dans une **image jetable AVANT** de l'appliquer :
  - SDK **`anthropic` 0.87 natif** (`agent/anthropic_adapter.py`, provider `base_url=https://api.anthropic.com`)
  - **prompt caching automatique** :
    - `run_agent.py:5302` → injecte `cache_control: {type: ephemeral}` sur le system prompt
    - `anthropic_adapter.py:1690` → cache le **tool schema** cross-session
    - `gateway/run.py` → garde-fous pour préserver le prefix caching (« ~10x more on providers with prompt caching »)
    - `slash_commands.py:1972` → indicateur `prompt_caching_enabled`

## MAJ appliquée (v0.16.0 → v0.18.2)

Procédure codifiée dans `scripts/hermes/update_hermes_image.py` :

1. **Pull de la nouvelle image par digest** → le tag `:latest` et le container qui tourne restent
   **intacts** ⇒ inspection sans aucun risque (c'est la clé de l'approche).
2. Backups : `config.yaml`, `.env`, `kanban.db`, `state.db` → `*.bak-pre-v0.18.2`.
3. `docker tag <digest> …:latest` puis `cd /root/hermes && docker compose up -d`.
4. Vérifs : version, `doctor`, `config show`, `skills list`, smoke test `hermes -z` → **OK**.

**Rollback** : `docker tag sha256:fb3fe8bd… nousresearch/hermes-agent:latest && cd /root/hermes && docker compose up -d`
+ restaurer les `*.bak-pre-v0.18.2`.

## Pièges rencontrés (à retenir)

- **`hermes migrate` ne gère QUE les modèles xAI** — ni les crons, ni la config. Ne pas compter dessus.
- **Le store des crons a changé** (`/opt/data/cron/`) → `hermes cron list` affiche 0 job après MAJ.
  **Mais rien n'a été perdu** : les crons étaient **déjà dormants avant** (email-responder `state: paused`
  depuis le 23/06 ; morning-brief supprimé plus tôt ; dernier output cron = 23/06 = arrêt d'Hermes pour
  cause de coût). ⚠️ Ne pas conclure trop vite à une régression — vérifier le store avant.
- **Ownership** : toute écriture SFTP dans `/root/.hermes` arrive root-owned → `chown 10000:10000`
  obligatoire (le gateway lit en `hermes`), sinon « Permission denied » au restart.
- **`/opt/data/.env` est bourré de secrets** (GMAIL/GOOGLE_WS `client_secret`, JWT n8n, SHOPIFY, ODOO,
  AIRTABLE, ANYTHINGLLM) → **redaction stricte obligatoire** avant tout `cat`. Un regex
  `API_KEY|TOKEN|secret` rate `*_CLIENT_SECRET` et `N8N_*` (à cause du chiffre). Cf. mémoire
  `feedback_debug_dumps_contain_secrets`.

## Nettoyage fait

- Workaround `OPENAI_API_KEY` retiré du `.env` (obsolète en routage natif) + chown + restart.
  Vérif : Anthropic intact, `OpenAI (STT/TTS) not set`, smoke test OK.
- `hermes doctor --fix` → symlink créé. Reste 1 « issue » cosmétique (clés d'intégrations optionnelles
  jamais utilisées : web search, Discord, feishu…).

## État final

| Sujet | Avant | Après |
|---|---|---|
| Version | v0.16.0 | **v0.18.2** |
| Routage Anthropic | hack OpenAI-compat | **natif (SDK anthropic 0.87)** |
| Prompt caching | impossible | **auto (system prompt + tool schema)** |
| Modèle | Opus 4.6 (→ 230 $) | **Sonnet 4.6** |
| `.env` | workaround bidouillé | **propre** |
| Crons | dormants depuis le 23/06 | dormants (**choix de Yoann**) |

## TODO

- 🔴 **Roter 2 secrets** exposés au transcript pendant l'inspection : Google OAuth `client_secret`
  (GOCSPX) + clé API n8n (JWT).
- Vérifier les **cache reads** dans la Console après quelques jours d'usage → chiffrer l'économie réelle
  du caching.
- Réactiver les crons si voulu : `add_morning_brief_v2.py` (brief 7-8h, script v2 déjà sur disque avec
  les mounts docker.sock + n8n) / `add_email_responder.py` (`0 9,13,17 * * 1-5`).
