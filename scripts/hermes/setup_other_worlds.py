"""Create d:\\MyLab "viewport" — junction points to all MyLab projects + vault,
plus a router CLAUDE.md, plus a junction so the auto-memory loads when opened
at d:\\MyLab too (not just d:\\be-yours-mylab).

Idempotent: re-running rebuilds junctions safely (rmdir on existing junctions).
"""
import subprocess
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


# Junctions to create: (link_path, target_path)
JUNCTIONS = [
    # 5 projects
    (r"d:\MyLab\worlds\be-yours-mylab", r"d:\be-yours-mylab"),
    (r"d:\MyLab\worlds\bastien-svc", r"d:\bastien-svc"),
    (r"d:\MyLab\worlds\mylab-studio-worker", r"d:\mylab-studio-worker"),
    (r"d:\MyLab\worlds\mylab-configurateur", r"d:\Configurateur Designs MyLab\mylab-configurateur"),
    (r"d:\MyLab\worlds\mylab-shopify-ext", r"d:\Configurateur Designs MyLab\mylab-shopify-ext"),
    # Obsidian vault (read-mostly; only .md writes allowed here)
    (r"d:\MyLab\worlds\obsidian-vault", r"C:\Users\startec\Documents\MyLab"),
    # Auto-memory: share the rich memory dir between be-yours-mylab and MyLab workspaces
    (
        r"C:\Users\startec\.claude\projects\d--MyLab\memory",
        r"C:\Users\startec\.claude\projects\d--be-yours-mylab\memory",
    ),
]


def ensure_parent(p):
    Path(p).parent.mkdir(parents=True, exist_ok=True)


def create_junction(link, target):
    link_p = Path(link)
    target_p = Path(target)

    if not target_p.exists():
        return f"⚠️  TARGET MISSING: {target} — skipping"

    ensure_parent(link)

    # If link already exists as junction, remove via `rmdir` (works for junctions on Windows)
    if link_p.exists() or link_p.is_symlink():
        # Junction in Python looks like a dir; rmdir removes only junctions/empty dirs
        try:
            subprocess.run(["cmd", "/c", "rmdir", str(link_p)], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            return f"❌ Couldn't remove existing {link}: {e.stderr.decode(errors='replace')}"

    # Create junction (mklink /J doesn't need admin for directories)
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link_p), str(target_p)],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        return f"✅ {link} → {target}"
    return f"❌ {link} ← FAILED: {result.stderr.strip()}"


print("Creating junctions...\n")
for link, target in JUNCTIONS:
    print(create_junction(link, target))


