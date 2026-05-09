"""Send the correction mail to AU LONG COURT for SO S00473.

Posts a chatter message on sale.order id=440 with subtype mail.mt_comment
so it gets emailed to the customer partner (id=2027) and stays traced in Odoo.
"""
import re
from pathlib import Path
from scripts.odoo._client import execute

SO_ID = 440
PARTNER_ID = 2027  # AU LONG COURT
SUBJECT = "MY.LAB — Précision sur votre commande S00473 (virement à effectuer)"
BODY_FILE = Path("docs/mail-correctif-au-long-court.html")


def main():
    raw = BODY_FILE.read_text(encoding="utf-8")
    # Strip the leading instructions HTML comment block, keep only the visible div
    body = re.sub(r'<!--.*?-->', '', raw, flags=re.DOTALL).strip()

    print(f"Sending message on sale.order id={SO_ID}")
    print(f"  to partner_id={PARTNER_ID}")
    print(f"  subject: {SUBJECT}")
    print(f"  body: {len(body)} chars")

    msg_id = execute("sale.order", "message_post", [[SO_ID]], {
        "body": body,
        "subject": SUBJECT,
        "subtype_xmlid": "mail.mt_comment",
        "message_type": "comment",
        "partner_ids": [PARTNER_ID],
    })
    print(f"\nmail.message id created: {msg_id}")


if __name__ == "__main__":
    main()
