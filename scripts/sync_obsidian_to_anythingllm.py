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

    # Attach to workspace ONE doc at a time. Empirically, AnythingLLM Desktop
    # processes multi-doc batches much slower than serial single-doc calls
    # (probable internal lock or O(n²) re-indexing). Single-doc calls return
    # in 0.1-3s each thanks to per-call caching.
    deletes = to_delete_old_loc + [loc for _, loc in removed]
    PER_CALL_TIMEOUT = 30
    if pending_attach:
        if verbose:
            print(f"Attach au workspace : {len(pending_attach)} docs, 1 par appel")
        # Handle deletes first (single call)
        if deletes:
            try:
                update_embeddings_batch([], deletes, api_key, timeout=PER_CALL_TIMEOUT)
            except APIError as e:
                print(f"  ! deletes initiaux : {e}", file=sys.stderr)

        loc_to_rel = {info["location"]: rel for rel, info in new_state["files"].items() if info.get("location")}
        t_start = time.time()
        for i, loc in enumerate(pending_attach, 1):
            try:
                update_embeddings_batch([loc], [], api_key, timeout=PER_CALL_TIMEOUT)
            except APIError as e:
                print(f"  ! {loc[:80]} : {e}", file=sys.stderr)
                continue
            rel = loc_to_rel.get(loc)
            if rel and rel in new_state["files"]:
                new_state["files"][rel]["attached"] = True
            # Save state every 10 docs to limit IO without losing too much progress
            if i % 10 == 0:
                save_state(new_state)
                if verbose:
                    rate = i / max(time.time() - t_start, 0.1)
                    eta = (len(pending_attach) - i) / max(rate, 0.01)
                    print(f"  attaché {i}/{len(pending_attach)} ({rate:.1f}/s, ETA {eta:.0f}s)")
        save_state(new_state)
    elif deletes:
        try:
            update_embeddings_batch([], deletes, api_key, timeout=PER_CALL_TIMEOUT)
        except APIError as e:
            print(f"  ! update-embeddings deletes : {e}", file=sys.stderr)

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--reset", action="store_true", help="Vide le state local (force full re-sync)")
    args = ap.parse_args()

    if args.reset:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
            print(f"State wiped: {STATE_FILE}")
        else:
            print("Pas de state à wipe.")
        return

    sync(dry_run=args.dry_run, verbose=args.verbose)


if __name__ == "__main__":
    main()
