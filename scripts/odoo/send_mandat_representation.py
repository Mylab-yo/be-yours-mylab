"""Envoi du mandat de representation au client (depuis une facture Odoo).

Usage:
    python -m scripts.odoo.send_mandat_representation --invoice INV/2026/00001 [--dry-run]
    python -m scripts.odoo.send_mandat_representation --invoice-id 1234 [--dry-run]

Voir docs/mandat-representation/README.md pour le setup initial (service account, dossier Drive).
"""
import argparse
import base64
import io
import os
import re
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from scripts.odoo._client import search_read, execute, create

ENV_PATH = Path(r"d:\Configurateur Designs MyLab\mylab-configurateur\.env.local")
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

GOOGLE_SA_JSON = os.environ.get("GOOGLE_SA_JSON", "")
TEMPLATE_DOC_ID = os.environ.get("MANDAT_TEMPLATE_DOC_ID", "1eCmScLGtG1XS9B2v90srZRVoY--55iVDr35WwJ6oIYo")
SENT_FOLDER_ID = os.environ.get("MANDAT_SENT_FOLDER_ID", "")

PRODUCT_DOSSIER_ID = 2313
SENDER_EMAIL = "yoann@mylab-shop.com"

# mail.activity.type id cree par setup_phase2_action_mandat.py
ACTIVITY_TYPE_ID_DEFAULT = 8

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]

MOIS_FR = ["janvier", "fevrier", "mars", "avril", "mai", "juin",
           "juillet", "aout", "septembre", "octobre", "novembre", "decembre"]


def fmt_date_fr(d: date) -> str:
    return f"{d.day} {MOIS_FR[d.month - 1]} {d.year}"


def extract_siren_from_vat(vat: str | None) -> str:
    if not vat:
        return ""
    digits = re.sub(r"\D", "", vat)
    if len(digits) >= 9:
        return digits[-9:]
    return ""


def build_address(partner: dict) -> str:
    parts = []
    if partner.get("street"):
        parts.append(partner["street"])
    if partner.get("street2"):
        parts.append(partner["street2"])
    cp_ville = " ".join(filter(None, [partner.get("zip"), partner.get("city")]))
    if cp_ville:
        parts.append(cp_ville)
    country = partner.get("country_id")
    if country and isinstance(country, list):
        parts.append(country[1])
    return ", ".join(parts)


def get_invoice_and_partner(target):
    if isinstance(target, int):
        domain = [("id", "=", target)]
    else:
        domain = [("name", "=", target)]
    rows = search_read(
        "account.move",
        domain + [("move_type", "in", ["out_invoice", "out_receipt"])],
        ["id", "name", "partner_id", "invoice_line_ids", "payment_state", "state"],
    )
    if not rows:
        raise SystemExit(f"Facture introuvable: {target}")
    inv = rows[0]
    lines = search_read(
        "account.move.line",
        [("id", "in", inv["invoice_line_ids"])],
        ["product_id"],
    )
    product_ids = [l["product_id"][0] for l in lines if l.get("product_id")]
    if PRODUCT_DOSSIER_ID not in product_ids:
        raise SystemExit(
            f"Facture {inv['name']} ne contient PAS le produit 'creation-du-dossier-cosmetologique' "
            f"(product.product id={PRODUCT_DOSSIER_ID}). Lignes: {product_ids}"
        )
    partner_id = inv["partner_id"][0]
    partner_rows = search_read(
        "res.partner",
        [("id", "=", partner_id)],
        ["id", "name", "commercial_company_name", "vat",
         "street", "street2", "zip", "city", "country_id", "email"],
    )
    return inv, partner_rows[0]


def build_placeholders(partner: dict) -> dict:
    raison_sociale = partner.get("commercial_company_name") or partner.get("name") or ""
    vat = partner.get("vat") or ""
    return {
        "[Raison sociale du Client]": raison_sociale,
        "[ville]": partner.get("city") or "",
        "[SIREN]": extract_siren_from_vat(vat),
        "[le cas echeant]": vat,
        "[le cas échéant]": vat,
        "[adresse complete]": build_address(partner),
        "[adresse complète]": build_address(partner),
        "29 mai 2026": fmt_date_fr(date.today()),
    }


