"""step41 — Separe les identites d'envoi : contact@ (devis) / comptabilite@ (compta).

Idempotent. Au 1er passage, remplace le bloc signature existant (en dur ou dynamique)
par la signature cible encadree de marqueurs. Aux passages suivants, remplace simplement
le contenu entre marqueurs.

Usage :
    python step41_split_mail_identities.py --dry-run   # inspecte, n'ecrit rien
    python step41_split_mail_identities.py             # backup puis ecrit
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from _client import search_read, write

REPO = Path(__file__).resolve().parents[2]
SIG_FILES = {
    "contact": REPO / "docs" / "signature-email-contact.html",
    "compta": REPO / "docs" / "signature-email-comptabilite.html",
}
BACKUP = Path(__file__).resolve().parent / "backups" / "mail_templates_pre-identity-split_2026-07-15.json"

MARK_START = "<!-- ML_SIG_START -->"
MARK_END = "<!-- ML_SIG_END -->"

CONTACT_FROM = '"MY.LAB" <contact@mylab-shop.com>'
CONTACT_REPLY = "contact@mylab-shop.com"
COMPTA_FROM = '"MY.LAB – Comptabilité" <comptabilite@mylab-shop.com>'
COMPTA_REPLY = "comptabilite@mylab-shop.com"

ROUTING = {
    34: ("contact", CONTACT_FROM, CONTACT_REPLY),
    18: ("compta", COMPTA_FROM, COMPTA_REPLY),
    20: ("compta", COMPTA_FROM, COMPTA_REPLY),
    35: ("compta", COMPTA_FROM, COMPTA_REPLY),
    36: ("compta", COMPTA_FROM, COMPTA_REPLY),
    37: ("compta", COMPTA_FROM, COMPTA_REPLY),
    38: ("compta", COMPTA_FROM, COMPTA_REPLY),
    39: ("compta", COMPTA_FROM, COMPTA_REPLY),
}

# 1. deja marque (passages >= 2)
RE_MARKED = re.compile(re.escape(MARK_START) + r".*?" + re.escape(MARK_END), re.S)
# 2. bloc signature dynamique Odoo (tpl 34, 20) ; groupe 1 = nom du champ (user_id, invoice_user_id...)
RE_USER_SIG = re.compile(
    r'<t t-if="not is_html_empty\(object\.(\w+)\.signature\)".*?</t>\s*</t>', re.S
)
# 3. signature en dur (tpl 18, 35-39) : table contenant l'adresse, sans table imbriquee
RE_HARD_SIG = re.compile(
    r"<table\b(?:(?!<table\b).)*?231 Avenue de la Voguette.*?</table>", re.S
)


def wrap(sig_html):
    return f"{MARK_START}{sig_html}{MARK_END}"


def inject(body, sig_html):
    """Retourne (nouveau_body, strategie). Leve ValueError si aucun point d'ancrage."""
    block = wrap(sig_html)
    if RE_MARKED.search(body):
        return RE_MARKED.sub(lambda _: block, body, count=1), "marqueurs"
    m = RE_USER_SIG.search(body)
    if m:
        field = m.group(1)
        new_body = body[:m.start()] + block + body[m.end():]
        return new_body, f"{field}.signature"
    if RE_HARD_SIG.search(body):
        return RE_HARD_SIG.sub(lambda _: block, body, count=1), "signature en dur"
    raise ValueError("aucun point d'ancrage signature trouve")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="inspecte sans ecrire")
    args = ap.parse_args()

    sigs = {}
    for key, path in SIG_FILES.items():
        if not path.exists():
            print(f"ABANDON — signature introuvable : {path}")
            return 1
        sigs[key] = path.read_text(encoding="utf-8").strip()

    rows = search_read(
        "mail.template", [("id", "in", sorted(ROUTING))],
        ["id", "name", "email_from", "reply_to", "body_html"],
    )
    found = {r["id"]: r for r in rows}
    missing = sorted(set(ROUTING) - set(found))
    if missing:
        print(f"ABANDON — templates introuvables : {missing}")
        return 1

    # Plan construit AVANT tout backup : un ancrage introuvable doit sortir sans
    # avoir touche au backup (rows est deja fige, deplacer le backup plus loin
    # ne change rien a sa fidelite).
    plan = []
    for tpl_id in sorted(ROUTING):
        identite, want_from, want_reply = ROUTING[tpl_id]
        t = found[tpl_id]
        try:
            new_body, strategie = inject(t.get("body_html") or "", sigs[identite])
        except ValueError as exc:
            print(f"ABANDON — tpl {tpl_id} ({t['name']}) : {exc}. Aucune ecriture effectuee.")
            return 1
        plan.append((tpl_id, t, identite, want_from, want_reply, new_body, strategie))

    print(f"\n{'=' * 72}")
    for tpl_id, t, identite, want_from, want_reply, new_body, strategie in plan:
        print(f"tpl {tpl_id:>2} {t['name'][:34]:<36} [{identite}] via {strategie}")
        print(f"      from  {t.get('email_from')!r}")
        print(f"        ->  {want_from!r}")
        print(f"      reply {t.get('reply_to')!r} -> {want_reply!r}")
        print(f"      body  {len(t.get('body_html') or '')} -> {len(new_body)} car.")

    if args.dry_run:
        print(f"\n--dry-run : aucune ecriture. {len(plan)} templates seraient modifies.")
        return 0

    # Backup APRES validation du plan, juste AVANT la boucle d'ecriture. Le backup
    # a une semantique "etat pre-bascule" : il ne doit etre ecrit qu'une seule fois,
    # au tout premier run reel — un rejeu ne doit jamais l'ecraser avec l'etat deja
    # splitte, sinon le seul chemin de rollback disparait.
    if BACKUP.exists():
        print(f"Backup deja present, conserve tel quel (etat vierge pre-bascule) : {BACKUP}")
    else:
        try:
            BACKUP.parent.mkdir(parents=True, exist_ok=True)
            BACKUP.write_text(
                json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            print(f"Backup ecrit : {BACKUP} ({len(rows)} templates)")
        except Exception as exc:
            print(f"ABANDON — backup impossible : {exc}. Aucune ecriture effectuee.")
            return 1

    for tpl_id, _t, _identite, want_from, want_reply, new_body, _strategie in plan:
        write("mail.template", [tpl_id], {
            "email_from": want_from,
            "reply_to": want_reply,
            "body_html": new_body,
        })
        print(f"  ecrit tpl {tpl_id}")

    print(f"\n{len(plan)} templates mis a jour. Lancer verify_mail_identities.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
