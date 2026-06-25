"""Fix wf 83JGhapLmLlBjR30 (Lead Design Valide -> Odoo): Odoo node gets 'Access Denied'
because its n8n credential is stale. We:
  1. verify crm.lead exists (node target),
  2. create a fresh odooApi credential with the known-good .env.local creds,
  3. repoint the Odoo node onto it (REST PUT),
  4. re-activate the workflow.

Run with --apply to mutate; default is dry/verify only.
Never prints the API key.
"""
import sys, io, json, os, urllib.request, xmlrpc.client
from pathlib import Path
from dotenv import load_dotenv
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

APPLY = "--apply" in sys.argv
ENV = Path(r"d:\Configurateur Designs MyLab\mylab-configurateur\.env.local")
load_dotenv(ENV)
ODOO_URL = os.environ["ODOO_URL"].strip()
ODOO_DB = os.environ["ODOO_DB"].strip()
ODOO_LOGIN = os.environ.get("ODOO_LOGIN", "").strip() or os.environ["ODOO_USER"].strip()
ODOO_KEY = os.environ["ODOO_API_KEY"].strip()

N8N_KEY = ENV.read_text(encoding="utf-8", errors="replace").splitlines()[39].strip()
BASE = "https://n8n.startec-paris.com/api/v1"
WF = "83JGhapLmLlBjR30"
CRED_NAME = "Odoo account (API key)"


def n8n(path, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{BASE}{path}", data=data, method=method,
                                 headers={"X-N8N-API-KEY": N8N_KEY,
                                          "Accept": "application/json",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
        return json.loads(raw) if raw else {}


# 1) verify crm.lead exists with the good creds
common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common", allow_none=True)
uid = common.authenticate(ODOO_DB, ODOO_LOGIN, ODOO_KEY, {})
models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object", allow_none=True)
n_leads = models.execute_kw(ODOO_DB, uid, ODOO_KEY, "crm.lead", "search_count", [[]])
print(f"Odoo uid={uid} | crm.lead exists, current count={n_leads}")

if not APPLY:
    print("\n--- DRY RUN. Re-run with --apply to create credential + repoint node. ---")
    sys.exit(0)

# 2) create fresh odooApi credential
cred = n8n("/credentials", "POST", {
    "name": CRED_NAME,
    "type": "odooApi",
    "data": {"url": ODOO_URL, "db": ODOO_DB, "username": ODOO_LOGIN, "password": ODOO_KEY},
})
new_id = cred.get("id")
print(f"Created credential id={new_id} name={cred.get('name')!r}")

# 3) repoint Odoo node onto the new credential (REST PUT)
wf = n8n(f"/workflows/{WF}")
nodes = wf["nodes"]
changed = []
for node in nodes:
    if node.get("type") == "n8n-nodes-base.odoo":
        node["credentials"] = {"odooApi": {"id": new_id, "name": CRED_NAME}}
        changed.append(node["name"])
print(f"Repointed Odoo node(s): {changed}")

put_body = {
    "name": wf["name"],
    "nodes": nodes,
    "connections": wf["connections"],
    "settings": wf.get("settings", {}),
}
if wf.get("staticData"):
    put_body["staticData"] = wf["staticData"]
n8n(f"/workflows/{WF}", "PUT", put_body)
print("Workflow updated (PUT ok)")

# 4) re-activate
try:
    n8n(f"/workflows/{WF}/activate", "POST")
    print("Workflow re-activated")
except Exception as e:
    print(f"Activate call: {e}")

# verify
w2 = n8n(f"/workflows/{WF}")
print(f"\nactive={w2.get('active')}")
for node in w2["nodes"]:
    if node.get("type") == "n8n-nodes-base.odoo":
        print(f"  node '{node['name']}' -> credentials={json.dumps(node.get('credentials'), ensure_ascii=False)}")
