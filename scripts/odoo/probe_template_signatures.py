"""Dump how signature is embedded in templates 34 (devis), 18 (facture), 37 (relance). Read-only."""
import re
from _client import search_read

for tid in (34, 18, 37):
    t = search_read("mail.template", [("id", "=", tid)], ["id", "name", "body_html"])
    if not t:
        print(f"--- template {tid} INTROUVABLE ---")
        continue
    body = t[0].get("body_html") or ""
    print(f"\n{'='*70}\n=== TEMPLATE {tid} : {t[0]['name']} (len={len(body)}) ===\n{'='*70}")
    # montre les zones autour du mot 'signature' et la fin du corps
    for m in re.finditer(r"signature", body, re.I):
        s = max(0, m.start() - 200)
        print(f"\n  ...[ctx @{m.start()}]... {body[s:m.end()+200]!r}")
    print(f"\n  --- 900 derniers caracteres ---\n{body[-900:]!r}")