def gdocs_clients():
    try:
        from googleapiclient.discovery import build
        from google.oauth2 import service_account
    except ImportError as e:
        raise SystemExit(
            "Manque google-api-python-client. Installe avec:\n"
            "  pip install google-api-python-client\n"
            f"({e})"
        )
    if not GOOGLE_SA_JSON or not Path(GOOGLE_SA_JSON).exists():
        raise SystemExit(
            f"GOOGLE_SA_JSON introuvable: {GOOGLE_SA_JSON!r}\n"
            "Configure .env.local avec le path du JSON service account "
            "(voir docs/mandat-representation/README.md)."
        )
    creds = service_account.Credentials.from_service_account_file(
        GOOGLE_SA_JSON, scopes=SCOPES
    )
    docs = build("docs", "v1", credentials=creds, cache_discovery=False)
    drive = build("drive", "v3", credentials=creds, cache_discovery=False)
    return docs, drive


def copy_and_fill_template(docs, drive, placeholders: dict, doc_name: str) -> str:
    if not SENT_FOLDER_ID:
        raise SystemExit("MANDAT_SENT_FOLDER_ID absent dans .env.local")
    copy_meta = drive.files().copy(
        fileId=TEMPLATE_DOC_ID,
        body={"name": doc_name, "parents": [SENT_FOLDER_ID]},
        supportsAllDrives=True,
    ).execute()
    new_doc_id = copy_meta["id"]
    requests = [
        {
            "replaceAllText": {
                "containsText": {"text": placeholder, "matchCase": True},
                "replaceText": value,
            }
        }
        for placeholder, value in placeholders.items()
        if value
    ]
    docs.documents().batchUpdate(documentId=new_doc_id, body={"requests": requests}).execute()
    return new_doc_id


def export_pdf(drive, doc_id: str) -> bytes:
    from googleapiclient.http import MediaIoBaseDownload
    request = drive.files().export_media(fileId=doc_id, mimeType="application/pdf")
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue()


def attach_to_invoice(invoice_id: int, pdf_bytes: bytes, filename: str) -> int:
    return create("ir.attachment", {
        "name": filename,
        "type": "binary",
        "datas": base64.b64encode(pdf_bytes).decode("ascii"),
        "res_model": "account.move",
        "res_id": invoice_id,
        "mimetype": "application/pdf",
    })


def build_email_body(raison_sociale: str) -> str:
    return f"""<p>Bonjour,</p>

<p>Suite à votre commande du <em>Dossier cosmétologique</em> auprès de MY.LAB,
vous trouverez en pièce jointe le <strong>mandat de Personne Responsable</strong>
désignant SARL VEGETAL ORIGIN comme Personne Responsable de vos produits
cosmétiques au sens de l'article 4 du règlement (CE) n° 1223/2009.</p>

<p>Merci de bien vouloir :</p>
<ol>
  <li><strong>Compléter les champs encore en blanc</strong> (forme juridique,
      capital, représentant légal, nom de marque, ville de signature) ;</li>
  <li><strong>Signer le document</strong> (par signature manuscrite directement
      sur le PDF, ou en l'imprimant) précédé de la mention manuscrite
      <em>« Bon pour acceptation du mandat de Personne Responsable »</em> ;</li>
  <li><strong>Nous le retourner par mail</strong> à
      <a href="mailto:{SENDER_EMAIL}">{SENDER_EMAIL}</a>.</li>
</ol>

<p>Le mandat est établi en deux (2) exemplaires originaux : un pour vous,
un pour MY.LAB.</p>

<p>Pour toute question, je reste à votre disposition.</p>

<p>Bien cordialement,<br/>
<strong>L'équipe MyLab</strong></p>
"""


def send_email_via_odoo(invoice_id: int, partner_email: str, raison_sociale: str, attachment_id: int) -> int:
    mail_vals = {
        "subject": "Mandat de Personne Responsable - a signer et retourner",
        "body_html": build_email_body(raison_sociale),
        "email_from": SENDER_EMAIL,
        "email_to": partner_email,
        "model": "account.move",
        "res_id": invoice_id,
        "attachment_ids": [(4, attachment_id)],
        "auto_delete": False,
    }
    mail_id = create("mail.mail", mail_vals)
    execute("mail.mail", "send", [[mail_id]])
    return mail_id


def log_chatter(invoice_id: int, doc_id: str, mail_id: int, recipient: str):
    body = (
        f"<p><strong>Mandat de Personne Responsable envoye</strong></p>"
        f"<ul>"
        f"<li>Destinataire : {recipient}</li>"
        f"<li>Doc Google : <a href=\"https://docs.google.com/document/d/{doc_id}/edit\" "
        f"target=\"_blank\">docs.google.com/document/d/{doc_id}</a></li>"
        f"<li>mail.mail id : {mail_id}</li>"
        f"<li>Date : {date.today().isoformat()}</li>"
        f"</ul>"
    )
    execute("account.move", "message_post", [[invoice_id]], {
        "body": body,
        "message_type": "comment",
        "subtype_xmlid": "mail.mt_note",
    })


