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
from email.header import decode_header, make_header
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


def _decode_mime_words(s):
    if not s:
        return s
    try:
        return str(make_header(decode_header(s)))
    except Exception:
        return s


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
    from_name = _decode_mime_words(from_name)
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
        chain = (references + " " + in_reply_to) if references else in_reply_to
        msg["References"] = " ".join(dict.fromkeys(chain.split()))
    msg.set_content(html_body, subtype="html")
    return base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")


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

    fetch_limit = max(MAX_PER_RUN * len(LABEL_QUERIES), 30)
    seen, thread_ids = set(), []
    for q in build_search_queries():
        for tid in gmail_search(token, q, max_results=fetch_limit):
            if tid not in seen:
                seen.add(tid)
                thread_ids.append(tid)

    capped_remaining = max(0, len(thread_ids) - MAX_PER_RUN)
    thread_ids = thread_ids[:MAX_PER_RUN]

    results = []
    for tid in thread_ids:
        from_email_ctx = "?"
        try:
            parsed = parse_thread(gmail_get_thread(token, tid))
            if not parsed or not parsed["from_email"]:
                results.append({"status": "error", "from_email": "?", "error": "thread illisible"})
                continue
            from_email_ctx = parsed["from_email"]
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
                # Draft first, then label. Deliberate: if labeling fails after a successful
                # draft, the worst case is a duplicate draft on the next run (visible,
                # harmless) rather than a silently missing reply — the safer failure mode
                # for a human-review workflow.
                gmail_create_draft(token, tid, raw)
                gmail_add_label(token, tid, label_id)
                results.append({"status": "drafted", "from_email": parsed["from_email"],
                                "from_name": parsed["from_name"], "subject": parsed["subject"],
                                "summary": summary})
        except Exception as e:
            results.append({"status": "error", "from_email": from_email_ctx, "error": str(e)})

    print(format_telegram_summary(results, capped_remaining))


if __name__ == "__main__":
    main()
