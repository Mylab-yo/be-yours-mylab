"""Cross-reference EBP net margin (per article, total period) with WP sales units (per product).
Bucket by format (ml) and output the final viability table.
"""
import re
from pathlib import Path
import pandas as pd

EBP_PATH = Path(r"C:/Users/startec/Downloads/évolution de la marge nette ebp.xls")
WP_PATH = Path(r"C:/Users/startec/Downloads/wp_sales_analysis.xlsx")
OUT_PATH = Path(r"C:/Users/startec/Downloads/croisement_ebp_wp_marge_format.xlsx")

# === 1. Read EBP cross-tab and extract article-level total margin ===
raw = pd.read_excel(EBP_PATH, engine="xlrd", header=None)
print(f"EBP raw: {raw.shape}")

# Identify article rows: col 3 (Code article) starts with 'AR'
mask = raw[3].astype(str).str.startswith("AR", na=False)
ebp = raw[mask].copy()
ebp = ebp[[0, 1, 2, 3, 25]].rename(columns={
    0: "famille",
    1: "code_famille",
    2: "libelle",
    3: "sku",
    25: "marge_nette_total_eur",
})
# Forward-fill famille (only first row of each family has the name)
ebp["famille"] = ebp["famille"].ffill()
ebp["code_famille"] = ebp["code_famille"].ffill()
ebp["marge_nette_total_eur"] = pd.to_numeric(ebp["marge_nette_total_eur"], errors="coerce")
print(f"EBP article rows: {len(ebp)}")
print(f"Total margin EBP: {ebp['marge_nette_total_eur'].sum():,.2f} EUR")

# === 2. Format detection on EBP labels ===
RE_ML = re.compile(r"(\d{2,4})\s*ML", re.IGNORECASE)
RE_PACK = re.compile(r"X\s*(\d+)\b", re.IGNORECASE)


def detect_format(name: str) -> str:
    if not isinstance(name, str):
        return "-"
    m = RE_ML.search(name)
    if m:
        return f"{int(m.group(1))}ml"
    return "-"


def detect_pack(name: str) -> int | None:
    if not isinstance(name, str):
        return None
    m = RE_PACK.search(name)
    if m:
        return int(m.group(1))
    return None


ebp["format_ml"] = ebp["libelle"].apply(detect_format)
ebp["pack_size"] = ebp["libelle"].apply(detect_pack)

# === 3. EBP margin grouped by format ===
ebp_by_format = ebp.groupby("format_ml").agg(
    nb_refs_ebp=("sku", "nunique"),
    marge_nette_eur=("marge_nette_total_eur", "sum"),
    marge_moyenne_par_ref=("marge_nette_total_eur", "mean"),
).round(2).reset_index()

# === 4. Read WP sales by format (we computed this earlier) ===
wp_by_format = pd.read_excel(WP_PATH, sheet_name="Par format")

# === 5. Cross-reference ===
cross = wp_by_format.merge(ebp_by_format, on="format_ml", how="outer")
# Compute key business metrics
cross["marge_par_unite_eur"] = (cross["marge_nette_eur"] / cross["units"]).round(2)
cross["marge_par_ref_par_mois"] = (cross["marge_nette_eur"] / cross["nb_refs_ebp"] / 16).round(2)
cross["ca_par_marge_ratio"] = (cross["marge_nette_eur"] / cross["ca_ttc"] * 100).round(1)

# Sort by format size
def fmt_sort(s):
    if s == "-" or pd.isna(s):
        return 99999
    try:
        return int(str(s).replace("ml", ""))
    except:
        return 99998


cross["_s"] = cross["format_ml"].apply(fmt_sort)
cross = cross.sort_values("_s").drop(columns="_s")
ebp_by_format["_s"] = ebp_by_format["format_ml"].apply(fmt_sort)
ebp_by_format = ebp_by_format.sort_values("_s").drop(columns="_s")

print("\n=== EBP MARGE NETTE PAR FORMAT ===")
print(ebp_by_format.to_string(index=False))

print("\n=== CROISEMENT FINAL (WP units x EBP marge) ===")
cols = ["format_ml", "nb_refs_ebp", "units", "ca_ttc",
        "marge_nette_eur", "marge_par_unite_eur", "ca_par_marge_ratio",
        "marge_par_ref_par_mois"]
print(cross[cols].to_string(index=False))

# === 6. Per-article (with sales) detail for 400ml and 500ml specifically ===
focus = ebp[ebp["format_ml"].isin(["400ml", "500ml"])].copy()
focus = focus.sort_values(["format_ml", "marge_nette_total_eur"], ascending=[True, False])

print("\n=== DETAIL 400ml + 500ml (par article EBP) ===")
print(focus[["sku", "libelle", "format_ml", "pack_size", "marge_nette_total_eur"]].to_string(index=False))

# === 7. Write Excel ===
with pd.ExcelWriter(OUT_PATH, engine="openpyxl") as xl:
    cross[cols].to_excel(xl, sheet_name="Croisement par format", index=False)
    ebp_by_format.to_excel(xl, sheet_name="EBP marge par format", index=False)
    ebp.sort_values("marge_nette_total_eur", ascending=False).to_excel(
        xl, sheet_name="EBP articles details", index=False)
    focus.to_excel(xl, sheet_name="Focus 400ml & 500ml", index=False)

print(f"\nOutput: {OUT_PATH}")
