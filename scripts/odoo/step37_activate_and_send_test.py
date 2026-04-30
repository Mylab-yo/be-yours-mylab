"""Activate the follow-up cron + send 5 preview emails to yoann@mylab-shop.com.

Each template is rendered against a real record (so the Jinja variables
populate with realistic data — partner name, amount, dates), but the
recipient is redirected to yoann@mylab-shop.com. The original partner
will NOT receive these test emails.

Note: send_mail() adds a chatter trace on the source record. Minor
pollution accepted for the test.

Run: python step37_activate_and_send_test.py
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from _client import search_read, write, execute

TEST_RECIPIENT = "yoann@mylab-shop.com"

# 1. Activate the cron
print("Step 1: Activate cron id=46")
write("ir.cron", [46], {"active": True})
cron = search_read("ir.cron", [("id", "=", 46)], ["active", "nextcall"])[0]
print(f"  ✓ Cron active={cron['active']}, next call={cron['nextcall']}")
print()

# 2. Pick representative records for each template
print("Step 2: Resolve preview records")
# Pick devis: use the ones flagged in the dry-run
devis_l1_records = search_read("sale.order",
    [("state", "=", "sent")],
    ["id", "name", "amount_total", "partner_id"],
    limit=10)
# Pick a devis (any will do; data is just for Jinja rendering)
devis = devis_l1_records[0] if devis_l1_records else None

# Pick a facture
fact_records = search_read("account.move",
    [("move_type", "=", "out_invoice"),
     ("state", "=", "posted"),
     ("payment_state", "in", ["not_paid", "partial"])],
    ["id", "name", "amount_total", "partner_id"],
    limit=10)
fact = fact_records[0] if fact_records else None

if not devis or not fact:
    print("ERROR: could not find a devis or facture to preview against")
    sys.exit(1)

print(f"  Devis source : {devis['name']} (id={devis['id']}, partner={devis['partner_id'][1]})")
print(f"  Facture source : {fact['name']} (id={fact['id']}, partner={fact['partner_id'][1]})")
print()

# 3. Resolve template IDs by name
print("Step 3: Resolve templates")
templates = {}
for tname in ["mylab_devis_relance_l1", "mylab_devis_relance_l2",
              "mylab_facture_relance_l1", "mylab_facture_relance_l2",
              "mylab_facture_relance_l3"]:
    t = search_read("mail.template", [("name", "=", tname)], ["id"])
    if t:
        templates[tname] = t[0]["id"]
        print(f"  {tname}: id={t[0]['id']}")
print()

# 4. Send each template, redirected to yoann
print(f"Step 4: Send 5 preview emails to {TEST_RECIPIENT}")
mapping = [
    ("mylab_devis_relance_l1", devis["id"], "Devis L1 doux (+7j)"),
    ("mylab_devis_relance_l2", devis["id"], "Devis L2 direct (+14j)"),
    ("mylab_facture_relance_l1", fact["id"], "Facture L1 courtois (+3j)"),
    ("mylab_facture_relance_l2", fact["id"], "Facture L2 ferme (+10j)"),
    ("mylab_facture_relance_l3", fact["id"], "Facture L3 MISE EN DEMEURE (+30j)"),
]

email_values = {
    "email_to": TEST_RECIPIENT,
    "recipient_ids": [(5, 0, 0)],  # Clear M2M to partners (no original recipient)
    "email_cc": "",
}

for tname, res_id, label in mapping:
    template_id = templates.get(tname)
    if not template_id:
        print(f"  ✗ {label}: template missing")
        continue
    try:
        mail_id = execute("mail.template", "send_mail",
                          [template_id, res_id],
                          {"force_send": True, "email_values": email_values})
        print(f"  ✓ {label} → mail.mail id={mail_id}")
    except Exception as e:
        print(f"  ✗ {label}: {str(e)[:200]}")

print()
print("Tu devrais avoir reçu 5 emails dans yoann@mylab-shop.com.")
print()
print("Le cron est ACTIF — il tournera demain matin à 8h UTC (~9-10h Paris).")
print("Pour le désactiver à tout moment :")
print("  python -c \"from _client import write; write('ir.cron', [46], {'active': False})\"")
