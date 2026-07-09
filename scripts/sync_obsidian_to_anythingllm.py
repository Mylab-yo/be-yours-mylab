#!/usr/bin/env python3
"""
Synchronise le vault Obsidian (`C:\\Users\\startec\\Documents\\MyLab`) avec le
workspace "MyLab" de AnythingLLM Desktop tournant en local sur :3001.

Conçu pour tourner via Windows Task Scheduler tous les jours à 17h00.
État sauvé dans %LOCALAPPDATA%\\anythingllm-sync\\state.json (hors repo).

Comportement
------------
- Scan récursif `Sessions/**/*.md` + `Memory/**/*.md`
- Hash MD5 par fichier pour détecter les changements
- Fichier nouveau ou modifié → upload via API → embed dans workspace
- Fichier supprimé du vault → retire du workspace
- Idempotent : ré-exécution ne fait que les deltas

Auth
----
Clé API lue dans (ordre de priorité) :
  1. Variable d'env ANYTHINGLLM_API_KEY
  2. Fichier `<repo>/.env.local` avec `ANYTHINGLLM_API_KEY=...`

Endpoints AnythingLLM utilisés (REST v1)
----------------------------------------
- POST /api/v1/document/raw-text          → upload texte → doc location
- POST /api/v1/workspace/<slug>/update-embeddings  → add/delete docs au workspace
- POST /api/v1/system/remove-documents    → suppression définitive du système
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

VAULT = Path(r"C:\Users\startec\Documents\MyLab")
WORKSPACE_SLUG = "mylab"
API_BASE = "http://127.0.0.1:3001/api/v1"

REPO_ROOT = Path(r"d:\be-yours-mylab")
ENV_LOCAL = REPO_ROOT / ".env.local"

STATE_DIR = Path(os.environ["LOCALAPPDATA"]) / "anythingllm-sync"
STATE_FILE = STATE_DIR / "state.json"

# Files to sync (relative to VAULT)
SYNC_GLOBS = ["Sessions/**/*.md", "Memory/**/*.md"]


# ---------------------------------------------------------------------------
# API key loading
# ---------------------------------------------------------------------------


def load_api_key() -> str:
    key = os.environ.get("ANYTHINGLLM_API_KEY", "").strip()
    if key:
        return key
    if ENV_LOCAL.exists():
        for line in ENV_LOCAL.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("ANYTHINGLLM_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError(
        "ANYTHINGLLM_API_KEY introuvable. Place-la dans .env.local ou la variable d'env."
    )


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


class APIError(Exception):
    pass


def api_request(method: str, path: str, api_key: str, body: dict | None = None, timeout: float = 60) -> dict:
    url = f"{API_BASE}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Accept", "application/json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            if not raw:
                return {}
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")[:500]
        raise APIError(f"HTTP {e.code} on {method} {path}: {err_body}") from e
    except TimeoutError as e:
        raise APIError(f"timed out after {timeout}s on {method} {path}") from e
    except urllib.error.URLError as e:
        raise APIError(f"URL error on {method} {path}: {e.reason}") from e
    except (ConnectionResetError, ConnectionAbortedError, ConnectionRefusedError, BrokenPipeError) as e:
        raise APIError(f"connection lost ({type(e).__name__}) on {method} {path}") from e
    except Exception as e:
        raise APIError(f"unexpected {type(e).__name__} on {method} {path}: {e}") from e


# ---------------------------------------------------------------------------
# Vault scan + state
# ---------------------------------------------------------------------------


def md5_file(p: Path) -> str:
    h = hashlib.md5()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_vault() -> dict[str, dict]:
    """Returns {rel_path: {hash, mtime, size}} for every md to sync."""
    out = {}
    for pattern in SYNC_GLOBS:
        for p in VAULT.glob(pattern):
            if not p.is_file():
                continue
            # Skip index files — regenerated each run, not knowledge
            if p.name == "index.md":
                continue
            rel = p.relative_to(VAULT).as_posix()
            out[rel] = {
                "hash": md5_file(p),
                "mtime": p.stat().st_mtime,
                "size": p.stat().st_size,
            }
    return out


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_state(state: dict):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Sync ops
# ---------------------------------------------------------------------------


def _to_rel_location(loc: str) -> str:
    """AnythingLLM raw-text returns an absolute path. The workspace endpoints
    expect a path relative to `storage/documents/`, e.g. 'custom-documents/xxx.json'.
    Convert absolute → relative; if already relative, return as-is."""
    if not loc:
        return loc
    norm = loc.replace("\\", "/")
    marker = "/documents/"
    idx = norm.rfind(marker)
    if idx != -1:
        return norm[idx + len(marker):]
    return norm  # assume already relative


def upload_doc(rel_path: str, content: str, api_key: str) -> str:
    """POST raw-text → returns RELATIVE doc location ('custom-documents/raw-xxx.json')."""
    payload = {
        "textContent": content,
        "metadata": {
            "title": rel_path,
            "description": f"Obsidian vault file {rel_path}",
            "docSource": "obsidian-mylab",
            "chunkSource": "obsidian",
            "published": datetime.now().astimezone().isoformat(),
        },
    }
    resp = api_request("POST", "/document/raw-text", api_key, payload)
    docs = resp.get("documents") or []
    if not docs:
        raise APIError(f"raw-text returned no documents for {rel_path}: {resp}")
    raw_loc = docs[0].get("location") or docs[0].get("path") or ""
    return _to_rel_location(raw_loc)


def update_embeddings_batch(adds: list[str], deletes: list[str], api_key: str, timeout: float = 300):
    """One workspace embeddings update call. Caller batches."""
    if not adds and not deletes:
        return
    api_request(
        "POST",
        f"/workspace/{WORKSPACE_SLUG}/update-embeddings",
        api_key,
        {"adds": adds, "deletes": deletes},
        timeout=timeout,
    )


def list_workspace_docs(api_key: str) -> set[str]:
    """Return the set of locations currently attached to the workspace."""
    resp = api_request("GET", f"/workspace/{WORKSPACE_SLUG}", api_key, timeout=15)
    ws = resp.get("workspace") or resp
    if isinstance(ws, list) and ws:
        ws = ws[0]
    docs = ws.get("documents") or []
    out = set()
    for d in docs:
        loc = d.get("docpath") or d.get("location")
        if loc:
            out.add(loc)
    return out


def attach_one(loc: str, api_key: str, timeout: float = 15) -> tuple[str, bool, str]:
    """Single-doc attach. Returns (loc, ok, error_msg)."""
    try:
        update_embeddings_batch([loc], [], api_key, timeout=timeout)
        return loc, True, ""
    except APIError as e:
        return loc, False, str(e)[:100]


def attach_parallel(locations: list[str], api_key: str, workers: int = 4,
                    timeout: float = 15, verbose: bool = False) -> dict[str, bool]:
    """Fire N concurrent attach requests. Returns {loc: ok_or_not}.
    NOTE: AnythingLLM Desktop tends to crash under parallel load.
    Prefer attach_sequential for the initial seed."""
    results: dict[str, bool] = {}
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(attach_one, loc, api_key, timeout): loc for loc in locations}
        done = 0
        for fut in as_completed(futures):
            loc, ok, err = fut.result()
            results[loc] = ok
            done += 1
            if verbose and done % 20 == 0:
                rate = done / max(time.time() - t0, 0.1)
                print(f"  fired {done}/{len(locations)} ({rate:.1f}/s, {sum(results.values())} OK)")
    return results


def wait_server_up(api_key: str, max_wait: float = 60, verbose: bool = False) -> bool:
    """Block until /api/ping returns 200 or max_wait elapsed. Returns True if up."""
    t0 = time.time()
    while time.time() - t0 < max_wait:
        try:
            urllib.request.urlopen("http://127.0.0.1:3001/api/ping", timeout=2).read()
            return True
        except Exception:
            time.sleep(2)
    return False


def attach_sequential(locations: list[str], api_key: str,
                      callback,
                      timeout: float = 60, pause: float = 0.3,
                      verbose: bool = False) -> dict[str, bool]:
    """Sequential single-doc attach. Survives server crashes (waits for restart).
    callback(loc, ok) is called after each attempt — use it to update state."""
    results: dict[str, bool] = {}
    t0 = time.time()
    for i, loc in enumerate(locations, 1):
        # Soft pause between requests to not flood the server
        if pause > 0:
            time.sleep(pause)
        # Check server is up before firing
        try:
            urllib.request.urlopen("http://127.0.0.1:3001/api/ping", timeout=2).read()
        except Exception:
            if verbose:
                print(f"  serveur down, attente jusqu'à 60s...", file=sys.stderr)
            if not wait_server_up(api_key, max_wait=60, verbose=verbose):
                print(f"  serveur toujours down après 60s, abandon à {i-1}/{len(locations)}",
                      file=sys.stderr)
                break
        loc_, ok, err = attach_one(loc, api_key, timeout)
        results[loc] = ok
        callback(loc, ok)
        if verbose and (i % 10 == 0 or i == len(locations)):
            n_ok = sum(results.values())
            rate = i / max(time.time() - t0, 0.1)
            eta = (len(locations) - i) / max(rate, 0.01)
            print(f"  [{i}/{len(locations)}] {n_ok} OK, {rate:.2f}/s, ETA {eta:.0f}s")
    return results


def wait_for_attach_settle(api_key: str, initial_count: int,
                           target_count: int | None = None,
                           verbose: bool = False) -> int:
    """Server may still be processing after our client timeouts.
    Poll workspace docs until count stable for STABLE_POLLS rounds.
    Returns final count."""
    POLL_INTERVAL = 15
    STABLE_POLLS = 4  # 60s of no progress = settled
    last = initial_count
    stable = 0
    while True:
        time.sleep(POLL_INTERVAL)
        try:
            cur = len(list_workspace_docs(api_key))
        except APIError:
            cur = last
        if cur == last:
            stable += 1
            if verbose:
                print(f"  poll : {cur} (stable {stable}/{STABLE_POLLS})")
            if stable >= STABLE_POLLS:
                return cur
        else:
            if verbose:
                print(f"  poll : {cur} (+{cur - last})")
            stable = 0
            last = cur
        if target_count and cur >= target_count:
            return cur


def remove_from_system(locations: list[str], api_key: str):
    """Permanently remove documents from AnythingLLM (not just the workspace)."""
    if not locations:
        return
    # AnythingLLM exposes this on the DELETE verb (not POST)
    api_request(
        "DELETE",
        "/system/remove-documents",
        api_key,
        {"names": locations},
        timeout=120,
    )


# ---------------------------------------------------------------------------
# Main sync driver
# ---------------------------------------------------------------------------


def sync(dry_run: bool = False, verbose: bool = False):
    api_key = load_api_key()

    # Validate auth + workspace exists
    try:
        api_request("GET", "/auth", api_key)
    except APIError as e:
        print(f"ERREUR auth : {e}", file=sys.stderr)
        sys.exit(2)

    state = load_state()
    # state shape: { rel_path: {hash, location} }
    prev = {k: v for k, v in state.get("files", {}).items()}
    current = scan_vault()

    to_upload = []  # list of (rel_path, content)
    to_delete_old_loc = []  # locations of previous versions to drop from workspace + system

    for rel, info in current.items():
        prev_info = prev.get(rel)
        if prev_info and prev_info.get("hash") == info["hash"]:
            continue  # unchanged
        # New or modified
        full = VAULT / rel
        try:
            content = full.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            print(f"  ! skip {rel}: {e}", file=sys.stderr)
            continue
        to_upload.append((rel, content, info["hash"]))
        if prev_info and prev_info.get("location"):
            to_delete_old_loc.append(prev_info["location"])

    # Files removed from vault since last sync
    removed = [(rel, prev[rel]["location"]) for rel in prev if rel not in current and prev[rel].get("location")]

    if verbose or dry_run:
        print(f"Vault   : {len(current)} fichiers")
        print(f"State   : {len(prev)} fichiers en cache")
        print(f"Nouveaux/modifs : {len(to_upload)}")
        print(f"Supprimés : {len(removed)}")

    if dry_run:
        for rel, _, _ in to_upload[:20]:
            print(f"  + {rel}")
        for rel, _ in removed[:20]:
            print(f"  - {rel}")
        return

    # Apply uploads with incremental state save (survives crashes / timeouts)
    new_state = {"last_sync": datetime.now().isoformat(), "files": dict(prev)}
    pending_attach: list[str] = []  # locations uploaded but not yet attached to workspace
    # Carry over any docs from previous run that were uploaded but never attached
    for rel, info in prev.items():
        if info.get("location") and not info.get("attached"):
            pending_attach.append(info["location"])

    t0 = time.time()
    for i, (rel, content, h) in enumerate(to_upload, 1):
        try:
            loc = upload_doc(rel, content, api_key)
        except APIError as e:
            print(f"  ! upload {rel}: {e}", file=sys.stderr)
            continue
        pending_attach.append(loc)
        new_state["files"][rel] = {
            "hash": h,
            "location": loc,
            "synced_at": time.time(),
            "attached": False,
        }
        save_state(new_state)  # incremental — never lose progress
        if verbose or (i % 25 == 0):
            print(f"  [{i}/{len(to_upload)}] uploaded {rel}")

    # Apply removals from state
    for rel, _ in removed:
        new_state["files"].pop(rel, None)

    # Attach to workspace: parallel fire + server-side settle + reconcile.
    # AnythingLLM Desktop tends to time out client-side on big docs while
    # finishing the work server-side. So we:
    #   1) Fire all requests in parallel with short timeout (don't care about errors)
    #   2) Poll workspace until count stops growing
    #   3) Read the actual workspace doc list and update state from ground truth
    #   4) Retry pass for any still-missing docs
    deletes = to_delete_old_loc + [loc for _, loc in removed]
    if deletes:
        try:
            update_embeddings_batch([], deletes, api_key, timeout=60)
        except APIError as e:
            print(f"  ! deletes initiaux : {e}", file=sys.stderr)

    if pending_attach:
        loc_to_rel = {info["location"]: rel for rel, info in new_state["files"].items()
                      if info.get("location")}

        # Initial state for delta tracking
        try:
            initial_attached = list_workspace_docs(api_key)
        except APIError:
            initial_attached = set()
        if verbose:
            print(f"Attach au workspace : {len(pending_attach)} pending, "
                  f"{len(initial_attached)} déjà attachés. Mode séquentiel (1 worker, robuste).")

        # Callback to update state.json after each successful attach
        def on_attach(loc, ok):
            if not ok:
                return
            for rel, info in new_state["files"].items():
                if info.get("location") == loc:
                    info["attached"] = True
                    break
            # Save state every 5 successful attaches to keep checkpoints fresh
            n = sum(1 for f in new_state["files"].values() if f.get("attached"))
            if n % 5 == 0:
                save_state(new_state)

        # Pass 1 : sequential fire, survives server crashes
        attach_sequential(pending_attach, api_key, on_attach,
                          timeout=60, pause=0.3, verbose=verbose)
        save_state(new_state)

        # Pass 2 : poll until server-side processing settles
        if verbose:
            print("Poll du workspace en attendant settle...")
        final_count = wait_for_attach_settle(
            api_key, len(initial_attached),
            target_count=len(initial_attached) + len(pending_attach),
            verbose=verbose,
        )
        if verbose:
            print(f"Workspace stable à {final_count} docs.")

        # Pass 3 : reconcile state from ground truth (catches docs that attached
        # server-side after a client timeout)
        try:
            attached_set = list_workspace_docs(api_key)
            for rel, info in new_state["files"].items():
                if info.get("location") in attached_set:
                    info["attached"] = True
            save_state(new_state)
        except APIError as e:
            print(f"  ! reconcile : {e}", file=sys.stderr)

    # Permanently remove obsolete docs from the system
    if deletes:
        try:
            remove_from_system(deletes, api_key)
        except APIError as e:
            print(f"  ! remove-documents: {e}", file=sys.stderr)

    save_state(new_state)
    elapsed = time.time() - t0
    n_attached = sum(1 for f in new_state["files"].values() if f.get("attached"))
    print(
        f"Sync OK · {len(pending_attach)} attache(s) tente(s) · "
        f"{n_attached}/{len(new_state['files'])} attaches · "
        f"{len(deletes)} suppressions · {elapsed:.0f}s"
    )


def reconcile():
    """Read the workspace's actual attached docs and update state.json."""
    api_key = load_api_key()
    state = load_state()
    files = state.get("files") or {}
    if not files:
        print("State vide, rien à reconcilier.")
        return
    attached_set = list_workspace_docs(api_key)
    n_now_attached = 0
    n_now_detached = 0
    for rel, info in files.items():
        loc = info.get("location")
        was = bool(info.get("attached"))
        is_ = loc in attached_set
        info["attached"] = is_
        if is_ and not was:
            n_now_attached += 1
        elif was and not is_:
            n_now_detached += 1
    save_state(state)
    total_attached = sum(1 for f in files.values() if f.get("attached"))
    print(f"Reconcile : {total_attached}/{len(files)} attachés "
          f"(+{n_now_attached} découverts, -{n_now_detached} perdus)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--reset", action="store_true", help="Vide le state local (force full re-sync)")
    ap.add_argument("--reconcile", action="store_true",
                    help="Met juste à jour state.json depuis l'état réel du workspace, sans rien upload/attach")
    args = ap.parse_args()

    if args.reset:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
            print(f"State wiped: {STATE_FILE}")
        else:
            print("Pas de state à wipe.")
        return

    if args.reconcile:
        reconcile()
        return

    sync(dry_run=args.dry_run, verbose=args.verbose)


if __name__ == "__main__":
    main()
