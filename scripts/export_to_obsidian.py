#!/usr/bin/env python3
"""
Exporte les conversations Claude Code (transcripts JSONL) vers le vault Obsidian
de Yoann à `C:\\Users\\startec\\Documents\\MyLab`.

Fonctionne pour TOUS les projets Claude Code (mylab-shop, configurateur,
bastien, general, etc.). Le nom de projet est dérivé du chemin du transcript
et mappé sur un nom propre via PROJECT_NAMES.

Modes d'invocation
------------------
1. Hook `Stop` : reçoit `{"transcript_path": "...", "session_id": "...", "cwd": "..."}`
   sur stdin. Utilisé automatiquement à chaque fin de réponse Claude.

2. Manuel  : `python export_to_obsidian.py --transcript <path.jsonl>`

3. Backfill : `python export_to_obsidian.py --backfill`
   Ré-exporte tous les transcripts JSONL de tous les projets.
   `--backfill --project mylab-shop` pour un seul projet.

Sortie
------
- `<vault>/Sessions/YYYY-MM/YYYY-MM-DD HH-MM — <slug>.md`  (frontmatter: project)
- `<vault>/Memory/<project>/*.md`     (copies miroir par projet)
- `<vault>/Sessions/index.md`         (index chrono regroupé par mois > projet)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

VAULT = Path(r"C:\Users\startec\Documents\MyLab")
SESSIONS_DIR = VAULT / "Sessions"
MEMORY_DIR = VAULT / "Memory"

# Racine où Claude Code stocke les projets
CC_PROJECTS_ROOT = Path(r"C:\Users\startec\.claude\projects")

# Mapping slug brut Claude Code → nom propre pour le vault.
# Tout slug non listé tombe dans le bucket "other".
PROJECT_NAMES = {
    "d--be-yours-mylab": "mylab-shop",
    "d--Configurateur-Designs-MyLab-mylab-configurateur": "configurateur",
    "d--bastien-svc": "bastien",
    "C--Users-startec": "general",
}

SLUG_MAX = 60
SUMMARY_MAX = 80

NOISE_TAG_RE = re.compile(
    r"<(system-reminder|ide_opened_file|ide_selection|command-name|local-command-stdout|"
    r"command-message|command-stdout|command-stderr|user-prompt-submit-hook|"
    r"command-args|stdin|stdout|stderr)[^>]*>.*?</\1>",
    re.DOTALL,
)
ANGLE_BRACKETS_RE = re.compile(r"<[^>]+>")


def project_name_from_slug(slug: str) -> str:
    return PROJECT_NAMES.get(slug, slug.lower())


def project_slug_from_transcript(transcript_path: Path) -> str:
    """C:\\...\\projects\\<slug>\\xxx.jsonl → <slug>"""
    return transcript_path.parent.name


# ---------------------------------------------------------------------------
# Helpers texte
# ---------------------------------------------------------------------------


def strip_noise(text: str) -> str:
    text = NOISE_TAG_RE.sub("", text)
    return text.strip()


def slugify(text: str, max_len: int = SLUG_MAX) -> str:
    text = strip_noise(text)
    text = ANGLE_BRACKETS_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", text)
    text = text.strip(" .")
    if len(text) > max_len:
        text = text[: max_len - 1].rstrip() + "…"
    return text or "untitled"


def truncate(text: str, max_len: int = SUMMARY_MAX) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


# ---------------------------------------------------------------------------
# Tool call summaries
# ---------------------------------------------------------------------------


def summarize_tool_use(name: str, params: dict) -> str:
    p = params or {}
    if name == "Bash":
        cmd = p.get("command", "")
        desc = p.get("description", "")
        return f"`{truncate(desc if desc else cmd)}`"
    if name in ("Read", "NotebookEdit"):
        return f"`{p.get('file_path', '')}`"
    if name in ("Edit", "Write"):
        return f"`{p.get('file_path', '')}`"
    if name == "Glob":
        return f"`{p.get('pattern', '')}` in `{p.get('path', '.')}`"
    if name == "Grep":
        return f"`{p.get('pattern', '')}`" + (
            f" in `{p['path']}`" if p.get("path") else ""
        )
    if name == "Agent":
        return f"**{p.get('subagent_type', 'general-purpose')}** — {truncate(p.get('description', ''))}"
    if name == "Task":
        return f"**{p.get('subagent_type', '?')}** — {truncate(p.get('description', ''))}"
    if name == "TodoWrite":
        return f"{len(p.get('todos') or [])} todo(s)"
    if name == "WebFetch":
        return f"`{p.get('url', '')}`"
    if name == "WebSearch":
        return f"`{p.get('query', '')}`"
    if name == "Skill":
        return f"**/{p.get('skill', '?')}** {truncate(p.get('args') or '')}"
    if name.startswith("mcp__"):
        keys = list(p.keys())[:3]
        return f"`{', '.join(keys)}`"
    return ""


# ---------------------------------------------------------------------------
# Transcript parser
# ---------------------------------------------------------------------------


def iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def parse_transcript(path: Path) -> dict:
    session_id = None
    started_at = None
    ended_at = None
    first_user_text = None
    blocks = []
    current_assistant_text = []
    current_assistant_tools = []
    seen_user_uuids = set()

    def flush_assistant():
        nonlocal current_assistant_text, current_assistant_tools
        text = "\n\n".join(t for t in current_assistant_text if t.strip())
        if text.strip() or current_assistant_tools:
            blocks.append(
                {"kind": "assistant", "text": text, "tools": current_assistant_tools}
            )
        current_assistant_text = []
        current_assistant_tools = []

    for ev in iter_jsonl(path):
        ev_type = ev.get("type")
        ts = ev.get("timestamp")
        if ts:
            ended_at = ts
            if not started_at:
                started_at = ts
        if not session_id:
            session_id = ev.get("sessionId")

        if ev_type == "user":
            msg = ev.get("message") or {}
            content = msg.get("content", [])
            uuid = ev.get("uuid")

            text_parts = []
            is_tool_result_only = True
            if isinstance(content, list):
                for c in content:
                    if not isinstance(c, dict):
                        continue
                    if c.get("type") == "text":
                        text_parts.append(c.get("text", ""))
                        is_tool_result_only = False
                    elif c.get("type") == "tool_result":
                        pass
            elif isinstance(content, str):
                text_parts.append(content)
                is_tool_result_only = False

            if is_tool_result_only:
                continue

            text = strip_noise("\n\n".join(text_parts))
            if not text or uuid in seen_user_uuids:
                continue
            seen_user_uuids.add(uuid)

            flush_assistant()
            if first_user_text is None:
                first_user_text = text
            blocks.append({"kind": "user", "text": text, "ts": ts})

        elif ev_type == "assistant":
            msg = ev.get("message") or {}
            content = msg.get("content", [])
            if not isinstance(content, list):
                continue
            for c in content:
                if not isinstance(c, dict):
                    continue
                if c.get("type") == "text":
                    current_assistant_text.append(c.get("text", ""))
                elif c.get("type") == "tool_use":
                    current_assistant_tools.append(
                        {
                            "name": c.get("name", "?"),
                            "summary": summarize_tool_use(
                                c.get("name", ""), c.get("input", {})
                            ),
                        }
                    )

    flush_assistant()

    return {
        "session_id": session_id,
        "started_at": started_at,
        "ended_at": ended_at,
        "first_user": first_user_text or "",
        "blocks": blocks,
    }


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def parse_iso(ts: str) -> datetime:
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts).astimezone()


def render_markdown(parsed: dict, transcript_path: Path, project: str) -> tuple[str, Path]:
    session_id = parsed["session_id"] or transcript_path.stem
    started = parse_iso(parsed["started_at"]) if parsed["started_at"] else datetime.now()
    ended = parse_iso(parsed["ended_at"]) if parsed["ended_at"] else started

    slug = slugify(parsed["first_user"]) if parsed["first_user"] else "session"
    filename = f"{started.strftime('%Y-%m-%d %H-%M')} — {slug}.md"
    month_dir = SESSIONS_DIR / started.strftime("%Y-%m")
    out_path = month_dir / filename

    n_user = sum(1 for b in parsed["blocks"] if b["kind"] == "user")
    n_assistant = sum(1 for b in parsed["blocks"] if b["kind"] == "assistant")
    n_tools = sum(len(b.get("tools") or []) for b in parsed["blocks"])

    lines = [
        "---",
        f"date: {started.strftime('%Y-%m-%d')}",
        f"time: {started.strftime('%H:%M')}",
        f"ended: {ended.strftime('%H:%M')}",
        f"project: {project}",
        f"session_id: {session_id}",
        f"transcript: {transcript_path.name}",
        f"messages: {n_user + n_assistant}",
        f"tool_calls: {n_tools}",
        "tags:",
        "  - claude-code",
        f"  - project/{project}",
        "---",
        "",
        f"# {slug}",
        "",
        f"> **{project}** · {started.strftime('%A %d %B %Y à %H:%M')} · "
        f"{n_user} user · {n_assistant} Claude · {n_tools} tools",
        "",
        "---",
        "",
    ]

    for block in parsed["blocks"]:
        if block["kind"] == "user":
            lines.append("## 👤 User")
            lines.append("")
            lines.append(block["text"])
            lines.append("")
        elif block["kind"] == "assistant":
            lines.append("## 🤖 Claude")
            lines.append("")
            if block["text"]:
                lines.append(block["text"])
                lines.append("")
            for tool in block.get("tools") or []:
                summary = tool.get("summary") or ""
                line = f"> 🔧 **{tool['name']}**"
                if summary:
                    line += f" — {summary}"
                lines.append(line)
            if block.get("tools"):
                lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines), out_path


# ---------------------------------------------------------------------------
# Memory sync (per-project subfolders)
# ---------------------------------------------------------------------------


def sync_memory_for_project(project: str, slug: str):
    """Sync <claude>/projects/<slug>/memory/*.md → <vault>/Memory/<project>/"""
    src_dir = CC_PROJECTS_ROOT / slug / "memory"
    if not src_dir.exists():
        return
    dst_dir = MEMORY_DIR / project
    dst_dir.mkdir(parents=True, exist_ok=True)
    src_files = {p.name for p in src_dir.glob("*.md")}
    for src in src_dir.glob("*.md"):
        dst = dst_dir / src.name
        if not dst.exists() or src.stat().st_mtime > dst.stat().st_mtime:
            shutil.copy2(src, dst)
    # Remove files no longer present in source
    for dst in dst_dir.glob("*.md"):
        if dst.name not in src_files:
            dst.unlink()


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------


def rebuild_index():
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    entries = []
    for md in SESSIONS_DIR.rglob("*.md"):
        if md.name == "index.md":
            continue
        # Pull project from frontmatter
        project = "unknown"
        try:
            head = md.read_text(encoding="utf-8", errors="replace").split("---", 2)
            if len(head) >= 2:
                for line in head[1].splitlines():
                    if line.startswith("project:"):
                        project = line.split(":", 1)[1].strip()
                        break
        except Exception:
            pass
        entries.append((md, project))

    entries.sort(key=lambda e: e[0].stat().st_mtime, reverse=True)

    # Group by month then project
    by_month: dict[str, dict[str, list[Path]]] = {}
    for md, project in entries:
        month = md.parent.name
        by_month.setdefault(month, {}).setdefault(project, []).append(md)

    lines = [
        "---",
        "tags:",
        "  - index",
        "  - claude-code",
        "---",
        "",
        "# Sessions Claude Code",
        "",
        f"_{len(entries)} session(s) — dernier export {datetime.now().strftime('%Y-%m-%d %H:%M')}_",
        "",
        "Toutes projets confondus. Filtre par tag `#project/<nom>` ou utilise la recherche.",
        "",
    ]
    for month in sorted(by_month.keys(), reverse=True):
        lines.append("")
        lines.append(f"## {month}")
        lines.append("")
        for project in sorted(by_month[month].keys()):
            mds = by_month[month][project]
            lines.append(f"### {project} ({len(mds)})")
            lines.append("")
            for md in mds:
                rel = md.relative_to(SESSIONS_DIR).as_posix().replace(".md", "")
                lines.append(f"- [[{rel}|{md.stem}]]")
            lines.append("")
    lines.append("")
    (SESSIONS_DIR / "index.md").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Export driver
# ---------------------------------------------------------------------------


def _fresh_enough(out_path: Path, transcript_path: Path) -> bool:
    """Skip re-render if output is already newer than transcript.
    Avoids redundant rewrites when UserPromptSubmit / PostToolUse / Stop
    all fire in close succession on the same JSONL state."""
    try:
        return out_path.exists() and out_path.stat().st_mtime >= transcript_path.stat().st_mtime
    except OSError:
        return False


def export_one(
    transcript_path: Path, force: bool = False
) -> tuple[Path | None, str | None, bool]:
    """Returns (out_path, project, changed). changed=False when skipped."""
    if not transcript_path.exists() or transcript_path.stat().st_size == 0:
        return None, None, False
    parsed = parse_transcript(transcript_path)
    if not parsed["blocks"]:
        return None, None, False
    slug = project_slug_from_transcript(transcript_path)
    project = project_name_from_slug(slug)
    md, out_path = render_markdown(parsed, transcript_path, project)
    if not force and _fresh_enough(out_path, transcript_path):
        return out_path, project, False
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    sync_memory_for_project(project, slug)
    return out_path, project, True


def backfill(only_project: str | None = None, quiet: bool = False):
    VAULT.mkdir(parents=True, exist_ok=True)
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    n_ok = 0
    for proj_dir in sorted(CC_PROJECTS_ROOT.iterdir()):
        if not proj_dir.is_dir():
            continue
        slug = proj_dir.name
        proj = project_name_from_slug(slug)
        if only_project and proj != only_project:
            continue
        for jsonl in sorted(proj_dir.glob("*.jsonl")):
            out, _, changed = export_one(jsonl, force=True)
            if out:
                n_ok += 1
                if not quiet:
                    print(f"[{proj}] {out.name}")
    rebuild_index()
    if not quiet:
        print(f"\nBackfill terminé : {n_ok} session(s).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcript", type=str, help="Path to a specific JSONL transcript")
    ap.add_argument("--backfill", action="store_true")
    ap.add_argument("--project", type=str, help="Filter backfill by project name")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if args.backfill:
        backfill(args.project, args.quiet)
        return

    transcript_path: Path | None = None
    if args.transcript:
        transcript_path = Path(args.transcript)
    else:
        try:
            raw = sys.stdin.read()
            if raw.strip():
                data = json.loads(raw)
                tp = data.get("transcript_path")
                if tp:
                    transcript_path = Path(tp)
        except Exception:
            pass

    if not transcript_path:
        return

    VAULT.mkdir(parents=True, exist_ok=True)
    out, project, changed = export_one(transcript_path)
    if changed:
        rebuild_index()
    if out and changed and not args.quiet:
        print(f"Exported [{project}]: {out}")


if __name__ == "__main__":
    main()
