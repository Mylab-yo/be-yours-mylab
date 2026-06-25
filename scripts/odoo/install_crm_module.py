"""Install the CRM module in Odoo so crm.lead exists (needed by the Lead Design wf)."""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from scripts.odoo._client import search_read, execute

mod = search_read("ir.module.module", [("name", "=", "crm")], ["id", "name", "state"])
if not mod:
    print("crm module not found in registry"); sys.exit(1)
mod = mod[0]
print(f"crm module: id={mod['id']} state={mod['state']}")

if mod["state"] in ("installed", "to upgrade"):
    print("Already installed.")
else:
    print("Installing crm (button_immediate_install)...")
    # returns an action dict (or None) — _client tolerates None marshalling
    execute("ir.module.module", "button_immediate_install", [[mod["id"]]])
    print("Install call returned.")

# poll until crm.lead resolves
ok = False
for attempt in range(10):
    try:
        cnt = execute("crm.lead", "search_count", [[]])
        print(f"crm.lead search_count = {cnt}  -> model EXISTS")
        ok = True
        break
    except Exception as e:
        print(f"  attempt {attempt+1}: crm.lead not ready yet ({str(e)[:60]})")
        time.sleep(3)

st = search_read("ir.module.module", [("name", "=", "crm")], ["state"])[0]["state"]
print(f"\nFinal crm module state = {st} | crm.lead usable = {ok}")
