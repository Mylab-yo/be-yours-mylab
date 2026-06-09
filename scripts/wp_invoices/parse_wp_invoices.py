"""Parse all WP/WooCommerce invoice PDFs and aggregate sales by product/format.

Input  : C:/Users/startec/Downloads/invoice_extracted/*.pdf (825 PDFs)
Output : C:/Users/startec/Downloads/wp_sales_analysis.xlsx
         - Sheet "Lignes brutes"    : every line item parsed
         - Sheet "Par produit"      : aggregate by full product name
         - Sheet "Par format"       : aggregate by ml format
         - Sheet "Par produit_format": product x format breakdown
         - Sheet "Erreurs"          : unparseable lines for review
"""
import os
import re
from datetime import datetime
from pathlib import Path

import pdfplumber
import pandas as pd

INVOICE_DIR = Path(r"C:/Users/startec/Downloads/invoice_extracted")
OUTPUT_XLSX = Path(r"C:/Users/startec/Downloads/wp_sales_analysis.xlsx")

# Line item regexes
# Format 1: "Product Name - 200 ml x 6  1  45,00€"
RE_WITH_FORMAT = re.compile(
    r"^(?P<name>.+?)\s*-\s*(?P<ml>\d+(?:[.,]\d+)?)\s*ml\s*x\s*(?P<pack>\d+)\s+(?P<qty>\d+)\s+(?P<price>[\d\s.,]+)€\s*$"
)
# Format 2: "Product Name  1  5,00€" (testeurs, coffrets, frais, etc.)
RE_NO_FORMAT = re.compile(
    r"^(?P<name>.+?)\s+(?P<qty>\d+)\s+(?P<price>[\d\s.,]+)€\s*$"
)

RE_INVOICE_NO = re.compile(r"N°?\s*de\s*facture\s*:\s*(MYLAB\d+)", re.IGNORECASE)
RE_DATE = re.compile(r"Date\s*de\s*facture\s*:\s*([\d]{1,2}\s+\w+\s+\d{4})", re.IGNORECASE)

FRENCH_MONTHS = {
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "août": 8, "aout": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12,
}

# Lines to skip when scanning product block
SKIP_PREFIXES = ("Poids :", "Poids:", "Quantité:", "Quantite:", "Quantité :", "Produits", "Sous-total")
# Lines that match a product-ish pattern but are addons we don't count as products
ADDON_KEYWORDS = ("Ajoutez des pompes", "Ajouter des pompes", "Frais de port", "Forfait")


def parse_price(s: str) -> float:
    """'1 234,56' or '364,80' -> 1234.56"""
    s = s.replace(" ", " ").replace(" ", "").replace(",", ".")
    return float(s)


def parse_date(s: str):
    m = re.match(r"(\d{1,2})\s+(\w+)\s+(\d{4})", s)
    if not m:
        return None
    d, mon, y = m.groups()
    mon_lc = mon.lower().replace("ç", "c").replace("é", "e").replace("û", "u").replace("â", "a")
    if mon_lc in FRENCH_MONTHS:
        return datetime(int(y), FRENCH_MONTHS[mon_lc], int(d)).date()
    # Try with original case for mojibake
    for k, v in FRENCH_MONTHS.items():
        if mon_lc.startswith(k[:3]):
            return datetime(int(y), v, int(d)).date()
    return None


def parse_invoice(pdf_path: Path):
    """Return dict with invoice_no, date, lines:list[dict]."""
    invoice_no = pdf_path.stem.replace("facture-", "")
    date = None
    lines = []
    errors = []

    with pdfplumber.open(pdf_path) as pdf:
        all_text = []
        for page in pdf.pages:
            t = page.extract_text() or ""
            all_text.append(t)
        full = "\n".join(all_text)

    # Extract metadata
    m_no = RE_INVOICE_NO.search(full)
    if m_no:
        invoice_no = m_no.group(1)
    m_d = RE_DATE.search(full)
    if m_d:
        date = parse_date(m_d.group(1))

    # Parse line items: find blocks between "Produits Quantité Prix" and "Sous-total"
    # On multi-page invoices, "Produits" header may repeat - process each block
    blocks = []
    for chunk in re.split(r"Produits\s+Quantit[ée]?\s*\W*\s+Prix", full):
        if "Sous-total" in chunk:
            block = chunk.split("Sous-total")[0]
            blocks.append(block)
        elif chunk.strip() and not chunk.startswith(full[:50]):
            # Continuation page where Sous-total may not appear on every page
            blocks.append(chunk)

    for block in blocks:
        for raw_line in block.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if any(line.startswith(p) for p in SKIP_PREFIXES):
                continue
            # Skip lines that don't have € (not a product line)
            if "€" not in line:
                continue
            # Skip addons (pompes, frais, forfaits) — not actual products
            if any(kw in line for kw in ADDON_KEYWORDS):
                continue

            m1 = RE_WITH_FORMAT.match(line)
            if m1:
                lines.append({
                    "invoice_no": invoice_no,
                    "date": date,
                    "product_name": m1.group("name").strip(),
                    "ml": parse_price(m1.group("ml")),
                    "pack_size": int(m1.group("pack")),
                    "qty": int(m1.group("qty")),
                    "total_price_ttc": parse_price(m1.group("price")),
                    "has_format": True,
                })
                continue

            m2 = RE_NO_FORMAT.match(line)
            if m2:
                lines.append({
                    "invoice_no": invoice_no,
                    "date": date,
                    "product_name": m2.group("name").strip(),
                    "ml": None,
                    "pack_size": None,
                    "qty": int(m2.group("qty")),
                    "total_price_ttc": parse_price(m2.group("price")),
                    "has_format": False,
                })
                continue

            errors.append({"invoice_no": invoice_no, "raw_line": line})

    return lines, errors


