"""Verifier si le dossier 'Mandats envoyes' est bien dans un Shared Drive."""
import os
from pathlib import Path
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2 import service_account

load_dotenv(Path(r"d:\Configurateur Designs MyLab\mylab-configurateur\.env.local"))

SCOPES = ["https://www.googleapis.com/auth/drive"]
creds = service_account.Credentials.from_service_account_file(
    os.environ["GOOGLE_SA_JSON"], scopes=SCOPES
)
drive = build("drive", "v3", credentials=creds, cache_discovery=False)

folder_id = os.environ["MANDAT_SENT_FOLDER_ID"]
print(f"Verification du dossier {folder_id}...")
print(f"SA email: {creds.service_account_email}\n")

meta = drive.files().get(
    fileId=folder_id,
    fields="id, name, mimeType, driveId, parents, owners, shared",
    supportsAllDrives=True,
).execute()

print(f"Nom         : {meta.get('name')}")
print(f"MimeType    : {meta.get('mimeType')}")
print(f"Parents     : {meta.get('parents', [])}")
print(f"driveId     : {meta.get('driveId', '(absent = My Drive d''un user, PAS un Shared Drive)')}")
print(f"Owners      : {[o.get('emailAddress') for o in meta.get('owners', [])]}")
print()

if meta.get("driveId"):
    drive_meta = drive.drives().get(driveId=meta["driveId"]).execute()
    print(f"OK ce dossier est dans le Shared Drive: '{drive_meta['name']}' (id={drive_meta['id']})")
    print("\n=> Le SA peut creer des fichiers dedans (Shared Drive utilise quota workspace, pas SA).")
else:
    print("KO ce dossier est dans le My Drive d'un utilisateur, PAS dans un Shared Drive.")
    print("=> Le copy() echouera encore avec storageQuotaExceeded.")
    print("\nAction requise : creer un Shared Drive, y mettre un sous-dossier, partager avec le SA.")
