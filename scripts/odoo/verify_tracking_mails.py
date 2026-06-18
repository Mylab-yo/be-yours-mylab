"""Verifie de bout en bout que les mails de tracking colis (n° de suivi DPD)
partent bien dans Odoo. LECTURE SEULE — ne modifie rien.

Controle :
  1) Carriers DPD (11-18) : tracking_url cliquable present
  2) Template mail #27 (Shipping) : sujet + corps contiennent bien le lien de suivi
     (logique split par colis) dans les 2 langues
  3) BL recents (outgoing, done) avec carrier_tracking_ref : un mail d'expedition
     a-t-il ete loggue + envoye ? statut de notification ? n° de suivi present ?
  4) Echecs d'envoi (mail.mail state=exception) lies a stock.picking

Usage : python -m scripts.odoo.verify_tracking_mails [--days 30]
"""
import sys, io, re, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from datetime import datetime, timedelta
from scripts.odoo._client import search_read, execute

TEMPLATE_ID = 27
DPD_IDS = [11, 12, 13, 14, 15, 16, 17, 18]


def section(t):
    print(f"\n{'='*70}\n{t}\n{'='*70}")


def check_carriers():
    section("1) CARRIERS DPD — tracking_url")
    cs = search_read("delivery.carrier", [("id", "in", DPD_IDS)],
                     ["id", "name", "tracking_url"])
    ok = 0
    for c in sorted(cs, key=lambda x: x["id"]):
        url = c.get("tracking_url") or ""
        good = "<shipmenttrackingnumber>" in url or "dpd" in url.lower()
        ok += good
        print(f"  id={c['id']:>2}  {c['name']:<42} {'OK ' if good else 'KO '} {url!r}")
    print(f"  -> {ok}/{len(cs)} carriers avec tracking_url exploitable")


def check_template():
    section("2) TEMPLATE MAIL #27 — sujet + corps (2 langues)")
    for lang in ("fr_FR", "en_US"):
        t = execute("mail.template", "read", [[TEMPLATE_ID],
                    ["name", "subject", "body_html", "model_id", "email_from"]],
                    {"context": {"lang": lang}})[0]
        body = t.get("body_html") or ""
        has_split = "carrier_tracking_ref.split" in body
        has_old = "get_multiple_carrier_tracking" in body
        has_ref = "carrier_tracking_ref" in body
        has_dpd = "dpd.fr/trace" in body
        print(f"  [{lang}] name={t.get('name')!r}")
        print(f"         subject = {t.get('subject')!r}")
        print(f"         email_from = {t.get('email_from')!r}")
        print(f"         tracking_ref dans corps : {has_ref} | lien DPD/trace : {has_dpd}")
        print(f"         split par colis : {has_split} | ancienne logique cassee : {has_old}")


def check_recent_pickings(days):
    section(f"3) BL EXPEDIES (outgoing/done) DES {days} DERNIERS JOURS avec n° suivi")
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d 00:00:00")
    pks = search_read("stock.picking",
        [("picking_type_code", "=", "outgoing"),
         ("carrier_tracking_ref", "not in", [False, ""]),
         ("date_done", ">=", since)],
        ["id", "name", "origin", "partner_id", "carrier_id",
         "carrier_tracking_ref", "state", "date_done"], limit=200)
    # fallback : certains BL n'ont pas date_done renseigne -> tenter sur scheduled_date
    if not pks:
        pks = search_read("stock.picking",
            [("picking_type_code", "=", "outgoing"),
             ("carrier_tracking_ref", "not in", [False, ""]),
             ("scheduled_date", ">=", since)],
            ["id", "name", "origin", "partner_id", "carrier_id",
             "carrier_tracking_ref", "state", "scheduled_date"], limit=200)

    print(f"  {len(pks)} BL avec carrier_tracking_ref sur la periode\n")
    if not pks:
        print("  (aucun — soit pas d'expedition recente, soit tracking non ecrit)")
        return

    sent = no_mail = 0
    for p in sorted(pks, key=lambda x: x.get("date_done") or x.get("scheduled_date") or ""):
        # messages mail sur ce BL
        msgs = search_read("mail.message",
            [("model", "=", "stock.picking"), ("res_id", "=", p["id"]),
             ("message_type", "in", ["email", "email_outgoing"])],
            ["id", "date", "subject", "body"], limit=10)
        ref = p["carrier_tracking_ref"]
        carrier = (p.get("carrier_id") or [None, "—"])[1]
        if not msgs:
            no_mail += 1
            flag = "PAS DE MAIL"
            notif_txt = ""
        else:
            sent += 1
            latest = max(msgs, key=lambda m: m["date"])
            # le n° de suivi apparait-il dans le corps du mail envoye ?
            body = latest.get("body") or ""
            refs = [r.strip() for r in ref.split(",") if r.strip()]
            in_body = all(r in body for r in refs) if refs else False
            notifs = search_read("mail.notification",
                [("mail_message_id", "=", latest["id"])],
                ["notification_type", "notification_status", "failure_reason"])
            statuses = [f"{n['notification_status']}"
                        + (f"({n['failure_reason']})" if n.get("failure_reason") else "")
                        for n in notifs]
            flag = f"MAIL {latest['date']}"
            notif_txt = (f" | suivi_dans_corps={in_body}"
                         f" | notif={statuses or 'aucune'}")
        print(f"  {p['name']:<14} {(p.get('origin') or '?'):<9} "
              f"{(p.get('partner_id') or [0,'?'])[1][:22]:<22} "
              f"ref={ref[:24]:<24} {carrier[:18]:<18} -> {flag}{notif_txt}")

    print(f"\n  -> {sent} BL avec mail loggue | {no_mail} BL SANS mail d'expedition")


def check_failures(days):
    section(f"4) ECHECS D'ENVOI (mail.mail exception) DES {days} DERNIERS JOURS")
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d 00:00:00")
    fails = search_read("mail.mail",
        [("state", "=", "exception"), ("create_date", ">=", since)],
        ["id", "subject", "email_to", "failure_reason", "model", "res_id"], limit=50)
    ship_fails = [f for f in fails if f.get("model") == "stock.picking"
                  or "exp" in (f.get("subject") or "").lower()
                  or "command" in (f.get("subject") or "").lower()]
    print(f"  {len(fails)} echecs mail total | {len(ship_fails)} potentiellement expedition")
    for f in fails[:20]:
        print(f"  #{f['id']} to={f.get('email_to')!r} model={f.get('model')} "
              f"subj={ (f.get('subject') or '')[:40]!r} reason={ (f.get('failure_reason') or '')[:60]!r}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    args = ap.parse_args()
    print(f"VERIF MAILS TRACKING DPD — Odoo (fenetre : {args.days} jours)")
    check_carriers()
    check_template()
    check_recent_pickings(args.days)
    check_failures(args.days)


if __name__ == "__main__":
    main()
