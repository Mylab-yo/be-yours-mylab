# -*- coding: utf-8 -*-
"""Export Claude Code → vault Obsidian MyLab.

v2 (2026-07-08) :
- Sessions : frontmatter enrichi (project, tags, résumé Gemini) + dialogue.
- Miroir des mémoires .claude/projects/*/memory/*.md → Vault/Memory/<projet>/
  (avec alias = slug `name:` pour que les liens [[name-slug]] résolvent).
- Hubs générés depuis MEMORY.md (mylab-shop) → Vault/Hubs/.
- Index des sessions → Vault/Claude Code/_index.md.

Flags : --quiet (hook Stop) · --backfill (re-résume tout, throttlé).
Le résumé LLM n'est tenté que sur les sessions inactives depuis 30 min
(max 6 par run hors backfill) pour garder le hook Stop rapide.
"""
import json, re, sys, time
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

VAULT_PATH = Path(r"C:\Users\startec\Documents\MyLab")
EXPORT_DIR = VAULT_PATH / "Claude Code"
MEMORY_DIR = VAULT_PATH / "Memory"
HUBS_DIR = VAULT_PATH / "Hubs"
CLAUDE_DIR = Path.home() / ".claude"
ENV_LOCAL = Path(r"d:\Configurateur Designs MyLab\mylab-configurateur\.env.local")

QUIET = "--quiet" in sys.argv
BACKFILL = "--backfill" in sys.argv
GEMINI_MODEL = "gemini-2.5-flash"
LLM_MIN_AGE_MIN = 30          # session inactive depuis N min avant résumé
MAX_LLM_PER_RUN = 500 if BACKFILL else 6
LLM_SLEEP_S = 4               # throttle free tier (15 req/min)

PROJECT_NAMES = {
    "d--be-yours-mylab": "mylab-shop",
    "c--Users-startec-Downloads-be-yours-mylab": "mylab-shop",
    "d--Configurateur-Designs-MyLab-mylab-configurateur": "configurateur",
    "d--Configurateur-Designs-MyLab": "configurateur",
    "d--bastien-svc": "bastien",
    "d--MyLab": "mylab-viewport",
    "d--Projet-cession-parts-mylab": "cession-parts",
    "d--VEGETAL-ORIGIN": "vegetal-origin",
    "C--Users-startec": "general",
}
MAIN_MEMORY = CLAUDE_DIR / "projects" / "d--be-yours-mylab" / "memory" / "MEMORY.md"


def log(msg):
    if not QUIET:
        print(msg)


def sanitize(name):
    name = re.sub(r'[<>:"/\\|?*]', '-', name)
    return re.sub(r'-+', '-', name).strip('-')[:100]


def project_of(path):
    parts = path.parts
    if "projects" in parts:
        slug = parts[parts.index("projects") + 1]
        if slug in PROJECT_NAMES:
            return PROJECT_NAMES[slug]
        if "theme-export" in slug:
            return "theme-export"
        return sanitize(slug.strip("-"))[:40] or "general"
    return "general"


# ── LLM (Gemini) ────────────────────────────────────────────────────────────

def gemini_key():
    try:
        for line in ENV_LOCAL.read_text(encoding="utf-8").splitlines():
            if line.startswith("GEMINI_API_KEY=") and line.split("=", 1)[1].strip():
                return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return None


def llm_summarize(key, dialogue):
    """Retourne (resume, tags) ou None. Ne lève jamais."""
    try:
        import requests
        excerpt = dialogue[:9000] + ("\n[…]\n" + dialogue[-3000:] if len(dialogue) > 12000 else "")
        prompt = (
            "Voici une session de travail entre Yoann (gérant de MY.LAB, cosmétiques capillaires B2B) "
            "et son assistant Claude Code. Résume en 2 à 3 phrases factuelles ce qui a été fait ou décidé, "
            "puis donne 3 à 6 tags courts en kebab-case et en français (domaines : odoo, shopify, n8n, airtable, "
            "devis, facturation, stock, theme, client-<nom>, etc.). "
            'Réponds UNIQUEMENT en JSON : {"resume": "...", "tags": ["...", "..."]}\n\n' + excerpt
        )
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
            params={"key": key},
            json={"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048,
                                       "responseMimeType": "application/json"}},
            timeout=30)
        if r.status_code != 200:
            return None
        parts = r.json()["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts).strip()
        text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.M).strip()
        data = json.loads(text)
        resume = str(data.get("resume", "")).strip()
        tags = [re.sub(r"[^a-z0-9/\-]", "", str(t).lower().replace(" ", "-"))
                for t in data.get("tags", [])][:6]
        tags = [t for t in tags if t]
        if resume and tags:
            return resume, tags
    except Exception:
        pass
    return None


