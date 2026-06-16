"""Cross-reference EBP (margin per SKU) with WP (units sold per product/format/pack).

Produces an article-level view that combines:
- WP : units sold, CA TTC (16 mois of WooCommerce invoices)
- EBP: marge nette EUR (16 mois of accounting data)

Matching strategy: normalize article name + format + pack size on both sides.
"""
import re
import unicodedata
from pathlib import Path
import pandas as pd

EBP_PATH = Path(r"C:/Users/startec/Downloads/évolution de la marge nette ebp.xls")
WP_PATH = Path(r"C:/Users/startec/Downloads/wp_sales_analysis.xlsx")
OUT_PATH = Path(r"C:/Users/startec/Downloads/croisement_complet_ebp_wp.xlsx")


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def normalize_name(name: str, ml: float | None = None, pack: int | None = None) -> str:
    """Normalize an article name to a join key:
    - uppercase, strip accents
    - remove the format/pack suffix
    - remove punctuation/extra spaces
    """
    if not isinstance(name, str):
        return ""
    n = strip_accents(name).upper()
    # Remove "MYLAB " prefix if any
    n = re.sub(r"^MYLAB\s+", "", n)
    # Remove "- 200 ML X 6" or "200ML X6" suffixes
    n = re.sub(r"[-\s]+\d{2,4}\s*ML(\s*X\s*\d+)?\s*$", "", n)
    # Strip any standalone "X 6" / "X12" at end
    n = re.sub(r"\s+X\s*\d+\s*$", "", n)
    # Collapse spaces, strip punctuation we don't care about
    n = re.sub(r"[^A-Z0-9 ]", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


# === 1. Read EBP article-level data ===
raw = pd.read_excel(EBP_PATH, engine="xlrd", header=None)
mask = raw[3].astype(str).str.startswith("AR", na=False)
ebp = raw[mask].copy()
ebp = ebp[[0, 1, 2, 3, 25]].rename(columns={
    0: "famille", 1: "code_famille", 2: "libelle", 3: "sku", 25: "marge_nette_eur",
})
ebp["famille"] = ebp["famille"].ffill()
ebp["code_famille"] = ebp["code_famille"].ffill()
ebp["marge_nette_eur"] = pd.to_numeric(ebp["marge_nette_eur"], errors="coerce")

# Detect format + pack from EBP name
RE_ML = re.compile(r"(\d{2,4})\s*ML", re.IGNORECASE)
RE_PACK = re.compile(r"X\s*(\d+)\b", re.IGNORECASE)


def ebp_format(name):
    if not isinstance(name, str):
        return None
    m = RE_ML.search(name)
    return int(m.group(1)) if m else None


def ebp_pack(name):
    if not isinstance(name, str):
        return None
    m = RE_PACK.search(name)
    return int(m.group(1)) if m else None


ebp["ml"] = ebp["libelle"].apply(ebp_format)
ebp["pack_size"] = ebp["libelle"].apply(ebp_pack)
ebp["name_key"] = ebp["libelle"].apply(normalize_name)
ebp["format_ml"] = ebp["ml"].apply(lambda x: f"{int(x)}ml" if pd.notna(x) else "-")

print(f"EBP articles: {len(ebp)}")
print(f"EBP marge nette totale: {ebp['marge_nette_eur'].sum():,.2f} EUR")

# === 2. Read WP raw line items and aggregate per article ===
wp = pd.read_excel(WP_PATH, sheet_name="Lignes brutes")
print(f"\nWP raw lines: {len(wp)}")

wp["name_key"] = wp.apply(lambda r: normalize_name(r["product_name"]), axis=1)
wp["ml"] = wp["ml"].astype("Int64")
wp["pack_size_int"] = wp["pack_size"].astype("Int64")

# Aggregate per (name_key, ml, pack)
wp_agg = wp.groupby(["name_key", "ml", "pack_size_int"], dropna=False).agg(
    nb_commandes=("invoice_no", "nunique"),
    packs_vendus=("qty", "sum"),
    units_total=("units_total", "sum"),
    ca_ttc=("total_price_ttc", "sum"),
    nom_wp_exemple=("product_name", "first"),
).reset_index().rename(columns={"pack_size_int": "pack_size"})
print(f"WP aggregated rows: {len(wp_agg)}")

# === 3. JOIN ===
# Strategy: match on (name_key, ml, pack) → if no match drop pack → if still no match drop ml
ebp_match = ebp.copy()
ebp_match["pack_size"] = ebp_match["pack_size"].astype("Int64")
ebp_match["ml"] = ebp_match["ml"].astype("Int64")

merged_full = ebp_match.merge(
    wp_agg, on=["name_key", "ml", "pack_size"], how="outer", indicator=True
)
print(f"\nJoin results:")
print(merged_full["_merge"].value_counts())

# Compute key metrics where we have both
m = merged_full.copy()
m["marge_par_unite_eur"] = (m["marge_nette_eur"] / m["units_total"]).round(2)
m["marge_par_pack_eur"] = (m["marge_nette_eur"] / m["packs_vendus"]).round(2)
m["taux_marge_pct"] = (m["marge_nette_eur"] / m["ca_ttc"] * 100).round(1)
m["ca_par_unite_eur"] = (m["ca_ttc"] / m["units_total"]).round(2)

# Reorder & rename for readability
out_cols = [
    "sku", "libelle", "famille", "format_ml", "pack_size",
    "units_total", "packs_vendus", "nb_commandes",
    "ca_ttc", "marge_nette_eur",
    "marge_par_unite_eur", "marge_par_pack_eur", "taux_marge_pct",
    "ca_par_unite_eur", "nom_wp_exemple", "_merge",
]
result = m[out_cols].rename(columns={"_merge": "match_status"})

# Sort by marge desc (matched ones at top)
result_sorted = result.sort_values(
    by=["match_status", "marge_nette_eur"],
    ascending=[True, False],
    key=lambda c: c if c.name != "match_status" else c.astype(str)
)

# Stats by match status
print(f"\n=== STATS PAR STATUT DE MATCH ===")
for status in ["both", "left_only", "right_only"]:
    sub = result[result["match_status"] == status]
    print(f"  {status:12s}: {len(sub):4d} lignes, marge={sub['marge_nette_eur'].sum() or 0:,.0f}EUR, CA={sub['ca_ttc'].sum() or 0:,.0f}EUR")

# Aggregate by format for the matched articles
matched = result[result["match_status"] == "both"].copy()
by_format_full = matched.groupby("format_ml").agg(
    nb_articles=("sku", "count"),
    units=("units_total", "sum"),
    ca_ttc=("ca_ttc", "sum"),
    marge_nette=("marge_nette_eur", "sum"),
).reset_index()
by_format_full["marge_par_unite"] = (by_format_full["marge_nette"] / by_format_full["units"]).round(2)
by_format_full["taux_marge_pct"] = (by_format_full["marge_nette"] / by_format_full["ca_ttc"] * 100).round(1)
by_format_full = by_format_full.sort_values("marge_nette", ascending=False)

print(f"\n=== AGREGATION PAR FORMAT (articles matchés uniquement) ===")
print(by_format_full.to_string(index=False))

# Top opportunites: articles très rentables sous-vendus
matched_sorted = matched[matched["units_total"] > 0].copy()
matched_sorted["score_opportunite"] = (matched_sorted["marge_par_unite_eur"] / matched_sorted["units_total"] * 1000).round(2)

print(f"\n=== TOP 10 ARTICLES À PROMOUVOIR (forte marge/unité, faibles ventes) ===")
opportunity = matched_sorted[
    (matched_sorted["marge_par_unite_eur"] > 5) &
    (matched_sorted["units_total"] < 200)
].sort_values("marge_par_unite_eur", ascending=False).head(10)
print(opportunity[["sku", "libelle", "format_ml", "units_total", "marge_par_unite_eur", "taux_marge_pct"]].to_string(index=False))

print(f"\n=== TOP 10 ARTICLES À RATIONALISER (faibles marge sur 16 mois) ===")
rationalize = matched[
    (matched["marge_nette_eur"] < 100) & (matched["marge_nette_eur"].notna())
].sort_values("marge_nette_eur").head(10)
print(rationalize[["sku", "libelle", "format_ml", "units_total", "marge_nette_eur", "taux_marge_pct"]].to_string(index=False))

# === 4. Write Excel ===
with pd.ExcelWriter(OUT_PATH, engine="openpyxl") as xl:
    by_format_full.to_excel(xl, sheet_name="Vue globale par format", index=False)
    result_sorted.to_excel(xl, sheet_name="Article par article", index=False)
    matched.sort_values("marge_nette_eur", ascending=False).to_excel(xl, sheet_name="Articles matchés", index=False)
    result[result["match_status"] == "left_only"].sort_values("marge_nette_eur", ascending=False).to_excel(
        xl, sheet_name="EBP sans match WP", index=False)
    result[result["match_status"] == "right_only"].to_excel(
        xl, sheet_name="WP sans match EBP", index=False)
    opportunity.to_excel(xl, sheet_name="À promouvoir", index=False)
    rationalize.to_excel(xl, sheet_name="À rationaliser", index=False)

print(f"\nOutput: {OUT_PATH}")
