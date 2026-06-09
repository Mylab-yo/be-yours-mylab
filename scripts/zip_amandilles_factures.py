"""Zip the 13 Amandilles / gilles GBIA invoices."""
import zipfile
from pathlib import Path

SRC = Path(r"C:\Users\startec\Downloads\invoice_extracted")
OUT = Path(r"C:\Users\startec\Downloads\amandilles_factures.zip")

FILES = [
    "facture-MYLAB1644.pdf",
    "facture-MYLAB1732.pdf",
    "facture-MYLAB1852.pdf",
    "facture-MYLAB1853.pdf",
    "facture-MYLAB1918.pdf",
    "facture-MYLAB1919.pdf",
    "facture-MYLAB1994.pdf",
    "facture-MYLAB2038.pdf",
    "facture-MYLAB2146.pdf",
    "facture-MYLAB2224.pdf",
    "facture-MYLAB2322.pdf",
    "facture-MYLAB2384.pdf",
    "facture-MYLAB2488.pdf",
]

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
    for name in FILES:
        src = SRC / name
        if not src.exists():
            print(f"MISSING: {name}")
            continue
        zf.write(src, arcname=name)
        print(f"added {name} ({src.stat().st_size} bytes)")

print(f"\nDone -> {OUT}  ({OUT.stat().st_size} bytes)")