# ── Sessions ────────────────────────────────────────────────────────────────

def extract_text(conv_file):
    messages = []
    for line in open(conv_file, "r", encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("isSidechain"):
            return []  # transcript de subagent : ne pas polluer le vault
        if entry.get("type", "") not in ("user", "assistant"):
            continue
        msg = entry.get("message", {})
        role = msg.get("role", "")
        content = msg.get("content", "")
        if isinstance(content, str):
            text = content.strip()
        elif isinstance(content, list):
            text = "\n".join(b.get("text", "") for b in content
                             if isinstance(b, dict) and b.get("type") == "text").strip()
        else:
            continue
        if not text:
            continue
        if (text.startswith("{") and text.endswith("}")) or (text.startswith("[") and text.endswith("]")):
            continue
        label = "Yoann" if role == "user" else "Claude"
        messages.append(f"### {label}\n\n{text}\n")
    return messages


def find_conversations():
    convs = []
    for d in [CLAUDE_DIR / "projects", CLAUDE_DIR / "sessions"]:
        if d.exists():
            convs.extend(d.rglob("*.jsonl"))
    convs.extend(CLAUDE_DIR.glob("*.jsonl"))
    return convs


def read_existing_meta(filepath):
    """Récupère (tags_line, resume) d'un export précédent pour les réutiliser sans re-appeler le LLM."""
    try:
        head = filepath.read_text(encoding="utf-8")[:2500]
    except OSError:
        return None, None
    m_tags = re.search(r"^tags: (\[.*\])$", head, re.M)
    m_resume = re.search(r"## Résumé\n\n(.+?)\n\n", head, re.S)
    return (m_tags.group(1) if m_tags else None,
            m_resume.group(1).strip() if m_resume else None)


class LlmBudget:
    def __init__(self):
        self.key = gemini_key()
        self.used = 0

    def take(self):
        if not self.key or self.used >= MAX_LLM_PER_RUN:
            return False
        if self.used:
            time.sleep(LLM_SLEEP_S)
        self.used += 1
        return True


def export_conv(conv_file, budget):
    messages = extract_text(conv_file)
    if len(messages) < 2:
        return False
    stat = conv_file.stat()
    date = datetime.fromtimestamp(stat.st_mtime)
    date_str = date.strftime("%Y-%m-%d")
    first_msg = ""
    for msg in messages:
        if msg.startswith("### Yoann"):
            first_msg = msg.split("\n\n", 1)[-1].split("\n")[0][:80]
            break
    if not first_msg:
        first_msg = conv_file.stem
    filepath = EXPORT_DIR / f"{sanitize(f'{date_str} - {first_msg}')}.md"

    exists = filepath.exists()
    up_to_date = exists and stat.st_mtime <= filepath.stat().st_mtime
    old_tags, old_resume = read_existing_meta(filepath) if exists else (None, None)
    idle_min = (time.time() - stat.st_mtime) / 60
    llm_eligible = BACKFILL or idle_min >= LLM_MIN_AGE_MIN

    want_llm = llm_eligible and (BACKFILL or not old_tags)
    if up_to_date and not want_llm:
        return False                      # à jour ; résumé viendra quand la session sera au repos

    project = project_of(conv_file)
    resume, tags_list = None, None
    if want_llm and budget.take():
        out = llm_summarize(budget.key, "\n".join(messages))
        if out:
            resume, tags_list = out
    if up_to_date and not tags_list:
        return False                      # rien de nouveau à écrire (budget épuisé ou LLM KO)

    if tags_list:
        tags_str = json.dumps(["claude-session", f"project/{project}"] + tags_list, ensure_ascii=False)
    elif old_tags:
        tags_str, resume = old_tags, (resume or old_resume)
    else:
        tags_str = None

    fm = [f"date: {date_str}", "source: Claude Code", f"project: {project}"]
    if tags_str:
        fm.append(f"tags: {tags_str}")
    header = "---\n" + "\n".join(fm) + f"\n---\n\n# {first_msg}\n\n"
    if resume:
        header += f"## Résumé\n\n{resume}\n\n---\n\n"
    filepath.write_text(header + "\n---\n\n".join(messages), encoding="utf-8")
    log(f"  Exporté : {filepath.name}" + (" (+résumé)" if resume else ""))
    return True


def build_index():
    entries = []
    for f in sorted(EXPORT_DIR.glob("*.md"), reverse=True):
        if f.name == "_index.md":
            continue
        head = f.read_text(encoding="utf-8")[:2500]
        m_date = re.search(r"^date: (\d{4}-\d{2}-\d{2})$", head, re.M)
        m_proj = re.search(r"^project: (.+)$", head, re.M)
        m_resume = re.search(r"## Résumé\n\n(.+?)\n", head, re.S)
        date = m_date.group(1) if m_date else f.name[:10]
        entries.append((date, m_proj.group(1) if m_proj else "?",
                        f.stem, (m_resume.group(1).strip()[:160] if m_resume else "")))
    lines = ["---", "tags: [index]", "---", "", "# Sessions Claude Code", "",
             "_Généré automatiquement par export_to_obsidian.py — ne pas éditer._", ""]
    month = None
    for date, proj, stem, resume in entries:
        if date[:7] != month:
            month = date[:7]
            lines += [f"## {month}", ""]
        lines.append(f"- [[{stem}]] `{proj}`" + (f" — {resume}" if resume else ""))
    (EXPORT_DIR / "_index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ── Miroir mémoire ──────────────────────────────────────────────────────────

def mirror_memories():
    count = 0
    projects_dir = CLAUDE_DIR / "projects"
    if not projects_dir.exists():
        return 0
    for mem_dir in projects_dir.glob("*/memory"):
        project = project_of(mem_dir)
        dest_dir = MEMORY_DIR / project
        for src in mem_dir.glob("*.md"):
            content = src.read_text(encoding="utf-8")
            m = re.search(r'^name:\s*"?([A-Za-z0-9\-]+)"?\s*$', content, re.M)
            slug = m.group(1) if m else None
            if slug and slug != src.stem and "aliases:" not in content[:600]:
                content = re.sub(r'^(name:.*)$', rf'\1\naliases: ["{slug}"]', content, count=1, flags=re.M)
            dest = dest_dir / src.name
            if dest.exists() and dest.read_text(encoding="utf-8") == content:
                continue
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding="utf-8")
            count += 1
    return count


# ── Hubs depuis MEMORY.md ───────────────────────────────────────────────────

def build_hubs():
    if not MAIN_MEMORY.exists():
        return 0
    sections, current = {}, None
    for line in MAIN_MEMORY.read_text(encoding="utf-8").splitlines():
        m_sec = re.match(r"^\|\s*\*\*(.+?)\*\*\s*\|\s*\|$", line)
        if m_sec:
            current = m_sec.group(1).strip()
            sections[current] = []
            continue
        if current and line.startswith("|") and ".md" in line:
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 2:
                files = re.findall(r"([A-Za-z0-9_\-]+)\.md", cells[0])
                if files:
                    sections[current].append((files, cells[1]))
    if not sections:
        return 0
    HUBS_DIR.mkdir(parents=True, exist_ok=True)
    for section, rows in sections.items():
        lines = ["---", "tags: [hub]", "---", "", f"# 🗂️ {section}", "",
                 "_Généré depuis MEMORY.md par export_to_obsidian.py — ne pas éditer._", ""]
        for files, desc in rows:
            links = " · ".join(f"[[{f}]]" for f in files)
            lines.append(f"- {links} — {desc}")
        (HUBS_DIR / f"{sanitize(section)}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    master = ["---", "tags: [hub]", "---", "", "# 🧭 MyLab — Index des hubs", "",
              "_Point d'entrée du vault. Généré automatiquement — ne pas éditer._", ""]
    for section, rows in sections.items():
        master.append(f"- [[{sanitize(section)}]] ({len(rows)} entrées)")
    master += ["", "Sessions : [[_index]]"]
    (HUBS_DIR / "MyLab — Index.md").write_text("\n".join(master) + "\n", encoding="utf-8")
    return len(sections)


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    log("Scan des conversations Claude Code…")
    convs = find_conversations()
    log(f"{len(convs)} fichiers de conversation trouvés")
    budget = LlmBudget()
    if not budget.key:
        log("  (pas de GEMINI_API_KEY — exports sans résumé/tags)")
    count = sum(1 for c in convs if export_conv(c, budget))
    log(f"{count} conversations exportées ({budget.used} résumés LLM) → {EXPORT_DIR}")
    m = mirror_memories()
    log(f"{m} fichiers mémoire miroirés → {MEMORY_DIR}")
    h = build_hubs()
    log(f"{h} hubs générés → {HUBS_DIR}")
    build_index()
    log("Index des sessions régénéré")

if __name__ == "__main__":
    main()
