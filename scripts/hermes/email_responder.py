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
