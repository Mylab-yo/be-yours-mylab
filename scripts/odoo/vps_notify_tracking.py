#!/usr/bin/env python3
"""Notif tracking DPD — version AUTONOME pour le VPS (stdlib only, pas de dotenv).

Port fidele de station_notify_tracking.py : lit le dernier export Station
*_Expeditions.txt uploade par le PC, matche chaque envoi a son BL Odoo par email,
ecrit le n° de colis (carrier_tracking_ref) puis envoie le mail d'expedition (template 27).

DRY-RUN PAR DEFAUT. --send pour ecrire + envoyer. Idempotent (ignore les BL deja
notifies = carrier_tracking_ref non vide).

Config via /root/mylab-tracking/.env :
  ODOO_URL=...  ODOO_DB=...  ODOO_LOGIN=...  ODOO_API_KEY=...

Usage :
  python3 vps_notify_tracking.py                 # dry-run, dernier fichier
  python3 vps_notify_tracking.py --send          # ECRIT + ENVOIE
  python3 vps_notify_tracking.py --file 20260617_Expeditions.txt --send
"""
import os
import re
import sys
import argparse
import xmlrpc.client
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

BASE_DIR = Path(os.environ.get("MYLAB_TRACKING_DIR", "/root/mylab-tracking"))
STATION_DIR = BASE_DIR / "station"
ENV_PATH = BASE_DIR / ".env"

TEMPLATE_ID = 27                 # mail.template "Shipping: Send by Email"
CARRIER_RELAIS = 11              # DPD Point Relais - France
CARRIER_DOMICILE = 13            # DPD Classic - France
DPD_CARRIER_IDS = [11, 12, 13, 14, 15, 16, 17, 18]
CANDIDATE_STATES = ["confirmed", "assigned", "waiting", "done"]

EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
PARCEL_RE = re.compile(r"^\d{12,16}$")


# ----- env + odoo client (stdlib only) -----
def load_env(path):
    if not path.exists():
        sys.exit(f"Fichier env introuvable : {path}")
    env = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


_ENV = load_env(ENV_PATH)
URL = _ENV["ODOO_URL"]
DB = _ENV["ODOO_DB"]
LOGIN = _ENV.get("ODOO_LOGIN") or _ENV["ODOO_USER"]
API_KEY = _ENV["ODOO_API_KEY"]

_common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common", allow_none=True)
UID = _common.authenticate(DB, LOGIN, API_KEY, {})
if not UID:
    sys.exit(f"Auth Odoo echouee (login={LOGIN!r}, db={DB!r})")
_models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object", allow_none=True)


def execute(model, method, args, kwargs=None):
    try:
        return _models.execute_kw(DB, UID, API_KEY, model, method, args, kwargs or {})
    except xmlrpc.client.Fault as exc:
        if "cannot marshal None" in str(exc):
            return None
        raise


def search_read(model, domain, fields, limit=0):
    return execute(model, "search_read", [domain], {"fields": fields, "limit": limit})


# ----- logique de notif (identique a station_notify_tracking.py) -----
def find_file(arg):
    if arg:
        p = STATION_DIR / arg
        if not p.exists():
            sys.exit(f"Fichier introuvable : {p}")
        return p
    files = sorted(STATION_DIR.glob("*_Expeditions.txt"))
    if not files:
        sys.exit(f"Aucun fichier *_Expeditions.txt dans {STATION_DIR}")
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


def known_parcels(all_parcels):
    """Set des n° de colis DEJA ecrits sur un BL Odoo (dedup niveau colis).

    Empeche de re-notifier un meme colis sur un 2e BL du meme client (cas reliquat /
    commande splittee : tous les colis du client se retrouveraient sinon deverses sur
    le BL restant -> mail en double)."""
    if not all_parcels:
        return set()
    pks = search_read("stock.picking",
        [("picking_type_code", "=", "outgoing"),
         ("carrier_tracking_ref", "not in", [False, ""])],
        ["carrier_tracking_ref"], limit=2000)
    known = set()
    for p in pks:
        for x in (p.get("carrier_tracking_ref") or "").split(","):
            x = x.strip()
            if x:
                known.add(x)
    return known & set(all_parcels)


def build_plan(rows):
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

    seen = known_parcels([r["parcel"] for r in rows if r["parcel"]])

    matched, multi, no_partner, no_bl, already = [], [], [], [], []
    for em, grp in by_email.items():
        parcels = [r["parcel"] for r in grp if r["parcel"]]
        # retire les colis deja notifies ailleurs (idempotence niveau colis)
        fresh = [p for p in parcels if p not in seen]
        if parcels and not fresh:
            already.append({"email": em, "name": grp[0]["name"], "parcels": parcels})
            continue
        parcels = fresh
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
    return matched, multi, no_partner, no_bl, no_email, already


def apply_record(rec):
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

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    f = find_file(args.file)
    rows = parse_station(f)
    matched, multi, no_partner, no_bl, no_email, already = build_plan(rows)

    mode = "ENVOI REEL" if args.send else "DRY-RUN (aucune ecriture/envoi)"
    print(f"[{stamp}] Fichier: {f.name} ({len(rows)} colis) | MODE: {mode}")

    print(f"=== A NOTIFIER ({len(matched)}) ===")
    for r in matched:
        line = (f"  {r['bl']:<15} <- {r['origin'] or '?':<8} | {len(r['parcels'])} colis "
                f"{'RELAIS '+r['relay'] if r['relay'] else 'domicile':<14} | {r['email']:<32}")
        if args.send:
            line += "  => " + apply_record(r)
        print(line)

    if multi:
        print(f"=== A VERIFIER ({len(multi)}) : plusieurs BL ouverts, choix par date ===")
        for r in multi:
            line = f"  ({r['ncands']} cand.) {r['bl']:<15} <- {r['origin'] or '?':<8} | {r['email']}"
            if args.send:
                line += "  => " + apply_record(r)
            print(line)

    print(f"RESUME: {len(matched)} notifies | {len(multi)} a verifier | "
          f"{len(already)} deja notifies (dedup colis) | {len(no_partner)} hors perimetre | "
          f"{len(no_bl)} sans BL | {len(no_email)} sans email")
    if not args.send:
        print("(DRY-RUN — relancer avec --send pour ecrire le tracking et envoyer les mails)")


if __name__ == "__main__":
    main()
