#!/usr/bin/env python3
"""
Importe un export de données Anthropic (claude.ai / Claude Desktop) dans le
vault Obsidian de Yoann à `C:\\Users\\startec\\Documents\\MyLab`.

L'export RGPD Anthropic est un .zip avec cette structure (constatée 2026-05) :
  - users.json                — identité du compte
  - conversations.json        — toutes les conversations chat (humain ↔ assistant)
  - memories.json             — la "Memory" cross-conversation (un blob texte)
  - projects/*.json           — les Claude.ai Projects (avec docs/knowledge attachée)
  - design_chats/*.json       — les chats du système "Design"

Usage
-----
    python import_claude_ai_export.py <chemin/vers/data-XXX.zip>

Sortie dans le vault
-------------------
  Sessions/claude-ai/YYYY-MM/YYYY-MM-DD HH-MM — <slug>.md   (1 par conversation)
  Memory/claude-ai/conversations_memory.md                  (la Memory globale)
  Memory/claude-ai/projects/<project-name>.md               (docs attachées à chaque projet)
  Sessions/claude-ai/index.md                               (index chronologique)

Idempotent : ré-exécuter sur un nouveau zip remplace les fichiers générés
sans toucher au reste du vault.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

VAULT = Path(r"C:\Users\startec\Documents\MyLab")
SESSIONS_DIR = VAULT / "Sessions" / "claude-ai"
MEMORY_DIR = VAULT / "Memory" / "claude-ai"

SLUG_MAX = 60

INVALID_FN_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def slugify(text: str, max_len: int = SLUG_MAX) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = INVALID_FN_RE.sub("", text)
    text = text.strip(" .")
    if len(text) > max_len:
        text = text[: max_len - 1].rstrip() + "…"
    return text or "untitled"


def parse_iso(ts: str) -> datetime:
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts).astimezone()


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------


def render_conversation(conv: dict) -> tuple[str, Path]:
    """Render one conversation as markdown. Returns (markdown, output_path)."""
    name = conv.get("name") or "Sans titre"
    created = parse_iso(conv["created_at"]) if conv.get("created_at") else datetime.now()
    updated = parse_iso(conv["updated_at"]) if conv.get("updated_at") else created
    messages = conv.get("chat_messages") or []

    slug = slugify(name)
    filename = f"{created.strftime('%Y-%m-%d %H-%M')} — {slug}.md"
    out_path = SESSIONS_DIR / created.strftime("%Y-%m") / filename

    n_human = sum(1 for m in messages if m.get("sender") == "human")
    n_assistant = sum(1 for m in messages if m.get("sender") == "assistant")

    lines = [
        "---",
        f"date: {created.strftime('%Y-%m-%d')}",
        f"time: {created.strftime('%H:%M')}",
        f"updated: {updated.strftime('%Y-%m-%d %H:%M')}",
        f"project: claude-ai",
        f"conversation_uuid: {conv.get('uuid', '')}",
        f"title: {name}",
        f"messages: {len(messages)}",
        "tags:",
        "  - claude-ai",
        "  - project/claude-ai",
        "---",
        "",
        f"# {slug}",
        "",
        f"> **claude.ai** · {created.strftime('%A %d %B %Y à %H:%M')} · "
        f"{n_human} user · {n_assistant} Claude",
        "",
    ]
    if conv.get("summary"):
        lines += [f"_{conv['summary']}_", ""]
    lines += ["---", ""]

    for msg in messages:
        sender = msg.get("sender", "?")
        if sender == "human":
            lines.append("## 👤 User")
        elif sender == "assistant":
            lines.append("## 🤖 Claude")
        else:
            lines.append(f"## {sender}")
        lines.append("")

        # Prefer structured `content[]` if present, fallback to `text`
        text = ""
        content = msg.get("content")
        if isinstance(content, list) and content:
            parts = []
            for c in content:
                if not isinstance(c, dict):
                    continue
                t = c.get("type")
                if t == "text":
                    parts.append(c.get("text", ""))
                elif t == "tool_use":
                    parts.append(
                        f"> 🔧 **{c.get('name', '?')}** "
                        f"`{json.dumps(c.get('input') or {}, ensure_ascii=False)[:120]}`"
                    )
                elif t == "tool_result":
                    pass  # skip raw tool results — too noisy
                elif t == "image":
                    parts.append("> 🖼️ [image]")
                elif t == "thinking":
                    pass  # skip extended thinking
            text = "\n\n".join(p for p in parts if p)
        if not text:
            text = msg.get("text", "")

        lines.append(text.strip() or "_(message vide)_")
        lines.append("")

        # Attachments / files
        attachments = msg.get("attachments") or []
        files = msg.get("files") or []
        if attachments or files:
            lines.append("**Pièces jointes :**")
            for a in attachments:
                fn = a.get("file_name") or a.get("name") or "?"
                lines.append(f"- 📎 {fn}")
            for f in files:
                fn = f.get("file_name") or f.get("name") or "?"
                lines.append(f"- 📎 {fn}")
            lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines), out_path


def import_conversations(zf: zipfile.ZipFile) -> int:
    try:
        raw = zf.read("conversations.json")
    except KeyError:
        return 0
    convs = json.loads(raw)
    n = 0
    for conv in convs:
        try:
            md, out_path = render_conversation(conv)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(md, encoding="utf-8")
            n += 1
        except Exception as e:
            print(f"  ! erreur sur {conv.get('uuid', '?')}: {e}", file=sys.stderr)
    return n


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------


def import_memories(zf: zipfile.ZipFile) -> int:
    try:
        raw = zf.read("memories.json")
    except KeyError:
        return 0
    mems = json.loads(raw)
    if not mems:
        return 0
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    n = 0
    for mem in mems:
        conv_mem = mem.get("conversations_memory") or ""
        if conv_mem:
            (MEMORY_DIR / "conversations_memory.md").write_text(
                "---\n"
                "tags:\n"
                "  - claude-ai\n"
                "  - memory\n"
                "  - cross-conversation\n"
                "---\n\n"
                "# Memory Claude.ai — Cross-conversation\n\n"
                f"_Export du {datetime.now().strftime('%Y-%m-%d')} · "
                "blob mémoire transverse stocké côté Anthropic, alimenté automatiquement à mesure des conversations claude.ai._\n\n"
                "---\n\n"
                f"{conv_mem}\n",
                encoding="utf-8",
            )
            n += 1
        project_mems = mem.get("project_memories") or {}
        if project_mems:
            proj_dir = MEMORY_DIR / "projects"
            proj_dir.mkdir(parents=True, exist_ok=True)
            # project_memories is typically a dict keyed by project uuid
            if isinstance(project_mems, dict):
                for proj_uuid, content in project_mems.items():
                    if not content:
                        continue
                    body = content if isinstance(content, str) else json.dumps(content, indent=2, ensure_ascii=False)
                    (proj_dir / f"memory-{proj_uuid}.md").write_text(
                        "---\n"
                        "tags:\n"
                        "  - claude-ai\n"
                        "  - memory\n"
                        "  - project-memory\n"
                        f"project_uuid: {proj_uuid}\n"
                        "---\n\n"
                        f"# Project memory · {proj_uuid}\n\n"
                        f"{body}\n",
                        encoding="utf-8",
                    )
                    n += 1
            else:
                (proj_dir / "_raw_project_memories.json").write_text(
                    json.dumps(project_mems, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
    return n


# ---------------------------------------------------------------------------
# Projects (knowledge docs)
# ---------------------------------------------------------------------------


def import_projects(zf: zipfile.ZipFile) -> int:
    proj_dir = MEMORY_DIR / "projects"
    proj_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for name in zf.namelist():
        if not name.startswith("projects/") or not name.endswith(".json"):
            continue
        proj = json.loads(zf.read(name))
        pname = proj.get("name") or proj.get("uuid", "?")
        slug = slugify(pname)
        out = proj_dir / f"{slug}.md"

        lines = [
            "---",
            "tags:",
            "  - claude-ai",
            "  - project-knowledge",
            f"project_uuid: {proj.get('uuid', '')}",
            f"title: {pname}",
            "---",
            "",
            f"# {pname}",
            "",
        ]
        if proj.get("description"):
            lines += [f"> {proj['description']}", ""]
        if proj.get("prompt_template"):
            lines += ["## Prompt template", "", "```", proj["prompt_template"], "```", ""]

        docs = proj.get("docs") or []
        if docs:
            lines += ["## Documents attachés", ""]
            for doc in docs:
                dname = doc.get("filename") or doc.get("name") or "doc"
                content = doc.get("content") or doc.get("body") or ""
                lines += [f"### {dname}", "", content.strip() if isinstance(content, str) else json.dumps(content, indent=2, ensure_ascii=False), ""]
        out.write_text("\n".join(lines), encoding="utf-8")
        n += 1
    return n


# ---------------------------------------------------------------------------
# Design chats
# ---------------------------------------------------------------------------


def import_design_chats(zf: zipfile.ZipFile) -> int:
    """Render any design_chats/*.json same way as a conversation."""
    n = 0
    for name in zf.namelist():
        if not name.startswith("design_chats/") or not name.endswith(".json"):
            continue
        chat = json.loads(zf.read(name))
        # Normalize to look like a conversation
        normalized = {
            "uuid": chat.get("uuid"),
            "name": chat.get("title") or chat.get("name") or "Design chat",
            "summary": "",
            "created_at": chat.get("created_at"),
            "updated_at": chat.get("updated_at"),
            "chat_messages": chat.get("messages") or [],
        }
        try:
            md, out_path = render_conversation(normalized)
            # Push design chats to a dedicated subfolder
            out_path = SESSIONS_DIR / "design" / out_path.relative_to(SESSIONS_DIR)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(md, encoding="utf-8")
            n += 1
        except Exception as e:
            print(f"  ! erreur design chat {chat.get('uuid', '?')}: {e}", file=sys.stderr)
    return n


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------


def rebuild_claude_ai_index():
    mds = sorted(
        (p for p in SESSIONS_DIR.rglob("*.md") if p.name != "index.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    by_month: dict[str, list[Path]] = {}
    for md in mds:
        # YYYY-MM folder name is the parent (or grandparent if under design/)
        for parent in md.parents:
            if re.match(r"^\d{4}-\d{2}$", parent.name):
                by_month.setdefault(parent.name, []).append(md)
                break

    lines = [
        "---",
        "tags:",
        "  - index",
        "  - claude-ai",
        "---",
        "",
        "# Conversations claude.ai",
        "",
        f"_{len(mds)} conversation(s) — dernier import {datetime.now().strftime('%Y-%m-%d %H:%M')}_",
        "",
    ]
    for month in sorted(by_month.keys(), reverse=True):
        lines.append(f"## {month}")
        lines.append("")
        for md in by_month[month]:
            rel = md.relative_to(SESSIONS_DIR).as_posix().replace(".md", "")
            lines.append(f"- [[claude-ai/{rel}|{md.stem}]]")
        lines.append("")
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    (SESSIONS_DIR / "index.md").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("zip", help="Path to Anthropic data export .zip")
    args = ap.parse_args()

    zpath = Path(args.zip)
    if not zpath.exists():
        print(f"ERROR: zip not found: {zpath}", file=sys.stderr)
        sys.exit(1)

    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zpath) as zf:
        names = set(zf.namelist())
        print(f"Zip: {zpath.name} ({len(names)} entrées)")

        n_conv = import_conversations(zf) if "conversations.json" in names else 0
        print(f"  Conversations importées : {n_conv}")

        n_mem = import_memories(zf) if "memories.json" in names else 0
        print(f"  Memories importées : {n_mem}")

        n_proj = import_projects(zf)
        print(f"  Projets (knowledge) importés : {n_proj}")

        n_design = import_design_chats(zf)
        print(f"  Design chats importés : {n_design}")

    rebuild_claude_ai_index()
    print(f"\nImport terminé. Vault : {VAULT}")


if __name__ == "__main__":
    main()
