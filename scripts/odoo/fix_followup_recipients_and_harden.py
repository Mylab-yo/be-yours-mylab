"""Fix the broken follow-up system (investigated 2026-06-12).

1. Templates 35-39 had no recipient mapping -> add partner_to.
2. Purge the dead 'exception' mails (empty recipients, undeliverable).
3. Harden the cron server action: only mark x_followup_level if the mail
   actually sent (state == 'sent'), so a future send failure no longer
   silently flags a record as relaunched.

Does NOT reset existing x_followup_level (no retro-blast — per decision).
Idempotent.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from _client import search_read, write, execute

# ── 1. Templates: add partner_to ───────────────────────────────────────────
NAMES = ["mylab_devis_relance_l1", "mylab_devis_relance_l2",
         "mylab_facture_relance_l1", "mylab_facture_relance_l2",
         "mylab_facture_relance_l3"]
tpls = search_read("mail.template", [("name", "in", NAMES)],
                   ["id", "name", "partner_to"])
print("=== 1. TEMPLATES partner_to ===")
for t in tpls:
    if t.get("partner_to"):
        print(f"  [{t['id']}] {t['name']} already set: {t['partner_to']}")
        continue
    write("mail.template", [t["id"]], {"partner_to": "{{ object.partner_id.id }}"})
    print(f"  [{t['id']}] {t['name']} -> partner_to set")

# ── 2. Purge dead exception mails (cancel — unlink cascades to mail.message,
#       which is blocked by Odoo's message security policy) ─────────────────
print("\n=== 2. CANCEL exception mails ===")
dead = execute("mail.mail", "search", [[("state", "=", "exception")]])
print(f"  Found {len(dead)} exception mails")
if dead:
    write("mail.mail", dead, {"state": "cancel"})
    print(f"  Cancelled {len(dead)}")

# ── 3. Harden cron server action ───────────────────────────────────────────
ACTION_NAME = "MyLab — Relances devis & factures"
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
    failed_count = 0
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
                mail_id = tpl.send_mail(order.id, force_send=True)
                mail = env['mail.mail'].browse(mail_id)
                if mail.exists() and mail.state == 'sent':
                    order.write({
                        'x_followup_level': target,
                        'x_followup_last_sent_date': today,
                    })
                    sent_count += 1
                else:
                    # send failed -> do NOT mark, so it retries next run
                    failed_count += 1

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
            mail_id = tpl.send_mail(inv.id, force_send=True)
            mail = env['mail.mail'].browse(mail_id)
            if mail.exists() and mail.state == 'sent':
                inv.write({
                    'x_followup_level': target,
                    'x_followup_last_sent_date': today,
                })
                sent_count += 1
            else:
                # send failed -> do NOT mark, so it retries next run
                failed_count += 1

    log("MyLab follow-up cron : {} envoye(s), {} echec(s), {} devis annule(s)".format(
        sent_count, failed_count, cancelled_count))
"""

print("\n=== 3. HARDEN server action ===")
action = search_read("ir.actions.server", [("name", "=", ACTION_NAME)], ["id"])
if not action:
    print("  ERROR: server action not found!")
    sys.exit(1)
write("ir.actions.server", [action[0]["id"]], {"code": SERVER_CODE})
print(f"  [{action[0]['id']}] code updated (marks level only on successful send)")

# ── Verify ─────────────────────────────────────────────────────────────────
print("\n=== VERIFY ===")
tpls = search_read("mail.template", [("name", "in", NAMES)], ["name", "partner_to"])
for t in tpls:
    print(f"  {t['name']}: partner_to={t['partner_to']!r}")
remaining = execute("mail.mail", "search_count", [[("state", "=", "exception")]])
print(f"  remaining exception mails: {remaining}")
