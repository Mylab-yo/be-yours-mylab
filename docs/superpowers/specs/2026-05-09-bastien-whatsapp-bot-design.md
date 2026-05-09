# Bastien — Assistant WhatsApp MY.LAB (sous-projet 1/3)

**Date** : 2026-05-09
**Auteur** : Yoann Durand + Claude
**Statut** : Spec validée, prête pour implémentation
**Sous-projet** : 1/3 (bot conversationnel — fondation)

---

## 1. Contexte & objectifs

### 1.1 Problème

MY.LAB Shop reçoit des questions clients sur plusieurs canaux (email, formulaires, WhatsApp). Yoann gère seul le service client et n'est pas disponible 24/7. Une partie significative des questions sont répétitives (MOQ, contenances, prix catalogue, statut commande, statut devis) et pourraient être traitées automatiquement, libérant du temps pour les sujets à forte valeur (création de marque, négociation, formulation).

### 1.2 Objectif

Mettre en place un assistant conversationnel WhatsApp nommé **Bastien**, capable de :
- Répondre aux questions générales prospects/clients en s'appuyant sur le catalogue MY.LAB et la FAQ
- Effectuer 4 lookups dynamiques (commande Shopify, devis Odoo, tracking DPD, stock)
- Identifier intelligemment quand passer la main à Yoann (handoff par email)
- Fonctionner 24/7 avec persona chaleureuse, sans se présenter spontanément comme IA mais sans mentir si questionné directement

### 1.3 Périmètre — décomposition en 3 sous-projets

Cette spec couvre **uniquement le sous-projet 1**. Les sous-projets 2 et 3 sont mentionnés pour cadrer mais seront spécifiés séparément.

| Sous-projet | Description | Statut |
|---|---|---|
| **1 — Bot conversationnel + KB** | Couvert par cette spec | À implémenter |
| **2 — Opt-in marketing + broadcasts** | Liste opt-in via Bastien, campagnes broadcast légales | Spec ultérieure |
| **3 — Notifs transactionnelles** | "Préviens-moi quand X est restock" | Spec ultérieure |

### 1.4 Hors périmètre v1 (non négociable)

- ❌ Création/modification de devis Odoo par Bastien (read-only uniquement)
- ❌ Modification de commandes Shopify
- ❌ Analyse d'images / fichiers envoyés par le client
- ❌ Broadcasts marketing (sous-projet 2)
- ❌ Bot multi-canal (Instagram DM, Messenger, etc.) — WhatsApp uniquement
- ❌ Multi-langue — FR uniquement

---

## 2. Stack technique

### 2.1 Composants existants réutilisés

| Composant | Rôle | Localisation |
|---|---|---|
| Evolution API | Gateway WhatsApp non-officiel | VPS, `wa.startec-paris.com` |
| Instance `Orangina_2026` | Numéro pro 33672833132, 238 contacts, 6242 messages | Evolution |
| n8n | Orchestration workflows | VPS, `n8n.startec-paris.com`, folder `Yo` |
| Odoo | Devis, commandes, factures | VPS, `odoo.startec-paris.com` |
| Shopify | Catalogue, commandes B2C | `mylab-shop-3.myshopify.com` |
| Gmail (Google Workspace) | Email handoff | `yoann@mylab-shop.com` |

### 2.2 Composants nouveaux

| Composant | Rôle | Hébergement |
|---|---|---|
| **bastien-svc** (Python/FastAPI) | Service IA : RAG, mémoire, Gemini function calling | Docker sur VPS, port `8080` interne uniquement |
| **ChromaDB** (embedded) | Vector store pour RAG | Inside bastien-svc container |
| **SQLite** | Mémoire conversation, clients, handoffs | Volume Docker persistant |
| **Workflows n8n** | `bastien-prod-router`, `bastien-staging-router`, `bastien-error-notify`, `bastien-daily-digest` | n8n existant |

### 2.3 LLM

- **Modèle** : `gemini-2.5-flash` (Google AI Studio)
- **Embeddings** : `text-embedding-004`
- **Quotas** : 1500 req/jour gratuits → couvre le volume estimé (20-50 conversations/jour). Bascule vers tier payant si dépassement (~5 €/mois max).
- **SDK** : `google-genai` Python (function calling natif, streaming)

### 2.4 Choix d'architecture : **hybride n8n + Python**

n8n = orchestration métier (lookups, emails, webhooks). Python = IA pure (RAG, mémoire, Gemini). Couplage faible via HTTP, déploiement indépendant.

---

## 3. Architecture & data flow

### 3.1 Vue d'ensemble

```
┌──────────────────┐
│ Client WhatsApp  │
└────────┬─────────┘
         │ message
         ▼
┌────────────────────────────┐
│ Evolution API (VPS)        │
│ instance "Orangina_2026"   │
└────────┬───────────────────┘
         │ webhook (messages.upsert)
         ▼
┌────────────────────────────┐
│ n8n: bastien-router        │
│ (orchestration métier)     │
└────────┬───────────────────┘
         │ POST /chat { from, message, history }
         ▼
┌────────────────────────────┐
│ bastien-svc (Python/FastAPI)│
│ - Vector store (Chroma)    │
│ - Conversation memory (SQLite)│
│ - Gemini Flash + tools     │
└────────┬───────────────────┘
         │ JSON: { reply, tool_calls[], handoff? }
         ▼
   n8n exécute :
   - lookups Odoo/Shopify natifs
   - email handoff Gmail si besoin
   - send-message via Evolution
```

