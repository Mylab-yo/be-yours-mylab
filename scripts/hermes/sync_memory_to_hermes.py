"""Duplicate Claude Code memory/ into the Hermes agent so it benefits from it too.

Design (chosen 2026-06-12): on-demand KB + pointer.
- Mirrors memory/*.md (EXCLUDING any file containing secrets) into the Hermes
  container at /opt/data/memories/mylab/ (host: /root/.hermes/memories/mylab/).
- Adds ONE pointer entry to Hermes' native always-loaded MEMORY.md telling the
  agent the full MyLab KB lives there (read on demand) — keeps per-message
  context tiny instead of injecting 55 files every turn.
- Secret guard: skips files matching token patterns (Shopify/Anthropic/Google/
  JWT/Airtable) and the known reference_api_keys.md — Hermes already has the
  creds it needs in .env. Skipped files are logged (never silently dropped).
- Change detection: SHA1 per file vs a local state file; exits BEFORE opening any
  SSH connection when nothing changed (cheap to call from a Stop hook every turn).

Run manually: python scripts/hermes/sync_memory_to_hermes.py [--force] [--quiet]
Hook usage  : python d:/be-yours-mylab/scripts/hermes/sync_memory_to_hermes.py --quiet
"""
import hashlib
import json
import os
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

QUIET = "--quiet" in sys.argv
FORCE = "--force" in sys.argv

ROOT = Path(__file__).resolve().parents[2]                 # d:\be-yours-mylab
MEMORY_DIR = Path.home() / ".claude" / "projects" / "d--be-yours-mylab" / "memory"
STATE_FILE = Path.home() / ".claude" / ".hermes_memory_sync.json"
REMOTE_HOST_DIR = "/root/.hermes/memories/mylab"           # = /opt/data/memories/mylab in container
REMOTE_NATIVE_MEMORY = "/root/.hermes/memories/MEMORY.md"
POINTER_MARKER = "/opt/data/memories/mylab/"
POINTER_TEXT = (
    "Base de connaissance MY.LAB complète (mémoire Claude Code de Yoann, dupliquée "
    "automatiquement) dans /opt/data/memories/mylab/ — index dans mylab/MEMORY.md. "
    "Quand tu as besoin de détail sur un sujet MY.LAB (Odoo, Shopify, n8n, "
    "fournisseurs, workflows, décisions passées, clients), lis le fichier .md "
    "pertinent de ce dossier avec tes outils fichier au lieu de deviner."
)

# Files never pushed (contain secrets) + entropy/token scan for safety.
EXPLICIT_EXCLUDE = {"reference_api_keys.md"}
SECRET_PATTERNS = [
    re.compile(r"shp(at|ss|ca|pa)_[A-Za-z0-9]{16,}"),       # Shopify tokens
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"),              # Anthropic
    re.compile(r"AIza[A-Za-z0-9_\-]{30,}"),                 # Google API
    re.compile(r"eyJ[A-Za-z0-9_\-]{15,}\.[A-Za-z0-9_\-]{15,}\.[A-Za-z0-9_\-]{10,}"),  # JWT
    re.compile(r"\bpat[A-Za-z0-9]{14}\.[A-Za-z0-9]{40,}"),  # Airtable PAT
    re.compile(r"xox[bp]-[A-Za-z0-9\-]{10,}"),              # Slack
]


def log(*a):
    if not QUIET:
        print(*a)


def sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", "replace")).hexdigest()


def has_secret(text: str) -> bool:
    return any(p.search(text) for p in SECRET_PATTERNS)


def collect():
    """Return (to_push: {name: text}, skipped_secrets: [name])."""
    push, skipped = {}, []
    for f in sorted(MEMORY_DIR.glob("*.md")):
        if f.name in EXPLICIT_EXCLUDE:
            skipped.append(f.name)
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        if has_secret(text):
            skipped.append(f.name)
            continue
        push[f.name] = text
    return push, skipped


def main():
    if not MEMORY_DIR.exists():
        log(f"[hermes-sync] memory dir not found: {MEMORY_DIR}")
        return

    push, skipped = collect()
    # Current fingerprint of what WOULD be on Hermes
    fingerprint = {name: sha1(text) for name, text in push.items()}

    state = {}
    if STATE_FILE.exists() and not FORCE:
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            state = {}
    prev = state.get("files", {})

    changed = [n for n, h in fingerprint.items() if prev.get(n) != h]
    removed = [n for n in prev if n not in fingerprint]
    pointer_done = state.get("pointer_done", False)

    if not changed and not removed and pointer_done and not FORCE:
        log("[hermes-sync] no memory change — skip (no network).")
        return

    # Only now do we pay the SSH cost.
    import paramiko
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env.vps")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(os.environ["VPS_HOST"], port=int(os.environ.get("VPS_PORT", "22")),
                    username=os.environ["VPS_USER"], password=os.environ["VPS_PASS"],
                    timeout=15)
    except Exception as e:
        log(f"[hermes-sync] SSH connect failed ({e}) — will retry next turn.")
        return  # don't update state -> retried next time

    sftp = ssh.open_sftp()
    ssh.exec_command(f"mkdir -p {REMOTE_HOST_DIR}")[1].read()

    pushed = 0
    for name in (fingerprint if FORCE else changed):
        with sftp.open(f"{REMOTE_HOST_DIR}/{name}", "w") as fh:
            fh.write(push[name])
        pushed += 1

    # Remove files no longer present locally (or now secret-excluded)
    for name in removed:
        try:
            sftp.remove(f"{REMOTE_HOST_DIR}/{name}")
        except IOError:
            pass

    # Idempotent pointer in the native always-loaded MEMORY.md
    try:
        with sftp.open(REMOTE_NATIVE_MEMORY, "r") as fh:
            native = fh.read().decode("utf-8", "replace")
    except IOError:
        native = ""
    if POINTER_MARKER not in native:
        new_native = native.rstrip() + ("\n§\n" if native.strip() else "") + POINTER_TEXT + "\n"
        with sftp.open(REMOTE_NATIVE_MEMORY, "w") as fh:
            fh.write(new_native)
        pointer_added = True
    else:
        pointer_added = False

    sftp.close()
    # gateway reads memory as user hermes (uid 10000)
    ssh.exec_command(f"docker exec hermes-gateway chown -R hermes:hermes "
                     f"/opt/data/memories/mylab {REMOTE_NATIVE_MEMORY} 2>/dev/null")[1].read()
    ssh.close()

    STATE_FILE.write_text(json.dumps(
        {"files": fingerprint, "pointer_done": True}, ensure_ascii=False, indent=0),
        encoding="utf-8")

    log(f"[hermes-sync] pushed {pushed} file(s), removed {len(removed)}, "
        f"pointer {'added' if pointer_added else 'present'}. "
        f"Excluded (secrets): {', '.join(skipped) if skipped else 'none'}")


if __name__ == "__main__":
    main()
