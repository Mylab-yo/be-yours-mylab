"""One-off : exporte 3 factures CAPILEM (588.24/25-07-2025, 896.52/05-01-2026, 509.16/21-03-2026)
depuis C:/Users/startec/Downloads/invoice_extracted vers C:/Users/startec/Downloads/factures_capilem.
"""
import re
import shutil
import unicodedata
from pathlib import Path

import pdfplumber

INVOICE_DIR = Path(r"C:/Users/startec/Downloads/invoice_extracted")
DEST = Path(r"C:/Users/startec/Downloads/factures_capilem")

TARGETS = [
    {"amount": "588,24", "date_re": re.compile(r"25\s+juillet\s+2025", re.I)},
    {"amount": "896,52", "date_re": re.compile(r"5\s+janvier\s+2026", re.I)},
    {"amount": "509,16", "date_re": re.compile(r"21\s+mars\s+2026", re.I)},
]

CLIENT_RE = re.compile(r"capilem", re.I)


def pdf_text(path: Path) -> str:
    try:
        with pdfplumber.open(path) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages)
    except Exception as e:
        print(f"  ! {path.name}: {e}")
        return ""


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(INVOICE_DIR.glob("*.pdf"))
    print(f"Scanning {len(pdfs)} PDFs in {INVOICE_DIR}")

    found = {i: None for i in range(len(TARGETS))}

    for i, p in enumerate(pdfs, 1):
        if i <= 3:
            print(f"  DEBUG iter {i}: {p.name}", flush=True)
        text = pdf_text(p)
        if i == 1:
            print(f"  DEBUG text len for first PDF: {len(text)}", flush=True)
            print(f"  DEBUG first 200 chars: {text[:200]!r}", flush=True)
        if not CLIENT_RE.search(text):
            continue
        for idx, tgt in enumerate(TARGETS):
            if found[idx]:
                continue
            if tgt["amount"] in text and tgt["date_re"].search(text):
                found[idx] = p
                out = DEST / p.name
                shutil.copy2(p, out)
                print(f"  [{idx+1}/3] MATCH {p.name} -> {out}  ({tgt['amount']} EUR)")
        if i % 100 == 0:
            print(f"  scanned {i}/{len(pdfs)}  found {sum(1 for v in found.values() if v)}/3")
        if all(found.values()):
            print("  All 3 found, stopping early.")
            break

    print()
    for idx, tgt in enumerate(TARGETS):
        status = found[idx].name if found[idx] else "NOT FOUND"
        print(f"  Target #{idx+1} ({tgt['amount']} EUR / {tgt['date_re'].pattern}) -> {status}")

    print(f"\nDest dir: {DEST}")


if __name__ == "__main__":
    main()
