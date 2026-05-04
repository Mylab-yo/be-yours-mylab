"""Create 5 mail templates for the follow-up cron.

  - mylab_devis_relance_l1   (devis +7j, doux)
  - mylab_devis_relance_l2   (devis +14j, direct)
  - mylab_facture_relance_l1 (facture +3j post-échéance, courtois)
  - mylab_facture_relance_l2 (facture +10j post-échéance, ferme)
  - mylab_facture_relance_l3 (facture +30j post-échéance, mise en demeure, CC yoann@)

All in French B2B tone, MY.LAB signature embedded. Uses Odoo 18 Jinja syntax
({{ object.field }}). Sender = yoann@mylab-shop.com.

Idempotent: identifies templates by `name`, updates if exist.

Run: python step33_create_followup_templates.py
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from _client import search_read, create, write

# Signature institutionnelle (Service Comptabilité) — utilisée pour les
# emails de facturation et relances, distincte de la signature personnelle
# Yoann DURAND utilisée pour les emails commerciaux/devis.
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

WRAPPER = """<div style="font-family: 'DM Sans', Arial, sans-serif; color: #333333; font-size: 14px; line-height: 1.6; max-width: 640px;">
{body}
{signature}
</div>"""

# Find user yoann@mylab-shop.com for email_from
yoann_user = search_read("res.users", [("login", "=", "yoann@mylab-shop.com")],
                         ["id", "partner_id"])
if not yoann_user:
    print("ERROR: user yoann@mylab-shop.com not found")
    sys.exit(1)
yoann_id = yoann_user[0]["id"]
print(f"Sender user: yoann@mylab-shop.com (id={yoann_id})")
print()

# Get model IDs
sale_model = search_read("ir.model", [("model", "=", "sale.order")], ["id"])[0]["id"]
move_model = search_read("ir.model", [("model", "=", "account.move")], ["id"])[0]["id"]


def upsert_template(name, model_id, subject, body, **extra):
    """Create or update mail template by `name`."""
    existing = search_read("mail.template", [("name", "=", name)], ["id"])
    values = {
        "name": name,
        "model_id": model_id,
        "subject": subject,
        "body_html": WRAPPER.format(body=body, signature=SIGNATURE),
        "use_default_to": False,
        "lang": "{{ object.partner_id.lang or 'fr_FR' }}",
        "auto_delete": False,
        "user_id": yoann_id,
        **extra,
    }
    if existing:
        write("mail.template", [existing[0]["id"]], values)
        print(f"  ✓ Updated [{existing[0]['id']}] {name}")
        return existing[0]["id"]
    new_id = create("mail.template", values)
    print(f"  ✓ Created [{new_id}] {name}")
    return new_id


# ── DEVIS L1 (+7j, doux) ────────────────────────────────
print("Devis relance L1 (7j) :")
upsert_template(
    name="mylab_devis_relance_l1",
    model_id=sale_model,
    subject="Votre devis MY.LAB {{ object.name }} — toujours d'actualité ?",
    body="""<p>Bonjour <t t-out="object.partner_id.name"/>,</p>
<p>Il y a une semaine, je vous ai transmis le devis <strong><t t-out="object.name"/></strong> pour un montant de <t t-out="format_amount(object.amount_total, object.currency_id)"/> TTC.</p>
<p>Je voulais simplement m'assurer qu'il vous est bien parvenu et savoir où ça en est de votre côté.</p>
<p>Vous pouvez consulter et valider votre devis directement via ce lien :</p>
<p style="text-align: center; margin: 24px 0;">
  <a t-att-href="object.get_portal_url()" style="display: inline-block; background: #1a1a1a; color: #fff; padding: 12px 28px; text-decoration: none; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase; font-size: 12px;">Voir mon devis</a>
</p>
<p>Si une question reste en suspens, n'hésitez pas à me répondre directement à ce mail.</p>
<p>Bonne journée,<br/>Service Comptabilité — MY.LAB</p>""",
    email_from='"Service Comptabilité MY.LAB" <yoann@mylab-shop.com>',
    reply_to="yoann@mylab-shop.com",
)

# ── DEVIS L2 (+14j, plus direct) ────────────────────────
print("Devis relance L2 (14j) :")
upsert_template(
    name="mylab_devis_relance_l2",
    model_id=sale_model,
    subject="Devis {{ object.name }} — un point bloque ?",
    body="""<p>Bonjour <t t-out="object.partner_id.name"/>,</p>
<p>Je reviens vers vous concernant le devis <strong><t t-out="object.name"/></strong> que je vous ai envoyé il y a deux semaines.</p>
<p>Si un point n'est pas clair ou si vous avez besoin d'un ajustement (quantités, gammes, packaging…), je suis disponible pour en discuter de vive voix : <a href="https://cal.com/mylab-shop/15min" style="color: #c5a467;">réservez 15 min</a>.</p>
<p>Sinon, vous pouvez consulter le devis ici :</p>
<p style="text-align: center; margin: 24px 0;">
  <a t-att-href="object.get_portal_url()" style="display: inline-block; background: #1a1a1a; color: #fff; padding: 12px 28px; text-decoration: none; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase; font-size: 12px;">Voir mon devis</a>
