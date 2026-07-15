#!/usr/bin/env python3
"""Miroir skills + mémoires : VPS Hermes -> Hermes maison (SFTP pull, pull-only).

À lancer SUR LE PC MAISON (celui du Hermes llama.cpp). C'est la maison qui va chercher
sur le VPS ; le VPS ne joint jamais la maison (NAT). Les skills (.md/.py) et mémoires (.md)
sont du TEXTE → aucune corruption (contrairement à un upload Google Drive). Hermes relit
skills + mémoires À CHAUD : pas besoin de le redémarrer après un miroir.

Source VPS (source de vérité, déjà déployée par deploy_skills_to_hermes.py / sync_memory_to_hermes.py).
ATTENTION : sur l'HÔTE VPS le volume Hermes est /root/.hermes (le /opt/data n'existe QUE dans le
conteneur). Par défaut on tire donc :
  skills   : /root/.hermes/skills/
  mémoires : /root/.hermes/memories/       (MEMORY.md, USER.md, mylab/*.md)
Override possible via VPS_HERMES_DIR (défaut /root/.hermes).
Les fichiers d'état interne Hermes (dotfiles : .hub, .archive, .usage.json, .curator_*, *.lock)
sont IGNORÉS — on ne copie que les vrais skills + mémoires, pour ne pas écraser l'état local.

Cible locale (configurable via .env — sinon valeurs par défaut pip ~/.hermes) :
  HERMES_SKILLS_DIR    défaut ~/.hermes/skills
  HERMES_MEMORIES_DIR  défaut ~/.hermes/memories

Config — variables d'env, ou fichier `.env` à côté de ce script (mêmes creds VPS que le miroir RAG) :
  VPS_HOST, VPS_PORT, VPS_USER, VPS_PASS
  HERMES_SKILLS_DIR, HERMES_MEMORIES_DIR   (optionnels)

Idempotent : ne télécharge un fichier que si absent en local, taille différente, ou VPS plus récent.
  --delete   retire en local les fichiers qui n'existent plus sur le VPS (skill supprimé côté VPS)
  --dry-run  montre ce qui serait fait, sans rien écrire
  --verbose  détaille fichier par fichier

Lancement : python mirror_skills_memory_from_vps.py [--verbose] [--dry-run] [--delete]
"""
from __future__ import annotations

import argparse
import os
import stat as statmod
import sys
from pathlib import Path

import paramiko

HERE = Path(__file__).resolve().parent


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


def _ignored(name: str) -> bool:
    """Dotfiles (état interne Hermes) et fichiers .lock → ignorés."""
    return name.startswith(".") or name.endswith(".lock")


def sftp_walk(sftp: paramiko.SFTPClient, root: str):
    """Yield (relpath_posix, attr) pour chaque FICHIER sous `root` (récursif),
    en sautant les dotfiles/dossiers d'état (.hub, .archive, .usage.json…) et les *.lock."""
    stack = [""]
    while stack:
        rel = stack.pop()
        remote_dir = root + ("/" + rel if rel else "")
        for attr in sftp.listdir_attr(remote_dir):
            if _ignored(attr.filename):
                continue
            child_rel = f"{rel}/{attr.filename}" if rel else attr.filename
            if statmod.S_ISDIR(attr.st_mode):
                stack.append(child_rel)
            else:
                yield child_rel, attr


