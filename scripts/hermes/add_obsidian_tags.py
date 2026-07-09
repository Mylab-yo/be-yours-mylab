"""Ajoute des tags YAML inférés du nom + contenu à toutes les memory files MyLab.

Source : `.claude/projects/d--be-yours-mylab/memory/*.md`
- Ces fichiers sont auto-syncés vers le vault Obsidian (Stop hook user-level)
- En modifiant ici, la prochaine sync les copiera taggés dans le vault

Inférence des tags :
- Préfixe filename : feedback_/project_/reference_/user_ → tag équivalent
- Mots-clés filename/contenu : odoo, shopify, n8n, bastien, etc.

Sécurité :
- Backup tar.gz avant modification
- Idempotent : si tags existent déjà, merge (dédup)
- Préserve le reste de la frontmatter
"""
import os
import re
import shutil
import sys
import tarfile
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

MEMORY_DIR = Path(r"C:\Users\startec\.claude\projects\d--be-yours-mylab\memory")

# Mapping filename keyword -> tag
KEYWORD_TAGS = {
    # Tech stack
    "odoo": "odoo",
    "shopify": "shopify",
    "n8n": "n8n",
    "bastien": "bastien",
    "vps": "vps",
    "docker": "vps",
    "hermes": "vps",
    "evolution": "vps",
    "playwright": "vps",
    "configurateur": "configurateur",
    "vercel": "configurateur",
    "nextjs": "configurateur",
    "react": "configurateur",
    # Domain
    "tva": "compta",
    "facture": "compta",
    "lettrage": "compta",
    "paiement": "compta",
    "lcl": "compta",
    "ebp": "compta",
    "compta": "compta",
    "stripe": "compta",
    "client": "clients",
    "customer": "clients",
    "b2b": "clients",
    "bss": "clients",
    "partner": "clients",
    "relance": "clients",
    "fournisseur": "fournisseurs",
    "takemoto": "fournisseurs",
    "packaging": "fournisseurs",
    "faconnier": "fournisseurs",
    # Migrations
    "wp": "migration",
    "migration": "migration",
    "aruba": "migration",
    "wc_migration": "migration",
    # Design (keywords spécifiques pour éviter faux-positifs)
    "design": "design",
    "typo": "design",
    "css": "design",
    "parcours": "design",
    "etiquette": "design",
    "typography": "design",
    # Workflow
    "workflow": "workflow",
    "automation": "workflow",
    "cron": "workflow",
    # Comms
    "telegram": "comms",
    "whatsapp": "comms",
    "gmail": "comms",
    "email": "comms",
    # Logistique
    "dpd": "logistique",
    "mondial": "logistique",
    "shipping": "logistique",
    "expedition": "logistique",
}

# Type tags by filename prefix
PREFIX_TAGS = {
    "feedback_": "feedback",
    "project_": "project",
    "reference_": "reference",
    "user_": "user",
}


def infer_tags(filename: str, content: str) -> set:
    """Infer tags from filename and first 800 chars of content.

    - Filename match : substring OK (filenames sont des slugs en kebab/snake)
    - Content match : word-boundary regex pour éviter faux-positifs
      (ex: "ui" qui match "build")
    """
    tags = set()
    fn_lower = filename.lower()
    content_lower = content[:800].lower()

    # Prefix → type tag
    for prefix, tag in PREFIX_TAGS.items():
        if fn_lower.startswith(prefix):
            tags.add(tag)
            break

    # Keywords in filename (substring OK)
    for kw, tag in KEYWORD_TAGS.items():
        if kw in fn_lower:
            tags.add(tag)

    # Keywords in content : word boundary uniquement
    for kw, tag in KEYWORD_TAGS.items():
        if re.search(r"\b" + re.escape(kw) + r"\b", content_lower):
            tags.add(tag)

    return tags


def parse_frontmatter(text: str):
    """Returns (frontmatter_text_or_None, body_text). Frontmatter without --- delimiters."""
    if not text.startswith("---"):
        return None, text
    end_match = re.search(r"\n---\s*\n", text[3:])
    if not end_match:
        return None, text
    fm_end = 3 + end_match.start()
    body_start = 3 + end_match.end()
    return text[3:fm_end].strip("\n"), text[body_start:]


