# -*- coding: utf-8 -*-
"""Read-only : compare le code LIVE de l'action 'Repartir en cartons' au fichier repo."""
from pathlib import Path
import _client as odoo

ACTION_NAME = "Répartir en cartons"
acts = odoo.search_read("ir.actions.server", [("name", "=", ACTION_NAME)],
                        ["id", "name", "model_id", "code"])
print(f"=== {len(acts)} action(s) '{ACTION_NAME}' ===")
repo = Path(__file__).with_name("server_action_code.py").read_text(encoding="utf-8")
for a in acts:
    live = a["code"] or ""
    same = live.strip() == repo.strip()
    print(f"  id={a['id']} model={a['model_id']} | live_len={len(live)} repo_len={len(repo)} | IDENTIQUE={same}")
    if not same:
        # montre les 1res divergences ligne a ligne
        ll = live.splitlines()
        rl = repo.splitlines()
        for i in range(max(len(ll), len(rl))):
            a_ = ll[i] if i < len(ll) else "<absente>"
            b_ = rl[i] if i < len(rl) else "<absente>"
            if a_ != b_:
                print(f"    L{i+1} DIFF\n      live: {a_!r}\n      repo: {b_!r}")
                break
