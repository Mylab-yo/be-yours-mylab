"""Create journal entry to neutralize orphan 77.98€ credit on partner 1074.

Accounts (from probe):
- 411100 Customers - id=887 (orphan credit account)
- 707000 Sales of goods - id=1223 (where CA was improperly reduced by avoir line on inv 659)
- 445710 VAT collected - id=933 (where TVA was improperly reduced)
- Journal OD - id=11 (Miscellaneous Operations)

JE lines:
  Débit  411100 partner 1074 :  77.98€  (clears orphan credit)
  Crédit 707000              :  64.98€  (restores improperly-reduced CA)
  Crédit 445710 (TVA G 20%)  :  13.00€  (restores improperly-reduced TVA)

Then reconcile new debit line with orphan credit line (id 2046).
"""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))
from _client import search_read, execute, create

PARTNER_ID = 1074
COMPANY_ID = 3
JE_DATE = "2026-06-10"
JOURNAL_OD_ID = 11

ACCT_RECEIVABLE = 887   # 411100
ACCT_CA = 1223          # 707000
ACCT_TVA = 933          # 445710
TAX_ID = 103            # 20% G (referenced via tax_ids on the CA line)

ORPHAN_LINE_ID = 2046

# Build the JE
line_vals = [
    # Debit 411 receivable partner 1074 : 77.98€
    (0, 0, {
        "account_id": ACCT_RECEIVABLE,
        "partner_id": PARTNER_ID,
        "name": "Neutralisation crédit orphelin (paiement 11/04/2026 - devis 300582)",
        "debit": 77.98,
        "credit": 0.0,
    }),
    # Credit CA 707000 : 64.98€ (with tax_ids=[103] so the JE is consistent with tax reporting)
    (0, 0, {
        "account_id": ACCT_CA,
        "partner_id": PARTNER_ID,
        "name": "Régularisation CA - avoir intégré dans FAC S00418 déjà compensé par crédit existant",
        "debit": 0.0,
        "credit": 64.98,
        "tax_ids": [(6, 0, [TAX_ID])],
    }),
    # Credit TVA collectée 445710 : 13.00€
    (0, 0, {
        "account_id": ACCT_TVA,
        "partner_id": PARTNER_ID,
        "name": "Régularisation TVA 20% G sur 64.98€",
        "debit": 0.0,
        "credit": 13.00,
        "tax_repartition_line_id": False,  # may need to set
    }),
]

je_vals = {
    "move_type": "entry",
    "company_id": COMPANY_ID,
    "journal_id": JOURNAL_OD_ID,
    "date": JE_DATE,
    "ref": "Neutralisation crédit 77.98€ - LA TRESSE PARISIENNE",
    "narration": (
        "<p>Écriture de neutralisation du crédit orphelin de 77,98 € TTC sur partner 1074 LA TRESSE PARISIENNE.</p>"
        "<p>Contexte : la cliente a versé 2 347,33 € le 11/04/2026 (paiement PBNK1/2026/00041) pour devis 300582, "
        "réconcilié partiellement avec FAC/2025/00001 (2 269,35 €). Reste un crédit de 77,98 € TTC en outstanding.</p>"
        "<p>Ce trop-perçu est intégré comme ligne 'Avoir sur règlement précédent' (-64,98 € HT) sur la facture "
        "S00418 (id 659) → la cliente paye le net (2 666,68 € TTC au lieu de 2 744,66 € brut).</p>"
        "<p>Cette JE rétablit le CA et la TVA improprement réduits par cette ligne avoir, et clôture le crédit "
        "orphelin par rapprochement avec la ligne créancière résiduelle du paiement (id 2046).</p>"
    ),
    "line_ids": line_vals,
}

print("=== Create JE in draft ===")
je_id = create("account.move", je_vals)
print(f"  Created JE id={je_id}")

je = search_read("account.move", [("id", "=", je_id)],
                 ["name", "state", "date", "ref", "amount_total", "line_ids"], limit=1)
print(f"  {je[0]}")

# Read lines
lines = search_read("account.move.line", [("move_id", "=", je_id)],
                    ["id", "account_id", "partner_id", "debit", "credit", "name", "tax_ids", "tax_line_id"],
                    limit=10)
print("\n=== JE lines ===")
for l in lines:
    print(f"  {l}")

# Try to post
print("\n=== Post JE ===")
try:
    execute("account.move", "action_post", [je_id])
    je = search_read("account.move", [("id", "=", je_id)], ["name", "state"], limit=1)
    print(f"  Posted: {je[0]}")
except Exception as e:
    print(f"  ERROR posting: {e}")
    sys.exit(1)

# Reconcile the new 411 line with the orphan line
print("\n=== Reconcile with orphan credit line ===")
new_debit = next((l for l in lines if l["account_id"][0] == ACCT_RECEIVABLE), None)
if not new_debit:
    print("  ERROR: cannot find debit line")
    sys.exit(1)
print(f"  Reconciling line {new_debit['id']} (JE debit 411 77.98€) with line {ORPHAN_LINE_ID} (orphan credit)")
execute("account.move.line", "reconcile", [[new_debit["id"], ORPHAN_LINE_ID]])

# Verify
orphan_after = search_read("account.move.line", [("id", "=", ORPHAN_LINE_ID)],
                           ["amount_residual", "reconciled"], limit=1)
print(f"  Orphan line after: {orphan_after[0]}")

new_debit_after = search_read("account.move.line", [("id", "=", new_debit["id"])],
                              ["amount_residual", "reconciled"], limit=1)
print(f"  New JE debit line after: {new_debit_after[0]}")

# Check final partner balance on 411
print("\n=== Final partner 1074 receivable balance (open lines) ===")
open_lines = search_read("account.move.line",
                         [("partner_id", "=", PARTNER_ID),
                          ("account_id", "=", ACCT_RECEIVABLE),
                          ("reconciled", "=", False),
                          ("parent_state", "=", "posted")],
                         ["id", "move_id", "name", "debit", "credit", "amount_residual"],
                         limit=20)
total = 0
for l in open_lines:
    total += l["amount_residual"]
    print(f"  {l}")
print(f"\n  NET open balance: {total:.2f} €  (should be 2666.68€ = invoice 659 still draft → only posted ones counted)")

print(f"\n👉 https://odoo.startec-paris.com/odoo/action-account.action_move_journal_line/{je_id}")
