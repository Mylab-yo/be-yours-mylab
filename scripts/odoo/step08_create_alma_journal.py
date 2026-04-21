"""Create the 'Alma' bank journal on company 3 for BNPL payments received via Alma.

Accounting flow this enables:
    1. Customer pays via Alma → on the invoice, click Payer → select Journal "Alma"
       → invoice is marked paid, amount booked on 511200 (suspense, 'Cheques for
       collection' in the default FR CoA).
    2. 10 days later Alma wires the net amount (after fees) to LCL. Bank statement
       import on BNK1 reconciles the wire against the 511200 suspense balance.
    3. Alma fees (~3-5%) are passed as a manual entry 627100 / 511200 at reconciliation
       time. No dedicated fees account — 627100 (Securities costs) already covers
       bank fees (LCL, PayPal).

Idempotent: skips journal creation if a journal with code='ALMA' exists on company 3,
and skips the payment method line if one already links the journal to 'Manual Payment'.
"""
from scripts.odoo._client import search_read, create, write

COMPANY_ID = 3                  # SARL STARTEC
SUSPENSE_ACCOUNT_ID = 1012      # 511200 Cheques for collection (used as Alma suspense)
JOURNAL_CODE = "ALMA"
JOURNAL_NAME = "Alma"


def main():
    existing_journal = search_read(
        "account.journal",
        [("code", "=", JOURNAL_CODE), ("company_id", "=", COMPANY_ID)],
        ["id", "name", "default_account_id"],
        limit=1,
    )
    if existing_journal:
        journal_id = existing_journal[0]["id"]
        print(f"Journal '{JOURNAL_CODE}' exists (id={journal_id}), skipping journal creation")
    else:
        journal_id = create("account.journal", {
            "name": JOURNAL_NAME,
            "code": JOURNAL_CODE,
            "type": "bank",
            "company_id": COMPANY_ID,
            "default_account_id": SUSPENSE_ACCOUNT_ID,
        })
        print(f"Created journal '{JOURNAL_NAME}' (id={journal_id})")

    manual_method = search_read(
        "account.payment.method",
        [("code", "=", "manual"), ("payment_type", "=", "inbound")],
        ["id"], limit=1,
    )
    if not manual_method:
        raise RuntimeError("Could not find 'manual' inbound account.payment.method")
    manual_method_id = manual_method[0]["id"]

    # Odoo auto-creates a 'Manual Payment' line when a bank journal is created,
    # so we may find an existing line here even though we never called create ourselves.
    # In that case we just rename it to 'Paiement Alma' for clarity in the UI dropdown.
    existing_line = search_read(
        "account.payment.method.line",
        [("journal_id", "=", journal_id), ("payment_method_id", "=", manual_method_id)],
        ["id", "name"], limit=1,
    )
    if existing_line:
        line_id = existing_line[0]["id"]
        if existing_line[0]["name"] != "Paiement Alma":
            write("account.payment.method.line", [line_id], {"name": "Paiement Alma"})
            print(f"Renamed payment method line id={line_id} to 'Paiement Alma'")
        else:
            print(f"Payment method line 'Paiement Alma' exists (id={line_id}), skipping")
    else:
        line_id = create("account.payment.method.line", {
            "name": "Paiement Alma",
            "journal_id": journal_id,
            "payment_method_id": manual_method_id,
        })
        print(f"Created payment method line 'Paiement Alma' (id={line_id})")


if __name__ == "__main__":
    main()
