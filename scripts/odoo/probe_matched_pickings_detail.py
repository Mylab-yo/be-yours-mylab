"""Detail des BL sortants des clients du fichier Station (matches par email)."""
import re
from pathlib import Path
from scripts.odoo._client import search_read

STATION_DIR = Path(r"C:\ProgramData\Station.NET")
EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")

f = sorted(STATION_DIR.glob("*_Expeditions.txt"))[-1]
emails = set()
for l in f.read_text(encoding="cp1252").splitlines():
    for c in l.split("\t"):
        c = c.strip()
        if EMAIL_RE.fullmatch(c):
            emails.add(c.lower())

partners = search_read("res.partner", [("email", "in", sorted(emails))],
    ["id", "name", "email", "commercial_partner_id"], limit=200)
print(f"{len(partners)} partners matches\n")

comm_ids = sorted({p["commercial_partner_id"][0] for p in partners if p.get("commercial_partner_id")})
all_ids = sorted(set(comm_ids) | {p["id"] for p in partners})

pks = search_read("stock.picking",
    [("picking_type_code", "=", "outgoing"), ("partner_id", "in", all_ids)],
    ["name", "state", "partner_id", "carrier_id", "carrier_tracking_ref",
     "scheduled_date", "date_done", "origin"], limit=200)

print(f"{len(pks)} BL sortants pour ces clients :\n")
for p in pks:
    car = p["carrier_id"][1] if p.get("carrier_id") else "—"
    print(f"  {p['name']:<16} {p['state']:<10} carrier={car:<28} "
          f"ref={p.get('carrier_tracking_ref') or '—':<14} "
          f"orig={p.get('origin') or '—':<12} sched={(p.get('scheduled_date') or '')[:10]} "
          f"part={p['partner_id'][1][:25]}")
