"""V2 - Cross-reference EBP × WP at the PRODUCT level (consolidating pack sizes).

Strategy:
- EBP: aggregate margins across all pack sizes per (product_family, format_ml)
- WP : aggregate sales across all pack variants per (product_family, format_ml)
- Join on (name_key, ml)
"""
import re
import unicodedata
from pathlib import Path
import pandas as pd

EBP_PATH = Path(r"C:/Users/startec/Downloads/évolution de la marge nette ebp.xls")
WP_PATH = Path(r"C:/Users/startec/Downloads/wp_sales_analysis.xlsx")
OUT_PATH = Path(r"C:/Users/startec/Downloads/croisement_v2_ebp_wp.xlsx")


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def normalize_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    n = strip_accents(name).upper()
    n = re.sub(r"^MYLAB\s+", "", n)
    n = re.sub(r"[-\s]+\d{2,4}\s*ML(\s*X\s*\d+)?\s*$", "", n)
    n = re.sub(r"\s+X\s*\d+\s*$", "", n)
    n = re.sub(r"[^A-Z0-9 ]", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


RE_ML = re.compile(r"(\d{2,4})\s*ML", re.IGNORECASE)
RE_PACK = re.compile(r"X\s*(\d+)\b", re.IGNORECASE)


def detect_ml(name):
    if not isinstance(name, str):
        return None
    m = RE_ML.search(name)
    return int(m.group(1)) if m else None


def detect_pack(name):
    if not isinstance(name, str):
        return None
    m = RE_PACK.search(name)
    return int(m.group(1)) if m else None


# === 1. Read EBP ===
raw = pd.read_excel(EBP_PATH, engine="xlrd", header=None)
mask = raw[3].astype(str).str.startswith("AR", na=False)
ebp = raw[mask].copy()
ebp = ebp[[0, 1, 2, 3, 25]].rename(columns={
    0: "famille", 1: "code_famille", 2: "libelle", 3: "sku", 25: "marge_nette_eur",
})
ebp["famille"] = ebp["famille"].ffill()
ebp["code_famille"] = ebp["code_famille"].ffill()
ebp["marge_nette_eur"] = pd.to_numeric(ebp["marge_nette_eur"], errors="coerce")
ebp["ml"] = ebp["libelle"].apply(detect_ml)
ebp["pack_size"] = ebp["libelle"].apply(detect_pack)
ebp["name_key"] = ebp["libelle"].apply(normalize_name)
ebp["format_ml"] = ebp["ml"].apply(lambda x: f"{int(x)}ml" if pd.notna(x) else "-")

print(f"EBP articles: {len(ebp)}")
print(f"EBP marge nette totale: {ebp['marge_nette_eur'].sum():,.2f} EUR")

# Aggregate EBP per (name_key, ml) — sum margins across pack variants
ebp_consol = ebp.groupby(["name_key", "ml", "format_ml"], dropna=False).agg(
    nb_sku_ebp=("sku", "nunique"),
    skus=("sku", lambda x: ", ".join(sorted(x.unique()))),
    libelles_ebp=("libelle", lambda x: " | ".join(sorted(x.unique()))),
    marge_nette_eur=("marge_nette_eur", "sum"),
    famille=("famille", "first"),
).reset_index()
print(f"EBP consolidated (name+format): {len(ebp_consol)}")

# === 2. Read WP raw lines ===
wp = pd.read_excel(WP_PATH, sheet_name="Lignes brutes")
print(f"\nWP raw lines: {len(wp)}")
wp["name_key"] = wp["product_name"].apply(normalize_name)
wp["ml_int"] = wp["ml"].apply(lambda x: int(x) if pd.notna(x) else None).astype("Int64")

wp_consol = wp.groupby(["name_key", "ml_int"], dropna=False).agg(
    nb_commandes_wp=("invoice_no", "nunique"),
    packs_vendus_wp=("qty", "sum"),
    units_total_wp=("units_total", "sum"),
    ca_ttc_wp=("total_price_ttc", "sum"),
    nom_wp=("product_name", "first"),
).reset_index().rename(columns={"ml_int": "ml"})
print(f"WP consolidated: {len(wp_consol)}")

# === 3. JOIN at product level ===
wp_consol["ml"] = wp_consol["ml"].astype("Int64")
ebp_consol["ml"] = ebp_consol["ml"].astype("Int64")

merged = ebp_consol.merge(wp_consol, on=["name_key", "ml"], how="outer", indicator=True)

# Compute metrics
merged["marge_par_unite_eur"] = (merged["marge_nette_eur"] / merged["units_total_wp"]).round(2)
merged["taux_marge_pct"] = (merged["marge_nette_eur"] / merged["ca_ttc_wp"] * 100).round(1)
merged["ca_par_unite_eur"] = (merged["ca_ttc_wp"] / merged["units_total_wp"]).round(2)

# Fill format_ml for WP-only rows
merged["format_ml"] = merged["format_ml"].fillna(
    merged["ml"].apply(lambda x: f"{int(x)}ml" if pd.notna(x) else "-")
)

print(f"\n=== STATS DE MATCH ===")
for status in ["both", "left_only", "right_only"]:
    sub = merged[merged["_merge"] == status]
    marge = sub["marge_nette_eur"].sum() if "marge_nette_eur" in sub.columns else 0
    ca = sub["ca_ttc_wp"].sum() if "ca_ttc_wp" in sub.columns else 0
    print(f"  {status:12s}: {len(sub):4d} produits, marge EBP={marge:>11,.0f}EUR, CA WP={ca:>11,.0f}EUR")

# === 4. Aggregation par format (matched only) ===
matched = merged[merged["_merge"] == "both"].copy()
by_format = matched.groupby("format_ml").agg(
    nb_produits=("name_key", "count"),
    nb_sku_ebp=("nb_sku_ebp", "sum"),
    units_wp=("units_total_wp", "sum"),
    ca_wp=("ca_ttc_wp", "sum"),
    marge_ebp=("marge_nette_eur", "sum"),
).reset_index()
by_format["marge_par_unite"] = (by_format["marge_ebp"] / by_format["units_wp"]).round(2)
by_format["taux_marge_pct"] = (by_format["marge_ebp"] / by_format["ca_wp"] * 100).round(1)


def fmt_sort(s):
    if s in (None, "", "-") or pd.isna(s):
        return 99999
    try:
        return int(str(s).replace("ml", ""))
    except:
        return 99998


by_format["_s"] = by_format["format_ml"].apply(fmt_sort)
by_format = by_format.sort_values("_s").drop(columns="_s")

print(f"\n=== AGREGATION PAR FORMAT (produits matchés) ===")
print(by_format.to_string(index=False))

# === 5. EBP-only (no WP sales) and WP-only (no EBP record) summaries ===
ebp_only = merged[merged["_merge"] == "left_only"].copy()
ebp_only_by_format = ebp_only.groupby("format_ml").agg(
    nb_produits=("name_key", "count"),
    marge=("marge_nette_eur", "sum"),
).reset_index().sort_values("marge", ascending=False)

wp_only = merged[merged["_merge"] == "right_only"].copy()
wp_only_by_format = wp_only.groupby("format_ml").agg(
    nb_produits=("name_key", "count"),
    units=("units_total_wp", "sum"),
    ca=("ca_ttc_wp", "sum"),
).reset_index().sort_values("ca", ascending=False)

print(f"\n=== EBP-only (vendus B2B hors WP) par format ===")
print(ebp_only_by_format.to_string(index=False))
print(f"\n=== WP-only (vendus WP sans match EBP) par format ===")
print(wp_only_by_format.to_string(index=False))

# === 6. Sort matched products for detail view ===
matched_sorted = matched.sort_values("marge_nette_eur", ascending=False)

# Top winners
print(f"\n=== TOP 15 PRODUITS PAR MARGE (matchés) ===")
top = matched_sorted.head(15)[[
    "name_key", "format_ml", "nb_sku_ebp", "units_total_wp", "ca_ttc_wp",
    "marge_nette_eur", "marge_par_unite_eur", "taux_marge_pct"
]]
print(top.to_string(index=False))

# Bleeders
print(f"\n=== PRODUITS A MARGE NEGATIVE (matchés) ===")
losers = matched[matched["marge_nette_eur"] < 0].sort_values("marge_nette_eur")
print(losers[[
    "name_key", "format_ml", "skus", "units_total_wp", "ca_ttc_wp",
    "marge_nette_eur", "marge_par_unite_eur"
]].to_string(index=False))

# === 7. Write Excel ===
with pd.ExcelWriter(OUT_PATH, engine="openpyxl") as xl:
    by_format.to_excel(xl, sheet_name="Synthese par format", index=False)
    matched_sorted.to_excel(xl, sheet_name="Produits matches (detail)", index=False)
    losers.to_excel(xl, sheet_name="Produits a marge negative", index=False)
    ebp_only.sort_values("marge_nette_eur", ascending=False).to_excel(
        xl, sheet_name="EBP only (B2B hors WP)", index=False)
    wp_only.sort_values("ca_ttc_wp", ascending=False).to_excel(
        xl, sheet_name="WP only (non match EBP)", index=False)
    ebp_only_by_format.to_excel(xl, sheet_name="EBP only par format", index=False)
    wp_only_by_format.to_excel(xl, sheet_name="WP only par format", index=False)

print(f"\nOutput: {OUT_PATH}")
