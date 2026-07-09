"""Search invoice PDFs for 'amandilles' or 'gilles gbia' (case-insensitive)."""
import sys
from pathlib import Path
import pypdf

FOLDER = Path(r"C:\Users\startec\Downloads\invoice_extracted")
NEEDLES = ["amandilles", "amandille", "gilles gbia", "gbia", "gilles"]

def text_of(pdf_path: Path) -> str:
    try:
        reader = pypdf.PdfReader(str(pdf_path))
        out = []
        for p in reader.pages:
            try:
                out.append(p.extract_text() or "")
            except Exception:
                pass
        return "\n".join(out)
    except Exception as e:
        return f"__ERR__: {e}"

matches = []
errors = []
for pdf in sorted(FOLDER.glob("*.pdf")):
    txt = text_of(pdf)
    if txt.startswith("__ERR__"):
        errors.append((pdf.name, txt))
        continue
    low = txt.lower()
    hits = [n for n in NEEDLES if n in low]
    if hits:
        matches.append((pdf.name, hits, txt))

print(f"Scanned {len(list(FOLDER.glob('*.pdf')))} PDFs")
print(f"Matches: {len(matches)}\n")
for name, hits, txt in matches:
    print("=" * 70)
    print(f"FILE: {name}")
    print(f"HITS: {hits}")
    # find context around first hit
    low = txt.lower()
    for n in hits:
        idx = low.find(n)
        if idx >= 0:
            start = max(0, idx - 120)
            end = min(len(txt), idx + 200)
            print(f"  ...{txt[start:end]}...")
            break
    print()

if errors:
    print("\nERRORS:")
    for n, e in errors[:10]:
        print(f"  {n}: {e}")
