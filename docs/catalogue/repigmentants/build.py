import subprocess, sys, pathlib
import fitz  # PyMuPDF
from pypdf import PdfReader

ROOT = pathlib.Path(__file__).parent
CAT = ROOT.parents[2] / "Catalogue mylab"
V1 = CAT / "MY.LAB_catalogue_2025_V1.pdf"
SECTION = CAT / "MY.LAB_repigmentants_section.pdf"
INCI_PDF = CAT / "inci-pages.pdf"
V2 = CAT / "MY.LAB_catalogue_2026_V2.pdf"
HTML = ROOT / "index.html"
INCI_HTML = ROOT / "inci.html"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
EXPECTED_PAGES = 48

def _print_to_pdf(html, out_pdf):
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    "--virtual-time-budget=10000",
                    f"--print-to-pdf={out_pdf}", html.resolve().as_uri()],
                   check=True, timeout=120)

def render():
    _print_to_pdf(HTML, SECTION)
    r = PdfReader(str(SECTION)); b = r.pages[0].mediabox
    print(f"section: {len(r.pages)} pages, {float(b.width):.1f}x{float(b.height):.1f} pts")
    assert len(r.pages) == 3, "la section doit faire 3 pages"
    assert abs(float(b.width) - 841.9) < 3 and abs(float(b.height) - 595.3) < 3, "A4 paysage attendu"
    _print_to_pdf(INCI_HTML, INCI_PDF)
    ri = PdfReader(str(INCI_PDF))
    print(f"inci: {len(ri.pages)} pages")
    assert len(ri.pages) == 3, "inci.html doit faire 3 pages"

def merge():
    # Compression sans perte (garbage + deflate + clean). Ne PAS recompresser les images
    # via update_stream (casse colorspace/dims -> images noires).
    v1 = fitz.open(str(V1)); sec = fitz.open(str(SECTION)); inci = fitz.open(str(INCI_PDF))
    out = fitz.open()
    # --- Corps ---
    out.insert_pdf(v1, from_page=0, to_page=27)    # p1-28  : intro .. Protecteurs de couleur (produits)
    out.insert_pdf(sec)                            # Repigmentants (3 p) -> créneau color-care ; Déjaunisseurs (p29-31) retirés
    out.insert_pdf(v1, from_page=31, to_page=39)   # p32-40 : Masque Réparateur .. Gamme Homme (produits) ; Cires (p41-42) retirées
    # --- Bas de catalogue (INCI) reconstruit ---
    out.insert_pdf(inci, from_page=0, to_page=0)   # LISTE INCI (index reconstruit)
    out.insert_pdf(v1, from_page=43, to_page=45)   # p44 Nourr/Vol, p45 Liss/HA, p46 Purif/Boucles (inchangés)
    out.insert_pdf(inci, from_page=1, to_page=2)   # Protecteurs+Masque Réparateur, puis Repigmentants ; Déjaunisseur/Botox/Cires retirés
    out.insert_pdf(v1, from_page=48, to_page=48)   # p49 Gamme Homme INCI (inchangé)
    out.insert_pdf(v1, from_page=50, to_page=50)   # p51 dos / contact
    out.save(str(V2), garbage=4, deflate=True, clean=True)
    print(f"V2: {out.page_count} pages (attendu {EXPECTED_PAGES})")
    assert out.page_count == EXPECTED_PAGES
    out.close(); v1.close(); sec.close(); inci.close()

if __name__ == "__main__":
    render()
    if "--merge" in sys.argv: merge()
