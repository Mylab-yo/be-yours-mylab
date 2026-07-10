"""Patch le node 'Match Products' du workflow n8n Shopify -> Odoo (Xj8T5a7aO8drZk5v)
avec le jsCode courant de 02_odoo_client.js + 04_match_products.js.

Contexte : fix 2026-07-10 — la ligne de port ignorait les remises Shopify
(discount_allocations sur shipping_lines), donc un code promo "frais de port
offerts" était quand même facturé par Odoo (cf. commande #3537 / FAC/2026/00167).

Usage:
    python scripts/n8n/shopify_order_workflow/patch_workflow_match_products.py [--dry-run]

Idempotent : remplace simplement le jsCode du node existant.
"""
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

HERE = Path(__file__).parent
ENV_FILE = Path(r"d:\Configurateur Designs MyLab\mylab-configurateur\.env.local")
ENV_LINE_INDEX = 39  # 0-indexed -> ligne 40 = N8N_API_KEY (meme source que devis_manuel)

N8N_URL = "https://n8n.startec-paris.com"
WORKFLOW_ID = "Xj8T5a7aO8drZk5v"
NODE_NAME = "Match Products"

ALLOWED_SETTINGS_KEYS = {
    "executionOrder", "saveDataErrorExecution", "saveDataSuccessExecution",
    "saveExecutionProgress", "saveManualExecutions", "timezone",
    "errorWorkflow", "callerPolicy", "executionTimeout",
}


def load_api_key() -> str:
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    key = lines[ENV_LINE_INDEX].strip()
    if "=" in key:
        key = key.split("=", 1)[1].strip().strip('"').strip("'")
    if not key or key.startswith("#"):
        sys.exit(f"ERROR: ligne {ENV_LINE_INDEX + 1} de .env.local vide ou commentaire")
    return key


def api_request(method: str, path: str, api_key: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        f"{N8N_URL}{path}",
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={
            "X-N8N-API-KEY": api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.exit(f"ERROR: HTTP {e.code} on {method} {path}\n{e.read().decode(errors='replace')[:500]}")


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    api_key = load_api_key()

    js_code = (
        (HERE / "02_odoo_client.js").read_text(encoding="utf-8")
        + "\n\n"
        + (HERE / "04_match_products.js").read_text(encoding="utf-8")
    )

    print(f"GET workflow {WORKFLOW_ID}")
    wf = api_request("GET", f"/api/v1/workflows/{WORKFLOW_ID}", api_key)
    print(f"  name={wf['name']!r} active={wf.get('active')} nodes={len(wf.get('nodes', []))}")

    node = next((n for n in wf["nodes"] if n["name"] == NODE_NAME), None)
    if node is None:
        sys.exit(f"ERROR: node {NODE_NAME!r} introuvable")

    old_len = len(node["parameters"].get("jsCode", ""))
    node["parameters"]["jsCode"] = js_code
    print(f"  [{NODE_NAME}] jsCode: {old_len} -> {len(js_code)} chars")

    if dry_run:
        print("DRY RUN: pas de PUT")
        return

    settings = {k: v for k, v in (wf.get("settings") or {}).items() if k in ALLOWED_SETTINGS_KEYS}
    put_body = {
        "name": wf["name"],
        "nodes": wf["nodes"],
        "connections": wf.get("connections", {}),
        "settings": settings,
    }
    if wf.get("staticData"):
        put_body["staticData"] = wf["staticData"]

    print("PUT workflow...")
    api_request("PUT", f"/api/v1/workflows/{WORKFLOW_ID}", api_key, put_body)

    wf2 = api_request("GET", f"/api/v1/workflows/{WORKFLOW_ID}", api_key)
    node2 = next(n for n in wf2["nodes"] if n["name"] == NODE_NAME)
    ok = "shipDiscountPct" in node2["parameters"].get("jsCode", "")
    print(f"Verify: active={wf2.get('active')} shipDiscountPct present={ok}")
    if not ok:
        sys.exit("ERROR: le jsCode patché ne contient pas le fix")
    print("DONE.")


if __name__ == "__main__":
    main()