### 3.2 Scénario 1 — Question simple (prospect, pas de lookup)

> Client : *"C'est quoi votre MOQ pour un shampoing en marque blanche ?"*

1. Evolution → webhook → n8n
2. n8n → POST `/chat` à bastien-svc avec `from` + `text`
3. bastien-svc :
   - Charge l'historique SQLite (vide ici)
   - Embed la question, retrieve top-3 chunks pertinents (KB)
   - Construit prompt : [system Bastien] + [tools] + [contexte KB] + [history] + [user]
   - Appelle Gemini Flash, qui répond directement (pas de tool call)
   - Sauve Q&A en SQLite
4. n8n → Evolution send-message
5. Client reçoit la réponse en ~3 s

### 3.3 Scénario 2 — Lookup dynamique avec OTP

> Client : *"Où en est ma commande passée la semaine dernière ?"*

1. Idem 1-3a
2. Gemini détecte qu'il faut un email pour identifier le client → demande l'email
3. Client répond : *"yoann@mylab-shop.com"*
4. bastien-svc envoie un **code OTP 6 chiffres à cet email** (via Gmail API n8n)
5. Bastien : *"Je vous ai envoyé un code à 6 chiffres, donnez-le moi pour vérifier votre commande."*
6. Client envoie le code → bastien-svc valide → marque l'email comme `verified` pour ce `whatsapp_id`
7. Gemini appelle `get_shopify_order_status(email=...)`
8. n8n exécute le tool natif Shopify → résultat retourné
9. Gemini formule la réponse finale avec les infos commande
10. n8n → Evolution send-message

**Latence totale** : ~15-20 s (incluant attente du code par le client). Acceptable.

### 3.4 Scénario 3 — Handoff (sujet sensible)

> Client : *"5000 flacons gel douche bio, parfum custom, prix ?"*

1. Idem 1-3a
2. Gemini détecte 3 triggers handoff (volume + custom + prix négo) → renvoie :
   ```json
   {
     "reply": "Avec plaisir ! C'est un projet sur-mesure, je le transmets à Yoann qui revient vers vous dans la journée. Pouvez-vous me confirmer votre email ?",
     "handoff": {
       "reason": "prix_negocie + formulation_custom",
       "summary": "5000 flacons gel douche bio, parfum custom",
       "urgency": "normal"
     }
   }
   ```
3. n8n :
   - Email handoff à `yoann@mylab-shop.com` avec récap + lien WA
   - Réponse au client via Evolution
4. Bastien continue de répondre poliment au client (état "handoff posé") sans re-handoff sur le même sujet

### 3.5 Règles de routage (résumé)

| Situation | Décideur | Action |
|---|---|---|
| Question répondable depuis KB | Gemini | Réponse directe |
| Manque info client (email) | Gemini | Demande l'email |
| Lookup nécessaire | Gemini → tool_call | n8n exécute, re-prompt |
| Trigger handoff détecté | Gemini → champ `handoff` | n8n email Yoann + accusé client |
| Bot bloque 2× d'affilée | bastien-svc (compteur en SQLite) | Force handoff `bot_stuck` |
| Client dit "humain" | Gemini (intent) | Force handoff `humain_demande` |

---

## 4. Function calls (tools Gemini)

4 outils, **tous en lecture seule**.

### 4.1 `get_shopify_order_status`

```python
def get_shopify_order_status(email: str, order_id: str | None = None) -> dict:
    """
    Récupère le statut d'une commande Shopify pour le client identifié par email.
    Si order_id fourni, cible cette commande. Sinon, retourne la dernière.
    Pré-requis : email vérifié par OTP pour ce whatsapp_id.
    """
    # Implémenté côté n8n via Shopify Admin API node
    # Retourne : { order_id, status, fulfillment_status, tracking, date, items_summary }
```

### 4.2 `get_odoo_quote_status`

```python
def get_odoo_quote_status(email: str, quote_id: str | None = None) -> dict:
    """
    Récupère le statut d'un devis Odoo (sale.order) pour le client.
    Pré-requis : email vérifié.
    """
    # Implémenté côté n8n via XML-RPC Odoo
    # Retourne : { quote_id, state (draft/sent/sale), date, amount_total, validity_date }
```

### 4.3 `get_shipping_tracking`

```python
def get_shipping_tracking(order_id: str) -> dict:
    """
    Récupère le numéro de suivi DPD et le lien tracking pour une commande.
    Pré-requis : email vérifié + commande appartient au client.
    """
    # Implémenté côté n8n (Shopify fulfillment + DPD URL)
    # Retourne : { tracking_number, carrier: "DPD", tracking_url, last_event }
```

### 4.4 `check_product_stock`

```python
def check_product_stock(product_query: str) -> dict:
    """
    Vérifie la dispo d'un produit en stock (par nom approximatif ou handle).
    Pas besoin d'identification client.
    """
    # Implémenté côté n8n via Shopify Admin API
    # Retourne : { product, variants: [{ contenance, available_qty, in_stock: bool }] }
```

