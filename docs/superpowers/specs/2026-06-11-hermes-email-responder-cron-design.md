# Spec — Auto-drafting des emails pro via cron Hermes

**Date** : 2026-06-11
**Auteur** : Yoann Durand (via Claude Code)
**Statut** : approuvé pour planification

## Problème

Yoann utilise actuellement **Cowork** pour auto-drafter ses réponses aux emails pro MY.LAB, mais n'en est pas satisfait. Il existe déjà un skill mûr — `skills/mylab-email-responder/SKILL.md` — qui encode toute la KB MY.LAB, le ton, les règles de rédaction et la création de brouillons Gmail. Mais ce skill se lance **à la main** dans Claude Desktop. L'objectif : l'**automatiser sur un cron Hermes** (agent déjà déployé sur le VPS) pour que les brouillons de réponse apparaissent seuls dans Gmail, prêts à relire et envoyer.

## Objectif

Un cron Hermes qui, plusieurs fois par jour en semaine, scanne les emails entrants ciblés, rédige une réponse de qualité avec la KB MY.LAB, la dépose **en brouillon** dans le bon thread Gmail, et notifie Yoann sur Telegram. Yoann garde toujours la main : il relit et envoie.

## Décisions de design (verrouillées)

| Sujet | Décision |
|---|---|
| Comportement | **Brouillon uniquement** — jamais d'envoi automatique |
| Périmètre | Emails **non-lus** des labels Gmail `URGENT` et `Commandes & Devis` uniquement |
| Fréquence | **3×/jour, lun-ven** : 9h, 13h, 17h (Europe/Paris) |
| Notification | **Résumé Telegram** sur `@mylab_hermes_bot` après chaque passage |
| Accès Gmail | **OAuth Gmail dédié** dans le `.env` Hermes (scope `gmail.modify`) |
| Re-draft thread | **Un thread = un brouillon, jamais re-drafté** (v1). Idempotence via label `Hermes-Drafted` |
| Modèle Claude | **Opus** (qualité max ; volume faible → coût négligeable). Id exact confirmé via skill `claude-api` au build |
| Orchestration | **Script Python déterministe** (`--no-agent --script`), pas le mode agent Hermes. Claude appelé uniquement comme API de rédaction |

## Architecture

### Composant unique : `email_responder.py`

Un script Python déterministe lancé par le cron Hermes, sur le modèle éprouvé de `morning_brief.py` (cf. [[hermes-agent-vps]]). Claude n'intervient **que** pour la rédaction (1 appel API par mail) ; toute l'orchestration (Gmail I/O, idempotence, notification) est déterministe et gratuite.

### Flux à chaque passage

1. **Scan Gmail** — 2 requêtes de recherche :
   - `label:URGENT is:unread -label:Hermes-Drafted`
   - `label:"Commandes & Devis" is:unread -label:Hermes-Drafted`

   Le filtre `-label:Hermes-Drafted` garantit qu'un mail déjà traité n'est jamais re-drafté, même s'il reste non-lu entre 2 runs.
2. **Lecture du thread complet** (`users.threads.get`) — contexte conversationnel entier, pas seulement le dernier message.
3. **Rédaction** — 1 appel API Claude (Opus) par mail. System prompt = KB MY.LAB + règles de ton + exemples, extraits de `SKILL.md`. Sortie : corps de réponse en HTML simple (pas de Markdown).
4. **Signature** — bloc HTML MY.LAB ajouté en fin de body après `<br><br>` (source : `docs/signature-email.html`, embarqué au déploiement).
5. **Création du brouillon** — `users.drafts.create` avec `threadId`, `To` = expéditeur original, `In-Reply-To`/`References` corrects pour rester dans le thread. **Jamais** `users.messages.send`.
6. **Tag d'idempotence** — applique le label `Hermes-Drafted` au thread (`users.threads.modify`).
7. **Résumé Telegram** — `📥 N brouillons prêts` + une ligne par mail (expéditeur · sujet · résumé court de la réponse).

### Source de vérité KB (anti-drift)

La KB ne doit exister qu'**une fois**. Le script de **déploiement** (`add_email_responder.py`) extrait les sections KB + règles de rédaction + exemples depuis `skills/mylab-email-responder/SKILL.md` et les écrit dans `/root/.hermes/scripts/email_responder_prompt.md`, monté dans le container.

→ Workflow de maintenance : Yoann édite `SKILL.md` (source de vérité unique, déjà utilisée par Claude Desktop) → re-run du déploiement → le cron suit. Aucune copie divergente.

