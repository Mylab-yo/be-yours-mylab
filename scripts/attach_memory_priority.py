#!/usr/bin/env python3
"""
Attache séquentiellement TOUS les docs non-attachés du vault au workspace
AnythingLLM, dans cet ordre :
  1. Memory/  (mémoires distillées — haute valeur sémantique, petits)
  2. Sessions/ (transcripts bruts — gros, beaucoup de chunks)

Si AnythingLLM crash (server down), attend jusqu'à 90s qu'il revienne,
puis continue. Si toujours down après 90s, sauvegarde le state et exit
proprement — le prochain run reprend où on en est.

State persisté tous les 5 docs, donc aucune perte en cas de coupure.
"""

from __future__ import annotations

import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sync_obsidian_to_anythingllm import (
    load_api_key, list_workspace_docs, attach_one, save_state, load_state,
    wait_server_up, APIError,
)


def server_alive() -> bool:
    try:
        urllib.request.urlopen("http://127.0.0.1:3001/api/ping", timeout=2).read()
        return True
    except Exception:
        return False


def attach_batch(candidates, api_key, state, label, max_server_wait=90):
    """Attach a list of (rel, loc) pairs. Returns (n_ok, n_fail, server_alive_at_end)."""
    if not candidates:
        return 0, 0, True
    print(f"\n=== {label} : {len(candidates)} à attacher ===")
    t0 = time.time()
    n_ok = 0
    n_fail = 0
    for i, (rel, loc) in enumerate(candidates, 1):
        if not server_alive():
            print(f"  serveur down après {i-1} docs, attente jusqu'à {max_server_wait}s...",
                  file=sys.stderr)
            if not wait_server_up(api_key, max_wait=max_server_wait):
                print(f"  serveur toujours down, sauvegarde et exit propre", file=sys.stderr)
                save_state(state)
                return n_ok, n_fail, False

        _, ok, err = attach_one(loc, api_key, timeout=30)
        if ok:
            n_ok += 1
            if rel in state["files"]:
                state["files"][rel]["attached"] = True
            if n_ok % 5 == 0:
                save_state(state)
        else:
            n_fail += 1
            # Truncate the location prefix from error for readability
            print(f"  ! {rel[:70]}: {err[:80]}", file=sys.stderr)

        if i % 10 == 0 or i == len(candidates):
            rate = i / max(time.time() - t0, 0.1)
            eta = (len(candidates) - i) / max(rate, 0.01)
            print(f"  [{i}/{len(candidates)}] ok={n_ok} fail={n_fail} "
                  f"({rate:.2f}/s, ETA {eta:.0f}s)")
        time.sleep(0.2)
    save_state(state)
    return n_ok, n_fail, server_alive()


def main():
    api_key = load_api_key()
    state = load_state()
    files = state.get("files") or {}

    attached_now = list_workspace_docs(api_key)

    memory = [(rel, info["location"]) for rel, info in files.items()
              if rel.startswith("Memory/") and info.get("location")
              and info["location"] not in attached_now]
    sessions = [(rel, info["location"]) for rel, info in files.items()
                if rel.startswith("Sessions/") and info.get("location")
                and info["location"] not in attached_now]

    print(f"Workspace actuel : {len(attached_now)} docs")
    print(f"Memory à attacher : {len(memory)}")
    print(f"Sessions à attacher : {len(sessions)}")

    total_ok = 0
    total_fail = 0

    # Pass 1 : Memory
    ok, fail, alive = attach_batch(memory, api_key, state, "Memory")
    total_ok += ok
    total_fail += fail
    if not alive:
        print(f"\nServer toujours down après Memory pass, exit. Total : {total_ok} ok, {total_fail} fail")
        return

    # Pass 2 : Sessions
    ok, fail, alive = attach_batch(sessions, api_key, state, "Sessions")
    total_ok += ok
    total_fail += fail

    # Final reconcile
    try:
        final_attached = list_workspace_docs(api_key)
        for rel, info in state["files"].items():
            if info.get("location") in final_attached:
                info["attached"] = True
        save_state(state)
        print(f"\n=== Bilan ===")
        print(f"  Workspace final : {len(final_attached)} docs attachés")
        print(f"  Ajouts session  : {total_ok} ok, {total_fail} fail")
    except APIError as e:
        print(f"Reconcile FAIL : {e}")


if __name__ == "__main__":
    main()