def main():
    pdfs = sorted(INVOICE_DIR.glob("*.pdf"))
    print(f"Found {len(pdfs)} PDFs in {INVOICE_DIR}")

    all_lines = []
    all_errors = []
    for i, p in enumerate(pdfs, 1):
        try:
            lines, errors = parse_invoice(p)
            all_lines.extend(lines)
            all_errors.extend(errors)
        except Exception as e:
            all_errors.append({"invoice_no": p.stem, "raw_line": f"EXCEPTION: {e}"})
        if i % 50 == 0 or i == len(pdfs):
            print(f"  {i}/{len(pdfs)} processed, {len(all_lines)} lines, {len(all_errors)} errors")

    df = pd.DataFrame(all_lines)
    df_err = pd.DataFrame(all_errors)

    print(f"\nTotal lines: {len(df)}")
    print(f"Total errors: {len(df_err)}")
    if len(df):
        dates_valid = df["date"].dropna()
        if len(dates_valid):
            print(f"Date range: {dates_valid.min()} -> {dates_valid.max()}")
        print(f"Total CA TTC: {df['total_price_ttc'].sum():,.2f}€")

    # Derive useful columns
    if len(df):
        # Total units = qty * pack_size (for formatted products), else qty
        df["units_total"] = df.apply(
            lambda r: (r["qty"] * r["pack_size"]) if pd.notna(r["pack_size"]) else r["qty"], axis=1
        )
        # Format bucket (200ml/500ml/etc) — None for testeurs/kits
        df["format_ml"] = df["ml"].apply(lambda x: f"{int(x)}ml" if pd.notna(x) else "—")
        # Family name (strip the volume suffix already done in parser via name capture)
        df["product_family"] = df["product_name"]

    # Aggregations
    # 1. By product name + format
    if len(df):
        by_product_format = df.groupby(["product_family", "format_ml"], dropna=False).agg(
            commandes=("invoice_no", "nunique"),
            packs=("qty", "sum"),
            units=("units_total", "sum"),
            ca_ttc=("total_price_ttc", "sum"),
        ).reset_index().sort_values("ca_ttc", ascending=False)

        by_format = df.groupby("format_ml").agg(
            commandes=("invoice_no", "nunique"),
            packs=("qty", "sum"),
            units=("units_total", "sum"),
            ca_ttc=("total_price_ttc", "sum"),
            nb_references=("product_family", "nunique"),
        ).reset_index().sort_values("ca_ttc", ascending=False)

        by_product = df.groupby("product_family").agg(
            commandes=("invoice_no", "nunique"),
            packs=("qty", "sum"),
            units=("units_total", "sum"),
            ca_ttc=("total_price_ttc", "sum"),
        ).reset_index().sort_values("ca_ttc", ascending=False)
    else:
        by_product_format = by_format = by_product = pd.DataFrame()

    # Write Excel
    with pd.ExcelWriter(OUTPUT_XLSX, engine="openpyxl") as xl:
        df.to_excel(xl, sheet_name="Lignes brutes", index=False)
        by_format.to_excel(xl, sheet_name="Par format", index=False)
        by_product.to_excel(xl, sheet_name="Par produit", index=False)
        by_product_format.to_excel(xl, sheet_name="Par produit_format", index=False)
        df_err.to_excel(xl, sheet_name="Erreurs", index=False)

    print(f"\n✓ Output: {OUTPUT_XLSX}")
    if len(df):
        print("\n=== TOP par format ===")
        print(by_format.to_string(index=False))


if __name__ == "__main__":
    main()
