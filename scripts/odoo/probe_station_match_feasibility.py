"""Test de faisabilite : matcher les lignes du fichier Station Expeditions
contre Odoo (partner par email + existence d'un BL DPD).

Lecture seule. Ne modifie rien dans Odoo."""
import re
from pathlib import Path
from collections import defaultdict
from scripts.odoo._client import search_read, execute

STATION_DIR = Path(r"C:\ProgramData\Station.NET")
DPD_CARRIER_IDS = [11, 12, 13, 14, 15, 16, 17, 18]  # tous les carriers DPD (pas Palette=19)

# Fichier le plus recent YYYYMMDD_Expeditions.txt
files = sorted(STATION_DIR.glob("*_Expeditions.txt"))
assert files, "Aucun fichier *_Expeditions.txt"
f = files[-1]
raw = f.read_text(encoding="cp1252")
lines = [l for l in raw.splitlines() if l.strip()]
print(f"Fichier: {f.name}  ({len(lines)} lignes)\n")

# Parse + detection auto des colonnes email / tracking
EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
PARCEL_RE = re.compile(r"^\d{12,16}$")

rows = []
for l in lines:
    cols = l.split("\t")
    email = next((c.strip() for c in cols if EMAIL_RE.fullmatch(c.strip())), "")
    tracking = cols[17].strip() if len(cols) > 17 and PARCEL_RE.fullmatch(cols[17].strip()) else ""
    date = cols[1].strip() if len(cols) > 1 else ""
    name = cols[3].strip() or (cols[5].strip() if len(cols) > 5 else "")
    rows.append({"date": date, "name": name, "email": email, "tracking": tracking,
                 "ncols": len(cols)})

print(f"Colonnes par ligne (min/max): {min(r['ncols'] for r in rows)}/{max(r['ncols'] for r in rows)}")
print("Echantillon (3 lignes) :")
for r in rows[:3]:
    print(f"  date={r['date']} colis={r['tracking']!r} email={r['email']!r} nom={r['name']!r}")

with_email = [r for r in rows if r["email"]]
with_track = [r for r in rows if r["tracking"]]
print(f"\nLignes totales         : {len(rows)}")
print(f"  avec n° de colis     : {len(with_track)}")
print(f"  avec email           : {len(with_email)}")

# Regrouper par email (un client peut avoir plusieurs colis)
emails = sorted({r["email"].lower() for r in with_email})
print(f"  emails distincts     : {len(emails)}")

# 1) Matching partner par email
print("\n--- Matching Odoo ---")
matched_partners = {}  # email -> partner dict
for em in emails:
    res = search_read("res.partner", [("email", "=ilike", em)],
                      ["id", "name", "commercial_partner_id", "parent_id"], limit=1)
    if res:
        matched_partners[em] = res[0]
print(f"Emails retrouves dans res.partner : {len(matched_partners)}/{len(emails)}")

# 2) Ces partners ont-ils un BL DPD (stock.picking outgoing) ?
# On cherche par commercial_partner_id (la societe) pour ratisser large.
comm_ids = sorted({mp["commercial_partner_id"][0] for mp in matched_partners.values()
                   if mp.get("commercial_partner_id")})
partner_ids = sorted({mp["id"] for mp in matched_partners.values()})
all_ids = sorted(set(comm_ids) | set(partner_ids))

pickings = []
if all_ids:
    pickings = search_read("stock.picking",
        [("picking_type_code", "=", "outgoing"),
         ("partner_id", "in", all_ids)],
        ["id", "name", "state", "partner_id", "carrier_id", "carrier_tracking_ref"], limit=200)

dpd_bl = [p for p in pickings if p.get("carrier_id") and p["carrier_id"][0] in DPD_CARRIER_IDS]
print(f"Partners matches ayant >=1 BL sortant : "
      f"{len({p['partner_id'][0] for p in pickings})}")
print(f"  dont BL avec carrier DPD            : {len(dpd_bl)}")
print(f"  dont BL DPD SANS tracking encore    : "
      f"{len([p for p in dpd_bl if not p.get('carrier_tracking_ref')])}")

print("\n--- Lignes non-matchables aujourd'hui (= Choose ou pas de BL Odoo) ---")
no_match = [r for r in with_email if r["email"].lower() not in matched_partners]
print(f"Emails absents d'Odoo (probables Choose / clients non crees) : "
      f"{len({r['email'].lower() for r in no_match})}")
for r in no_match[:8]:
    print(f"  {r['email']:<35} {r['name']}")
