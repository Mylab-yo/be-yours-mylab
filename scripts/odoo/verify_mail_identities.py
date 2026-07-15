"""Verifie l'etat cible des 8 templates mail (identites contact@ / comptabilite@).

Exit 0 si conforme, 1 sinon. Volontairement independant de step41 : un verificateur
qui partagerait le code d'injection validerait ses propres bugs.
"""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from _client import search_read

MARK_START = "<!-- ML_SIG_START -->"
MARK_END = "<!-- ML_SIG_END -->"

CONTACT_FROM = '"MY.LAB" <contact@mylab-shop.com>'
CONTACT_REPLY = "contact@mylab-shop.com"
COMPTA_FROM = '"MY.LAB – Comptabilité" <comptabilite@mylab-shop.com>'
COMPTA_REPLY = "comptabilite@mylab-shop.com"

# tpl_id -> (identite, email_from attendu, reply_to attendu)
EXPECTED = {
    34: ("contact", CONTACT_FROM, CONTACT_REPLY),
    18: ("compta", COMPTA_FROM, COMPTA_REPLY),
    20: ("compta", COMPTA_FROM, COMPTA_REPLY),
    35: ("compta", COMPTA_FROM, COMPTA_REPLY),
    36: ("compta", COMPTA_FROM, COMPTA_REPLY),
    37: ("compta", COMPTA_FROM, COMPTA_REPLY),
    38: ("compta", COMPTA_FROM, COMPTA_REPLY),
    39: ("compta", COMPTA_FROM, COMPTA_REPLY),
}

# Marqueurs d'identite attendus DANS le bloc signature injecte
SIG_MARKERS = {
    "contact": ("Yoann DURAND", "contact@mylab-shop.com", "comptabilite@mylab-shop.com"),
    "compta": ("MY.LAB", "comptabilite@mylab-shop.com", None),
}


def check(tpl_id, identite, want_from, want_reply, failures):
    rows = search_read(
        "mail.template", [("id", "=", tpl_id)],
        ["id", "name", "email_from", "reply_to", "body_html"],
    )
    if not rows:
        failures.append(f"tpl {tpl_id}: introuvable")
        return
    t = rows[0]
    body = t.get("body_html") or ""
    tag = f"tpl {tpl_id} ({t['name']})"

    if t.get("email_from") != want_from:
        failures.append(f"{tag}: email_from={t.get('email_from')!r} attendu {want_from!r}")
    if t.get("reply_to") != want_reply:
        failures.append(f"{tag}: reply_to={t.get('reply_to')!r} attendu {want_reply!r}")

    n_start, n_end = body.count(MARK_START), body.count(MARK_END)
    if n_start != 1 or n_end != 1:
        failures.append(f"{tag}: marqueurs signature = {n_start} start / {n_end} end, attendu 1/1")
        return

    sig = body.split(MARK_START, 1)[1].split(MARK_END, 1)[0]
    must_a, must_b, must_not = SIG_MARKERS[identite]
    if must_a not in sig:
        failures.append(f"{tag}: signature sans {must_a!r}")
    if must_b not in sig:
        failures.append(f"{tag}: signature sans {must_b!r}")
    if must_not and must_not in sig:
        failures.append(f"{tag}: signature contient {must_not!r} alors qu'elle est {identite}")

    if "user_id.signature" in body:
        failures.append(f"{tag}: reference residuelle a user_id.signature")
    if "231 Avenue de la Voguette" in body.replace(sig, ""):
        failures.append(f"{tag}: bloc signature residuel HORS marqueurs (double signature)")


def main():
    failures = []
    for tpl_id, (identite, want_from, want_reply) in sorted(EXPECTED.items()):
        check(tpl_id, identite, want_from, want_reply, failures)

    if failures:
        print(f"ECHEC — {len(failures)} probleme(s) :")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"OK — les {len(EXPECTED)} templates sont conformes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
