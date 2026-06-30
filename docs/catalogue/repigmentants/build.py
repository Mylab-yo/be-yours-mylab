import subprocess, sys, pathlib
from pypdf import PdfReader, PdfWriter

ROOT = pathlib.Path(__file__).parent
CAT = ROOT.parents[2] / "Catalogue mylab"
V1 = CAT / "MY.LAB_catalogue_2025_V1.pdf"
SECTION = CAT / "MY.LAB_repigmentants_section.pdf"
V2 = CAT / "MY.LAB_catalogue_2025_V2.pdf"
HTML = ROOT / "index.html"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
INSERT_AFTER_PAGE = 31  # 1-based, confirmé Task 1 (p.31 = dernière page Déjaunisseurs)

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
    v1 = PdfReader(str(V1)); sec = PdfReader(str(SECTION)); w = PdfWriter()
    for p in v1.pages[:INSERT_AFTER_PAGE]: w.add_page(p)
    for p in sec.pages: w.add_page(p)
    for p in v1.pages[INSERT_AFTER_PAGE:]: w.add_page(p)
    with open(V2, "wb") as f: w.write(f)
    total = len(v1.pages) + len(sec.pages)
    out = PdfReader(str(V2))
    print(f"V2: {len(out.pages)} pages (attendu {total})")
    assert len(out.pages) == total

if __name__ == "__main__":
    render()
    if "--merge" in sys.argv: merge()
