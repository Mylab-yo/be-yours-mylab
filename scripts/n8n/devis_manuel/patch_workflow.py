"""Patch le workflow n8n 'MY.LAB - Devis Manuel (Formulaire)' avec le nouveau
code JS des nodes Parse Gemini et Creer Devis Odoo.

Usage:
    python scripts/n8n/devis_manuel/patch_workflow.py [--dry-run]

Lit:
    d:\\Configurateur Designs MyLab\\mylab-configurateur\\.env.local
        (ligne 39 = N8N_API_KEY ; meme source que create_order_cancelled_workflow.py)
    01_parse_gemini.js                   (jsCode pour le node Parse)
    02_creer_devis_odoo.js               (jsCode pour le node Creer Devis)

Met a jour:
    n8n workflow id e0rRHlz61Ll807gX     (via PUT REST API)
    ../../../docs/n8n-devis-manuel.json  (export local re-genere)

Champs read-only a exclure du PUT (n8n 1.x) :
    updatedAt, createdAt, versionId, activeVersionId, triggerCount,
    isArchived, versionCounter, description, meta, pinData, staticData,
    shared, id, active, tags, activeVersion
"""
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

HERE = Path(__file__).parent
REPO_ROOT = HERE.parent.parent.parent
EXPORT_FILE = REPO_ROOT / "docs" / "n8n-devis-manuel.json"
ENV_FILE = Path(r"d:\Configurateur Designs MyLab\mylab-configurateur\.env.local")
ENV_LINE_INDEX = 39  # 0-indexed; same as create_order_cancelled_workflow.py

WORKFLOW_ID = "e0rRHlz61Ll807gX"
N8N_BASE = "https://n8n.startec-paris.com"
PARSE_NODE_ID = "a1b2c3d4-0002-4000-8000-000000000002"
ODOO_NODE_ID = "a1b2c3d4-0003-4000-8000-000000000003"

READ_ONLY_FIELDS = {
    "updatedAt", "createdAt", "versionId", "activeVersionId", "triggerCount",
    "isArchived", "versionCounter", "description", "meta", "pinData",
    "staticData", "shared", "id", "active", "tags", "activeVersion"
}


def load_api_key() -> str:
    if not ENV_FILE.exists():
        sys.exit(f"ERROR: env file not found at {ENV_FILE}")
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    if len(lines) <= ENV_LINE_INDEX:
        sys.exit(f"ERROR: env file has only {len(lines)} lines, need line index {ENV_LINE_INDEX}")
    key = lines[ENV_LINE_INDEX].strip()
    if not key or key.startswith("#"):
        sys.exit(f"ERROR: line {ENV_LINE_INDEX} of env file is empty or a comment")
    return key


def n8n_request(method: str, path: str, api_key: str, body: dict | None = None) -> dict:
    url = f"{N8N_BASE}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("X-N8N-API-KEY", api_key)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        sys.exit(f"ERROR: HTTP {e.code} on {method} {path}\n{body_text}")


def patch_node_jscode(nodes: list, node_id: str, new_js: str, label: str) -> None:
    for node in nodes:
        if node.get("id") == node_id:
            old_len = len(node["parameters"].get("jsCode", ""))
            node["parameters"]["jsCode"] = new_js
            print(f"  [{label}] jsCode replaced: {old_len} -> {len(new_js)} chars")
            return
    sys.exit(f"ERROR: node id {node_id} ({label}) not found in workflow")


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    api_key = load_api_key()
    parse_js = (HERE / "01_parse_gemini.js").read_text(encoding="utf-8")
    odoo_js = (HERE / "02_creer_devis_odoo.js").read_text(encoding="utf-8")

    print(f"GET workflow {WORKFLOW_ID}")
    wf = n8n_request("GET", f"/api/v1/workflows/{WORKFLOW_ID}", api_key)
    print(f"  name: {wf.get('name')}")
    print(f"  active: {wf.get('active')}")
    print(f"  nodes count: {len(wf.get('nodes', []))}")

    patch_node_jscode(wf["nodes"], PARSE_NODE_ID, parse_js, "Parse avec Gemini")
    patch_node_jscode(wf["nodes"], ODOO_NODE_ID, odoo_js, "Creer devis Odoo")

    put_body = {k: v for k, v in wf.items() if k not in READ_ONLY_FIELDS}

    if dry_run:
        print("DRY RUN: not sending PUT")
        return

    print(f"PUT workflow {WORKFLOW_ID}")
    updated = n8n_request("PUT", f"/api/v1/workflows/{WORKFLOW_ID}", api_key, put_body)
    print(f"  versionId: {updated.get('versionId')}")
    print(f"  active: {updated.get('active')}")

    print(f"GET workflow (re-export) -> {EXPORT_FILE.relative_to(REPO_ROOT)}")
    fresh = n8n_request("GET", f"/api/v1/workflows/{WORKFLOW_ID}", api_key)
    EXPORT_FILE.write_text(json.dumps(fresh, ensure_ascii=False), encoding="utf-8")
    print(f"  size: {EXPORT_FILE.stat().st_size} bytes")

    print("\nDONE.")


if __name__ == "__main__":
    main()
