"""Garde-fou : le cron de relance ne doit jamais reclamer un reglement pour une
facture issue d'une commande passee et payee sur la boutique Shopify.

Contexte (2026-07-21, demande Yoann) : une commande Shopify est reglee en ligne;
si le rapprochement du paiement decroche cote Odoo (Stripe/Alma non reconcilie),
la facture apparait 'not_paid' et le cron enverrait une relance a un client qui a
DEJA paye. Embarrassant et evitable.

Marqueur d'une commande Shopify (pose par le workflow n8n Shopify->Odoo) :
    sale.order.origin = 'Shopify #3545'  (+ client_order_ref = id Shopify)

Le lien facture->commande est resolu via invoice_line_ids.sale_line_ids.order_id
et NON via le texte invoice_origin (qui peut concatener plusieurs SO).

Le script repart du code LIVE de l'action serveur (le repo derive), injecte le
garde-fou, et ne fait rien si celui-ci est deja present. Idempotent.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from _client import execute

CRON_ID = 46
MARKER = "SHOPIFY_PAID_GUARD"

cron = execute("ir.cron", "read", [[CRON_ID],
               ["name", "ir_actions_server_id", "active", "nextcall"]])[0]
action_id = cron["ir_actions_server_id"][0]
srv = execute("ir.actions.server", "read", [[action_id], ["name", "code"]])[0]
code = srv["code"]

print(f"Cron [{CRON_ID}] {cron['name']} -> action serveur [{action_id}]")
print(f"  actif={cron['active']} prochain={cron['nextcall']}")

if MARKER in code:
    print("\n>>> Garde-fou deja present, rien a faire (idempotent).")
    sys.exit(0)

# Ancre : juste apres le calcul de days_overdue dans la boucle FACTURES.
ANCHOR = "    for inv in unpaid:\n        days_overdue = (today - inv.invoice_date_due).days\n"
if code.count(ANCHOR) != 1:
    print(f"\n!! Ancre introuvable ou ambigue ({code.count(ANCHOR)} occurrence(s)). "
          "Le code live a change : re-verifier avant de patcher.")
    sys.exit(1)

GUARD = """    for inv in unpaid:
        days_overdue = (today - inv.invoice_date_due).days

        # SHOPIFY_PAID_GUARD : jamais de demande de reglement sur une commande
        # passee sur la boutique (deja reglee en ligne ; un residuel ici signale
        # un rapprochement de paiement en retard, pas un impaye client).
        orders = inv.invoice_line_ids.sale_line_ids.order_id
        if any(o.origin and o.origin.startswith('Shopify') for o in orders):
            skipped_shopify += 1
            continue
"""

new_code = code.replace(ANCHOR, GUARD)

# Compteur + log
new_code = new_code.replace(
    "    sent_count = 0\n",
    "    sent_count = 0\n    skipped_shopify = 0\n", 1)
new_code = new_code.replace(
    'log("MyLab follow-up cron : {} envoye(s), {} echec(s), {} devis annule(s)".format(\n'
    "        sent_count, failed_count, cancelled_count))",
    'log("MyLab follow-up cron : {} envoye(s), {} echec(s), {} devis annule(s), '
    '{} facture(s) Shopify ignoree(s)".format(\n'
    "        sent_count, failed_count, cancelled_count, skipped_shopify))")

for token in ("skipped_shopify = 0", "skipped_shopify += 1", "Shopify ignoree(s)"):
    assert token in new_code, f"injection ratee : {token!r} absent"

execute("ir.actions.server", "write", [[action_id], {"code": new_code}])
check = execute("ir.actions.server", "read", [[action_id], ["code"]])[0]["code"]
print("\n=== VERIFICATION ===")
print("  garde-fou present :", MARKER in check)
print("  compteur initialise:", "skipped_shopify = 0" in check)
print("  log mis a jour     :", "Shopify ignoree(s)" in check)
print("\n>>> Patch applique.")