### 4.5 Tools NON exposés (anti-abuse)

Aucun tool d'écriture, de suppression, de modification. Aucun tool d'exécution arbitraire. C'est par design : même si le LLM est jailbreaké, il ne peut pas faire de dégâts.

---

## 5. Knowledge base & ingestion

### 5.1 Sources

| Source | Méthode | Fréquence re-index |
|---|---|---|
| Pages Shopify publiques (FAQ, parcours, étuis, étiquettes — ~15 pages) | API Admin REST `/pages.json` (`published_status=published`), strip HTML | Quotidienne 6h |
| Fiches produits Shopify (~80 produits actifs) | API Admin REST `/products.json` + metafields (MOQ, contenance) | Quotidienne 6h |
| Pages configurateur Vercel | Lecture repo Git (README + pages clés) ou scrape HTTP | Hebdomadaire dim 4h |
| **Pages internes Bastien-only** | Pages Shopify **non publiées** (`published=false`) ET marquées par metafield `bastien.internal=true` | Quotidienne 6h |

### 5.2 Pipeline d'ingestion

```python
# bastien.ingest (cron quotidien)
1. Fetch toutes les sources → liste de documents
2. Pour chaque doc :
   a. Découpe en chunks ~500 tokens, overlap 50, frontières paragraphes
   b. Génère embedding via text-embedding-004
   c. Stocke dans Chroma : vector + metadata
3. Diff vs index précédent :
   - Supprimé en source → supprime chunks
   - Modifié (updated_at) → re-embed + remplace
   - Identique → skip
```

**Coût** : ~200 chunks total, embeddings gratuits. Aucun problème de quota.

### 5.3 Retrieval (à chaque message)

```python
1. Embed la question
2. Cherche top-5 chunks similaires dans Chroma
3. Re-rank simple : boost si source = "shopify_product" et title match
4. Injecte top-3 dans le system prompt sous tag [CONTEXTE PERTINENT]
```

### 5.4 Garde-fous anti-hallucination (system prompt)

```
RÈGLES STRICTES — non négociables :
1. Ne donne JAMAIS un prix qui n'est pas explicitement dans le contexte fourni
   ou retourné par check_product_stock.
2. Ne promets JAMAIS un délai sans avoir consulté get_shopify_order_status.
3. Si une information n'est pas dans le contexte ni accessible par tool :
   réponds "Je ne dispose pas de cette information précise, je passe le
   relais à Yoann qui vous répondra rapidement." → trigger handoff.
4. Pour toute question sur formulation, INCI, certifications spécifiques,
   composition exacte → handoff systématique.
```

### 5.5 Pages internes — usage

Yoann peut créer dans Shopify des pages **non publiées** (`published=false`) avec un metafield `bastien.internal=true` (namespace `bastien`, key `internal`, type `boolean`). Ces pages :
- N'apparaissent jamais sur le front (Shopify ne les sert pas, statut `unpublished`)
- Sont accessibles via l'API Admin REST avec `published_status=unpublished`
- Sont ingérées par bastien-svc qui filtre sur le metafield `bastien.internal`

Exemples d'usage :
- Argumentaire commercial
- Réponses aux objections fréquentes
- Process devis interne
- "Bastien doit savoir : XXX"

Permet d'enrichir Bastien sans toucher au code ni redéployer. La création initiale du metafield definition se fait une seule fois via l'admin Shopify (Settings → Custom data → Pages → Add definition).

---

## 6. Identité & ton de Bastien

### 6.1 Persona

- **Nom** : Bastien
- **Rôle perçu** : assistant MY.LAB (sans préciser proactivement IA)
- **Ton** : chaleureux, professionnel, concis, tutoie/vouvoie selon le client (vouvoie par défaut, switche au tutoiement si le client tutoie)
- **Signature** : aucune signature explicite à la fin (pas de "Bastien" en pied — trop signal bot)
- **Emojis** : usage modéré (👋 en intro, ✅ pour confirmer, 📦 pour commandes). Jamais plus d'1 par message.

### 6.2 Comportement zone grise (Option 🟧 validée)

- Ne mentionne **jamais spontanément** être une IA
- Si questionné directement (*"tu es un bot ?"*, *"tu es humain ?"*) → reconnaît avec élégance :
  > *"Je suis l'assistant virtuel de l'équipe MY.LAB, conçu pour vous répondre rapidement à toute heure. Pour les sujets qui demandent l'expertise humaine, je passe le relais à Yoann."*
- Ne ment **jamais** activement sur sa nature

### 6.3 Premier message type

Quand un nouveau numéro écrit pour la 1ère fois :
> *"Bonjour 👋 Comment puis-je vous aider ?"*

Sobre, pas trop bavard. Si le client semble perdu, Bastien complète : *"Je peux vous renseigner sur nos produits, vérifier l'état de votre commande ou de votre devis, ou vous mettre en relation avec Yoann pour les sujets plus spécifiques."*

### 6.4 RGPD — info initiale

Au 1er échange avec un nouveau numéro, Bastien glisse une mention courte :
> *"Vos messages sont conservés pour le suivi de votre demande, conformément à notre politique de confidentialité (mylab-shop.com/privacy)."*

