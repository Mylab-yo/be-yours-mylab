"""Patch le workflow n8n 'Sync Stock Odoo -> Shopify' (id 1AUxe9M9d9cNKz6W).

Remplace le jsCode du node "Lire stocks Shopify et comparer" par le contenu de
02-lire-shopify-comparer.js (ajout filtre odoo_qty>0 + miroir testeurs->parent),
pour que la synchro auto (toutes les 5h) ne remette JAMAIS un produit a 0.

Usage:
    python scripts/n8n/sync-stock-odoo-shopify/patch_workflow.py [--dry-run]

Token : .env.local ligne index 39 (N8N_API_KEY), meme source que devis_manuel/patch_workflow.py.
"""
import json, sys, urllib.request, urllib.error
from pathlib import Path

HERE = Path(__file__).parent
ENV_FILE = Path(r"d:\Configurateur Designs MyLab\mylab-configurateur\.env.local")
ENV_LINE_INDEX = 39
WORKFLOW_ID = "1AUxe9M9d9cNKz6W"
N8N_BASE = "https://n8n.startec-paris.com"
NODE_NAME = "Lire stocks Shopify et comparer"

READ_ONLY_FIELDS = {
    "updatedAt", "createdAt", "versionId", "activeVersionId", "triggerCount",
    "isArchived", "versionCounter", "description", "meta", "pinData",
    "staticData", "shared", "id", "active", "tags", "activeVersion",
}


def api_key():
    return ENV_FILE.read_text(encoding="utf-8").splitlines()[ENV_LINE_INDEX].strip()


def req(method, path, key, body=None):
    url = f"{N8N_BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("X-N8N-API-KEY", key)
    r.add_header("Content-Type", "application/json")
    r.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} on {method} {path}\n{e.read().decode('utf-8','replace')}")


def main():
    dry = "--dry-run" in sys.argv
    key = api_key()
    new_js = (HERE / "02-lire-shopify-comparer.js").read_text(encoding="utf-8")

    wf = req("GET", f"/api/v1/workflows/{WORKFLOW_ID}", key)
    print(f"GET {wf['name']} | active={wf['active']} | nodes={len(wf['nodes'])}")

    node = next((n for n in wf["nodes"] if n["name"] == NODE_NAME), None)
    if not node:
        sys.exit(f"node '{NODE_NAME}' introuvable")
    old = node["parameters"].get("jsCode", "")
    node["parameters"]["jsCode"] = new_js
    print(f"  jsCode {NODE_NAME}: {len(old)} -> {len(new_js)} chars")
    print(f"  contient filtre >0 : {'m.eff > 0' in new_js} | testeur : {'testeur' in new_js}")

    if dry:
        print("DRY RUN : pas de PUT")
        return

    body = {k: v for k, v in wf.items() if k not in READ_ONLY_FIELDS}
    # n8n PUT refuse les settings additionnels (availableInMCP, binaryMode...) -> whitelist
    allowed_settings = {"executionOrder", "callerPolicy", "saveManualExecutions",
                        "saveExecutionProgress", "saveDataErrorExecution",
                        "saveDataSuccessExecution", "executionTimeout", "errorWorkflow",
                        "timezone", "callerIds"}
    body["settings"] = {k: v for k, v in (wf.get("settings") or {}).items() if k in allowed_settings}
    updated = req("PUT", f"/api/v1/workflows/{WORKFLOW_ID}", key, body)
    print(f"PUT OK | versionId={updated.get('versionId')}")

    # re-verifier
    fresh = req("GET", f"/api/v1/workflows/{WORKFLOW_ID}", key)
    fnode = next(n for n in fresh["nodes"] if n["name"] == NODE_NAME)
    js = fnode["parameters"]["jsCode"]
    print(f"VERIF : node a 'm.eff > 0' = {'m.eff > 0' in js} | 'parentOf' = {'parentOf' in js} | active={fresh['active']}")


if __name__ == "__main__":
    main()