> Note : la signature est elle aussi extraite de `docs/signature-email.html` au déploiement (déjà la source de vérité, cf. [[gmail-signature]]).

## Garde-fous

- **Draft-only en dur** : le script n'appelle jamais l'endpoint *send*. Le scope OAuth `gmail.modify` autorise lecture + labels + brouillons mais le code n'envoie jamais. Double sécurité (scope + code).
- **Cap anti-coût** : maximum **15 mails traités par run**. Au-delà → loggé et signalé dans le résumé Telegram (« 15 traités, X restants »). Pas de troncature silencieuse.
- **Isolation des erreurs** : `try/except` par mail. Un échec (rédaction, Gmail) est sauté et reporté dans le résumé Telegram ; le run continue sur les autres.
- **Allowlist labels** : uniquement les 2 labels ciblés. Jamais toute la boîte → pas de drafting sur du démarchage, des newsletters ou des notifs.
- **Erreurs globales** → `errors.log` + message Telegram (cohérent avec le pattern morning brief).

## Setup one-time (hors run quotidien)

1. **OAuth Gmail** : générer un refresh token (`scope=https://www.googleapis.com/auth/gmail.modify`, compte `yoann@mylab-shop.com`) via le flow OAuth existant (`scripts/oauth_receiver.py` + client OAuth du projet Google Cloud `mylab-design-studio`). Ajouter le scope Gmail au client OAuth, ou créer un client dédié.
   - Stocker dans le `.env` Hermes : `GMAIL_REFRESH_TOKEN`, `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`.
2. **Label Gmail** : créer le label `Hermes-Drafted` (via API au premier run si absent, ou manuellement).
3. **Vérifier les noms réels des labels** `URGENT` et `Commandes & Devis` (encodage du token de recherche Gmail) avant de figer les requêtes.
4. **Cron Hermes** :
   ```bash
   docker exec hermes-gateway hermes cron create \
     "Auto-draft emails pro MY.LAB" \
     --no-agent --script email_responder.py --deliver telegram \
     --name email-responder --schedule "0 9,13,17 * * 1-5"
   ```

## Fichiers

| Fichier | Emplacement | Rôle |
|---|---|---|
| `add_email_responder.py` | `scripts/hermes/` (repo) | Déploiement idempotent : extrait le prompt depuis `SKILL.md` + signature depuis `signature-email.html`, upload `email_responder.py` + `email_responder_prompt.md` sur le VPS, crée/maj le cron |
| `email_responder.py` | `/root/.hermes/scripts/` (VPS, monté) | Le worker : Gmail scan → rédaction Claude → brouillon → tag → Telegram |
| `email_responder_prompt.md` | `/root/.hermes/scripts/` (VPS, monté) | KB + règles générées depuis `SKILL.md` (ne pas éditer à la main) |

## Dépendances

- **Container Hermes** : `hermes-gateway` (cf. [[hermes-agent-vps]]). `ANTHROPIC_API_KEY` déjà présent dans `.env`.
- **Librairies Python** dans le container : `google-api-python-client` + `google-auth` (pour Gmail), `anthropic` (ou appel HTTP direct), `requests`. À vérifier/installer dans l'image ou via `pip` au build.
- **VPS** : `root@82.25.112.124`, accès SSH paramiko (cf. [[reference_vps_ssh_python]]).

## Hors périmètre (YAGNI v1)

- Envoi automatique des réponses (même « confiance haute »).
- Re-drafting sur relance client dans un thread déjà traité.
- Drafting hors des 2 labels ciblés.
- Tri intelligent / classification de tous les non-lus.
- Apprentissage des corrections de Yoann sur les brouillons.

## Critères de succès

1. À 9h/13h/17h en semaine, les emails non-lus des 2 labels reçoivent un brouillon de réponse pertinent, dans le bon thread, avec la signature MY.LAB.
2. Aucun mail n'est drafté 2×.
3. Aucun envoi automatique.
4. Yoann reçoit un résumé Telegram lisible après chaque passage.
5. Éditer `SKILL.md` + re-déployer suffit à mettre à jour le comportement de rédaction.

## Mémoire liée

- [[hermes-agent-vps]] — infra Hermes, pattern cron, commandes Docker
- [[gmail-signature]] — bloc signature à embarquer
- [[reference_vps_ssh_python]] — accès SSH au VPS
- [[reference_api_keys]] — gestion des clés