Une seule fois par client, pas à chaque conversation.

---

## 7. Conversation memory & session

### 7.1 Modèle SQLite

```sql
CREATE TABLE clients (
  whatsapp_id       TEXT PRIMARY KEY,         -- "33612345678"
  email             TEXT,                     -- collecté quand fourni
  email_verified    BOOLEAN DEFAULT 0,        -- post-OTP
  display_name      TEXT,                     -- nom WhatsApp
  first_seen        TIMESTAMP,
  last_seen         TIMESTAMP,
  consent_marketing BOOLEAN DEFAULT 0,        -- pour sous-projet 2
  rgpd_notified     BOOLEAN DEFAULT 0,        -- mention RGPD déjà envoyée
  notes             TEXT,                     -- annotations Yoann
  blocked           BOOLEAN DEFAULT 0         -- blocklist manuelle
);

CREATE TABLE messages (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  whatsapp_id     TEXT NOT NULL,
  role            TEXT NOT NULL,              -- 'user'|'assistant'|'tool'
  content         TEXT NOT NULL,
  tool_name       TEXT,
  tool_args       TEXT,                       -- JSON
  mode            TEXT DEFAULT 'prod',        -- 'prod'|'staging'
  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (whatsapp_id) REFERENCES clients(whatsapp_id)
);
CREATE INDEX idx_messages_client ON messages(whatsapp_id, created_at);

CREATE TABLE handoffs (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  whatsapp_id     TEXT NOT NULL,
  reason          TEXT,                       -- "prix_negocie","sav",etc
  summary         TEXT,
  resolved        BOOLEAN DEFAULT 0,
  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE otp_codes (
  whatsapp_id     TEXT NOT NULL,
  email           TEXT NOT NULL,
  code            TEXT NOT NULL,              -- 6 chiffres
  expires_at      TIMESTAMP NOT NULL,
  attempts        INTEGER DEFAULT 0,
  used            BOOLEAN DEFAULT 0,
  PRIMARY KEY (whatsapp_id, email)
);

CREATE TABLE rate_limits (
  whatsapp_id     TEXT NOT NULL,
  window_start    TIMESTAMP NOT NULL,
  count           INTEGER NOT NULL,
  PRIMARY KEY (whatsapp_id, window_start)
);
```

### 7.2 Stratégie de mémoire

- **Court terme** : 20 derniers messages chargés à chaque appel `/chat`
- **Moyen terme** : session = enchaînement avec ≤ 1h de silence. Au-delà, nouvelle session mais historique passé toujours accessible.
- **Long terme** : table `clients` accumule email vérifié, consent_marketing, notes — base du CRM léger Bastien

### 7.3 Données NON conservées

- Aucun media (images, audio, documents)
- Pas de mots de passe / CB / CVV → redaction par regex avant envoi à Gemini

### 7.4 Conformité RGPD

| Obligation | Implémentation |
|---|---|
| Information | Mention au 1er message + privacy policy publique mise à jour |
| Droit d'accès | Handoff `rgpd_acces` → export manuel par Yoann |
| Droit à l'effacement | Handoff `rgpd_suppression` → script `bastien-admin delete <numero>` |
| Conservation limitée | Cron mensuel : suppression messages > 24 mois, clients inactifs > 36 mois |
| DPA Google (Gemini) | Couvert par DPA standard Google API. Mention dans privacy policy. |

### 7.5 Commande spéciale `/reset`

Si un client envoie `/reset`, Bastien efface l'historique de cette conversation (mais conserve la table `clients`). Utile pour debug et conversations dérapées.

### 7.6 Endpoints admin (pas d'HTTP — SSH only)

```bash
docker exec bastien-svc python -m bastien.admin <commande>
```

Commandes disponibles :
- `list-conversations [--since=DATE]` → liste clients triés par last_seen
- `show-conversation <whatsapp_id>` → historique complet
- `list-handoffs [--unresolved]` → file de handoffs
- `resolve-handoff <id>` → marquer traité
- `block <whatsapp_id>` / `unblock <whatsapp_id>`
- `delete <whatsapp_id>` → RGPD suppression
- `export <whatsapp_id> > file.json` → RGPD accès
- `pause [--duration=1h]` → kill switch doux
- `reset-breaker` → reset circuit breaker manuel
- `cleanup` → purge données expirées
- `send-digest` → force envoi daily digest

### 7.7 Privacy policy à rédiger

