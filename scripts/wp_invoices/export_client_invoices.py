"""Find invoices belonging to a given client (by name match in PDF text) and copy them out.

Usage:
    python export_client_invoices.py "Melody Aranda" [destination_dir]
"""
import re
import shutil
import sys
import unicodedata
from pathlib import Path

import pdfplumber

INVOICE_DIR = Path(r"C:/Users/startec/Downloads/invoice_extracted")
DEFAULT_DEST = Path(r"C:/Users/startec/Downloads")


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


def name_variants(full_name: str):
    parts = [p for p in re.split(r"\s+", full_name.strip()) if p]
    if len(parts) < 2:
        return {normalize(full_name)}
    first, last = parts[0], parts[-1]
    return {
        normalize(f"{first} {last}"),
        normalize(f"{last} {first}"),
    }


def pdf_text(path: Path) -> str:
    try:
        with pdfplumber.open(path) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages)
    except Exception as e:
        print(f"  ! {path.name}: {e}")
        return ""


def main():
    if len(sys.argv) < 2:
        print("Usage: export_client_invoices.py <client name> [dest]")
        sys.exit(1)
    client = sys.argv[1]
    dest = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_DEST / f"factures_{normalize(client).replace(' ', '_')}"
    dest.mkdir(parents=True, exist_ok=True)

    targets = name_variants(client)
    print(f"Searching {INVOICE_DIR} for: {sorted(targets)}")
    print(f"Destination: {dest}")

    pdfs = sorted(INVOICE_DIR.glob("*.pdf"))
    matches = []
    for i, p in enumerate(pdfs, 1):
        text = normalize(pdf_text(p))
        if any(t in text for t in targets):
            matches.append(p)
        if i % 100 == 0:
            print(f"  scanned {i}/{len(pdfs)} (matches so far: {len(matches)})")
    print(f"\nDone. {len(matches)} match(es) on {len(pdfs)} PDFs.")

    for p in matches:
        out = dest / p.name
        shutil.copy2(p, out)
        print(f"  copied -> {out}")

    print(f"\nAll done. {len(matches)} file(s) in {dest}")


if __name__ == "__main__":
    main()
