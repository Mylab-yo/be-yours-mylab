"""Inspect n8n workflow Xj8T5a7aO8drZk5v: Register Payment node state + recent
executions, to find why the payment step is skipped for some Shopify orders."""
import sys, io, json, urllib.request, urllib.parse
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# n8n API key = bare JWT on line 40 of .env.local
lines = Path(r"d:\Configurateur Designs MyLab\mylab-configurateur\.env.local").read_text(
    encoding="utf-8", errors="replace").splitlines()
API_KEY = lines[39].strip()
BASE = "https://n8n.startec-paris.com/api/v1"
WF = "Xj8T5a7aO8drZk5v"

def api(path):
    req = urllib.request.Request(f"{BASE}{path}",
                                 headers={"X-N8N-API-KEY": API_KEY,
                                          "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)

# 1. Workflow structure
wf = api(f"/workflows/{WF}")
print(f"=== WORKFLOW: {wf['name']} | active={wf['active']} ===")
nodes = wf["nodes"]
print(f"nodes: {len(nodes)}")
node_by_name = {n["name"]: n for n in nodes}
for n in nodes:
    disabled = n.get("disabled", False)
    flag = " [DISABLED]" if disabled else ""
    print(f"  - {n['name']} ({n['type'].split('.')[-1]}){flag}")

# 2. Connections out of Create Invoice / into Register Payment
print("\n=== CONNECTIONS (who feeds Register Payment) ===")
conns = wf.get("connections", {})
# find the payment node name
pay_names = [nm for nm in node_by_name if "payment" in nm.lower() or "règlement" in nm.lower()
             or "reglement" in nm.lower() or "paiement" in nm.lower()]
inv_names = [nm for nm in node_by_name if "invoice" in nm.lower() or "facture" in nm.lower()]
print("payment-ish nodes:", pay_names)
print("invoice-ish nodes:", inv_names)
for src, outs in conns.items():
    for outname, branches in outs.items():
        for branch in branches:
            for c in branch:
                if c["node"] in pay_names:
                    print(f"  {src} --{outname}--> {c['node']}")

# 3. Recent executions
print("\n=== RECENT EXECUTIONS ===")
ex = api(f"/executions?workflowId={WF}&limit=20&includeData=false")
for e in ex.get("data", []):
    print(f"  id={e['id']} status={e.get('status')} finished={e.get('finished')} "
          f"mode={e.get('mode')} started={e.get('startedAt')} stopped={e.get('stoppedAt')}")
