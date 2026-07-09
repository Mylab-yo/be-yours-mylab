# Hermes Email Responder Cron — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Déployer un cron Hermes qui draft 3×/jour (lun-ven) les réponses aux emails non-lus des labels Gmail `URGENT` + `Commandes & Devis` de yoann@mylab-shop.com, en brouillon, avec la KB MY.LAB, et notifie Yoann sur Telegram.

**Architecture:** Un worker Python déterministe (`email_responder.py`) lancé par le cron Hermes (`--no-agent --script ... --deliver telegram`). Il parle à l'API Gmail REST (via OAuth refresh token + `requests`, pas de lib Google) et à l'API Claude native (`api.anthropic.com/v1/messages`) pour la seule étape de rédaction. Idempotence par label Gmail `Hermes-Drafted`. La KB est extraite de `skills/mylab-email-responder/SKILL.md` au déploiement (source unique).

**Tech Stack:** Python 3 (stdlib + `requests`, déjà dans le container Hermes), API Gmail REST v1, API Anthropic Messages v1, paramiko (SSH/SFTP depuis le poste), Hermes cron CLI.

**Spec source:** `docs/superpowers/specs/2026-06-11-hermes-email-responder-cron-design.md`

---

## File Structure

| Fichier | Création/Modif | Responsabilité |
|---|---|---|
| `scripts/hermes/email_responder.py` | Create | Le worker (source de vérité, uploadé verbatim sur le VPS). Helpers purs + fonctions réseau + `main()` |
| `scripts/hermes/test_email_responder.py` | Create | Tests auto-portés (plain `assert`, lançables avec `python`, sans pytest) des helpers purs |
| `scripts/hermes/build_email_prompt.py` | Create | Extrait le system prompt depuis `SKILL.md`. Importé par le déploiement + testé |
| `scripts/hermes/test_build_email_prompt.py` | Create | Tests de l'extraction de prompt |
| `scripts/hermes/gmail_oauth_setup.py` | Create | Helper one-time : flow OAuth Desktop → imprime le refresh token Gmail |
| `scripts/hermes/add_email_responder.py` | Create | Déploiement : build prompt + signature, SFTP upload, upsert `.env`, crée le cron |
| `scripts/hermes/README.md` | Modify (si existe) ou Create | Note d'ordre d'exécution |

**Container paths (VPS):** worker → `/root/.hermes/scripts/email_responder.py` (monté `/opt/data/scripts/`), prompt → `email_responder_prompt.md`, signature → `email_responder_signature.html`, env → `/root/.hermes/.env` (monté `/opt/data/.env`).

**Env requis (poste, dans `.env.vps`):** `VPS_HOST`, `VPS_PORT`, `VPS_USER`, `VPS_PASS` (déjà présents), `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN` (ajoutés en Task 6).

**Env requis (container, dans `/root/.hermes/.env`):** `ANTHROPIC_API_KEY` (déjà présent), `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN` (upsertés en Task 7).

---

## Task 0: Prérequis Google Cloud (manuel, GUI)

**Aucun fichier.** Étape manuelle dans la console Google Cloud, projet `mylab-design-studio` (déjà utilisé pour la sync GCal).

- [ ] **Step 1: Activer l'API Gmail**

Console Google Cloud → projet `mylab-design-studio` → "APIs & Services" → "Enable APIs and Services" → chercher "Gmail API" → Enable.

- [ ] **Step 2: Créer un client OAuth "Desktop app"**

"APIs & Services" → "Credentials" → "Create Credentials" → "OAuth client ID" → Application type = **Desktop app** → Name = `MyLab Hermes Email Responder` → Create.
Noter le **Client ID** et le **Client secret** affichés.

- [ ] **Step 3: Autoriser le scope + le test user**

