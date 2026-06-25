"""Verify the opportunities created by the fixed Lead Design workflow."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from scripts.odoo._client import search_read

opps = search_read("crm.lead", [], ["id", "name", "email_from", "phone", "priority", "type", "description"])
print(f"crm.lead records: {len(opps)}\n")
for o in sorted(opps, key=lambda x: x["id"]):
    print(f"#{o['id']} [{o['type']}] prio={o['priority']} | {o['name']}")
    print(f"   email={o['email_from']} phone={o['phone']}")
    desc = (o.get("description") or "").replace("\n", " | ")
    print(f"   desc: {desc[:240]}")
    print()
