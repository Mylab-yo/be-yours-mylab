"""Diagnostic : verifier que le service account peut lire le template Doc."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(r"d:\Configurateur Designs MyLab\mylab-configurateur\.env.local"))

GOOGLE_SA_JSON = os.environ["GOOGLE_SA_JSON"]
TEMPLATE_DOC_ID = os.environ["MANDAT_TEMPLATE_DOC_ID"]

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]

print(f"SA JSON   : {GOOGLE_SA_JSON}")
print(f"Doc ID    : {TEMPLATE_DOC_ID}")
print()

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account

creds = service_account.Credentials.from_service_account_file(GOOGLE_SA_JSON, scopes=SCOPES)
print(f"OK creds chargees pour: {creds.service_account_email}")
print()

drive = build("drive", "v3", credentials=creds, cache_discovery=False)
docs = build("docs", "v1", credentials=creds, cache_discovery=False)

# Test 1 : Drive API access (file metadata)
print("Test 1 : Drive API - acceder aux metadata du template...")
try:
    meta = drive.files().get(fileId=TEMPLATE_DOC_ID, fields="id, name, mimeType, owners").execute()
    print(f"  OK Drive API actif, template lu : {meta['name']} ({meta['mimeType']})")
except HttpError as e:
    status = e.resp.status
    msg = e._get_reason() or str(e)
    print(f"  ECHEC HTTP {status} : {msg[:200]}")
    if status == 403 and "SERVICE_DISABLED" in str(e):
        print("  -> Drive API n'est PAS activee dans le projet api-relais-colis-dpd.")
        print("     Active : https://console.cloud.google.com/apis/library/drive.googleapis.com?project=api-relais-colis-dpd")
    elif status == 404:
        print(f"  -> Le service account n'a PAS acces au template (404 = invisible pour lui).")
        print(f"     Partage le template avec : {creds.service_account_email} (Lecteur suffit)")
    elif status == 403:
        print(f"  -> 403 = soit API desactivee, soit pas partage. Verifie les deux.")
print()

# Test 2 : Docs API access (read structure)
print("Test 2 : Docs API - lire le contenu du template...")
try:
    doc = docs.documents().get(documentId=TEMPLATE_DOC_ID).execute()
    print(f"  OK Docs API actif, titre = {doc.get('title')!r}")
except HttpError as e:
    status = e.resp.status
    msg = e._get_reason() or str(e)
    print(f"  ECHEC HTTP {status} : {msg[:200]}")
    if "SERVICE_DISABLED" in str(e):
        print("  -> Docs API n'est PAS activee dans le projet.")
        print("     Active : https://console.cloud.google.com/apis/library/docs.googleapis.com?project=api-relais-colis-dpd")
print()

# Test 3 : MANDAT_SENT_FOLDER_ID
folder_id = os.environ.get("MANDAT_SENT_FOLDER_ID", "").strip()
if not folder_id:
    print("Test 3 : MANDAT_SENT_FOLDER_ID n'est pas encore renseigne dans .env.local")
    print("  -> Cree un dossier 'Mandats envoyes' sur Drive, partage-le avec le SA (Editeur),")
    print("     puis recupere son ID depuis l'URL drive.google.com/drive/folders/<ID>")
else:
    print(f"Test 3 : verifier acces au dossier {folder_id}...")
    try:
        meta = drive.files().get(fileId=folder_id, fields="id, name, mimeType").execute()
        print(f"  OK dossier accessible : {meta['name']} ({meta['mimeType']})")
    except HttpError as e:
        print(f"  ECHEC : {e._get_reason() or str(e)[:200]}")
