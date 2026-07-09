"""DRY-RUN : mappe les colis du fichier Station Expeditions -> BL Odoo -> email client.
LECTURE SEULE. N'ecrit rien dans Odoo, n'envoie aucun mail.

Logique :
- regroupe les lignes Station par email destinataire (col 38)
- pour chaque email : retrouve le(s) partner(s) Odoo -> societe (commercial_partner_id)
- cherche les BL sortants non encore tracke (carrier_tracking_ref vide, non annule)
- si plusieurs BL : prend celui dont scheduled_date est le plus proche de la date Station
"""
import re
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from scripts.odoo._client import search_read

STATION_DIR = Path(r"C:\ProgramData\Station.NET")
EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
PARCEL_RE = re.compile(r"^\d{12,16}$")
OPEN_STATES = ("confirmed", "assigned", "waiting")


def pick_file():
    if len(sys.argv) > 1:
        return STATION_DIR / sys.argv[1]
    return sorted(STATION_DIR.glob("*_Expeditions.txt"))[-1]


def parse_station(f):
    """Retourne liste de dict : {date, parcel, email, name, relay}."""
    rows = []
    for l in f.read_text(encoding="cp1252").splitlines():
        if not l.strip():
            continue
        c = l.split("\t")
        email = next((x.strip() for x in c if EMAIL_RE.fullmatch(x.strip())), "")
        parcel = c[17].strip() if len(c) > 17 and PARCEL_RE.fullmatch(c[17].strip()) else ""
        relay = c[31].strip() if len(c) > 31 and c[31].strip().startswith("P") else ""
        rows.append({"date": c[1].strip(), "parcel": parcel, "email": email.lower(),
                     "name": (c[3].strip() or c[5].strip()), "relay": relay})
    return rows


def to_date(s):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:19] if " " in s else s, fmt)
        except (ValueError, TypeError):
            continue
    return None


def main():
    f = pick_file()
    rows = parse_station(f)
    print(f"Fichier: {f.name}  ({len(rows)} colis)\n")

    # Regroupe par email (un envoi multi-colis = N lignes -> 1 client -> 1 BL)
    by_email = defaultdict(list)
    no_email = []
    for r in rows:
        if r["email"]:
            by_email[r["email"]].append(r)
        else:
            no_email.append(r)

    # Partners pour tous les emails
    emails = sorted(by_email)
    partners = search_read("res.partner", [("email", "in", emails)],
        ["id", "name", "email", "commercial_partner_id"], limit=300)
    email2comm = defaultdict(set)
    for p in partners:
        comm = p["commercial_partner_id"][0] if p.get("commercial_partner_id") else p["id"]
        email2comm[(p.get("email") or "").lower()].add(comm)
        email2comm[(p.get("email") or "").lower()].add(p["id"])

    matched, ambiguous, no_partner, no_bl = [], [], [], []

    for em, grp in by_email.items():
        parcels = [r["parcel"] for r in grp if r["parcel"]]
        sdate = to_date(grp[0]["date"])
        relay = next((r["relay"] for r in grp if r["relay"]), "")
        ids = sorted(email2comm.get(em, set()))
        if not ids:
            no_partner.append((em, grp[0]["name"], parcels))
            continue
        bls = search_read("stock.picking",
            [("picking_type_code", "=", "outgoing"),
             ("partner_id", "in", ids),
             ("state", "in", list(OPEN_STATES) + ["done"]),
             ("carrier_tracking_ref", "in", [False, ""])],
            ["name", "state", "origin", "partner_id", "scheduled_date"], limit=50)
        if not bls:
            no_bl.append((em, grp[0]["name"], parcels))
            continue
        if len(bls) > 1 and sdate:
            bls.sort(key=lambda b: abs(((to_date(b.get("scheduled_date")) or sdate) - sdate).days))
        chosen = bls[0]
        rec = {"email": em, "name": grp[0]["name"], "parcels": parcels, "relay": relay,
               "bl": chosen["name"], "origin": chosen.get("origin"),
               "partner": chosen["partner_id"][1], "state": chosen["state"],
               "ncands": len(bls)}
        (ambiguous if len(bls) > 1 else matched).append(rec)

    def show(rec):
        mode = f"RELAIS {rec['relay']}" if rec["relay"] else "domicile"
        print(f"  {rec['bl']:<15} <- {rec['origin'] or '?':<8} | {len(rec['parcels'])} colis {mode:<14}"
              f" | {rec['email']:<32} | {rec['partner'][:28]}")

    print(f"=== MATCH NET ({len(matched)}) : 1 BL evident, prets a notifier ===")
    for r in matched:
        show(r)
    if ambiguous:
        print(f"\n=== A ARBITRER ({len(ambiguous)}) : plusieurs BL ouverts, choix par date ===")
        for r in ambiguous:
            print(f"  ({r['ncands']} candidats)", end="")
            show(r)
    print(f"\n=== HORS PERIMETRE / EN ATTENTE ===")
    print(f"  Email absent d'Odoo (Choose / non cree) : {len(no_partner)} envoi(s)")
    for em, nm, pc in no_partner:
        print(f"     {em:<32} {nm} ({len(pc)} colis)")
    print(f"  Client Odoo mais aucun BL ouvert        : {len(no_bl)} envoi(s)")
    for em, nm, pc in no_bl:
        print(f"     {em:<32} {nm} ({len(pc)} colis)")
    print(f"  Lignes sans email (manuel)              : {len(no_email)} colis")

    total_env = len(by_email) + 0
    print(f"\nRESUME: {total_env} envois distincts | "
          f"{len(matched)} notifiables auto | {len(ambiguous)} a arbitrer | "
          f"{len(no_partner)} hors perimetre | {len(no_bl)} sans BL")


if __name__ == "__main__":
    main()