# --- Write CLAUDE.md router at d:\MyLab\CLAUDE.md
CLAUDE_MD = r"""# MyLab — Router

Vue d'ensemble cross-projet pour Yoann (STARTEC, MY.LAB). Ouvre Claude à `d:\MyLab` pour que la session voie tous les projets simultanément. Pour travailler en focus sur UN projet, ouvre directement son dossier d'origine (les chemins sont indiqués ci-dessous — les junctions ne sont qu'un viewport, les vrais repos vivent à leur emplacement d'origine).

## Worlds (projets accessibles via `worlds/`)

| Junction | Cible réelle | Stack | Repo GitHub | Branche par défaut |
|---|---|---|---|---|
| `worlds/be-yours-mylab/` | `d:\be-yours-mylab` | Shopify theme (Liquid) + scripts Odoo XML-RPC + scripts Hermes | github.com/Mylab-yo/be-yours-mylab | feature/stock-mrp-setup |
| `worlds/bastien-svc/` | `d:\bastien-svc` | Bot chat web (Python FastAPI sur VPS, chat.mylab-shop.com) | github.com/Mylab-yo/bastien-svc | main |
| `worlds/mylab-studio-worker/` | `d:\mylab-studio-worker` | Worker GPU ComfyUI pour SaaS MY.LAB Studio | github.com/Mylab-yo/mylab-studio-worker | master |
| `worlds/mylab-configurateur/` | `d:\Configurateur Designs MyLab\mylab-configurateur` | Configurateur produits B2B (Next.js Vercel) | github.com/Mylab-yo/mylab-configurateur | main |
| `worlds/mylab-shopify-ext/` | `d:\Configurateur Designs MyLab\mylab-shopify-ext` | Extension Shopify (assets/secrets pour intégration configurateur) | — | — |
| `worlds/obsidian-vault/` | `C:\Users\startec\Documents\MyLab` | Vault Obsidian (notes + export auto Claude Code) | local | — |

## Règles de navigation cross-world

- **Édition autorisée partout** sauf le vault Obsidian (voir règle suivante)
- **Vault Obsidian (`worlds/obsidian-vault/`)** : READ libre pour cross-référencer notes existantes. WRITE uniquement en `.md` (Obsidian ne traite pas correctement les .py/.json/.tsx). Ne JAMAIS y écrire de code source, de logs bruts, de JSON volumineux.
- **Git** : chaque world a son propre `.git`. Toujours `cd` dans le world avant tout `git ...`. Ne JAMAIS faire un `git init` à la racine `d:\MyLab\`.
- **Cwd pour les scripts** : si un script attend un cwd spécifique (ex: `shopify theme push` veut le repo theme), utiliser le chemin RÉEL (`d:\be-yours-mylab`) ou `cd worlds/be-yours-mylab` puis exécuter — les junctions Windows sont transparentes pour la quasi-totalité des outils.

## Mémoire

L'auto-memory MyLab est junction-iée à `C:\Users\startec\.claude\projects\d--MyLab\memory\` → la vraie mémoire à `d--be-yours-mylab\memory\`. Donc :
- Le `MEMORY.md` racine se charge automatiquement quand tu ouvres Claude à `d:\MyLab` aussi
- Tout fichier mémoire écrit ici est visible depuis les 2 workspaces (be-yours-mylab et MyLab)
- Index complet : `worlds/be-yours-mylab/CLAUDE.md` (pour contexte technique Shopify+Odoo)

## Skills MyLab disponibles globalement (`/<nom>`)

- `/import-releve` — relevé LCL CSV → Odoo
- `/lettrage-bancaire` — lettrage automatique lignes bancaires Odoo
- `/sync-produits-odoo` — sync catalogues Shopify↔Odoo
- `/import-choose-dpd-mr` — split DPD Predict + Mondial Relay quotidien
- `/parcours-harmonize-page` — habiller page Shopify avec grammaire parcours
- `/detourer-logo` — détourer logo PDF/PNG/JPG → PNG transparent
- `/grill-me` — extraction de savoir tacite vers mémoire
- `/shopify-oauth-token` — récupérer shpat_ via OAuth+ngrok
- `/customize-odoo-pdf` — personnaliser template PDF Odoo

## Infrastructure partagée

- **VPS** : 82.25.112.124 (Ubuntu 24.04, root) — héberge Odoo, n8n, Bastien, Evolution, Hermes
- **Odoo** : odoo.startec-paris.com (DB OdooYJ, UID 8)
- **n8n** : n8n.startec-paris.com
- **Hermes Agent** : container Docker sur VPS, bot Telegram @mylab_hermes_bot, cron morning brief quotidien 8h Paris
- **Shopify** : mylab-shop-3.myshopify.com

## Quand utiliser ce viewport vs le repo direct

- **Ouvre `d:\MyLab\`** quand tu veux du cross-projet : ex "synchronise le configurateur et le thème", "le bot Bastien doit pointer vers la nouvelle URL Shopify", audit global, brainstorming structure produit
- **Ouvre `d:\be-yours-mylab\`** (ou autre repo direct) quand tu fais du focus pur sur ce repo : développement Shopify theme, scripts Odoo, debug d'un workflow n8n

Les 2 entrées chargent la même mémoire (junction), donc pas de divergence.
"""

claude_md_path = Path(r"d:\MyLab\CLAUDE.md")
claude_md_path.write_text(CLAUDE_MD, encoding="utf-8")
print(f"\n✅ Wrote {claude_md_path}")


README_MD = r"""# MyLab — Viewport

Ce dossier n'est PAS un projet, c'est un **viewport** : un point d'entrée unique pour ouvrir tous les projets MyLab dans une seule session Claude Code.

## Comment ça marche

Le dossier `worlds/` contient des **junctions Windows** (équivalent symlinks) vers les vrais repos qui vivent ailleurs sur le disque. Aucun fichier n'a été déplacé.

## Usage

```bash
# Ouvrir Claude / VS Code à la racine pour voir tous les projets
code d:\MyLab

# Ou ouvrir un repo en focus
code d:\be-yours-mylab
```

## Maintenance

Pour reconstruire les junctions (ex: ajout d'un nouveau projet) :
```bash
python d:\be-yours-mylab\scripts\hermes\setup_other_worlds.py
```

Le script est idempotent.

## Architecture

Voir [`CLAUDE.md`](./CLAUDE.md) pour la cartographie des worlds, les règles cross-projet, et les skills disponibles.
"""

readme_path = Path(r"d:\MyLab\README.md")
readme_path.write_text(README_MD, encoding="utf-8")
print(f"✅ Wrote {readme_path}")

# --- Verify everything
print("\n=== Verification ===")
for link, target in JUNCTIONS:
    link_p = Path(link)
    exists = link_p.exists()
    is_dir = link_p.is_dir() if exists else False
    print(f"  {link}: exists={exists} is_dir={is_dir}")

print(f"\n  d:\\MyLab\\ contents: {sorted(p.name for p in Path('d:/MyLab').iterdir())}")
print(f"  d:\\MyLab\\worlds\\ contents: {sorted(p.name for p in Path('d:/MyLab/worlds').iterdir())}")
