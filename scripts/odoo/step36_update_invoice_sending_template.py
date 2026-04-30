"""Update the standard 'Invoice: Sending' (id=18) template to use the
Service Comptabilité signature instead of Yoann's personal user.signature.

Also switches email_from from the dynamic invoice_user_id pattern to a
fixed "Service Comptabilité MY.LAB" sender, consistent with the relance
templates from step33.

Idempotent: detects if already patched.

Run: python step36_update_invoice_sending_template.py
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from _client import search_read, write

TEMPLATE_ID = 18  # Invoice: Sending

SIGNATURE = """<table cellpadding="0" cellspacing="0" border="0" style="font-family: 'DM Sans', Arial, sans-serif; font-size: 11px; color: #333333; line-height: 1.4; margin-top: 24px;">
  <tr>
    <td style="padding-right: 12px; border-right: 2px solid #c5a467; vertical-align: top;">
      <img src="https://cdn.shopify.com/s/files/1/0924/1922/7982/files/Logo-rond-noir-sans-fond.png?v=1773170347" alt="MY.LAB" width="55" height="55" style="border-radius: 50%; display: block;" />
    </td>
    <td style="padding-left: 12px; vertical-align: top;">
      <p style="margin: 0 0 1px 0; font-size: 13px; font-weight: 700; color: #1a1a1a;">Service Comptabilit&eacute;</p>
      <p style="margin: 0 0 6px 0; font-size: 10px; font-weight: 500; color: #c5a467; text-transform: uppercase; letter-spacing: 1px;">MY.LAB</p>
      <p style="margin: 0 0 2px 0; font-size: 11px;"><span style="color: #999;">T</span>&nbsp;<a href="tel:+33485693347" style="color: #333; text-decoration: none;">04 85 69 33 47</a></p>
      <p style="margin: 0 0 2px 0; font-size: 11px;"><span style="color: #999;">E</span>&nbsp;<a href="mailto:contact@mylab-shop.com" style="color: #333; text-decoration: none;">contact@mylab-shop.com</a></p>
      <p style="margin: 0 0 6px 0; font-size: 11px;"><span style="color: #999;">W</span>&nbsp;<a href="https://mylab-shop.com" style="color: #c5a467; text-decoration: none; font-weight: 600;">mylab-shop.com</a></p>
      <p style="margin: 0; font-size: 9px; color: #999;">231 Avenue de la Voguette, 84300 Cavaillon &mdash; France</p>
      <p style="margin: 5px 0 0 0; padding-top: 5px; border-top: 1px solid #e5e5e5; font-size: 9px; color: #c5a467; font-style: italic;">SARL STARTEC &mdash; SIRET 499 500 668 00059 &mdash; TVA FR38499500668</p>
    </td>
  </tr>
</table>"""

# Read current body
t = search_read("mail.template", [("id", "=", TEMPLATE_ID)],
                ["name", "body_html", "email_from"])[0]
print(f"Template: {t['name']}")
print(f"Current email_from: {t['email_from']}")
print()

body = t["body_html"]

# Idempotency check
if "Service Comptabilit" in body:
    print("✓ Already patched — skipping body update.")
else:
    # Replace the dynamic invoice_user_id.signature block with our SIGNATURE.
    # Target the segment from the t-if test through its closing </t></t>.
    # Use a known landmark that's unique in this template.
    OLD_SIG = ('<t t-if="not is_html_empty(object.invoice_user_id.signature)" '
               'data-o-mail-quote-container="1"><br/><br/>'
               '<t t-out="object.invoice_user_id.signature or \'\'" '
               'data-o-mail-quote="1">--<br data-o-mail-quote="1"/>Yoann DURAND</t></t>')

    if OLD_SIG not in body:
        print("ERROR: dynamic signature block not found — body structure may have changed.")
        print("Looking for marker: 'invoice_user_id.signature' presence:",
              "invoice_user_id.signature" in body)
        sys.exit(1)

    new_body = body.replace(OLD_SIG, "<br/><br/>" + SIGNATURE)
    write("mail.template", [TEMPLATE_ID], {"body_html": new_body})
    print("✓ Body updated with Service Comptabilité signature.")

# Update email_from to fixed Service Comptabilité sender
NEW_EMAIL_FROM = '"Service Comptabilité MY.LAB" <yoann@mylab-shop.com>'
if t["email_from"] != NEW_EMAIL_FROM:
    write("mail.template", [TEMPLATE_ID], {
        "email_from": NEW_EMAIL_FROM,
        "reply_to": "yoann@mylab-shop.com",
    })
    print(f"✓ email_from updated to: {NEW_EMAIL_FROM}")
else:
    print("✓ email_from already set correctly.")

print()
print("Le prochain envoi de facture (depuis Odoo → Send & Print) utilisera")
print("la nouvelle signature et le sender Service Comptabilité.")
