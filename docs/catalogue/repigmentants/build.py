import subprocess, sys, pathlib
import fitz  # PyMuPDF
from pypdf import PdfReader

ROOT = pathlib.Path(__file__).parent
CAT = ROOT.parents[2] / "Catalogue mylab"
V1 = CAT / "MY.LAB_catalogue_2025_V1.pdf"
SECTION = CAT / "MY.LAB_repigmentants_section.pdf"
V2 = CAT / "MY.LAB_catalogue_2025_V2.pdf"
HTML = ROOT / "index.html"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# Assemblage V2 (indices V1 0-based, V1 = 51 pages) :
#   - 0..27  : pages 1-28  (intro + gammes jusqu'aux Protecteurs de couleur)
#   - section: 3 pages Repigmentants (prend le créneau color-care)
#   - 31..39 : pages 32-40 (Masque Réparateur .. Gamme Homme)  -> Déjaunisseurs (29-31) RETIRÉS
#   - 42..50 : pages 43-51 (INCI .. dos)                       -> Cires (41-42) RETIRÉS
KEEP_BEFORE = (0, 27)
KEEP_MID = (31, 39)
KEEP_END = (42, 50)
EXPECTED_PAGES = 49

def render():
    url = HTML.resolve().as_uri()
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    "--virtual-time-budget=10000",
                    f"--print-to-pdf={SECTION}", url], check=True, timeout=120)
    r = PdfReader(str(SECTION))
    b = r.pages[0].mediabox
    print(f"section: {len(r.pages)} pages, {float(b.width):.1f}x{float(b.height):.1f} pts")
    assert len(r.pages) == 3, "la section doit faire 3 pages"
    assert abs(float(b.width) - 841.9) < 3 and abs(float(b.height) - 595.3) < 3, "A4 paysage attendu"

def merge():
    v1 = fitz.open(str(V1)); sec = fitz.open(str(SECTION)); out = fitz.open()
    out.insert_pdf(v1, from_page=KEEP_BEFORE[0], to_page=KEEP_BEFORE[1])
    out.insert_pdf(sec)
    out.insert_pdf(v1, from_page=KEEP_MID[0], to_page=KEEP_MID[1])
    out.insert_pdf(v1, from_page=KEEP_END[0], to_page=KEEP_END[1])
    out.save(str(V2), garbage=4, deflate=True, clean=True)
    print(f"V2: {out.page_count} pages (attendu {EXPECTED_PAGES})")
    assert out.page_count == EXPECTED_PAGES
    out.close(); v1.close(); sec.close()

if __name__ == "__main__":
    render()
    if "--merge" in sys.argv: merge()
