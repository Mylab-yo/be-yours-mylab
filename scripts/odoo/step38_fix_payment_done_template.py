"""Fix mail.template id=23 (Sales: Payment Done) to handle wire transfers correctly.

Problem: native Odoo template sends 'Paiement recu' even when the customer just
selected wire transfer in the portal (transaction state=pending). This misleads
the customer into thinking nothing more is needed.

Fix: rewrite subject + body_html with a conditional QWeb branch that detects
pending transactions (= wire transfer) vs done/authorized (= real payment), and
sends appropriate wording. Wire transfer branch includes IBAN/BIC and reference.
"""
from pathlib import Path
from scripts.odoo._client import write

TEMPLATE_ID = 23
NEW_SUBJECT = "MYLAB - Confirmation de votre commande {{ object.name }}"
BODY_FILE = Path("scripts/odoo/templates/mail_payment_done.html")


def main():
    body = BODY_FILE.read_text(encoding="utf-8")
    write("mail.template", [TEMPLATE_ID], {
        "subject": NEW_SUBJECT,
        "body_html": body,
    })
    print(f"Updated mail.template id={TEMPLATE_ID}")
    print(f"  subject: {NEW_SUBJECT}")
    print(f"  body: {len(body)} chars from {BODY_FILE}")


if __name__ == "__main__":
    main()