"OAuth consent screen" → vérifier que l'app est en mode "Testing" → "Test users" → ajouter `yoann@mylab-shop.com` s'il n'y est pas.
(Le scope `gmail.modify` est demandé au runtime par Task 6, pas besoin de le déclarer ici tant que l'app est en Testing.)

- [ ] **Step 4: Vérification**

Confirmer : Gmail API = Enabled, un client Desktop existe, Client ID/secret notés, `yoann@mylab-shop.com` est test user.
Expected: les 3 conditions remplies.

---

## Task 1: Extraction du system prompt depuis SKILL.md

**Files:**
- Create: `scripts/hermes/build_email_prompt.py`
- Test: `scripts/hermes/test_build_email_prompt.py`

- [ ] **Step 1: Write the failing test**

`scripts/hermes/test_build_email_prompt.py` :
```python
"""Tests for build_email_prompt — run: python scripts/hermes/test_build_email_prompt.py"""
from build_email_prompt import extract_kb_prompt

SAMPLE = """---
name: x
---
# Title

## Workflow
Étape 1 : utilise gmail_search_messages ...

## Identité de l'agent
Tu es Yoann.

## Base de connaissance MY.LAB
Prix shampoing 200ml : 7.00€
"""

def test_drops_workflow_keeps_identity_and_kb():
    out = extract_kb_prompt(SAMPLE)
    assert "gmail_search_messages" not in out          # workflow API-tool removed
    assert "Tu es Yoann." in out                        # identity kept
    assert "Prix shampoing 200ml : 7.00€" in out        # KB kept

def test_has_html_only_preamble():
    out = extract_kb_prompt(SAMPLE)
    assert "UNIQUEMENT" in out and "HTML" in out        # output instruction present

def test_raises_without_marker():
    try:
        extract_kb_prompt("no marker here")
        assert False, "should have raised"
    except ValueError:
        pass

if __name__ == "__main__":
    test_drops_workflow_keeps_identity_and_kb()
    test_has_html_only_preamble()
    test_raises_without_marker()
    print("OK build_email_prompt")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts/hermes && python test_build_email_prompt.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'build_email_prompt'`

- [ ] **Step 3: Write minimal implementation**

`scripts/hermes/build_email_prompt.py` :
```python
"""Extrait le system prompt de rédaction depuis skills/mylab-email-responder/SKILL.md.

Source de vérité unique : on prend tout depuis '## Identité de l'agent' jusqu'à la fin
(identité + KB + règles + exemples), en excluant la section '## Workflow' qui décrit
des outils Gmail non pertinents pour un appel API direct.
"""

MARKER = "## Identité de l'agent"

PREAMBLE = (
    "Tu rédiges le corps HTML d'une réponse à un email professionnel reçu par MY.LAB. "
    "Réponds UNIQUEMENT avec le HTML du corps du message : pas de signature, pas de balise "
    "<html> ni <body>, pas de Markdown. Respecte scrupuleusement la base de connaissance, "
    "le ton et les règles ci-dessous.\n\n"
)


def extract_kb_prompt(skill_md_text):
    idx = skill_md_text.find(MARKER)
    if idx == -1:
        raise ValueError(f"Marqueur '{MARKER}' introuvable dans SKILL.md")
    return PREAMBLE + skill_md_text[idx:]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd scripts/hermes && python test_build_email_prompt.py`
Expected: `OK build_email_prompt`

- [ ] **Step 5: Commit**

```bash
git add scripts/hermes/build_email_prompt.py scripts/hermes/test_build_email_prompt.py
git commit -m "feat(hermes): extraction du system prompt email depuis SKILL.md"
```

---

## Task 2: Worker — helpers purs (queries, signature, résumé Telegram)

**Files:**
- Create: `scripts/hermes/email_responder.py` (début du fichier)
- Test: `scripts/hermes/test_email_responder.py`

- [ ] **Step 1: Write the failing test**

`scripts/hermes/test_email_responder.py` :
```python
"""Tests helpers purs du worker — run: python scripts/hermes/test_email_responder.py"""
import email_responder as er

def test_build_search_queries():
    qs = er.build_search_queries()
    assert qs == [
        'label:URGENT is:unread -label:Hermes-Drafted',
        'label:"Commandes & Devis" is:unread -label:Hermes-Drafted',
    ]

def test_append_signature():
    assert er.append_signature("<p>Bonjour</p>", "<table>SIG</table>") == \
        "<p>Bonjour</p><br><br><table>SIG</table>"

def test_summary_empty():
    out = er.format_telegram_summary([], 0)
    assert "aucun nouveau mail" in out

def test_summary_drafted_and_error():
    results = [
        {"status": "drafted", "from_name": "Marie", "from_email": "m@x.fr",
         "subject": "Devis shampoing", "summary": "Tarifs envoyés"},
        {"status": "error", "from_email": "bad@x.fr", "error": "thread illisible"},
    ]
    out = er.format_telegram_summary(results, 0)
    assert "1 brouillon(s)" in out
    assert "Marie" in out and "Devis shampoing" in out
    assert "1 échec(s)" in out and "bad@x.fr" in out
    assert "rien n'a été envoyé" in out

def test_summary_capped():
    results = [{"status": "drafted", "from_name": "A", "from_email": "a@x.fr",
                "subject": "S", "summary": "x"}]
    out = er.format_telegram_summary(results, 3)
    assert "3 mail(s) restant" in out

if __name__ == "__main__":
    test_build_search_queries()
    test_append_signature()
    test_summary_empty()
    test_summary_drafted_and_error()
    test_summary_capped()
    print("OK email_responder helpers")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts/hermes && python test_email_responder.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'email_responder'`

- [ ] **Step 3: Write minimal implementation**

Créer `scripts/hermes/email_responder.py` avec l'en-tête + config + ces helpers. **`requests` est importé paresseusement dans les fonctions réseau (Task 4)** pour que ce module reste importable avec la seule stdlib pendant les tests.

```python
#!/usr/bin/env python3
"""MyLab Email Responder — worker du cron Hermes.

Scanne les threads Gmail non-lus des labels URGENT + Commandes & Devis,
rédige une réponse HTML avec Claude (KB MY.LAB), l'enregistre en BROUILLON
(jamais d'envoi), tague le thread Hermes-Drafted (idempotence), et imprime
un résumé Telegram sur stdout.

Lancé par : hermes cron, --no-agent --script email_responder.py --deliver telegram
"""
import base64
import os
import re
from email.message import EmailMessage
from email.utils import parseaddr

try:
    from dotenv import load_dotenv
    load_dotenv("/opt/data/.env")
except Exception:
    pass

# --- Config (overridable via env) ---
MODEL = os.environ.get("EMAIL_RESPONDER_MODEL", "claude-opus-4-8")
MAX_PER_RUN = int(os.environ.get("EMAIL_RESPONDER_MAX", "15"))
DRY_RUN = os.environ.get("EMAIL_RESPONDER_DRY_RUN", "") == "1"
DRAFTED_LABEL = "Hermes-Drafted"
PROMPT_PATH = "/opt/data/scripts/email_responder_prompt.md"
SIGNATURE_PATH = "/opt/data/scripts/email_responder_signature.html"

LABEL_QUERIES = [
    'label:URGENT is:unread -label:Hermes-Drafted',
    'label:"Commandes & Devis" is:unread -label:Hermes-Drafted',
]

GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"
TOKEN_URL = "https://oauth2.googleapis.com/token"
ANTHROPIC_API = "https://api.anthropic.com/v1/messages"


# --- Helpers purs (testables hors-ligne) ---
def build_search_queries():
    return list(LABEL_QUERIES)


def append_signature(html_body, signature_html):
    return f"{html_body}<br><br>{signature_html}"


def format_telegram_summary(results, capped_remaining=0):
    drafted = [r for r in results if r.get("status") == "drafted"]
    errors = [r for r in results if r.get("status") == "error"]
    if not results:
        return "\U0001F4E5 *Emails MY.LAB* — aucun nouveau mail à traiter"
    lines = [f"\U0001F4E5 *{len(drafted)} brouillon(s) prêt(s)* dans Gmail", ""]
    for r in drafted:
        who = r.get("from_name") or r.get("from_email", "?")
        lines.append(f"• *{who}* — {(r.get('subject') or '')[:60]}")
        if r.get("summary"):
            lines.append(f"  _{r['summary'][:120]}_")
    if errors:
        lines.append("")
        lines.append(f"⚠️ *{len(errors)} échec(s) :*")
        for r in errors:
            lines.append(f"• {r.get('from_email', '?')} — {(r.get('error') or '?')[:80]}")
    if capped_remaining:
        lines.append("")
        lines.append(f"_Cap atteint : {capped_remaining} mail(s) restant(s) pour le prochain passage._")
    lines.append("")
    lines.append("_Brouillons à relire et envoyer — rien n'a été envoyé automatiquement._")
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd scripts/hermes && python test_email_responder.py`
Expected: `OK email_responder helpers`

- [ ] **Step 5: Commit**

```bash
git add scripts/hermes/email_responder.py scripts/hermes/test_email_responder.py
git commit -m "feat(hermes): worker email — helpers queries/signature/résumé + tests"
```

---

## Task 3: Worker — parsing thread Gmail + construction MIME

**Files:**
- Modify: `scripts/hermes/email_responder.py` (ajout de fonctions)
- Modify: `scripts/hermes/test_email_responder.py` (ajout de tests)

- [ ] **Step 1: Write the failing test**

Ajouter à `test_email_responder.py` (avant le bloc `if __name__`) :
```python
def _b64url(s):
    import base64
    return base64.urlsafe_b64encode(s.encode("utf-8")).decode("ascii")

def test_parse_thread_extracts_last_sender_and_body():
    thread = {"id": "T1", "messages": [
        {"payload": {"headers": [{"name": "From", "value": "Marie <m@x.fr>"},
                                 {"name": "Subject", "value": "Devis"},
                                 {"name": "Message-ID", "value": "<a@mail>"}],
                     "mimeType": "text/plain",
                     "body": {"data": _b64url("Bonjour, vos prix ?")}}},
    ]}
    p = er.parse_thread(thread)
    assert p["from_email"] == "m@x.fr"
    assert p["from_name"] == "Marie"
    assert p["subject"] == "Devis"
    assert p["message_id"] == "<a@mail>"
    assert "vos prix" in p["conversation"]

def test_parse_thread_multipart_prefers_plain():
    thread = {"id": "T2", "messages": [
        {"payload": {"headers": [{"name": "From", "value": "p@x.fr"}],
                     "mimeType": "multipart/alternative",
                     "parts": [
                         {"mimeType": "text/plain", "body": {"data": _b64url("texte brut")}},
                         {"mimeType": "text/html", "body": {"data": _b64url("<p>html</p>")}},
                     ]}},
    ]}
    p = er.parse_thread(thread)
    assert "texte brut" in p["conversation"]

def test_build_reply_subject():
    assert er.build_reply_subject("Devis") == "Re: Devis"
    assert er.build_reply_subject("Re: Devis") == "Re: Devis"
    assert er.build_reply_subject("RE: Devis") == "RE: Devis"

def test_build_reply_mime_is_html_in_thread():
    raw = er.build_reply_mime("m@x.fr", "Devis", "<p>Bonjour</p>", "<a@mail>", "")
    import base64
    decoded = base64.urlsafe_b64decode(raw + "===").decode("utf-8", "replace")
    assert "To: m@x.fr" in decoded
    assert "Subject: Re: Devis" in decoded
    assert "In-Reply-To: <a@mail>" in decoded
    assert "References: <a@mail>" in decoded
    assert "text/html" in decoded
    assert "<p>Bonjour</p>" in decoded
```

Et compléter le bloc `if __name__ == "__main__":` avec les appels correspondants + `print` :
```python
    test_parse_thread_extracts_last_sender_and_body()
    test_parse_thread_multipart_prefers_plain()
    test_build_reply_subject()
    test_build_reply_mime_is_html_in_thread()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts/hermes && python test_email_responder.py`
Expected: FAIL — `AttributeError: module 'email_responder' has no attribute 'parse_thread'`

- [ ] **Step 3: Write minimal implementation**

Ajouter à `email_responder.py` (après les helpers de Task 2) :
```python
def _decode_part(data_b64url):
    return base64.urlsafe_b64decode(data_b64url + "===").decode("utf-8", "replace")


def _walk_parts(payload):
    """Yield (mimeType, text) pour chaque feuille porteuse de body.data."""
    if "parts" in payload:
        for p in payload["parts"]:
            yield from _walk_parts(p)
    else:
        data = payload.get("body", {}).get("data")
        if data:
            yield payload.get("mimeType", ""), _decode_part(data)


def _extract_plaintext(payload):
    plains, htmls = [], []
    for mime, txt in _walk_parts(payload):
        if mime == "text/plain":
            plains.append(txt)
        elif mime == "text/html":
            htmls.append(txt)
    if plains:
        return "\n".join(plains).strip()
    return re.sub(r"<[^>]+>", " ", "\n".join(htmls)).strip()


def _header(headers, name):
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def parse_thread(thread_json):
    msgs = thread_json.get("messages", [])
    if not msgs:
        return None
    last = msgs[-1]
    h = last.get("payload", {}).get("headers", [])
    from_name, from_email = parseaddr(_header(h, "From"))
    convo = []
    for m in msgs:
        mh = m.get("payload", {}).get("headers", [])
        convo.append(f"--- De: {_header(mh, 'From')} ---\n{_extract_plaintext(m.get('payload', {}))}")
    return {
        "thread_id": thread_json.get("id"),
        "from_email": from_email,
        "from_name": from_name,
        "subject": _header(h, "Subject"),
        "message_id": _header(h, "Message-ID"),
        "references": _header(h, "References"),
        "conversation": "\n\n".join(convo),
    }


def build_reply_subject(subject):
    s = (subject or "").strip()
    return s if s[:3].lower() == "re:" else f"Re: {s}"


def build_reply_mime(to_email, subject, html_body, in_reply_to, references):
    msg = EmailMessage()
    msg["To"] = to_email
    msg["Subject"] = build_reply_subject(subject)
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = (references + " " + in_reply_to).strip() if references else in_reply_to
    msg.set_content(html_body, subtype="html")
    return base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd scripts/hermes && python test_email_responder.py`
Expected: `OK email_responder helpers`

- [ ] **Step 5: Commit**

```bash
git add scripts/hermes/email_responder.py scripts/hermes/test_email_responder.py
git commit -m "feat(hermes): worker email — parsing thread Gmail + MIME réponse"
```

---

## Task 4: Worker — fonctions réseau (Gmail + Claude)

**Files:**
- Modify: `scripts/hermes/email_responder.py`

Pas de test unitaire (I/O réseau) — code complet, validé en smoke test (Task 8).

- [ ] **Step 1: Add network functions**

Ajouter à `email_responder.py` (après les fonctions de Task 3) :
```python
def refresh_access_token():
    import requests
    data = {
        "client_id": os.environ["GMAIL_CLIENT_ID"],
        "client_secret": os.environ["GMAIL_CLIENT_SECRET"],
        "refresh_token": os.environ["GMAIL_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }
    r = requests.post(TOKEN_URL, data=data, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def _gh(token):
    return {"Authorization": f"Bearer {token}"}


def gmail_search(token, query, max_results=15):
    import requests
    r = requests.get(f"{GMAIL_API}/threads", headers=_gh(token),
                     params={"q": query, "maxResults": max_results}, timeout=30)
    r.raise_for_status()
    return [t["id"] for t in r.json().get("threads", [])]


def gmail_get_thread(token, thread_id):
    import requests
    r = requests.get(f"{GMAIL_API}/threads/{thread_id}", headers=_gh(token),
                     params={"format": "full"}, timeout=30)
    r.raise_for_status()
    return r.json()


def gmail_get_or_create_label(token, name):
    import requests
    r = requests.get(f"{GMAIL_API}/labels", headers=_gh(token), timeout=30)
    r.raise_for_status()
    for lbl in r.json().get("labels", []):
        if lbl["name"] == name:
            return lbl["id"]
    r = requests.post(f"{GMAIL_API}/labels", headers=_gh(token),
                      json={"name": name, "labelListVisibility": "labelShow",
                            "messageListVisibility": "show"}, timeout=30)
    r.raise_for_status()
    return r.json()["id"]


def gmail_create_draft(token, thread_id, raw_mime):
    import requests
    r = requests.post(f"{GMAIL_API}/drafts", headers=_gh(token),
                      json={"message": {"threadId": thread_id, "raw": raw_mime}}, timeout=30)
    r.raise_for_status()
    return r.json()


def gmail_add_label(token, thread_id, label_id):
    import requests
    r = requests.post(f"{GMAIL_API}/threads/{thread_id}/modify", headers=_gh(token),
                      json={"addLabelIds": [label_id]}, timeout=30)
    r.raise_for_status()
    return r.json()


def claude_draft(system_prompt, conversation_text):
    import requests
    headers = {
        "x-api-key": os.environ["ANTHROPIC_API_KEY"],
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": MODEL,
        "max_tokens": 1500,
        "system": system_prompt,
        "messages": [{"role": "user", "content":
            "Voici le fil d'emails reçu. Rédige UNIQUEMENT le corps HTML de la réponse "
            "(sans signature, sans balise <html>/<body>), en suivant les règles MY.LAB.\n\n"
            + conversation_text}],
    }
    r = requests.post(ANTHROPIC_API, headers=headers, json=body, timeout=120)
    r.raise_for_status()
    blocks = r.json().get("content", [])
    return "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
```

> **Modèle Claude :** avant de figer `MODEL = "claude-opus-4-8"`, invoquer le skill `claude-api` pour confirmer l'id Opus courant et les paramètres de l'endpoint Messages. Ajuster la constante si besoin.

- [ ] **Step 2: Verify import still clean (no network call at import)**

Run: `cd scripts/hermes && python -c "import email_responder; print('import ok')"`
Expected: `import ok` (les `import requests` sont paresseux, donc l'import du module ne nécessite pas `requests` ni le réseau).

- [ ] **Step 3: Re-run helper tests (régression)**

Run: `cd scripts/hermes && python test_email_responder.py`
Expected: `OK email_responder helpers`

- [ ] **Step 4: Commit**

```bash
git add scripts/hermes/email_responder.py
git commit -m "feat(hermes): worker email — fonctions réseau Gmail REST + Claude API"
```

---

## Task 5: Worker — orchestration `main()`

**Files:**
- Modify: `scripts/hermes/email_responder.py`

- [ ] **Step 1: Add main()**

Ajouter à la fin de `email_responder.py` :
```python
def _load_text(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""


def _short_summary(html_body):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html_body)).strip()[:160]


def main():
    system_prompt = _load_text(PROMPT_PATH)
    signature = _load_text(SIGNATURE_PATH)
    if not system_prompt:
        print("⚠️ *Email responder* — prompt KB introuvable, run annulé")
        return

    token = refresh_access_token()
    label_id = gmail_get_or_create_label(token, DRAFTED_LABEL)

    seen, thread_ids = set(), []
    for q in build_search_queries():
        for tid in gmail_search(token, q, max_results=MAX_PER_RUN):
            if tid not in seen:
                seen.add(tid)
                thread_ids.append(tid)

    capped_remaining = max(0, len(thread_ids) - MAX_PER_RUN)
    thread_ids = thread_ids[:MAX_PER_RUN]

    results = []
    for tid in thread_ids:
        try:
            parsed = parse_thread(gmail_get_thread(token, tid))
            if not parsed or not parsed["from_email"]:
                results.append({"status": "error", "from_email": "?", "error": "thread illisible"})
                continue
            html_body = claude_draft(system_prompt, parsed["conversation"])
            if not html_body:
                results.append({"status": "error", "from_email": parsed["from_email"],
                                "error": "réponse Claude vide"})
                continue
            full_body = append_signature(html_body, signature)
            summary = _short_summary(html_body)
            if DRY_RUN:
                results.append({"status": "drafted", "from_email": parsed["from_email"],
                                "from_name": parsed["from_name"], "subject": parsed["subject"],
                                "summary": "[DRY-RUN] " + summary})
            else:
                raw = build_reply_mime(parsed["from_email"], parsed["subject"], full_body,
                                       parsed["message_id"], parsed["references"])
                gmail_create_draft(token, tid, raw)
                gmail_add_label(token, tid, label_id)
                results.append({"status": "drafted", "from_email": parsed["from_email"],
                                "from_name": parsed["from_name"], "subject": parsed["subject"],
                                "summary": summary})
        except Exception as e:
            results.append({"status": "error", "from_email": "?", "error": str(e)})

    print(format_telegram_summary(results, capped_remaining))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify import + helpers still pass**

Run: `cd scripts/hermes && python -c "import email_responder; print('ok')" && python test_email_responder.py`
Expected: `ok` puis `OK email_responder helpers`

- [ ] **Step 3: Commit**

```bash
git add scripts/hermes/email_responder.py
git commit -m "feat(hermes): worker email — orchestration main (cap, idempotence, dry-run)"
```

---

## Task 6: Helper OAuth Gmail (one-time) + obtention du refresh token

**Files:**
- Create: `scripts/hermes/gmail_oauth_setup.py`

- [ ] **Step 1: Write the OAuth helper**

`scripts/hermes/gmail_oauth_setup.py` :
```python
#!/usr/bin/env python3
"""One-time : obtenir un refresh token Gmail (scope gmail.modify) pour yoann@mylab-shop.com.

Prérequis (Task 0) : client OAuth 'Desktop app' dans le projet mylab-design-studio,
Gmail API activée, yoann@mylab-shop.com en test user.

Usage (PowerShell) :
  $env:GMAIL_CLIENT_ID="..."; $env:GMAIL_CLIENT_SECRET="..."; python scripts/hermes/gmail_oauth_setup.py

Le script ouvre la page de consentement, reçoit le code sur localhost, et imprime
le refresh token à coller dans .env.vps (poste) puis dans /root/.hermes/.env (Task 7).
"""
import http.server
import os
import secrets
import sys
import urllib.parse
import urllib.request
import webbrowser

CLIENT_ID = os.environ["GMAIL_CLIENT_ID"]
CLIENT_SECRET = os.environ["GMAIL_CLIENT_SECRET"]
SCOPE = "https://www.googleapis.com/auth/gmail.modify"
PORT = int(os.environ.get("PORT", "8765"))
REDIRECT = f"http://localhost:{PORT}/callback"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
STATE = secrets.token_urlsafe(16)
RESULT = {}


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if qs.get("state", [None])[0] != STATE or "code" not in qs:
            self._html(400, "<h1>Erreur</h1>")
            return
        body = urllib.parse.urlencode({
            "code": qs["code"][0], "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT, "grant_type": "authorization_code",
        }).encode()
        req = urllib.request.Request(TOKEN_URL, data=body, method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            import json
            data = json.loads(resp.read().decode())
        RESULT.update(data)
        self._html(200, "<h1>OK</h1><p>Refresh token récupéré, retourne au terminal.</p>")
        import threading
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def _html(self, code, html):
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())


def main():
    params = urllib.parse.urlencode({
        "client_id": CLIENT_ID, "redirect_uri": REDIRECT, "response_type": "code",
        "scope": SCOPE, "access_type": "offline", "prompt": "consent", "state": STATE,
        "login_hint": "yoann@mylab-shop.com",
    })
    url = f"{AUTH_URL}?{params}"
    print("Ouvre cette URL et connecte-toi avec yoann@mylab-shop.com :\n")
    print(f"    {url}\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    http.server.HTTPServer(("localhost", PORT), Handler).serve_forever()
    rt = RESULT.get("refresh_token")
    if rt:
        print("\n" + "=" * 60)
        print("SUCCESS — ajoute ces lignes à .env.vps :")
        print(f"GMAIL_CLIENT_ID={CLIENT_ID}")
        print(f"GMAIL_CLIENT_SECRET={CLIENT_SECRET}")
        print(f"GMAIL_REFRESH_TOKEN={rt}")
        print("=" * 60)
    else:
        print(f"\nÉCHEC — pas de refresh_token. Réponse : {RESULT}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the OAuth flow (manuel)**

Run (PowerShell, avec les valeurs de Task 0) :
```powershell
$env:GMAIL_CLIENT_ID="<client_id>"; $env:GMAIL_CLIENT_SECRET="<client_secret>"; python scripts/hermes/gmail_oauth_setup.py
```
Se connecter avec `yoann@mylab-shop.com`, accepter le consentement (écran "app non vérifiée" → "Continuer", normal en mode Testing).
Expected: bloc `SUCCESS` avec `GMAIL_REFRESH_TOKEN=1//...`

- [ ] **Step 3: Stocker les credentials dans `.env.vps`**

Ajouter à `.env.vps` (poste, **gitignored**) les 3 lignes `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN` imprimées.
Verify: `python -c "import os; from dotenv import load_dotenv; load_dotenv('.env.vps'); print(bool(os.environ.get('GMAIL_REFRESH_TOKEN')))"`
Expected: `True`

- [ ] **Step 4: Commit (script seulement, jamais le token)**

```bash
git add scripts/hermes/gmail_oauth_setup.py
git commit -m "feat(hermes): helper OAuth Gmail one-time (refresh token gmail.modify)"
```

---

## Task 7: Script de déploiement (build prompt + upload + env + cron)

**Files:**
- Create: `scripts/hermes/add_email_responder.py`

- [ ] **Step 1: Write the deploy script**

`scripts/hermes/add_email_responder.py` :
```python
"""Déploie le cron email-responder sur le VPS Hermes.

1. Build le system prompt depuis SKILL.md (build_email_prompt.extract_kb_prompt)
2. Lit la signature depuis docs/signature-email.html
3. Upsert GMAIL_* dans /root/.hermes/.env
4. SFTP upload : email_responder.py, email_responder_prompt.md, email_responder_signature.html
5. Crée/maj le cron (idempotent : remove puis create)
6. Test dry-run dans le container

Idempotent : ré-exécutable à volonté (ex : après édition de SKILL.md).
"""
import os
import sys
from pathlib import Path

import paramiko
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_email_prompt import extract_kb_prompt

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env.vps")

SKILL_MD = ROOT / "skills" / "mylab-email-responder" / "SKILL.md"
SIGNATURE_HTML = ROOT / "docs" / "signature-email.html"
WORKER_PY = Path(__file__).resolve().parent / "email_responder.py"

REMOTE_DIR = "/root/.hermes/scripts"
REMOTE_ENV = "/root/.hermes/.env"
CRON_NAME = "email-responder"
CRON_SCHEDULE = "0 9,13,17 * * 1-5"

GMAIL_KEYS = ["GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN"]


def run(ssh, cmd, label=None, timeout=120):
    if label:
        print(f"\n=== {label} ===")
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace").rstrip()
    err = stderr.read().decode(errors="replace").rstrip()
    rc = stdout.channel.recv_exit_status()
    if out:
        print(out)
    if err:
        for l in err.splitlines():
            if l.strip():
                print(f"[stderr] {l}")
    print(f"[rc={rc}]")
    return out, rc


def upsert_env(sftp, remote_path, pairs):
    """Met à jour/ajoute des clés dans un fichier .env distant, sans toucher au reste."""
    try:
        with sftp.open(remote_path, "r") as f:
            lines = f.read().decode("utf-8").splitlines()
    except IOError:
        lines = []
    keys = set(pairs)
    kept = [l for l in lines if l.split("=", 1)[0].strip() not in keys]
    kept += [f"{k}={v}" for k, v in pairs.items()]
    with sftp.open(remote_path, "w") as f:
        f.write("\n".join(kept) + "\n")


def main():
    # 1. Build prompt
    prompt = extract_kb_prompt(SKILL_MD.read_text(encoding="utf-8"))
    signature = SIGNATURE_HTML.read_text(encoding="utf-8").strip()
    worker_src = WORKER_PY.read_text(encoding="utf-8")
    gmail_pairs = {k: os.environ[k] for k in GMAIL_KEYS}  # KeyError clair si manquant

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(os.environ["VPS_HOST"], port=int(os.environ.get("VPS_PORT", "22")),
                username=os.environ["VPS_USER"], password=os.environ["VPS_PASS"], timeout=15)
    sftp = ssh.open_sftp()

    print("[1/5] Upsert GMAIL_* dans /root/.hermes/.env")
    upsert_env(sftp, REMOTE_ENV, gmail_pairs)
    print("  done (3 clés Gmail)")

    print("\n[2/5] Upload worker + prompt + signature")
    with sftp.open(f"{REMOTE_DIR}/email_responder.py", "w") as f:
        f.write(worker_src)
    sftp.chmod(f"{REMOTE_DIR}/email_responder.py", 0o755)
    with sftp.open(f"{REMOTE_DIR}/email_responder_prompt.md", "w") as f:
        f.write(prompt)
    with sftp.open(f"{REMOTE_DIR}/email_responder_signature.html", "w") as f:
        f.write(signature)
    print(f"  done (prompt {len(prompt)} chars, signature {len(signature)} chars)")
    sftp.close()

    print("\n[3/5] Test dry-run dans le container (pas d'écriture Gmail, appelle Claude)")
    run(ssh, "docker exec -e EMAIL_RESPONDER_DRY_RUN=1 hermes-gateway "
             "python /opt/data/scripts/email_responder.py", label="dry-run", timeout=180)

    print("\n[4/5] (Re)création du cron (idempotent)")
    run(ssh, f"docker exec hermes-gateway hermes cron remove {CRON_NAME} 2>/dev/null; true",
        label="remove ancien cron si présent")
    run(ssh, f'docker exec hermes-gateway hermes cron create '
             f'"Auto-draft emails pro MY.LAB" --no-agent '
             f'--script email_responder.py --deliver telegram '
             f'--name {CRON_NAME} --schedule "{CRON_SCHEDULE}"',
        label="cron create")

    print("\n[5/5] Vérif cron")
    run(ssh, "docker exec hermes-gateway hermes cron list", label="cron list")

    ssh.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify the prompt+signature build locally (no SSH)**

Run:
```bash
cd scripts/hermes && python -c "from build_email_prompt import extract_kb_prompt; from pathlib import Path; r=Path('../..').resolve(); p=extract_kb_prompt((r/'skills/mylab-email-responder/SKILL.md').read_text(encoding='utf-8')); print('prompt chars:', len(p)); print('Identité' in p, 'Base de connaissance' in p)"
```
Expected: `prompt chars:` > 5000, puis `True True`. Confirme que l'extraction marche sur le vrai SKILL.md.

- [ ] **Step 3: Confirm signature file exists**

Run: `python -c "from pathlib import Path; print((Path('docs/signature-email.html')).read_text(encoding='utf-8')[:40])"`
Expected: début du HTML de signature (ex `<table`). Si le fichier n'existe pas, le créer depuis le memo `feedback_gmail_signature.md` avant de continuer.

- [ ] **Step 4: Commit**

```bash
git add scripts/hermes/add_email_responder.py
git commit -m "feat(hermes): déploiement cron email-responder (prompt SKILL.md + upload + cron)"
```

---

## Task 8: Déploiement + smoke test end-to-end

**Files:** aucun (exécution).

- [ ] **Step 1: Vérifier les deps du container**

Run: `python scripts/hermes/ssh_run.py "docker exec hermes-gateway python -c 'import requests, dotenv; print(\"deps ok\")'"`
*(ou via une session SSH ad hoc)*
Expected: `deps ok`. Si `ModuleNotFoundError`, installer dans le container : `docker exec hermes-gateway pip install requests python-dotenv` puis re-tester. (Note : `requests` est déjà utilisé par `morning_brief.py`, donc présent en principe.)

- [ ] **Step 2: Lancer le déploiement**

Run: `python scripts/hermes/add_email_responder.py`
Expected: les 5 étapes passent, le dry-run imprime soit `aucun nouveau mail à traiter`, soit un ou plusieurs `[DRY-RUN]` avec un corps de réponse résumé. `cron list` montre `email-responder` avec schedule `0 9,13,17 * * 1-5`.

- [ ] **Step 3: Smoke test réel — déclencher le cron maintenant**

Run: `python scripts/hermes/ssh_run.py "docker exec hermes-gateway hermes cron run email-responder"`
Attendre ~90s (le ticker cron est à 60s, cf. memory).
Expected: Yoann reçoit un message Telegram sur `@mylab_hermes_bot` (`📥 N brouillon(s) prêt(s)` ou `aucun nouveau mail`).

- [ ] **Step 4: Vérifier dans Gmail**

Manuel : ouvrir Gmail yoann@mylab-shop.com → vérifier que les mails non-lus des labels ciblés ont un **brouillon** de réponse dans le thread, avec la signature, et que le thread porte le label `Hermes-Drafted`.
Expected: brouillons présents, pertinents, **aucun email envoyé**, threads taggés.

- [ ] **Step 5: Vérifier l'idempotence**

Run à nouveau: `python scripts/hermes/ssh_run.py "docker exec hermes-gateway hermes cron run email-responder"` (attendre 90s).
Expected: les mails déjà draftés ne sont PAS re-draftés (résumé Telegram = `aucun nouveau mail` si rien de neuf). Pas de doublon de brouillon dans Gmail.

- [ ] **Step 6: Mettre à jour la mémoire projet**

Mettre à jour `project_hermes_agent_vps.md` (section "Cron jobs actifs") avec le nouveau cron `email-responder` (schedule, script, mode agent-API, deps Gmail), et ajouter l'entrée d'index dans `MEMORY.md`. Mentionner le workflow de maintenance : éditer `SKILL.md` → re-run `add_email_responder.py`.

- [ ] **Step 7: Commit final + push**

```bash
git add scripts/hermes/README.md
git commit -m "docs(hermes): README ordre d'exécution email-responder"
git push -u origin feature/stock-mrp-setup
```

---

## Self-Review (rempli par l'auteur du plan)

**Spec coverage :**
- Brouillon uniquement → Task 5 (`DRY_RUN` + jamais `send`), scope `gmail.modify` Task 0/6 ✓
- Labels URGENT + Commandes & Devis, non-lus → Task 2 `LABEL_QUERIES` ✓
- 3×/jour lun-ven → Task 7 `CRON_SCHEDULE="0 9,13,17 * * 1-5"` ✓
- Résumé Telegram → Task 2 `format_telegram_summary` + `--deliver telegram` Task 7 ✓
- OAuth Gmail dédié → Task 0, 6 ✓
- Un thread = un brouillon (idempotence) → Task 4/5 label `Hermes-Drafted` + query `-label:` ✓
- Modèle Opus → Task 4 `MODEL` + note skill claude-api ✓
- KB sourcée de SKILL.md (une source) → Task 1 + Task 7 build ✓
- Cap 15/run → Task 5 `MAX_PER_RUN` + `capped_remaining` ✓
- Isolation erreurs → Task 5 try/except par mail ✓

**Placeholder scan :** modèle Claude = note explicite (skill claude-api), pas un TODO ; tous les blocs de code sont complets. ✓

**Type consistency :** `parse_thread` renvoie `from_email/from_name/subject/message_id/references/conversation/thread_id`, consommés tels quels par `main()` et `build_reply_mime` ✓. `format_telegram_summary(results, capped_remaining)` signature cohérente Task 2/5 ✓.
