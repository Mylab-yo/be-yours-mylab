"""Cleanup des residus de tests sur FAC/2026/00012 + dossier Drive 'Mandats envoyes'.

Supprime :
  - Les ir.attachment Mandat_Personne_Responsable_Myan_Coiffure.pdf sur FAC/2026/00012
  - Les docs Google "Mandat Personne Responsable - Myan Coiffure - 2026-05-29" dans le dossier Drive

A executer UNE FOIS apres validation du pipeline.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

from scripts.odoo._client import search_read, execute

load_dotenv(Path(r"d:\Configurateur Designs MyLab\mylab-configurateur\.env.local"))

# --- 1. Odoo attachments ---
print("=== Cleanup attachments Odoo sur FAC/2026/00012 ===")
attachments = search_read(
    "ir.attachment",
    [("res_model", "=", "account.move"),
     ("res_id", "=", 221),
     ("name", "like", "Mandat_Personne_Responsable_Myan_Coiffure")],
    ["id", "name", "create_date"],
)
print(f"-> {len(attachments)} attachment(s) trouve(s)")
for a in attachments:
    print(f"  id={a['id']} create={a['create_date']} name={a['name']!r}")

if attachments:
    ids = [a["id"] for a in attachments]
    execute("ir.attachment", "unlink", [ids])
    print(f"  -> SUPPRIMES : {ids}")

# --- 2. Google Drive docs ---
print("\n=== Cleanup docs Drive 'Mandats envoyes' ===")
from googleapiclient.discovery import build
from google.oauth2 import service_account

SCOPES = ["https://www.googleapis.com/auth/drive"]
creds = service_account.Credentials.from_service_account_file(
    os.environ["GOOGLE_SA_JSON"], scopes=SCOPES,
)
drive = build("drive", "v3", credentials=creds, cache_discovery=False)

folder_id = os.environ["MANDAT_SENT_FOLDER_ID"]
query = (
    f"'{folder_id}' in parents and "
    "name contains 'Mandat Personne Responsable - Myan Coiffure' and "
    "trashed = false"
)
res = drive.files().list(
    q=query, fields="files(id, name)", supportsAllDrives=True,
    includeItemsFromAllDrives=True, corpora="allDrives",
).execute()
files = res.get("files", [])
print(f"-> {len(files)} doc(s) trouve(s)")
for f in files:
    print(f"  id={f['id']} name={f['name']!r}")

for f in files:
    try:
        drive.files().update(
            fileId=f["id"], body={"trashed": True}, supportsAllDrives=True,
        ).execute()
        print(f"  -> CORBEILLE : {f['id']}")
    except Exception as e:
        print(f"  -> ECHEC trash {f['id']} : {str(e)[:120]}")
        print(f"     -> a supprimer manuellement dans Drive")

print("\nOK cleanup termine.")