Une nouvelle page privacy publiée sur `mylab-shop.com/pages/privacy` (ou mise à jour de l'existante) intégrant :
- Mention de Bastien (assistant IA basé sur Gemini)
- Sous-traitants : Google (Gemini API), n8n self-hosted, Evolution API self-hosted
- Données collectées via WhatsApp : numéro, messages, email si fourni
- Durées de conservation
- Procédure RGPD (mail à `dpo@mylab-shop.com` ou autre)

À produire en parallèle de l'implé bastien-svc.

---

## 8. Sécurité — threat model & mitigations

### 8.1 Menaces couvertes (12 menaces)

| # | Menace | Mitigation principale |
|---|---|---|
| 1 | Prompt injection / jailbreak | System prompt verrouillé + zéro tool destructif |
| 2 | Tool abuse (fuite données autre client) | OTP email obligatoire avant tout lookup |
| 3 | Webhook spoofing Evolution → n8n | Header `X-Evolution-Key` (shared secret) + IP allowlist |
| 4 | bastien-svc exposé public | Bind 127.0.0.1 + réseau Docker interne uniquement |
| 5 | Spam / DDoS WhatsApp | Rate limit 30/h, 100/jour par numéro |
| 6 | Endpoints admin exposés | Aucun endpoint HTTP admin, SSH + docker exec only |
| 7 | Email injection / phishing via handoff | Email plain text, contenu user non interprété |
| 8 | PII envoyé à Gemini | Regex redaction CB/IBAN/CVV avant prompt |
| 9 | Secrets leak | `.env` 600 + .gitignore + rotation 6 mois + pre-commit hook |
| 10 | SQL injection | Requêtes paramétrées strictement (sqlmodel) |
| 11 | Cross-conversation leak | Tests d'isolation auto + indexation stricte par whatsapp_id |
| 12 | WhatsApp ban Meta | Délai humain 1-3s, max 80 msg sortants/24h, monitoring manuel |

### 8.2 Système OTP — détail

- Code 6 chiffres généré par `secrets.randbelow(1000000)`
- Envoyé par email via Gmail SMTP (n8n Gmail node)
- Validité : 10 min
- Max 3 tentatives par couple `(whatsapp_id, email)` → au-delà, handoff `tentative_acces_suspect`
- Une fois validé, marquage `email_verified=1` pour ce `whatsapp_id` → plus de revérification (sauf changement d'email)

### 8.3 Système de redaction PII

```python
PII_PATTERNS = {
    'cb': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
    'iban': r'\b[A-Z]{2}\d{2}[A-Z0-9]{1,30}\b',
    'cvv': r'(?i)(?:cvv|cvc|crypto)\D{0,5}(\d{3,4})',
}

def redact_pii(text: str) -> str:
    for label, pattern in PII_PATTERNS.items():
        text = re.sub(pattern, f'[{label.upper()}_REDACTED]', text)
    return text
```

Appliqué sur **tout** message client avant envoi à Gemini.

### 8.4 Tests de sécurité obligatoires

`tests/test_security.py` doit passer avant déploiement :
- Injection prompts → refus
- Lookup d'un email tiers sans OTP → refus
- Rate limit déclenché à la 31e requête en 1h
- Redaction CB/IBAN/CVV effective
- SQL injection tentée → bloquée
- Cross-conversation isolation → 2 clients ne voient pas leurs historiques

---

## 9. Error handling & resilience

### 9.1 Catalogue pannes & comportement

| Panne | Réponse client | Action interne |
|---|---|---|
| Gemini timeout >15s | "Un instant, je consulte..." puis "Je rencontre un souci, je transmets à Yoann." | Email alerte + handoff |
| Gemini quota dépassé (429) | "Je suis très sollicité, Yoann reprend la main." | Email "QUOTA_EXCEEDED", désactivation auto 1h |
| Gemini réponse malformée | "Je n'ai pas tout suivi, pouvez-vous reformuler ?" | Log + retry simplifié |
| Lookup Odoo timeout | "Je n'arrive pas à accéder à votre devis, Yoann va vérifier." | Handoff `odoo_unreachable` |
| Lookup Shopify 5xx | Idem | Handoff `shopify_unreachable` |
| Evolution send-message KO | (silence client, l'envoi a échoué) | Email URGENT + retry 3× exponentiel |
| bastien-svc down | Auto-réply Evolution : "Bastien en maintenance" | Email URGENT + Docker restart auto |
| n8n workflow crash | (silence client) | Workflow `bastien-error-notify` envoie mail |
| SQLite verrouillé | Réponse différée | Retry 3×, log warning |

### 9.2 Politique de retry

| Cible | Tentatives | Backoff |
|---|---|---|
| Gemini | 2 | 1s, 3s |
| Shopify | 3 | 1s, 3s, 9s |
| Odoo | 3 | 2s, 5s, 15s |
| Evolution send | 3 | 1s, 3s, 9s |
| Gmail SMTP | 3 | 5s, 30s, 2min |

Au-delà → handoff `tech_failure`.

### 9.3 Circuit breakers

Chaque dépendance (Gemini, Odoo, Shopify, Evolution) a son propre circuit breaker :
- Seuil : 5 erreurs consécutives en < 5 min → ouvre le circuit
- Pendant ouverture (30 min) : aucun appel à cette dépendance, fallback message
- Reset auto après 30 min, ou manuel via `bastien-admin reset-breaker`

### 9.4 Monitoring

- **Logs structurés JSON** dans `/var/log/bastien/`, rotation hebdo, rétention 30 jours
- **Health endpoint** `GET /healthz` → `{ status, gemini, db, chroma, uptime }`
- **Cron healthcheck VPS** toutes les 5 min, alerte mail si KO 2× consécutifs
- **Daily digest** envoyé à 8h à `yoann@mylab-shop.com` :
  ```
  📊 Bastien — récap du JJ-MM-AAAA
  - X messages traités (Y conversations distinctes)
  - Z handoffs (détails par catégorie)
  - W lookups Shopify, V Odoo, U stock
  - Latence moyenne : Xs
  - Erreurs : N
  - Quota Gemini : X/1500 (Y%)
  ```

### 9.5 Backup & recovery

- SQLite : backup quotidien 3h → `/var/backups/bastien/bastien-YYYYMMDD.db.gz`, rétention 30 jours
- ChromaDB : reconstruit depuis sources, pas de backup nécessaire
- Snapshot VPS hebdo (Hostinger) couvre les volumes Docker
- Restore documenté dans `RUNBOOK.md`, RTO < 5 min

### 9.6 Kill switch

```bash
docker stop bastien-svc           # arrêt total, n8n détecte 502 → fallback
docker exec bastien-svc python -m bastien.admin pause --duration 1h  # pause douce
```

---

## 10. Testing & rollout

### 10.1 Architecture staging vs prod

Une seule instance bastien-svc, deux modes via header `X-Bastien-Mode: prod|staging` :
- **Prod** : SQLite `bastien.db`, vraies API, emails handoff vers `yoann@mylab-shop.com`
- **Staging** : SQLite `bastien-test.db`, mêmes API (read-only safe), emails vers `yoann+bastien-test@mylab-shop.com` avec sujet `[STAGING]`

### 10.2 Stratégie de staging — 100 % gratuite

**A. Test harness CLI** (90 % des tests quotidiens) :
```bash
docker exec -it bastien-svc python -m bastien.chat --as 33600000001
docker exec bastien-svc python -m bastien.chat --as 33600000001 "Bonjour"
docker exec bastien-svc python -m bastien.chat --scenario tests/scenarios/handoff-prix.txt
```
Génère un payload identique à Evolution, passe par tout le pipeline, affiche en terminal. Permet itération rapide + scénarios automatisés.

**B. Préfixe `/test` sur WhatsApp perso** (validation E2E pré-prod) :
- Si message vient du numéro perso de Yoann ET commence par `/test` → mode staging
- Réponse préfixée `🧪 [TEST]`
- Email handoff vers `yoann+bastien-test@`
- Config : `STAGING_TRIGGER_NUMBER` + `STAGING_TRIGGER_PREFIX` dans `.env`

**C. Allowlist phase 1** : Bastien ne répond qu'aux numéros dans `allowlist.txt` pendant l'alpha.

**Coût total staging : 0 €.**

### 10.3 Tests automatisés

```
tests/
├── test_security.py       # injection, OTP forçage, redaction PII, rate limit
├── test_isolation.py      # 2 conversations parallèles ne se mélangent pas
├── test_tools.py          # mocks Shopify/Odoo, vérifs args/résultats
├── test_handoff.py        # 6 triggers déclenchent handoff
├── test_persona.py        # Bastien admet IA si questionné, refuse de mentir
├── test_kb_retrieval.py   # questions standards retournent bons chunks
└── test_e2e.py            # scénarios complets via mock Evolution
```

CI : GitHub Actions ou cron VPS, `pytest` à chaque push. Aucun déploiement si rouge.

### 10.4 Checklist d'acceptation manuelle (avant phase 2)

Yoann valide via le harness ou `/test` :
- [ ] Question prospect "C'est quoi MY.LAB ?" → réponse claire
- [ ] Question MOQ → réponse précise (200u min)
- [ ] Question prix produit → prix exact
- [ ] Lookup commande complet (email → OTP → statut)
- [ ] Lookup devis complet
- [ ] Handoff prix négo
- [ ] Handoff SAV
- [ ] Handoff humain demandé
- [ ] Question hors sujet (météo) → recadrage poli
- [ ] Tentative jailbreak → refus
- [ ] Tentative usurpation email tiers → bloqué OTP
- [ ] "T'es un bot ?" → admet zone grise
- [ ] `/reset` efface l'historique
- [ ] Latence p50 < 5s

### 10.5 Phases de rollout

| Phase | Durée | Description |
|---|---|---|
| **0 — Dev** | ~1 sem | Code, tests verts, déploiement staging OK |
| **1 — Alpha fermée** | 3-5 j | Allowlist : Yoann + 2-3 proches. Monitoring manuel chaque conversation. |
| **2 — Beta restreinte** | 7-14 j | Allowlist : 5-10 clients de confiance prévenus. KPIs suivis. |
| **3 — GA** | continu | Allowlist supprimée, ouvert à tous. Daily digest. Surveillance 1ère semaine. |

### 10.6 Critères Go/No-Go

| De → vers | Critère obligatoire |
|---|---|
| 0 → 1 | 100 % checklist manuelle + tests auto verts |
| 1 → 2 | 0 hallucination critique sur 50+ msg, 0 fuite données, latence p95 < 5s |
| 2 → 3 | Taux handoff < 40 %, feedback positif sur 5+ clients beta, 0 incident sécu |

---

## 11. Déploiement & opérations

### 11.1 Topologie VPS

```
VPS (82.25.112.124)
└── Docker network: bastien_net
    ├── bastien-svc        :8080  (interne uniquement)
    ├── volumes:
    │   ├── bastien_data    → /data
    │   └── bastien_secrets → /secrets:ro
    │
    ├── (existant) n8n      :5678
    ├── (existant) Evolution :8080
    └── (existant) Odoo      :8069
```

bastien-svc n'est **jamais exposé publiquement**. Communication interne uniquement via le réseau Docker partagé `bastien_net` avec n8n.

### 11.2 Repo

**Nouveau repo Git** : `bastien-svc` (séparé de be-yours-mylab — cycle de vie différent).

```
bastien-svc/
├── src/bastien/
│   ├── main.py              # FastAPI app, endpoints
│   ├── llm.py               # Gemini wrapper, function calling loop
│   ├── kb.py                # ChromaDB, embeddings, retrieval
│   ├── ingest.py            # Pipeline ingestion (cron)
│   ├── memory.py            # SQLite, conversations, clients
│   ├── security.py          # Redaction, OTP, rate limit, blocklist
│   ├── persona.py           # System prompt
│   ├── circuit.py           # Circuit breakers
│   ├── admin.py             # CLI (docker exec)
│   ├── chat.py              # Test harness CLI
│   └── config.py            # Pydantic settings
├── tests/                    # cf. 10.3
├── n8n/                      # workflows JSON exportés
│   ├── bastien-router.json
│   ├── bastien-error-notify.json
│   └── bastien-daily-digest.json
├── scripts/
│   ├── backup.sh
│   ├── healthcheck.sh
│   └── deploy.sh
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .gitignore               # .env, *.db, /data/
├── requirements.txt
├── pyproject.toml
├── README.md
└── RUNBOOK.md               # Procédures ops
```

**Repo `be-yours-mylab`** : aucune modification. Bastien est totalement indépendant.

### 11.3 Workflows n8n (folder `Yo`)

| Workflow | Rôle | Trigger |
|---|---|---|
| `bastien-router` | Webhook Evolution → détection mode (prod/staging selon préfixe `/test` + numéro perso) → bastien-svc → exécution lookups → Evolution send | Webhook Evolution |
| `bastien-error-notify` | Notif Yoann en cas de crash workflow | Error workflow attaché à `bastien-router` |
| `bastien-daily-digest` | Email récap quotidien | Cron 8h |

Un seul workflow `bastien-router` qui gère prod **et** staging via switch interne (basé sur préfixe `/test` + numéro perso). Évite duplication. Tous placés dans le folder `Yo` (id `Z2t5yT17QDhgf2XO`, project `HUgJsuxI2uJxkLLk`) conformément à la convention.

### 11.4 Secrets (`.env` permissions 600 sur VPS)

```bash
# === LLM ===
GEMINI_API_KEY=

# === Evolution API ===
EVOLUTION_BASE_URL=http://evolution:8080
EVOLUTION_API_KEY=
EVOLUTION_INSTANCE=Orangina_2026
# Pas d'instance staging dédiée : le mode staging est déclenché par le préfixe /test
# depuis le numéro perso de Yoann sur la même instance prod (cf. section 10.2)

# === Webhook security ===
WEBHOOK_SHARED_SECRET=  # openssl rand -hex 32
BASTIEN_AUTH_TOKEN=     # openssl rand -hex 32 (n8n -> bastien-svc bearer)
BASTIEN_MODE=prod

# === Email handoff ===
HANDOFF_EMAIL_TO=yoann@mylab-shop.com
HANDOFF_EMAIL_FROM=bastien@mylab-shop.com  # alias Gmail
SMTP_HOST=smtp.gmail.com
SMTP_USER=
SMTP_APP_PASSWORD=  # password applicatif Gmail

# === Staging trigger ===
STAGING_TRIGGER_NUMBER=  # numéro perso Yoann
STAGING_TRIGGER_PREFIX=/test

# === Data retention ===
MESSAGE_RETENTION_DAYS=730   # 24 mois
CLIENT_INACTIVE_DAYS=1095    # 36 mois

# === Rate limits ===
RATE_LIMIT_PER_HOUR=30
RATE_LIMIT_PER_DAY=100

# === Circuit breakers ===
BREAKER_THRESHOLD=5
BREAKER_WINDOW_SECONDS=300
BREAKER_OPEN_DURATION_SECONDS=1800
```

Secrets ajoutés au gestionnaire de secrets MY.LAB (cf. `reference_api_keys.md`) après génération.

### 11.5 Cron jobs (host VPS)

```cron
# Ingestion KB quotidienne (6h)
0 6 * * * docker exec bastien-svc python -m bastien.ingest

# Backup SQLite (3h)
0 3 * * * /root/bastien/scripts/backup.sh

# Cleanup données expirées (mensuel)
0 4 1 * * docker exec bastien-svc python -m bastien.admin cleanup

# Daily digest (8h)
0 8 * * * docker exec bastien-svc python -m bastien.admin send-digest

# Healthcheck (toutes les 5 min)
*/5 * * * * /root/bastien/scripts/healthcheck.sh
```

### 11.6 Procédure de déploiement initial

1. **Setup VPS** (~30 min) : créer `/root/bastien/`, cloner repo, créer `.env`, créer alias Gmail `bastien@mylab-shop.com` + app password
2. **Build & run** (~10 min) : `docker compose up -d --build` puis ingestion initiale + healthcheck
3. **Config n8n** (~1h) : importer 4 workflows, configurer credentials, configurer webhook Evolution
4. **Tests staging** : harness CLI + checklist manuelle
5. **Rollout phasé** (cf. 10.5)

### 11.7 Estimation d'effort

| Phase | Effort dev |
|---|---|
| Code bastien-svc (Python) | 4-5 jours |
| Workflows n8n + intégrations | 1-2 jours |
| Tests & ajustements | 1-2 jours |
| Setup VPS, secrets, déploiement | 0.5 jour |
| Privacy policy rédaction & publication | 0.5 jour |
| **Total dev** | **~9-12 jours** |
| Phase 1-3 (calendaire) | 3-4 semaines |

### 11.8 Coûts récurrents

| Poste | Mensuel |
|---|---|
| Gemini Flash API | 0 € (sous quota gratuit, max ~5 € si dépassement) |
| Staging | 0 € (harness CLI + préfixe /test) |
| VPS | 0 € (cohabite existant) |
| Domaine | 0 € (interne) |
| **Total** | **~0 €/mois** |

---

## 12. Risques & mitigations résiduelles

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| WhatsApp ban Orangina_2026 | Moyenne | Élevé | Rate limit, délai humain, monitoring manuel |
| Hallucination Bastien sur prix/délai | Moyenne | Élevé | System prompt strict + handoff fallback + tests réguliers |
| Quota Gemini dépassé en cas de buzz | Faible | Moyen | Circuit breaker + fallback handoff massif |
| Bug fuite cross-conversation | Faible | Très élevé | Tests d'isolation auto + indexation stricte |
| Client mécontent découverte IA | Moyenne | Moyen | Zone grise + persona chaleureuse + handoff facile |
| Complaint CNIL pour AI Act | Faible | Élevé | Mention RGPD au 1er msg + privacy policy à jour |

---

## 13. Définition de "fait" (DoD) v1

Bastien est considéré livré v1 (= prêt pour phase 3 GA) quand :

- [ ] Repo `bastien-svc` créé, code Python complet, `pytest` 100 % vert
- [ ] Docker image build OK, `docker compose up` fonctionne sur VPS
- [ ] 4 workflows n8n importés dans folder `Yo`, credentials configurés
- [ ] Webhook Evolution → n8n configuré avec shared secret
- [ ] Cron jobs installés sur VPS
- [ ] Privacy policy mise à jour et publiée sur `mylab-shop.com/pages/privacy`
- [ ] Secrets ajoutés au gestionnaire MY.LAB
- [ ] `RUNBOOK.md` rédigé (procédures restart, restore, rotate keys)
- [ ] Phase 0 → 1 : 100 % checklist manuelle validée
- [ ] Phase 1 → 2 : 0 hallucination critique sur 50+ messages alpha
- [ ] Phase 2 → 3 : taux handoff < 40 % + feedback positif beta
- [ ] Daily digest reçu et lu par Yoann pendant 1 semaine sans intervention

---

## 14. Suite — sous-projets 2 et 3 (esquisse, hors scope)

### 14.1 Sous-projet 2 — Opt-in marketing & broadcasts

Réutilise l'infra Bastien :
- Bastien propose au cours d'une conversation : *"Souhaitez-vous être informé de nos nouveautés ? Vous pouvez vous désinscrire à tout moment en répondant STOP."*
- Si oui → `consent_marketing=1` en SQLite
- Commande admin pour broadcaster : `bastien-admin broadcast --template promo-mai --to consenting`
- Risque ban Meta → décision possible de basculer vers WhatsApp Business Cloud API (officiel, payant) si volume marketing significatif

### 14.2 Sous-projet 3 — Notifs transactionnelles trigger-based

Réutilise l'infra :
- Webhook Shopify `orders/fulfilled` → n8n → si client a `consent_marketing=1` → message WhatsApp "Votre commande a été expédiée 📦"
- "Préviens-moi quand X est restock" → SQLite `notifications` table → cron quotidien check stock

Ces sous-projets seront spécifiés séparément après livraison de la v1 du sous-projet 1.

---

## 15. Décisions clés validées

| # | Décision | Validé le |
|---|---|---|
| 1 | Décomposition en 3 sous-projets, sous-projet 1 d'abord | 2026-05-09 |
| 2 | LLM = Gemini 2.5 Flash (gratuit) | 2026-05-09 |
| 3 | Audience cible = D (mix prospects/devis/SAV) | 2026-05-09 |
| 4 | Sources KB = pages Shopify + produits + Vercel + tag `bastien-internal` | 2026-05-09 |
| 5 | 4 function calls (commande, devis, tracking, stock) — read-only uniquement | 2026-05-09 |
| 6 | Identification = email à la demande + OTP obligatoire | 2026-05-09 |
| 7 | 6 triggers handoff + email auto à yoann@mylab-shop.com + accusé client | 2026-05-09 |
| 8 | Bot 24/7, persona "Bastien", zone grise (admet IA si questionné) | 2026-05-09 |
| 9 | Architecture C = hybride n8n + Python | 2026-05-09 |
| 10 | Staging 100 % gratuit (harness CLI + préfixe /test) | 2026-05-09 |
| 11 | Privacy policy à rédiger intégrant Bastien | 2026-05-09 |
| 12 | bastien-svc dans nouveau repo séparé, jamais exposé publiquement | 2026-05-09 |

---

**Fin de la spec.**
