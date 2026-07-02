"""Patch le workflow n8n 'Sync Stock Odoo -> Shopify' (id 1AUxe9M9d9cNKz6W).

Remplace le jsCode du node "Lire stocks Shopify et comparer" par le contenu de
02-lire-shopify-comparer.js (MIROIR EXACT Odoo->Shopify, 0 inclus, negatifs clamp a 0,
miroir testeurs->parent), pour que la synchro auto (toutes les 5h) garde Shopify aligne
sur Odoo. A 0 : le backorder (continue) ou le prevenez-moi (deny) prend le relais.

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
    print(f"  miroir exact (Math.max(0, m.eff)) : {'Math.max(0, m.eff)' in new_js} | testeur : {'testeur' in new_js}")

    if dry:
        print("DRY RUN : pas de PUT")
        return

    # n8n PUT n'accepte QUE name/nodes/connections/settings. Whitelist stricte : un
    # blacklist casse des que l'API renvoie un nouveau champ lecture seule (400
    # "must NOT have additional properties"). settings aussi whiteliste (refuse
    # availableInMCP, binaryMode...).
    allowed_settings = {"executionOrder", "callerPolicy", "saveManualExecutions",
                        "saveExecutionProgress", "saveDataErrorExecution",
                        "saveDataSuccessExecution", "executionTimeout", "errorWorkflow",
                        "timezone", "callerIds"}
    # Nettoyer les connexions orphelines : une source qui ne reference plus un node
    # existant (ici "Toutes les 5 minutes", vestige d'un renommage du trigger) fait
    # echouer le PUT ("unknown_connection_source"). n8n l'ignore au runtime mais la
    # validation PUT est stricte. On ne garde que les sources = node existant.
    node_names = {n["name"] for n in wf["nodes"]}
    clean_connections = {src: conns for src, conns in (wf.get("connections") or {}).items()
                         if src in node_names}
    dropped = set(wf.get("connections", {})) - set(clean_connections)
    if dropped:
        print(f"  connexions orphelines retirees : {sorted(dropped)}")
    body = {
        "name": wf["name"],
        "nodes": wf["nodes"],
        "connections": clean_connections,
        "settings": {k: v for k, v in (wf.get("settings") or {}).items() if k in allowed_settings},
    }
    updated = req("PUT", f"/api/v1/workflows/{WORKFLOW_ID}", key, body)
    print(f"PUT OK | versionId={updated.get('versionId')}")

    # Republier : un PUT met a jour le brouillon (versionId) mais PAS forcement la
    # version active (activeVersionId). deactivate+activate aligne l'active sur le neuf.
    if wf.get("active"):
        req("POST", f"/api/v1/workflows/{WORKFLOW_ID}/deactivate", key)
        req("POST", f"/api/v1/workflows/{WORKFLOW_ID}/activate", key)
        print("republie (deactivate + activate)")

    # re-verifier
    fresh = req("GET", f"/api/v1/workflows/{WORKFLOW_ID}", key)
    fnode = next(n for n in fresh["nodes"] if n["name"] == NODE_NAME)
    js = fnode["parameters"]["jsCode"]
    print(f"VERIF : miroir 'Math.max(0, m.eff)' = {'Math.max(0, m.eff)' in js} | 'parentOf' = {'parentOf' in js} | active={fresh['active']}")


if __name__ == "__main__":
    main()
