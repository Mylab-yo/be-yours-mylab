"""Re-send the payloads of the previously-failed Lead Design executions to the now-fixed
webhook, so the lost leads get their Odoo opportunity. Dedupe by 'reference'.

Default = dry (list unique leads). Pass --send to actually POST to the production webhook.
"""
import sys, io, json, urllib.request
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SEND = "--send" in sys.argv
N8N_KEY = Path(r"d:\Configurateur Designs MyLab\mylab-configurateur\.env.local").read_text(
    encoding="utf-8", errors="replace").splitlines()[39].strip()
BASE = "https://n8n.startec-paris.com/api/v1"
WEBHOOK = "https://n8n.startec-paris.com/webhook/lead-design-validated"
FAILED_EXECS = [91859, 91862, 91902, 91903]


def n8n(path):
    req = urllib.request.Request(f"{BASE}{path}",
                                 headers={"X-N8N-API-KEY": N8N_KEY, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


# Collect bodies from failed executions
leads = {}
for exid in FAILED_EXECS:
    e = n8n(f"/executions/{exid}?includeData=true")
    rd = e.get("data", {}).get("resultData", {})
    run = rd.get("runData", {})
    body = None
    for nm in run:
        if "Webhook" in nm or "Lead" in nm:
            try:
                body = run[nm][0]["data"]["main"][0][0]["json"]["body"]
            except Exception:
                pass
    if body:
        # dedupe by email (a prospect = one opportunity); FAILED_EXECS ascending so
        # the most recent execution wins and keeps its reference
        key = (body.get("email") or body.get("reference") or str(exid)).lower()
        leads[key] = {"exid": exid, "body": body}

print(f"Failed execs: {FAILED_EXECS} -> {len(leads)} unique lead(s) by email:")
for ref, info in leads.items():
    b = info["body"]
    print(f"  ref={ref} | exec {info['exid']} | {b.get('brandName')} | {b.get('email')}")

if not SEND:
    print("\n--- DRY. Re-run with --send to POST these to the production webhook. ---")
    sys.exit(0)

print("\n=== SENDING ===")
for ref, info in leads.items():
    payload = json.dumps(info["body"]).encode()
    req = urllib.request.Request(WEBHOOK, data=payload, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = r.read().decode("utf-8", "replace")
        print(f"  ref={ref} -> HTTP {r.status} | {resp[:200]}")
    except urllib.error.HTTPError as he:
        print(f"  ref={ref} -> HTTP ERROR {he.code} | {he.read().decode('utf-8','replace')[:300]}")
    except Exception as ex:
        print(f"  ref={ref} -> ERROR {ex}")
