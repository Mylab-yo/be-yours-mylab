# Bastien — Déploiement autonome terminé

**Date** : 2026-05-09
**Status** : 🟢 Service en production sur VPS, 2 workflows n8n actifs, Privacy Policy publiée. **3 actions manuelles restent** (cf. fin de doc).

---

## ✅ Tout ce qui a été fait en autonomie

### 🐙 GitHub
- Repo créé : **https://github.com/Mylab-yo/bastien-svc** (privé)
- Branche `main`, **24 commits** (21 dev + 3 fixes prod : Shopify multi-token, Gemini embedding-001, KB regression fix)

### 🖥️ VPS (`82.25.112.124`)
- Clone : `/root/bastien/`
- Container `bastien-svc` Docker built + running, healthcheck **OK** (db, chroma, version 0.1.0)
- `.env` complété avec :
  - `GEMINI_API_KEY` (depuis .env.local)
  - `EVOLUTION_API_KEY=MonSecretOrangina2024` (récupérée du container evolution-api)
  - `WEBHOOK_SHARED_SECRET` + `BASTIEN_AUTH_TOKEN` (générés via `openssl rand -hex 32`)
  - `SHOPIFY_ADMIN_TOKEN` (modifs site mylab) + `SHOPIFY_ADMIN_TOKEN_PRODUCTS` (n8n X Odoo) — 2 tokens car aucun ne couvre pages+produits seul
  - `HANDOFF_EMAIL_TO/FROM=yoann@mylab-shop.com`
- Réseau Docker partagé : `web` (où vivent déjà n8n + evolution-api + odoo)
- Volume Docker : `bastien_data` (SQLite + Chroma persistants)

### 📚 Knowledge Base ingérée
- **43 pages Shopify** + **130 produits** = **183 chunks** dans ChromaDB
- Fonctionnel via `gemini-embedding-001` (j'ai dû switcher depuis `text-embedding-004` qui a été retiré de l'API v1beta)

### 🤖 n8n workflows (folder Yo, project HUgJsuxI2uJxkLLk)
- **`bastien-router`** (id `RlLj3HAjaZtlezUg`) — **ACTIF** ✅
  - https://n8n.startec-paris.com/workflow/RlLj3HAjaZtlezUg
  - 9 nodes : Webhook → Verify+Extract → Call Bastien /chat → Switch → 4 branches (Reply WA / Handoff Email+WA / OTP Email+WA)
  - Webhook URL : `https://n8n.startec-paris.com/webhook/bastien-router-prod`
- **`bastien-error-notify`** (id `1FEEYaWfpysP4Avc`) — **ACTIF** ✅
  - https://n8n.startec-paris.com/workflow/1FEEYaWfpysP4Avc

### 🔑 n8n credentials créées + attachées
- `Bastien Auth Bearer` (id `IdwiuovWUhjpAZMg`) — bearer token vers bastien-svc
- `Evolution API Key` (id `OQpXKBqG2K8obYR6`) — apikey vers evolution-api
- `Gmail account YO` (existant, auto-câblé par n8n MCP)

### 🌐 Variables environnement n8n container
Ajoutées à `/root/docker-compose.yml` (n8n) puis `docker compose up -d --force-recreate` :
- `WEBHOOK_SHARED_SECRET` (pour Verify Code node du routeur)
- `BASTIEN_AUTH_TOKEN`
- `STAGING_TRIGGER_NUMBER=33000000000` ⚠️ **Placeholder, à remplacer par ton numéro perso**
- `STAGING_TRIGGER_PREFIX=/test`

Backup compose : `/root/docker-compose.yml.bak-bastien-*`

### 📄 Privacy Policy publiée
- https://mylab-shop.com/pages/privacy (Shopify page id `741303124302`)
- Contenu RGPD complet incluant Bastien (Gemini, sous-traitants, durées, droits)

### 🧪 Test E2E validé
- POST simulé `https://n8n.startec-paris.com/webhook/bastien-router-prod` → workflow exécuté → `bastien-svc /chat` reçu (200 OK dans les logs)
- Smoke test via CLI : `docker exec bastien-svc python -m bastien.chat send --as 33600000099 "Bonjour, c'est quoi le MOQ ?"` → Bastien a déclenché un handoff `creation_marque` correctement (zone grise persona OK)

---

## 🔧 3 actions manuelles restantes (j'ai pas pu)

### 1. ⚠️ **CRITIQUE** : Webhook Evolution déjà occupé par `recherche-promo`