def merge_tags_in_frontmatter(fm_text: str, new_tags: set) -> str:
    """Inject or merge `tags: [...]` line in the YAML frontmatter."""
    # Look for existing tags line
    tags_match = re.search(r"^tags:\s*(\[.*?\]|.*)$", fm_text, re.MULTILINE)
    if tags_match:
        # Parse existing tags
        existing_raw = tags_match.group(1).strip()
        existing_tags = set()
        if existing_raw.startswith("["):
            # YAML flow style: [a, b, c]
            inner = existing_raw.strip("[]").strip()
            if inner:
                existing_tags = {t.strip().strip("\"'") for t in inner.split(",") if t.strip()}
        else:
            existing_tags = {existing_raw.strip().strip("\"'")} if existing_raw else set()
        merged = sorted(existing_tags | new_tags)
        new_line = f"tags: [{', '.join(merged)}]"
        return fm_text[: tags_match.start()] + new_line + fm_text[tags_match.end():]
    else:
        # Inject after description line if present, else at end
        desc_match = re.search(r"^description:.*?(\n|$)", fm_text, re.MULTILINE | re.DOTALL)
        if desc_match:
            inject_at = desc_match.end()
        else:
            inject_at = len(fm_text)
            if not fm_text.endswith("\n"):
                fm_text = fm_text + "\n"
                inject_at = len(fm_text)
        new_line = f"tags: [{', '.join(sorted(new_tags))}]\n"
        return fm_text[:inject_at] + new_line + fm_text[inject_at:]


def process_file(path: Path, dry_run: bool = False):
    content = path.read_text(encoding="utf-8")
    fm_text, body = parse_frontmatter(content)
    if fm_text is None:
        # No frontmatter — create minimal one
        new_tags = infer_tags(path.name, content)
        if not new_tags:
            return None, set()
        new_fm = f"---\ntags: [{', '.join(sorted(new_tags))}]\n---\n\n"
        new_content = new_fm + content
        if not dry_run:
            path.write_text(new_content, encoding="utf-8")
        return "created-fm", new_tags

    new_tags = infer_tags(path.name, body)
    if not new_tags:
        return None, set()

    new_fm_text = merge_tags_in_frontmatter(fm_text, new_tags)
    if new_fm_text == fm_text:
        return None, set()  # no change

    new_content = f"---\n{new_fm_text}\n---\n{body}"
    if not dry_run:
        path.write_text(new_content, encoding="utf-8")
    return "updated", new_tags


def main():
    dry_run = "--apply" not in sys.argv

    if not MEMORY_DIR.exists():
        print(f"❌ Memory dir not found: {MEMORY_DIR}", file=sys.stderr)
        sys.exit(1)

    files = sorted(MEMORY_DIR.glob("*.md"))
    print(f"[i] {len(files)} .md files found in {MEMORY_DIR}")
    print(f"[i] Mode: {'DRY-RUN (use --apply to write)' if dry_run else 'APPLY (writing changes)'}\n")

    # Backup if applying
    if not dry_run:
        backup_dir = MEMORY_DIR.parent / "_backups"
        backup_dir.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"memory-pre-tags-{stamp}.tar.gz"
        with tarfile.open(backup_path, "w:gz") as tar:
            tar.add(MEMORY_DIR, arcname="memory")
        print(f"[✓] Backup: {backup_path} ({backup_path.stat().st_size // 1024} KB)\n")

    stats = {"updated": 0, "created-fm": 0, "no-change": 0}
    tag_freq = {}

    for path in files:
        try:
            action, tags = process_file(path, dry_run=dry_run)
            if action:
                stats[action] = stats.get(action, 0) + 1
                for t in tags:
                    tag_freq[t] = tag_freq.get(t, 0) + 1
                if dry_run:
                    print(f"  {action:12} {path.name:50} -> {sorted(tags)}")
            else:
                stats["no-change"] += 1
        except Exception as e:
            print(f"❌ Error on {path.name}: {e}", file=sys.stderr)

    print("\n=== Summary ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    print("\n=== Tag frequency ===")
    for tag, count in sorted(tag_freq.items(), key=lambda x: -x[1]):
        print(f"  {tag:18} {count}")

    if dry_run:
        print("\n[i] Dry-run only. Re-run with --apply to write changes.")


if __name__ == "__main__":
    main()
