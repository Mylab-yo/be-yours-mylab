"""Prepare draft journal entry to neutralize the orphan 77.98€ credit on partner 1074.

Context:
- Payment PBNK1/2026/00041 (id 85) of 2347.33€ from customer
- Reconciled partially with invoice FAC/2025/00001 (id 652, 2269.35€)
- Residual: -77.98€ on receivable line id 2046
- New invoice FAC/2026/XXXX (id 659) integrates a "remboursement précédent" line of -64.98€ HT (-77.98€ TTC)
- → Orphan credit on partner must be neutralized accounting-wise.

Approach: JE that
  - Debits the receivable 411 of partner 1074 by 77.98€ (clears the orphan credit)
  - Credits CA 70x by 64.98€ (restores the CA improperly reduced by the avoir line in inv 659)
  - Credits TVA collectée 4457xxx by 13.00€ (restores TVA improperly reduced)

End result: CA + TVA net = as if no avoir line in inv 659. Receivable balance = 0 once inv 659 paid.
"""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, os.path.dirname(__file__))
from _client import search_read, execute

PARTNER_ID = 1074
COMPANY_ID = 3

# 1. Find the receivable line of payment 85 to know which receivable account to use
print("=== Probe orphan credit line ===")
orphan = search_read("account.move.line", [("id", "=", 2046)],
                    ["id", "account_id", "partner_id", "debit", "credit",
                     "amount_residual", "reconciled", "move_id"], limit=1)
print(f"  {orphan[0]}")
RECEIVABLE_ACCOUNT_ID = orphan[0]["account_id"][0]
print(f"  Receivable account id: {RECEIVABLE_ACCOUNT_ID} = {orphan[0]['account_id'][1]!r}")
print(f"  Amount to neutralize: {abs(orphan[0]['amount_residual']):.2f} €")

# 2. Find the CA and TVA accounts used on the avoir line of invoice 659
print("\n=== Probe inv 659 avoir line accounts ===")
avoir_lines = search_read("account.move.line",
                          [("move_id", "=", 659),
                           ("name", "ilike", "Avoir sur règlement")],
                          ["id", "account_id", "name", "debit", "credit", "tax_ids", "tax_line_id"],
                          limit=5)
for l in avoir_lines:
    print(f"  {l}")

# Find the related tax lines (TVA on avoir)
tva_lines = search_read("account.move.line",
                        [("move_id", "=", 659),
                         ("tax_line_id", "!=", False)],
                        ["id", "account_id", "name", "debit", "credit", "tax_line_id"], limit=10)
print("\n  TVA lines on inv 659:")
for l in tva_lines:
    print(f"    {l}")

# 3. Get the standard CA account and TVA account
# Typically on French Plan Comptable: CA = 706/707, TVA collectée = 44571
ca_accounts = search_read("account.account",
                         [("company_ids", "in", [COMPANY_ID]),
                          ("code", "in", ["706000", "707000", "707100", "707800"])],
                         ["id", "code", "name"], limit=10)
print(f"\n  Sales accounts: {ca_accounts}")

tva_accounts = search_read("account.account",
                          [("company_ids", "in", [COMPANY_ID]),
                           ("code", "=like", "44571%")],
                          ["id", "code", "name"], limit=10)
print(f"  TVA collected accounts: {tva_accounts}")

# 4. Find the OD (Opérations Diverses) journal
print("\n=== Probe OD journal ===")
od_journals = search_read("account.journal",
                          [("company_id", "=", COMPANY_ID),
                           ("type", "=", "general")],
                          ["id", "name", "code"], limit=10)
print(f"  General journals: {od_journals}")

# Stop here for review, no creation yet
