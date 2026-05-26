"""Helper : genere un JSON payload pour tester le webhook devis manuel en mode fichier.

Usage:
    python build_file_payload.py /chemin/vers/fichier.pdf > /tmp/payload.json
    python build_file_payload.py /chemin/vers/fichier.jpg --email client@salon.fr > /tmp/payload.json

Output sur stdout : JSON pret pour curl -d @-
"""
import argparse
import base64
import json
import mimetypes
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="PDF ou JPEG a inclure")
    parser.add_argument("--email", default="yoann@mylab-shop.com")
    parser.add_argument("--client-name", default="TEST SMOKE - Mode fichier")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        sys.exit(f"ERROR: {path} not found")

    mime, _ = mimetypes.guess_type(str(path))
    if mime not in {"application/pdf", "image/jpeg", "image/jpg"}:
        sys.exit(f"ERROR: unsupported mime {mime!r} (need PDF or JPEG)")

    data = path.read_bytes()
    if len(data) > 10 * 1024 * 1024:
        sys.exit(f"ERROR: file too large ({len(data)/1024/1024:.2f} Mo > 10 Mo)")

    payload = {
        "email": args.email,
        "client_name": args.client_name,
        "file_base64": base64.b64encode(data).decode("ascii"),
        "file_mime": mime,
        "file_name": path.name
    }
    json.dump(payload, sys.stdout)


if __name__ == "__main__":
    main()
