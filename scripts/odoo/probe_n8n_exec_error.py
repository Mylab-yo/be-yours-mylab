"""Fetch the error detail of failing executions to see where/why it breaks."""
import sys, io, json, urllib.request
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

lines = Path(r"d:\Configurateur Designs MyLab\mylab-configurateur\.env.local").read_text(
    encoding="utf-8", errors="replace").splitlines()
API_KEY = lines[39].strip()
BASE = "https://n8n.startec-paris.com/api/v1"
WF = "Xj8T5a7aO8drZk5v"

def api(path):
    req = urllib.request.Request(f"{BASE}{path}",
                                 headers={"X-N8N-API-KEY": API_KEY,
                                          "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

# First error (06-06) and a recent one (06-11)
for exid in (87737, 89243):
    print(f"\n{'='*70}\n=== EXECUTION {exid} ===")
    e = api(f"/executions/{exid}?includeData=true")
    data = e.get("data", {})
    rd = data.get("resultData", {})
    err = rd.get("error")
    if err:
        print("ERROR node:", err.get("node", {}).get("name") if isinstance(err.get("node"), dict) else err.get("node"))
        print("ERROR message:", err.get("message"))
        desc = err.get("description")
        if desc:
            print("ERROR description:", str(desc)[:500])
    # which nodes ran
    runData = rd.get("runData", {})
    print("nodes executed:", list(runData.keys()))
    # inspect Register Payment / Create Invoice output
    for nm in ("Create Invoice", "Register Payment"):
        if nm in runData:
            try:
                out = runData[nm][0]
                if out.get("error"):
                    print(f"  [{nm}] node error: {out['error'].get('message')}")
                else:
                    j = out["data"]["main"][0][0]["json"]
                    # print key payment/invoice fields
                    keys = {k: j[k] for k in j if any(s in k.lower() for s in
                            ("payment", "invoice", "error", "status"))}
                    print(f"  [{nm}] output keys: {json.dumps(keys, ensure_ascii=False)[:600]}")
            except Exception as ex:
                print(f"  [{nm}] (couldn't parse: {ex})")
