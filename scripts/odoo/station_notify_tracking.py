"""Notif tracking DPD : lit le fichier Station Expeditions du jour, matche chaque
envoi a son BL Odoo (par email), ecrit le n° de colis et envoie le mail d'expedition.

DRY-RUN PAR DEFAUT (n'ecrit rien, n'envoie rien). Ajouter --send pour agir.

Usage :
  python -m scripts.odoo.station_notify_tracking                 # dry-run, fichier du jour
  python -m scripts.odoo.station_notify_tracking --file 20260615_Expeditions.txt
  python -m scripts.odoo.station_notify_tracking --send          # ECRIT + ENVOIE

Idempotent : ignore les BL qui ont deja un carrier_tracking_ref (= deja notifies).
"""
import re
import sys
import argparse
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from scripts.odoo._client import search_read, execute

STATION_DIR = Path(r"C:\ProgramData\Station.NET")
TEMPLATE_ID = 27                 # mail.template "Shipping: Send by Email"
CARRIER_RELAIS = 11              # DPD Point Relais - France
CARRIER_DOMICILE = 13            # DPD Classic - France
DPD_CARRIER_IDS = [11, 12, 13, 14, 15, 16, 17, 18]
CANDIDATE_STATES = ["confirmed", "assigned", "waiting", "done"]

EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
PARCEL_RE = re.compile(r"^\d{12,16}$")


def find_file(arg):
    if arg:
        p = STATION_DIR / arg
        if not p.exists():
            sys.exit(f"Fichier introuvable : {p}")
        return p
    files = sorted(STATION_DIR.glob("*_Expeditions.txt"))
    if not files:
        sys.exit("Aucun fichier *_Expeditions.txt")
    return files[-1]


def parse_station(f):
    rows = []
    for l in f.read_text(encoding="cp1252").splitlines():
        if not l.strip():
            continue
        c = l.split("\t")
        email = next((x.strip() for x in c if EMAIL_RE.fullmatch(x.strip())), "")
        parcel = c[17].strip() if len(c) > 17 and PARCEL_RE.fullmatch(c[17].strip()) else ""
        relay = c[31].strip() if len(c) > 31 and c[31].strip().startswith("P") else ""
        rows.append({"date": c[1].strip(), "parcel": parcel, "email": email.lower(),
                     "name": (c[3].strip() or (c[5].strip() if len(c) > 5 else "")),
                     "relay": relay})
    return rows


def to_date(s):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:19] if " " in s else s, fmt)
        except (ValueError, TypeError):
            continue
    return None


def build_plan(rows):
    """Retourne (matched, multi, no_partner, no_bl, no_email_rows)."""
    by_email, no_email = defaultdict(list), []
    for r in rows:
        (by_email[r["email"]] if r["email"] else no_email).append(r)

    partners = search_read("res.partner", [("email", "in", sorted(by_email))],
        ["id", "email", "commercial_partner_id"], limit=500)
    email2ids = defaultdict(set)
    for p in partners:
        em = (p.get("email") or "").lower()
        email2ids[em].add(p["id"])
        if p.get("commercial_partner_id"):
            email2ids[em].add(p["commercial_partner_id"][0])

    matched, multi, no_partner, no_bl = [], [], [], []
    for em, grp in by_email.items():
        parcels = [r["parcel"] for r in grp if r["parcel"]]
        sdate = to_date(grp[0]["date"])
        relay = next((r["relay"] for r in grp if r["relay"]), "")
        ids = sorted(email2ids.get(em, set()))
        if not ids:
            no_partner.append({"email": em, "name": grp[0]["name"], "parcels": parcels})
            continue
        bls = search_read("stock.picking",
            [("picking_type_code", "=", "outgoing"), ("partner_id", "in", ids),
             ("state", "in", CANDIDATE_STATES), ("carrier_tracking_ref", "in", [False, ""])],
            ["name", "state", "origin", "partner_id", "carrier_id", "scheduled_date"], limit=50)
        if not bls:
            no_bl.append({"email": em, "name": grp[0]["name"], "parcels": parcels})
            continue
        if len(bls) > 1:
            # Priorite au BL reellement parti (done/assigned) sur le reliquat en
            # attente (waiting), puis a la proximite de date d'expedition.
            state_rank = {"done": 0, "assigned": 1, "confirmed": 2, "waiting": 3}
            bls.sort(key=lambda b: (
                state_rank.get(b.get("state"), 9),
                abs(((to_date(b.get("scheduled_date")) or sdate) - sdate).days) if sdate else 0))
        chosen = bls[0]
        rec = {"email": em, "name": grp[0]["name"], "parcels": parcels, "relay": relay,
               "pid": chosen["id"], "bl": chosen["name"], "origin": chosen.get("origin"),
               "partner": chosen["partner_id"][1], "state": chosen["state"],
               "cur_carrier": chosen.get("carrier_id"), "ncands": len(bls)}
        (multi if len(bls) > 1 else matched).append(rec)
    return matched, multi, no_partner, no_bl, no_email


