"""Comprehensive rationalization analysis: which references and formats to keep/drop.

Outputs to: C:/Users/startec/Downloads/mylab_rationalisation_analyse.xlsx
"""
import re
from pathlib import Path
import pandas as pd

WP_PATH = Path(r"C:/Users/startec/Downloads/wp_sales_analysis.xlsx")
OUT = Path(r"C:/Users/startec/Downloads/mylab_rationalisation_analyse.xlsx")


def base_name(n):
    return re.sub(r"\s*-?\s*\d+\s*ml.*$", "", str(n), flags=re.IGNORECASE).strip()


wp = pd.read_excel(WP_PATH, sheet_name="Lignes brutes")
TOTAL_TTC = wp["total_price_ttc"].sum()
N_MONTHS = 16
N_INVOICES = wp["invoice_no"].nunique()

print(f"Periode: 16 mois (2025-01 -> 2026-05)")
print(f"CA total TTC: {TOTAL_TTC:,.0f} EUR / {N_INVOICES} commandes")

# === Aggregate per product (consolidate pack variants, keep format) ===
wp["family"] = wp["product_name"].apply(base_name)
wp["format_ml"] = wp["ml"].apply(lambda x: f"{int(x)}ml" if pd.notna(x) else "Sans format")

per_product = wp.groupby(["family", "format_ml"]).agg(
    units=("units_total", "sum"),
    ca_ttc=("total_price_ttc", "sum"),
    nb_commandes=("invoice_no", "nunique"),
    first_date=("date", "min"),
    last_date=("date", "max"),
).reset_index()
per_product["ca_par_mois"] = (per_product["ca_ttc"] / N_MONTHS).round(2)
per_product["pct_ca"] = (per_product["ca_ttc"] / TOTAL_TTC * 100).round(2)
per_product = per_product.sort_values("ca_ttc", ascending=False).reset_index(drop=True)
per_product["rang"] = per_product.index + 1
per_product["cumul_pct"] = per_product["pct_ca"].cumsum().round(1)

print(f"\nTotal references (family x format): {len(per_product)}")

# === PARETO ===
print(f"\n=== PARETO ===")
n_ref = len(per_product)
for pct_threshold in [50, 70, 80, 90, 95, 99]:
    n_refs_to_reach = (per_product["cumul_pct"] <= pct_threshold).sum() + 1
    ratio = n_refs_to_reach / n_ref * 100
    print(f"  {pct_threshold}% du CA = top {n_refs_to_reach} refs ({ratio:.0f}% des refs)")

# === SEUIL DE VIABILITE ===
# Une reference qui fait moins de X EUR/mois est candidate a la suppression
print(f"\n=== SEUILS DE VIABILITE (CA/mois) ===")
for threshold in [200, 100, 50, 25, 10, 0]:
    n_under = (per_product["ca_par_mois"] <= threshold).sum()
    ca_under = per_product[per_product["ca_par_mois"] <= threshold]["ca_ttc"].sum()
    pct = ca_under / TOTAL_TTC * 100
    print(f"  Refs <= {threshold:3d} EUR/mois : {n_under:3d} refs ({n_under/n_ref*100:.0f}%) = {ca_under:>8,.0f} EUR ({pct:.1f}% du CA)")

# === SCENARIOS DE RATIONALISATION ===
print(f"\n=== SCENARIOS DE RATIONALISATION ===")
for name, threshold in [("Soft (kill < 25 EUR/mois)", 25),
                         ("Moyen (kill < 50 EUR/mois)", 50),
                         ("Strict (kill < 100 EUR/mois)", 100),
                         ("Tres strict (kill < 200 EUR/mois)", 200)]:
    keep = per_product[per_product["ca_par_mois"] > threshold]
    kill = per_product[per_product["ca_par_mois"] <= threshold]
    pct_ca_keep = keep["ca_ttc"].sum() / TOTAL_TTC * 100
    n_kill = len(kill)
    print(f"\n  {name}:")
    print(f"    Refs gardees: {len(keep)} ({len(keep)/n_ref*100:.0f}%) couvrant {pct_ca_keep:.1f}% du CA")
    print(f"    Refs supprimees: {n_kill} pour {kill['ca_ttc'].sum():,.0f} EUR ({100-pct_ca_keep:.1f}% du CA)")

# === COUVERTURE FAMILLE x FORMAT ===
print(f"\n=== COUVERTURE FAMILLE x FORMAT ===")
fam_format = wp.groupby(["family", "format_ml"]).agg(ca_ttc=("total_price_ttc", "sum")).reset_index()
matrix = fam_format.pivot(index="family", columns="format_ml", values="ca_ttc").fillna(0)
# Total per family + nb formats
matrix["TOTAL"] = matrix.sum(axis=1)
matrix["nb_formats"] = (matrix.drop(columns="TOTAL") > 0).sum(axis=1)
matrix = matrix.sort_values("TOTAL", ascending=False)
print(f"\nFamilles avec 4+ formats (candidats reduction):")
multi_fmt = matrix[matrix["nb_formats"] >= 3].copy()
print(multi_fmt[["nb_formats", "TOTAL"]].head(20).to_string())

# === PRODUITS LONG TAIL ===
print(f"\n=== LONG TAIL (refs < 50 EUR/mois sur 16 mois) ===")
tail = per_product[per_product["ca_par_mois"] < 50].copy()
tail_by_format = tail.groupby("format_ml").agg(
    nb_refs=("family", "count"),
    ca_total=("ca_ttc", "sum"),
).reset_index().sort_values("nb_refs", ascending=False)
print(tail_by_format.to_string(index=False))

# === RECO PAR FORMAT ===
print(f"\n=== ANALYSE PAR FORMAT (nb refs + concentration) ===")
fmt_analysis = []
for fmt in per_product["format_ml"].unique():
    sub = per_product[per_product["format_ml"] == fmt]
    if len(sub) == 0:
        continue
    sub_sorted = sub.sort_values("ca_ttc", ascending=False)
    top3_pct = sub_sorted.head(3)["ca_ttc"].sum() / sub["ca_ttc"].sum() * 100
    top5_pct = sub_sorted.head(5)["ca_ttc"].sum() / sub["ca_ttc"].sum() * 100
    median_ca = sub["ca_par_mois"].median()
    fmt_analysis.append({
        "format": fmt,
        "nb_refs": len(sub),
        "ca_total": sub["ca_ttc"].sum(),
        "ca_median_par_ref": sub["ca_ttc"].median(),
        "ca_par_mois_median": median_ca,
        "concentration_top3_pct": round(top3_pct, 1),
        "concentration_top5_pct": round(top5_pct, 1),
    })

fmt_df = pd.DataFrame(fmt_analysis).sort_values("ca_total", ascending=False)
print(fmt_df.to_string(index=False))

# === Write Excel ===
with pd.ExcelWriter(OUT, engine="openpyxl") as xl:
    per_product.to_excel(xl, sheet_name="Tous produits (Pareto)", index=False)
    fmt_df.to_excel(xl, sheet_name="Analyse par format", index=False)
    tail.sort_values("ca_par_mois").to_excel(xl, sheet_name="Long tail (a etudier)", index=False)
    matrix.to_excel(xl, sheet_name="Matrice famille x format")
    multi_fmt.to_excel(xl, sheet_name="Familles multi-formats")

print(f"\nOutput: {OUT}")