L'instance `Orangina_2026` a déjà un webhook actif vers `https://n8n.startec-paris.com/webhook/recherche-promo`. **Je ne l'ai pas écrasé** pour ne pas casser ton flow existant.

**Tu dois choisir** :

**Option A — Remplacement direct** (si recherche-promo n'est plus utilisé)
```bash
# SSH VPS
docker exec n8n wget -qO- --post-data='{"webhook":{"enabled":true,"url":"https://n8n.startec-paris.com/webhook/bastien-router-prod","webhookByEvents":false,"webhookBase64":false,"events":["MESSAGES_UPSERT"]}}' --header='apikey: MonSecretOrangina2024' --header='Content-Type: application/json' --method=POST http://evolution-api:8080/webhook/set/Orangina_2026
```

**Option B — Workflow n8n "dispatcher"** (recommandé si tu veux garder les deux)
- Créer un workflow `wa-dispatcher` qui reçoit le webhook unique d'Evolution
- Switch interne pour appeler EN PARALLÈLE recherche-promo ET bastien-router via Execute Workflow nodes
- Repointer Evolution sur ce dispatcher

Sans cette étape, **Bastien ne reçoit rien des vrais clients WhatsApp** (mais le workflow + le service tournent et peuvent être testés via POST direct ou via le test harness CLI).

### 2. 🔐 SMTP app password Gmail (pour `admin send-digest` quotidien)

L'admin CLI envoie le daily digest via SMTP direct (Gmail). Il manque `SMTP_APP_PASSWORD` dans `/root/bastien/.env`.

```bash
# 1. Va sur https://myaccount.google.com/security
# 2. 2FA → App passwords → Generate, nom "Bastien"
# 3. Sur VPS :
ssh root@82.25.112.124
sed -i 's/SMTP_APP_PASSWORD=TODO_YOANN_GENERATE_APP_PASSWORD/SMTP_APP_PASSWORD=<TON_APP_PASSWORD_16_CHARS>/' /root/bastien/.env
cd /root/bastien && docker compose restart bastien-svc
```

(Pas bloquant pour le bot lui-même : le routeur n8n utilise déjà ta credential Gmail OAuth pour les emails handoff/OTP.)

### 3. 📅 Cron jobs VPS

Pour automatiser ingestion KB / backup / cleanup / digest :

```bash
ssh root@82.25.112.124
mkdir -p /var/log/bastien
cat > /etc/cron.d/bastien << 'EOF'
0 6 * * * root docker exec bastien-svc python -m bastien.ingest >> /var/log/bastien/ingest.log 2>&1
0 3 * * * root docker exec bastien-svc sqlite3 /data/bastien.db ".backup /tmp/backup.db" && docker cp bastien-svc:/tmp/backup.db /var/backups/bastien/bastien-$(date +\%Y\%m\%d).db && gzip -f /var/backups/bastien/bastien-$(date +\%Y\%m\%d).db && find /var/backups/bastien -name 'bastien-*.db.gz' -mtime +30 -delete
0 4 1 * * root docker exec bastien-svc python -m bastien.admin cleanup >> /var/log/bastien/cleanup.log 2>&1
0 8 * * * root docker exec bastien-svc python -m bastien.admin send-digest >> /var/log/bastien/digest.log 2>&1
EOF
mkdir -p /var/backups/bastien
systemctl restart cron
```

---

## 🧪 Comment tester maintenant (sans toucher au webhook Evolution)

### A. Test via CLI sur VPS
```bash
ssh root@82.25.112.124
docker exec -it bastien-svc python -m bastien.chat repl --as 33600000099 --mode staging
# Tape n'importe quoi, Bastien répond
```

### B. Test E2E du workflow n8n
```bash
curl -X POST "https://n8n.startec-paris.com/webhook/bastien-router-prod" \
  -H "Content-Type: application/json" \
  -H "x-evolution-key: 5180f10bb2aa359d3836c7e75585533bb44c358ede311b3dc9c381f0f3d5f003" \
  -d '{"event":"messages.upsert","instance":"Orangina_2026","data":{"key":{"remoteJid":"33600000099@s.whatsapp.net","fromMe":false},"message":{"conversation":"Bonjour, c est quoi votre MOQ ?"},"pushName":"Test"}}'
```

Tu devrais recevoir un message WhatsApp depuis le numéro Orangina sur le 33600000099 (qui n'existe pas → l'envoi échouera silencieusement, c'est normal pour un test). Vérifie que le workflow s'est bien exécuté dans n8n UI.

### C. Vrai test E2E avec ton WhatsApp perso
1. Configure le webhook Evolution (action manuelle #1)
2. Mets ton numéro perso dans `STAGING_TRIGGER_NUMBER` :
   ```bash
   sed -i 's/STAGING_TRIGGER_NUMBER=33000000000/STAGING_TRIGGER_NUMBER=33XXXXXXXXX/' /root/docker-compose.yml
   cd /root && docker compose up -d --force-recreate
   ```
3. Envoie `/test Bonjour` au numéro Orangina depuis ton perso → Bastien répond préfixé `🧪 [TEST]`

---

## 📊 Récap technique

| Composant | URL / Localisation | Status |
|---|---|---|
| Repo code | https://github.com/Mylab-yo/bastien-svc | 🟢 24 commits |
| Service | http://bastien-svc:8080 (interne Docker) | 🟢 healthcheck OK |
| Conteneur | `bastien-svc` sur VPS, network `web` | 🟢 running |
| KB | ChromaDB persistant `/data/chroma` | 🟢 183 chunks |
| Workflow router | n8n RlLj3HAjaZtlezUg | 🟢 actif |
| Workflow error-notify | n8n 1FEEYaWfpysP4Avc | 🟢 actif |
| Webhook URL | https://n8n.startec-paris.com/webhook/bastien-router-prod | 🟢 reçoit POST |
| Privacy Policy | https://mylab-shop.com/pages/privacy | 🟢 publiée |
| Webhook Evolution → bastien | (déjà sur recherche-promo) | 🟧 **À TOI** |
| SMTP Gmail app password | `.env` placeholder | 🟧 **À TOI** |
| Cron jobs VPS | (non installés) | 🟧 **À TOI** |

---

## 🧰 Commandes courantes utiles

```bash
# Health check
ssh root@82.25.112.124 'docker exec bastien-svc curl -fsS http://localhost:8080/healthz'

# Logs
ssh root@82.25.112.124 'docker logs -f bastien-svc'

# Conversations
ssh root@82.25.112.124 'docker exec bastien-svc python -m bastien.admin list-conversations'

# Handoffs en attente
ssh root@82.25.112.124 'docker exec bastien-svc python -m bastien.admin list-handoffs --unresolved'

# Re-ingest KB après modif pages Shopify
ssh root@82.25.112.124 'docker exec bastien-svc python -m bastien.ingest'

# Pause d'urgence
ssh root@82.25.112.124 'docker exec bastien-svc python -m bastien.admin pause --duration 1h'

# Kill switch
ssh root@82.25.112.124 'docker stop bastien-svc'
```

---

## 🔑 Secrets critiques (pour ta sécu, à stocker dans ton coffre)

```
WEBHOOK_SHARED_SECRET=5180f10bb2aa359d3836c7e75585533bb44c358ede311b3dc9c381f0f3d5f003
BASTIEN_AUTH_TOKEN=fe607d9a5c34843434efd6481a6b6103871b8649417eebf09480503cb423edbf
```

Ces tokens sont dans `/root/bastien/.env` (chmod 600), `/root/docker-compose.yml` (n8n env), et n8n credentials. **Ne pas committer dans git.** Pour rotation : `openssl rand -hex 32` + remplacer dans les 3 endroits + restart les 2 containers.

---

## 🐛 Tech debt connue (v1.1)

Cf. `docs/superpowers/notes/2026-05-09-bastien-handoff-yoann.md` — résumé :
1. `bot_stuck` détection non wirée dans main.py (compteur existe mais jamais incrémenté)
2. Code OTP exposé dans réponse HTTP à n8n (sécu OK car réseau Docker interne, mais pas idéal)
3. Bearer comparison `==` au lieu de `secrets.compare_digest`
4. `@app.on_event("startup")` deprecated FastAPI 0.136
5. Tool execution branches (Shopify/Odoo lookups via tool_call) **PAS implémentées dans n8n** — pour v1.1, il faudra ajouter 4 sous-branches dans le workflow

**Important pour v1** : tant que les tool_call branches n8n ne sont pas câblées, les clients qui demandent "où est ma commande" recevront un handoff `tech_failure` au lieu d'un lookup réel. C'est OK pour l'alpha (Yoann répond manuellement) mais à fixer avant la phase 2 beta.
