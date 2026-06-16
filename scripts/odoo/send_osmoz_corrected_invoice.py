"""Resend corrected invoice FAC/2026/00093 to Maison Osmoz with new billing address.

Uses template 18 (attaches the Invoice PDF, report 325) but overrides recipient
(billing contact 2177 has no email) and body (personalised correction note).
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from _client import search_read, execute

TEMPLATE_ID = 18
INV_ID = 456
TO = "maisonosmoz@gmail.com"

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

BODY = f"""<div style="font-family: 'DM Sans', Arial, sans-serif; font-size: 14px; color: #333; line-height: 1.6;">
<p>Bonjour,</p>
<p>Suite &agrave; votre message, nous avons corrig&eacute; l'adresse de facturation de votre facture <strong>FAC/2026/00093</strong>.</p>
<p>Vous trouverez ci-joint la facture mise &agrave; jour, &eacute;tablie &agrave; l'adresse suivante&nbsp;:</p>
<p style="margin-left: 16px;">
Maison Osmoz Akbulut<br/>
Avenue d'Echallens 4a<br/>
1004 Lausanne
</p>
<p>L'adresse de livraison reste inchang&eacute;e. Nous restons &agrave; votre disposition pour toute question.</p>
<p>Bien cordialement,</p>
{SIGNATURE}
</div>"""

SUBJECT = "MY.LAB - Facture FAC/2026/00093 (adresse de facturation corrigee)"

mail_id = execute("mail.template", "send_mail", [TEMPLATE_ID, INV_ID], {
    "force_send": True,
    "email_values": {
        "email_to": TO,
        "subject": SUBJECT,
        "body_html": BODY,
    },
})
print(f"mail.mail id = {mail_id}")

m = search_read("mail.mail", [("id", "=", mail_id)],
                ["state", "email_to", "subject", "attachment_ids",
                 "failure_reason"])
print(m)
if m:
    atts = m[0].get("attachment_ids") or []
    if atts:
        names = execute("ir.attachment", "read", [atts], {"fields": ["name"]})
        print("attachments:", [n["name"] for n in names])
