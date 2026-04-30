"""Create the daily cron that processes devis and factures for follow-up.

The cron runs the server action which:
  1. Skips weekends
  2. For each devis state='sent' & x_followup_level < target:
     - +7j  → send template L1, set level=1
     - +14j → send template L2, set level=2
     - +30j → cancel (no email), set level=3
  3. For each invoice (out_invoice posted, not fully paid, overdue):
     - +3j  → send template L1, set level=1
     - +10j → send template L2, set level=2
     - +30j → send template L3 mise en demeure (CC yoann), set level=3

The check `level < target` ensures only ONE email per follow-up level is sent
(important on first run for old invoices: only the highest applicable level
fires, not all 3 cumulatively).

The cron is created **active=False**. Run step35 (dry-run) first, then
activate manually via UI or via `python -c "from _client import write; write('ir.cron', [<cron_id>], {'active': True})"`.

Idempotent: identifies cron by server action name, updates if exists.

Run: python step34_create_followup_cron.py
"""
import sys, io
from datetime import datetime, timedelta, timezone
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from _client import search_read, create, write

ACTION_NAME = "MyLab — Relances devis & factures"

# Python code executed by the cron — uses Odoo's safe_eval sandbox.
# IMPORTANT: assignments to record fields MUST go through .write() (no STORE_ATTR).
SERVER_CODE = """# MyLab follow-up cron logic — daily 8:00 UTC
today = datetime.date.today()
if today.weekday() < 5:
    # Mon-Fri only (skip weekends)
    Template = env['mail.template']
    devis_l1 = Template.search([('name', '=', 'mylab_devis_relance_l1')], limit=1)
    devis_l2 = Template.search([('name', '=', 'mylab_devis_relance_l2')], limit=1)
    fact_l1  = Template.search([('name', '=', 'mylab_facture_relance_l1')], limit=1)
    fact_l2  = Template.search([('name', '=', 'mylab_facture_relance_l2')], limit=1)
    fact_l3  = Template.search([('name', '=', 'mylab_facture_relance_l3')], limit=1)

    sent_count = 0
    cancelled_count = 0

    # ── DEVIS ────────────────────────────────────────────────
    sent_orders = env['sale.order'].search([('state', '=', 'sent')])
    for order in sent_orders:
        if not order.date_order:
            continue
        ref_date = order.date_order.date()
        days_old = (today - ref_date).days

        if days_old >= 30:
            target = 3
        elif days_old >= 14:
            target = 2
        elif days_old >= 7:
            target = 1
        else:
            target = 0

        current = order.x_followup_level or 0
        if target == 0 or current >= target:
            continue

        if target == 3:
            # No email — cancel + internal note
            order.write({
                'state': 'cancel',
                'x_followup_level': 3,
                'x_followup_last_sent_date': today,
            })
            order.message_post(
                body="Devis annulé automatiquement après 30 jours sans suite (relance auto MY.LAB).",
                subtype_xmlid='mail.mt_note',
            )
            cancelled_count += 1
        else:
            tpl = devis_l1 if target == 1 else devis_l2
            if tpl and order.partner_id.email:
                tpl.send_mail(order.id, force_send=True)
                order.write({
                    'x_followup_level': target,
                    'x_followup_last_sent_date': today,
                })
                sent_count += 1

    # ── FACTURES ─────────────────────────────────────────────
    unpaid = env['account.move'].search([
        ('move_type', '=', 'out_invoice'),
        ('state', '=', 'posted'),
        ('payment_state', 'in', ['not_paid', 'partial']),
        ('invoice_date_due', '!=', False),
        ('invoice_date_due', '<', today),
    ])
    for inv in unpaid:
        days_overdue = (today - inv.invoice_date_due).days

        if days_overdue >= 30:
            target = 3
        elif days_overdue >= 10:
            target = 2
        elif days_overdue >= 3:
            target = 1
        else:
            target = 0

        current = inv.x_followup_level or 0
        if target == 0 or current >= target:
            continue

        tpl_map = {1: fact_l1, 2: fact_l2, 3: fact_l3}
        tpl = tpl_map[target]
        if tpl and inv.partner_id.email:
            tpl.send_mail(inv.id, force_send=True)
            inv.write({
                'x_followup_level': target,
                'x_followup_last_sent_date': today,
            })
            sent_count += 1

    log("MyLab follow-up cron : {} email(s) envoyé(s), {} devis annulé(s)".format(
        sent_count, cancelled_count))
"""

# Find the model id for sale.order (any will do; the action just needs A model_id)
sale_model_id = search_read("ir.model", [("model", "=", "sale.order")], ["id"])[0]["id"]

# 1. Upsert the server action
existing_action = search_read("ir.actions.server",
                              [("name", "=", ACTION_NAME)],
                              ["id"])
action_values = {
    "name": ACTION_NAME,
    "model_id": sale_model_id,
    "state": "code",
    "code": SERVER_CODE,
}
if existing_action:
    action_id = existing_action[0]["id"]
    write("ir.actions.server", [action_id], action_values)
    print(f"✓ Updated server action [{action_id}]")
else:
    action_id = create("ir.actions.server", action_values)
    print(f"✓ Created server action [{action_id}]")

# 2. Upsert the cron — INACTIVE by default (user activates after dry-run)
existing_cron = search_read("ir.cron",
                            [("ir_actions_server_id", "=", action_id)],
                            ["id", "active"])

# Schedule next call: tomorrow 8:00 UTC (≈9-10:00 Paris)
tomorrow = datetime.now(timezone.utc).date() + timedelta(days=1)
nextcall = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 8, 0, 0)

cron_values = {
    "ir_actions_server_id": action_id,
    "interval_number": 1,
    "interval_type": "days",
    "nextcall": nextcall.strftime("%Y-%m-%d %H:%M:%S"),
    "active": False,  # ← USER ACTIVATES AFTER DRY-RUN
}

if existing_cron:
    cron_id = existing_cron[0]["id"]
    write("ir.cron", [cron_id], cron_values)
    print(f"✓ Updated cron [{cron_id}] (active=False)")
else:
    cron_id = create("ir.cron", cron_values)
    print(f"✓ Created cron [{cron_id}] (active=False)")

print()
print(f"Cron next call: {nextcall.strftime('%Y-%m-%d %H:%M UTC')}")
print(f"To activate after verifying dry-run :")
print(f'  python -c "from _client import write; write(\'ir.cron\', [{cron_id}], {{\'active\': True}})"')
