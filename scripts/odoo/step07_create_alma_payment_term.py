"""Create the 'Paiement Alma' payment term on company 3 (SARL STARTEC).

Alma pays MY.LAB at 10 days (not immediate), so the invoice is due 10 days after
issuance. The customer pays Alma in X1/X2/X3/X4 installments — that's Alma's
problem, not ours. The name + note makes the payment method explicit on the
invoice for accounting reconciliation.

Idempotent: if a term with this name already exists on company 3, prints its id
and exits without changes.
"""
from scripts.odoo._client import search_read, create

COMPANY_ID = 3  # SARL STARTEC

TERM = {
    "name": "Paiement Alma (3x/4x sans frais)",
    "note": (
        "<p>Paiement traité par Alma (formules X1, X2, X3, X4 sans frais pour le client). "
        "Alma règle MY.LAB à 10 jours. Frais Alma à comptabiliser séparément.</p>"
    ),
    "company_id": COMPANY_ID,
    "display_on_invoice": True,
    "line_ids": [
        (0, 0, {
            "value": "percent",
            "value_amount": 100.0,
            "delay_type": "days_after",
            "nb_days": 10,
        }),
    ],
}


def main():
    existing = search_read(
        "account.payment.term",
        [("name", "=", TERM["name"]), ("company_id", "=", COMPANY_ID)],
        ["id", "name"],
        limit=1,
    )
    if existing:
        print(f"Payment term '{TERM['name']}' exists (id={existing[0]['id']}), skipping")
        return
    new_id = create("account.payment.term", TERM)
    print(f"Created payment term '{TERM['name']}' (id={new_id})")


if __name__ == "__main__":
    main()