def mirror_tree(sftp, remote_root, local_root, label, delete, dry, verbose, counts,
                include_top: set | None = None) -> None:
    """include_top : si fourni, ne mirroir QUE les fichiers dont le dossier de 1er niveau
    est dans cet ensemble (allow-list). Le --delete est lui aussi scopé à cet ensemble,
    pour ne JAMAIS toucher les skills bundlés que la box maison possède déjà."""
    local_root = Path(local_root).expanduser()
    try:
        sftp.stat(remote_root)
    except FileNotFoundError:
        print(f"  ! {label}: source VPS introuvable ({remote_root}) — ignoré", file=sys.stderr)
        return

    def in_scope(rel: str) -> bool:
        return include_top is None or rel.split("/", 1)[0] in include_top

    remote_files = {rel: attr for rel, attr in sftp_walk(sftp, remote_root) if in_scope(rel)}
    for rel, attr in remote_files.items():
        lpath = local_root / rel
        need = True
        if lpath.exists():
            lst = lpath.stat()
            same_size = lst.st_size == attr.st_size
            not_older = int(lst.st_mtime) >= int(attr.st_mtime)
            need = not (same_size and not_older)
        if need:
            counts["dl"] += 1
            if verbose or dry:
                print(f"  + {label}/{rel}")
            if not dry:
                lpath.parent.mkdir(parents=True, exist_ok=True)
                sftp.get(f"{remote_root}/{rel}", str(lpath))
                os.utime(lpath, (attr.st_mtime, attr.st_mtime))
        else:
            counts["skip"] += 1

    if delete and local_root.exists():
        for lf in local_root.rglob("*"):
            if lf.is_file():
                rel = lf.relative_to(local_root).as_posix()
                if in_scope(rel) and rel not in remote_files:
                    counts["del"] += 1
                    if verbose or dry:
                        print(f"  - {label}/{rel}")
                    if not dry:
                        lf.unlink()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--delete", action="store_true",
                    help="retire en local les fichiers absents du VPS")
    args = ap.parse_args()

    load_env()
    host = cfg("VPS_HOST", required=True)
    port = int(cfg("VPS_PORT", "22"))
    user = cfg("VPS_USER", required=True)
    pwd = cfg("VPS_PASS", required=True)
    skills_dir = cfg("HERMES_SKILLS_DIR", str(Path.home() / ".hermes" / "skills"))
    mem_dir = cfg("HERMES_MEMORIES_DIR", str(Path.home() / ".hermes" / "memories"))
    vps_home = cfg("VPS_HERMES_DIR", "/root/.hermes").rstrip("/")
    remote_skills = f"{vps_home}/skills"
    remote_memories = f"{vps_home}/memories"

    # Allow-list des skills MyLab (NE PAS rapatrier les skills bundlés Hermes que la box a déjà).
    # Surcharger via HERMES_SKILLS_INCLUDE (noms séparés par des virgules) quand tu en ajoutes un.
    default_skills = ("check-ca,check-customer,check-order,check-stock,faire-of,gerer-bl,"
                      "mylab-rag,mylab-chatbot-ops,mylab-printer-ops,n8n-workflow-ops,relance-impayes")
    skills_include = {s.strip() for s in cfg("HERMES_SKILLS_INCLUDE", default_skills).split(",") if s.strip()}

    print(f"Miroir skills+mémoires VPS→maison")
    print(f"  skills   : {remote_skills:<28} → {Path(skills_dir).expanduser()}")
    print(f"             (MyLab uniquement : {', '.join(sorted(skills_include))})")
    print(f"  mémoires : {remote_memories:<28} → {Path(mem_dir).expanduser()}")
    if args.dry_run:
        print("  (dry-run : aucune écriture)")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=user, password=pwd, timeout=20)
    sftp = ssh.open_sftp()

    counts = {"dl": 0, "skip": 0, "del": 0}
    try:
        mirror_tree(sftp, remote_skills, skills_dir, "skills",
                    args.delete, args.dry_run, args.verbose, counts, include_top=skills_include)
        mirror_tree(sftp, remote_memories, mem_dir, "memories",
                    args.delete, args.dry_run, args.verbose, counts, include_top=None)
    finally:
        sftp.close()
        ssh.close()

    print(f"\nMiroir OK · téléchargés={counts['dl']} · à jour={counts['skip']} · supprimés={counts['del']}")
    if counts["dl"]:
        print("Hermes relit skills+mémoires à chaud — rien d'autre à faire.")


if __name__ == "__main__":
    main()
