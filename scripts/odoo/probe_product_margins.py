"""Pull product cost + price from Odoo, bucket by ml format,
compute margin €/% per format. Cross-reference with WP sales volumes.

Output: C:/Users/startec/Downloads/odoo_margins_per_format.xlsx
"""
import re
from pathlib import Path
import pandas as pd
from _client import search_read

# 1. Pull product catalog from Odoo
print("Pulling product.template from Odoo...")
products = search_read(
    "product.template",
    [("sale_ok", "=", True), ("company_id", "in", [3, False])],
    [
        "id", "name", "default_code", "list_price", "standard_price",
        "categ_id", "active", "type",
        "weight",
    ],
    limit=0,
)
print(f"  -> {len(products)} active sellable products")

df = pd.DataFrame(products)

# 2. Detect format (ml) from name
RE_ML = re.compile(r"(\d+(?:[.,]\d+)?)\s*ml\b", re.IGNORECASE)
RE_L = re.compile(r"\b(\d+)\s*L\b")  # "1 L" = 1000ml


def detect_format(name: str) -> str:
    if not isinstance(name, str):
        return "—"
    m = RE_ML.search(name)
    if m:
        v = int(float(m.group(1).replace(",", ".")))
        return f"{v}ml"
    m = RE_L.search(name)
    if m:
        v = int(m.group(1)) * 1000
        return f"{v}ml"
    return "—"


df["format_ml"] = df["name"].apply(detect_format)
df["categ"] = df["categ_id"].apply(lambda x: x[1] if isinstance(x, list) else None)
df["marge_unit_eur"] = df["list_price"] - df["standard_price"]
df["marge_pct"] = df.apply(
    lambda r: (r["marge_unit_eur"] / r["list_price"] * 100) if r["list_price"] else None, axis=1
)

# 3. Filter out products with zero list_price (services, kits, etc.) for format analysis
prod_with_price = df[df["list_price"] > 0].copy()

# 4. Aggregate by format
print("\n=== MARGE MOYENNE PAR FORMAT (catalogue Odoo) ===")
by_format = prod_with_price[prod_with_price["format_ml"] != "—"].groupby("format_ml").agg(
    nb_refs=("id", "count"),
    prix_vente_moy=("list_price", "mean"),
    cout_moy=("standard_price", "mean"),
    marge_unit_moy=("marge_unit_eur", "mean"),
    marge_pct_moy=("marge_pct", "mean"),
    prix_vente_med=("list_price", "median"),
    cout_med=("standard_price", "median"),
).round(2).reset_index()

# Sort by format size for readability
def format_sort(s):
    if s == "—":
        return 99999
    try:
        return int(s.replace("ml", ""))
    except:
        return 99998

by_format["_sort"] = by_format["format_ml"].apply(format_sort)
by_format = by_format.sort_values("_sort").drop(columns="_sort")
print(by_format.to_string(index=False))

# 5. Cross-reference with WP sales
wp_path = Path(r"C:/Users/startec/Downloads/wp_sales_analysis.xlsx")
if wp_path.exists():
    wp_by_format = pd.read_excel(wp_path, sheet_name="Par format")
    print("\n=== CROISEMENT VENTES WP × MARGE ODOO ===")
    cross = wp_by_format.merge(by_format, on="format_ml", how="left")
    # Estimated total margin = units × marge_unit_moy
    cross["marge_totale_estim_eur"] = (cross["units"] * cross["marge_unit_moy"]).round(2)
    cross["ca_par_ref_par_mois"] = (cross["ca_ttc"] / cross["nb_references"] / 16).round(2)
    print(cross[[
        "format_ml", "nb_references", "units", "ca_ttc",
        "prix_vente_moy", "cout_moy", "marge_unit_moy", "marge_pct_moy",
        "marge_totale_estim_eur", "ca_par_ref_par_mois",
    ]].to_string(index=False))
else:
    cross = pd.DataFrame()

# 6. Write Excel
out = Path(r"C:/Users/startec/Downloads/odoo_margins_per_format.xlsx")
with pd.ExcelWriter(out, engine="openpyxl") as xl:
    df[["id", "default_code", "name", "format_ml", "categ",
        "list_price", "standard_price", "marge_unit_eur", "marge_pct",
        "weight", "active"]].sort_values(["format_ml", "name"]).to_excel(
        xl, sheet_name="Catalogue Odoo", index=False)
    by_format.to_excel(xl, sheet_name="Marge par format", index=False)
    if len(cross):
        cross.to_excel(xl, sheet_name="Ventes WP x Marge", index=False)

print(f"\nOutput: {out}")
