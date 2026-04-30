"""DRY-RUN of the follow-up cron — read-only.

Reports what the cron WOULD do today, without sending any email or
modifying any record. Use this to verify the impact before activating
the cron (step34 created it inactive).

For each affected devis or facture, prints:
  - the level that would be sent (1/2/3)
  - the partner email
  - the days_old / days_overdue
  - whether it'd be a cancel (devis L3)

Run: python step35_dry_run_followup.py
"""
import sys, io
from datetime import date
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from _client import search_read

today = date.today()
weekday = today.weekday()
if weekday >= 5:
    print(f"⚠ {today} is {'Saturday' if weekday == 5 else 'Sunday'} — cron would SKIP today.")
    print("  Showing what it would do on the next weekday.")
    print()

# ── DEVIS dry-run ────────────────────────────────────────
print("═══ DEVIS — état='sent' ═══")
sent_orders = search_read(
    "sale.order",
    [("state", "=", "sent")],
    ["id", "name", "partner_id", "date_order",
     "x_followup_level", "amount_total"],
)
print(f"Total devis 'sent' : {len(sent_orders)}\n")

devis_emails = 0
devis_cancels = 0
devis_skipped = 0

for o in sorted(sent_orders, key=lambda x: x["date_order"] or ""):
    if not o["date_order"]:
        devis_skipped += 1
        continue
    # date_order returned by XML-RPC is "YYYY-MM-DD HH:MM:SS" string
    ref_date = date.fromisoformat(o["date_order"][:10])
    days_old = (today - ref_date).days

    if days_old >= 30:
        target = 3
    elif days_old >= 14:
        target = 2
    elif days_old >= 7:
        target = 1
    else:
        target = 0

    current = o["x_followup_level"] or 0
    if target == 0:
        continue
    if current >= target:
        continue

    partner_email = "?"
    p = search_read("res.partner", [("id", "=", o["partner_id"][0])], ["email"])
    if p:
        partner_email = p[0]["email"] or "(NO EMAIL)"

    if target == 3:
        action = f"CANCEL (no email)"
        devis_cancels += 1
    else:
        action = f"send L{target} email → {partner_email}"
        if not partner_email or partner_email == "(NO EMAIL)":
            action += " ⚠ NO EMAIL — would be skipped"
        else:
            devis_emails += 1

    print(f"  {o['name']:8s} | {days_old:3d}d old | TTC {o['amount_total']:>10.2f}€ "
          f"| current_level={current} → target={target} | {action}")

print(f"\n→ Devis: {devis_emails} email(s) à envoyer, {devis_cancels} à annuler\n")

# ── FACTURES dry-run ──────────────────────────────────────
print("═══ FACTURES — out_invoice posted, impayées, échéance dépassée ═══")
unpaid = search_read(
    "account.move",
    [
        ("move_type", "=", "out_invoice"),
        ("state", "=", "posted"),
        ("payment_state", "in", ["not_paid", "partial"]),
        ("invoice_date_due", "!=", False),
        ("invoice_date_due", "<", today.isoformat()),
    ],
    ["id", "name", "partner_id", "invoice_date_due",
     "x_followup_level", "amount_total", "amount_residual"],
)
print(f"Total factures impayées en retard : {len(unpaid)}\n")

fact_emails = {1: 0, 2: 0, 3: 0}

for inv in sorted(unpaid, key=lambda x: x["invoice_date_due"] or ""):
    due = date.fromisoformat(inv["invoice_date_due"])
    days_overdue = (today - due).days

    if days_overdue >= 30:
        target = 3
    elif days_overdue >= 10:
        target = 2
    elif days_overdue >= 3:
        target = 1
    else:
        target = 0

    current = inv["x_followup_level"] or 0
    if target == 0:
        continue
    if current >= target:
        continue

    partner_email = "?"
    p = search_read("res.partner", [("id", "=", inv["partner_id"][0])], ["email"])
    if p:
        partner_email = p[0]["email"] or "(NO EMAIL)"

    level_label = {1: "L1 courtois", 2: "L2 ferme", 3: "L3 MISE EN DEMEURE"}[target]
    action = f"send {level_label} → {partner_email}"
    if not partner_email or partner_email == "(NO EMAIL)":
        action += " ⚠ NO EMAIL — would be skipped"
    else:
        fact_emails[target] += 1

    print(f"  {inv['name']:18s} | {days_overdue:3d}d overdue | "
          f"TTC {inv['amount_total']:>10.2f}€ (résiduel {inv['amount_residual']:>10.2f}€) "
          f"| current_level={current} → target={target} | {action}")

print(f"\n→ Factures :")
print(f"  L1 (courtois)        : {fact_emails[1]} email(s)")
print(f"  L2 (ferme)           : {fact_emails[2]} email(s)")
print(f"  L3 (mise en demeure) : {fact_emails[3]} email(s)")
print(f"  TOTAL                : {sum(fact_emails.values())} email(s)")

print()
print("═══ Résumé global ═══")
print(f"  {devis_emails + sum(fact_emails.values())} email(s) seraient envoyé(s)")
print(f"  {devis_cancels} devis seraient annulé(s)")
print()
print("Si OK, active le cron :")
print('  python -c "from _client import write; write(\'ir.cron\', [46], {\'active\': True})"')
print("Le cron tournera tous les jours ouvrés à 9-10h Paris (8h UTC).")