</p>
<p>Dans l'attente de votre retour,<br/>Service Comptabilité — MY.LAB</p>""",
    email_from='"Service Comptabilité MY.LAB" <yoann@mylab-shop.com>',
    reply_to="yoann@mylab-shop.com",
)

# ── FACTURE L1 (+3j post-échéance, courtois) ──────────────
print("Facture relance L1 (3j) :")
upsert_template(
    name="mylab_facture_relance_l1",
    model_id=move_model,
    subject="Facture {{ object.name }} — petit rappel",
    body="""<p>Bonjour <t t-out="object.partner_id.name"/>,</p>
<p>Petit rappel amical : votre facture <strong><t t-out="object.name"/></strong> d'un montant de <strong><t t-out="format_amount(object.amount_total, object.currency_id)"/></strong> était arrivée à échéance le <t t-out="format_date(object.invoice_date_due)"/>.</p>
<p>Si vous l'avez déjà réglée dans les derniers jours, merci d'ignorer ce message. Sinon, vous pouvez procéder au règlement par virement (IBAN dans la facture jointe) ou directement en ligne :</p>
<p style="text-align: center; margin: 24px 0;">
  <a t-att-href="object.get_portal_url()" style="display: inline-block; background: #1a1a1a; color: #fff; padding: 12px 28px; text-decoration: none; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase; font-size: 12px;">Régler en ligne</a>
</p>
<p>Bonne journée,<br/>Service Comptabilité — MY.LAB</p>""",
    email_from='"Service Comptabilité MY.LAB" <yoann@mylab-shop.com>',
    reply_to="yoann@mylab-shop.com",
)

# ── FACTURE L2 (+10j, ferme) ─────────────────────────────
print("Facture relance L2 (10j) :")
upsert_template(
    name="mylab_facture_relance_l2",
    model_id=move_model,
    subject="Facture {{ object.name }} en retard de paiement",
    body="""<p>Bonjour <t t-out="object.partner_id.name"/>,</p>
<p>Sauf erreur de ma part, votre facture <strong><t t-out="object.name"/></strong> d'un montant de <strong><t t-out="format_amount(object.amount_total, object.currency_id)"/></strong> est toujours en attente de règlement (échéance dépassée depuis le <t t-out="format_date(object.invoice_date_due)"/>).</p>
<p>Merci de procéder au règlement <strong>sous huitaine</strong>, ou de me revenir si un point bloque ou si vous avez besoin d'un échéancier.</p>
<p style="text-align: center; margin: 24px 0;">
  <a t-att-href="object.get_portal_url()" style="display: inline-block; background: #1a1a1a; color: #fff; padding: 12px 28px; text-decoration: none; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase; font-size: 12px;">Régler maintenant</a>
</p>
<p>Cordialement,<br/>Service Comptabilité — MY.LAB</p>""",
    email_from='"Service Comptabilité MY.LAB" <yoann@mylab-shop.com>',
    reply_to="yoann@mylab-shop.com",
)

# ── FACTURE L3 (+30j, mise en demeure) ────────────────────
print("Facture relance L3 (30j, mise en demeure) :")
upsert_template(
    name="mylab_facture_relance_l3",
    model_id=move_model,
    subject="MISE EN DEMEURE — Facture {{ object.name }} impayée",
    body="""<p>Bonjour <t t-out="object.partner_id.name"/>,</p>
<p>Malgré nos précédentes relances, votre facture <strong><t t-out="object.name"/></strong> d'un montant de <strong><t t-out="format_amount(object.amount_total, object.currency_id)"/></strong> reste impayée à ce jour, soit plus de 30 jours après son échéance (<t t-out="format_date(object.invoice_date_due)"/>).</p>
<p>Conformément à l'article L441-10 du Code de commerce, je vous mets en demeure de procéder au règlement intégral de cette somme dans un <strong>délai de 8 jours</strong> à réception de la présente.</p>
<p>À défaut de règlement dans ce délai, je serai contraint de transférer votre dossier à notre service de recouvrement, lequel appliquera de plein droit :</p>
<ul>
  <li>des pénalités de retard au taux légal majoré de 10 points,</li>
  <li>une indemnité forfaitaire pour frais de recouvrement de 40 € (Art. L441-10 II du Code de commerce),</li>
  <li>les frais réels de recouvrement complémentaires.</li>
</ul>
<p>Si vous traversez une difficulté ponctuelle, contactez-moi dès que possible pour étudier ensemble une solution amiable.</p>
<p>Cordialement,<br/>Service Comptabilité — SARL STARTEC / MY.LAB</p>""",
    email_from='"Service Comptabilité MY.LAB" <yoann@mylab-shop.com>',
    reply_to="yoann@mylab-shop.com",
    email_cc="yoann@mylab-shop.com",  # Yoann en copie pour escalade
)

print("\n✓ All 5 templates ready.")
