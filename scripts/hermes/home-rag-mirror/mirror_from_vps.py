#!/usr/bin/env python3
"""Miroir RAG : copie les documents de la base VPS (AnythingLLM) vers une AnythingLLM LOCALE.

À lancer SUR LE PC MAISON (celui du Hermes llama.cpp/llama-swap). Pull-only : c'est la
maison qui va chercher sur le VPS (le VPS, lui, ne peut pas joindre la maison derrière NAT).

Source VPS  : fichiers bruts `/root/anythingllm/storage/documents/custom-documents/*.json`
              (chaque JSON contient `title` + `pageContent`), récupérés par SFTP.
Cible locale: AnythingLLM sur LOCAL_ANYTHINGLLM_URL, workspace WORKSPACE, clé LOCAL_ANYTHINGLLM_KEY.

Idempotent : hash MD5 du `pageContent` par titre (état dans `.mirror_state.json`).
Gère les suppressions : un doc retiré du VPS est retiré du workspace local.

Config — variables d'env, ou fichier `.env` à côté de ce script :
  VPS_HOST, VPS_PORT, VPS_USER, VPS_PASS     accès SFTP au VPS (mêmes creds que .env.vps)
  LOCAL_ANYTHINGLLM_URL   (défaut http://127.0.0.1:3001)
  LOCAL_ANYTHINGLLM_KEY   clé API de TON AnythingLLM local (UI → Settings → Tools → Developer API)
  WORKSPACE               (défaut mylab-kb)

Lancement : python mirror_from_vps.py [--verbose] [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

import paramiko

HERE = Path(__file__).resolve().parent
STATE_FILE = HERE / ".mirror_state.json"
VPS_DOCS_DIR = "/root/anythingllm/storage/documents/custom-documents"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_env() -> None:
    """Charge un .env voisin dans os.environ (sans écraser l'existant)."""
    envf = HERE / ".env"
    if envf.exists():
        for line in envf.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def cfg(name: str, default: str | None = None, required: bool = False) -> str:
    val = os.environ.get(name, default)
    if required and not val:
        sys.exit(f"Config manquante : {name} (mets-la dans .env ou en variable d'env)")
    return val or ""


# ---------------------------------------------------------------------------
# Local AnythingLLM API
# ---------------------------------------------------------------------------

def lapi(method: str, path: str, key: str, base: str, body: dict | None = None, timeout: float = 240):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method)
    req.add_header("Authorization", f"Bearer {key}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, {"_err": e.read().decode("utf-8", "replace")[:300]}
    except Exception as e:  # noqa: BLE001
        return -1, {"_err": f"{type(e).__name__}: {e}"}


def ensure_workspace(key: str, base: str, slug: str, verbose: bool) -> str:
    st, ws = lapi("GET", "/api/v1/workspaces", key, base)
    if st != 200:
        sys.exit(f"AnythingLLM local injoignable sur {base} (HTTP {st}). Démarre-le + vérifie la clé.")
    for w in (ws.get("workspaces") or []):
        if w.get("slug") == slug:
            return slug
    # créer
    name = slug.replace("-", " ").title()
    st, r = lapi("POST", "/api/v1/workspace/new", key, base, {"name": name})
    new_slug = ((r.get("workspace") or {}) if isinstance(r, dict) else {}).get("slug") or slug
    if verbose:
        print(f"  workspace local '{new_slug}' créé")
    return new_slug


# ---------------------------------------------------------------------------
# VPS pull (SFTP)
# ---------------------------------------------------------------------------

def pull_vps_docs(verbose: bool) -> dict[str, str]:
    """Retourne {title: pageContent} pour chaque doc brut du VPS."""
    host = cfg("VPS_HOST", required=True)
    port = int(cfg("VPS_PORT", "22"))
    user = cfg("VPS_USER", required=True)
    pwd = cfg("VPS_PASS", required=True)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=user, password=pwd, timeout=20)
    sftp = ssh.open_sftp()
    out: dict[str, str] = {}
    try:
        names = [n for n in sftp.listdir(VPS_DOCS_DIR) if n.endswith(".json")]
    except FileNotFoundError:
        sftp.close(); ssh.close()
        sys.exit(f"Dossier introuvable sur le VPS : {VPS_DOCS_DIR}")
    for fn in names:
        with sftp.open(f"{VPS_DOCS_DIR}/{fn}") as f:
            try:
                d = json.loads(f.read().decode("utf-8", "replace"))
            except Exception as e:  # noqa: BLE001
                print(f"  ! skip {fn}: {e}", file=sys.stderr)
                continue
        title = d.get("title") or fn
        out[title] = d.get("pageContent") or ""
    sftp.close(); ssh.close()
    if verbose:
        print(f"  VPS : {len(out)} document(s)")
    return out


# ---------------------------------------------------------------------------
# Mirror
# ---------------------------------------------------------------------------

def md5(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    load_env()
    base = cfg("LOCAL_ANYTHINGLLM_URL", "http://127.0.0.1:3001").rstrip("/")
    key = cfg("LOCAL_ANYTHINGLLM_KEY", required=True)
    slug = cfg("WORKSPACE", "mylab-kb")

    vps = pull_vps_docs(args.verbose)
    state = json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.exists() else {}

    to_upload = [(t, c) for t, c in vps.items() if state.get(t, {}).get("hash") != md5(c)]
    to_delete = [t for t in state if t not in vps]

    print(f"VPS={len(vps)} · à (ré)uploader={len(to_upload)} · à supprimer={len(to_delete)}")
    if args.dry_run:
        for t, _ in to_upload:
            print(f"  + {t}")
        for t in to_delete:
            print(f"  - {t}")
        return

    slug = ensure_workspace(key, base, slug, args.verbose)

    # Uploads (remplace l'ancienne version : on supprime l'ancien location puis on ré-ajoute)
    for title, content in to_upload:
        old = state.get(title, {}).get("location")
        st, r = lapi("POST", "/api/v1/document/raw-text", key, base,
                     {"textContent": content, "metadata": {"title": title, "docSource": "vps-mirror"}})
        loc = (r.get("documents") or [{}])[0].get("location") if isinstance(r, dict) else None
        if not loc:
            print(f"  ! upload {title}: {st} {str(r)[:120]}", file=sys.stderr)
            continue
        adds = [loc]
        dels = [old] if old else []
        lapi("POST", f"/api/v1/workspace/{slug}/update-embeddings", key, base, {"adds": adds, "deletes": dels})
        if old:
            lapi("DELETE", "/api/v1/system/remove-documents", key, base, {"names": [old]})
        state[title] = {"hash": md5(content), "location": loc}
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
        if args.verbose:
            print(f"  ✓ {title}")

    # Suppressions
    for title in to_delete:
        loc = state.get(title, {}).get("location")
        if loc:
            lapi("POST", f"/api/v1/workspace/{slug}/update-embeddings", key, base, {"adds": [], "deletes": [loc]})
            lapi("DELETE", "/api/v1/system/remove-documents", key, base, {"names": [loc]})
        state.pop(title, None)
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
        if args.verbose:
            print(f"  ✗ retiré {title}")

    print(f"Miroir OK · {len(state)} doc(s) dans le workspace local '{slug}'.")


if __name__ == "__main__":
    main()