def apply_record(rec):
    """Ecrit le tracking + carrier sur le BL puis envoie le mail. Retourne msg."""
    pid = rec["pid"]
    vals = {"carrier_tracking_ref": ",".join(rec["parcels"])}
    cur = rec["cur_carrier"]
    if not cur or cur[0] not in DPD_CARRIER_IDS:
        vals["carrier_id"] = CARRIER_RELAIS if rec["relay"] else CARRIER_DOMICILE
    execute("stock.picking", "write", [[pid], vals])
    mail_id = execute("mail.template", "send_mail", [TEMPLATE_ID, pid], {"force_send": True})
    return f"ecrit {vals.get('carrier_tracking_ref')} + mail#{mail_id}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="YYYYMMDD_Expeditions.txt (defaut = le plus recent)")
    ap.add_argument("--send", action="store_true", help="ECRIT dans Odoo + ENVOIE les mails")
    args = ap.parse_args()

    f = find_file(args.file)
    rows = parse_station(f)
    matched, multi, no_partner, no_bl, no_email = build_plan(rows)

    mode = "ENVOI REEL" if args.send else "DRY-RUN (aucune ecriture/envoi)"
    print(f"Fichier: {f.name} ({len(rows)} colis) | MODE: {mode}\n")

    print(f"=== A NOTIFIER ({len(matched)}) ===")
    for r in matched:
        line = (f"  {r['bl']:<15} <- {r['origin'] or '?':<8} | {len(r['parcels'])} colis "
                f"{'RELAIS '+r['relay'] if r['relay'] else 'domicile':<14} | {r['email']:<32}")
        if args.send:
            line += "  => " + apply_record(r)
        print(line)

    if multi:
        print(f"\n=== A VERIFIER ({len(multi)}) : plusieurs BL ouverts, choix par date ===")
        for r in multi:
            line = f"  ({r['ncands']} cand.) {r['bl']:<15} <- {r['origin'] or '?':<8} | {r['email']}"
            if args.send:
                line += "  => " + apply_record(r)
            print(line)

    print(f"\n=== NON TRAITES (log) ===")
    print(f"  Hors perimetre (Choose / pas dans Odoo) : {len(no_partner)}")
    for r in no_partner:
        print(f"     {r['email']:<32} {r['name']} ({len(r['parcels'])} colis)")
    print(f"  Client Odoo mais aucun BL a tracker     : {len(no_bl)}")
    for r in no_bl:
        print(f"     {r['email']:<32} {r['name']} ({len(r['parcels'])} colis)")
    print(f"  Colis sans email (manuel)               : {len(no_email)}")

    print(f"\nRESUME: {len(matched)} notifies | {len(multi)} a verifier | "
          f"{len(no_partner)} hors perimetre | {len(no_bl)} sans BL | {len(no_email)} sans email")
    if not args.send:
        print("\n(DRY-RUN — relancer avec --send pour ecrire le tracking et envoyer les mails)")


if __name__ == "__main__":
    main()