def process_invoice(target, to: str | None = None, force: bool = False,
                    dry_run: bool = False, verbose: bool = True) -> dict:
    """Pipeline complet d'envoi pour une facture.

    target = int (invoice_id) ou str (invoice name)
    Retourne un dict {success, recipient, doc_id, mail_id, attachment_id, error}.
    """
    def log(msg=""):
        if verbose:
            print(msg)

    result = {"success": False, "invoice": None}
    inv, partner = get_invoice_and_partner(target)
    placeholders = build_placeholders(partner)
    result["invoice"] = inv["name"]
    result["raison_sociale"] = placeholders["[Raison sociale du Client]"]

    log(f"=== Facture {inv['name']} (id={inv['id']}) ===")
    log(f"Client    : {partner['name']} (id={partner['id']})")
    log(f"Email     : {partner.get('email') or '(absent)'}")
    log(f"Etat      : state={inv['state']}, payment_state={inv['payment_state']}")
    log()
    log("Placeholders qui seront remplaces :")
    for k, v in placeholders.items():
        if v:
            log(f"  {k!r} -> {v!r}")
    log()

    if not partner.get("email") and not to:
        result["error"] = "no_email"
        log("ERREUR : pas d'email sur le partner et pas de --to. Abandon.")
        return result

    if inv["payment_state"] != "paid" and not force:
        result["error"] = f"not_paid (payment_state={inv['payment_state']})"
        log(f"ERREUR : facture non payee (payment_state={inv['payment_state']!r}).")
        log("Le mandat n'est envoye qu'aux clients ayant regle leur dossier cosmetologique.")
        log("Pour bypass : ajouter --force")
        return result

    recipient = to or partner["email"]
    if to:
        log(f"!! REDIRECTION email vers {to} (au lieu de {partner.get('email')!r})")
        log()
    result["recipient"] = recipient

    if dry_run:
        log("(dry-run, aucune action reelle)")
        result["success"] = True
        result["dry_run"] = True
        return result

    log("-> Connexion Google APIs...")
    docs, drive = gdocs_clients()

    raison_sociale = placeholders["[Raison sociale du Client]"]
    safe_name = re.sub(r"[^A-Za-z0-9 _-]", "", raison_sociale).strip() or "Client"
    doc_name = f"Mandat Personne Responsable - {safe_name} - {date.today():%Y-%m-%d}"
    log(f"-> Copie du template vers '{doc_name}'...")
    new_doc_id = copy_and_fill_template(docs, drive, placeholders, doc_name)
    log(f"  Doc cree : https://docs.google.com/document/d/{new_doc_id}/edit")
    result["doc_id"] = new_doc_id

    log("-> Export PDF...")
    pdf_bytes = export_pdf(drive, new_doc_id)
    log(f"  PDF genere : {len(pdf_bytes)} octets")

    filename = f"Mandat_Personne_Responsable_{safe_name.replace(' ', '_')}.pdf"
    log("-> Attachement a la facture Odoo...")
    attachment_id = attach_to_invoice(inv["id"], pdf_bytes, filename)
    log(f"  ir.attachment id={attachment_id}")
    result["attachment_id"] = attachment_id

    log(f"-> Envoi mail a {recipient}...")
    mail_id = send_email_via_odoo(inv["id"], recipient, raison_sociale, attachment_id)
    log(f"  mail.mail id={mail_id}")
    result["mail_id"] = mail_id

    log("-> Log chatter...")
    log_chatter(inv["id"], new_doc_id, mail_id, recipient)

    log()
    log(f"OK Mandat envoye a {recipient} pour {raison_sociale}")
    result["success"] = True
    return result


def main():
    ap = argparse.ArgumentParser(
        description="Envoi du mandat de Personne Responsable depuis une facture Odoo",
    )
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--invoice", help="Reference facture (ex: INV/2026/00001)")
    g.add_argument("--invoice-id", type=int, help="ID interne facture (account.move.id)")
    ap.add_argument("--dry-run", action="store_true", help="Affiche sans rien envoyer")
    ap.add_argument("--to", help="Redirige le mail vers cette adresse au lieu du client (test)")
    ap.add_argument("--force", action="store_true",
                    help="Bypass la verification payment_state=paid (envoi meme si non paye)")
    args = ap.parse_args()

    target = args.invoice_id if args.invoice_id else args.invoice
    result = process_invoice(target, to=args.to, force=args.force, dry_run=args.dry_run)
    if not result["success"]:
        sys.exit(2 if result.get("error") == "no_email" else 3)


if __name__ == "__main__":
    main()
