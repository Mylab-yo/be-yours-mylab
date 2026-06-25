"""Inspect failing executions of 'MY.LAB - Lead Design Valide -> Odoo' (wf 83JGhapLmLlBjR30)."""
import sys, io, json, urllib.request, urllib.parse
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

lines = Path(r"d:\Configurateur Designs MyLab\mylab-configurateur\.env.local").read_text(
    encoding="utf-8", errors="replace").splitlines()
API_KEY = lines[39].strip()
BASE = "https://n8n.startec-paris.com/api/v1"
WF = "83JGhapLmLlBjR30"

def api(path):
    req = urllib.request.Request(f"{BASE}{path}",
                                 headers={"X-N8N-API-KEY": API_KEY, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

# List recent executions (errored first)
q = urllib.parse.urlencode({"workflowId": WF, "status": "error", "limit": 10, "includeData": "false"})
lst = api(f"/executions?{q}")
execs = lst.get("data", [])
print(f"Found {len(execs)} errored executions for wf {WF}")
for e in execs:
    print(f"  id={e['id']} | startedAt={e.get('startedAt')} | status={e.get('status')}")

if not execs:
    # fall back: list ALL recent to see statuses
    q2 = urllib.parse.urlencode({"workflowId": WF, "limit": 10})
    allx = api(f"/executions?{q2}").get("data", [])
    print(f"\nAll recent ({len(allx)}):")
    for e in allx:
        print(f"  id={e['id']} | startedAt={e.get('startedAt')} | status={e.get('status')}")
    execs = allx

# Detail of most recent errored (or most recent)
if execs:
    exid = execs[0]["id"]
    print(f"\n{'='*70}\n=== DETAIL EXECUTION {exid} ===")
    e = api(f"/executions/{exid}?includeData=true")
    data = e.get("data", {})
    rd = data.get("resultData", {}) if isinstance(data, dict) else {}
    err = rd.get("error")
    if err:
        node = err.get("node")
        node = node.get("name") if isinstance(node, dict) else node
        print("ERROR node:", node)
        print("ERROR message:", err.get("message"))
        if err.get("description"):
            print("ERROR description:", str(err.get("description"))[:800])
        if err.get("context"):
            print("ERROR context:", json.dumps(err.get("context"), ensure_ascii=False)[:800])
    runData = rd.get("runData", {})
    print("\nnodes executed:", list(runData.keys()))
    # webhook payload received
    for nm in runData:
        if "Webhook" in nm or "Lead" in nm:
            try:
                out = runData[nm][0]["data"]["main"][0][0]["json"]
                print(f"\n[{nm}] received payload:")
                print(json.dumps(out, ensure_ascii=False, indent=2)[:1500])
            except Exception as ex:
                print(f"[{nm}] couldn't parse payload: {ex}")
    # odoo node error
    for nm in runData:
        if "Odoo" in nm or "Opportunit" in nm:
            try:
                out = runData[nm][0]
                if out.get("error"):
                    print(f"\n[{nm}] node error: {out['error'].get('message')}")
                    if out['error'].get('description'):
                        print(f"[{nm}] desc: {str(out['error']['description'])[:600]}")
            except Exception as ex:
                print(f"[{nm}] couldn't parse: {ex}")
