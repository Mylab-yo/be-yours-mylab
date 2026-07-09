"""Deep dive on the 'Hors format' category that bleeds -21,522 EUR.

Identifies which articles are losing money, by how much, and categorizes them.
"""
import re
from pathlib import Path
import pandas as pd

EBP_PATH = Path(r"C:/Users/startec/Downloads/évolution de la marge nette ebp.xls")
OUT_PATH = Path(r"C:/Users/startec/Downloads/hors_format_investigation.xlsx")

# Read EBP raw
raw = pd.read_excel(EBP_PATH, engine="xlrd", header=None)

mask = raw[3].astype(str).str.startswith("AR", na=False)
ebp = raw[mask].copy()
ebp = ebp[[0, 1, 2, 3, 25]].rename(columns={
    0: "famille", 1: "code_famille", 2: "libelle", 3: "sku", 25: "marge_totale_eur",
})
ebp["famille"] = ebp["famille"].ffill()
ebp["code_famille"] = ebp["code_famille"].ffill()
ebp["marge_totale_eur"] = pd.to_numeric(ebp["marge_totale_eur"], errors="coerce")

# Also extract monthly columns (5-22, skipping separator cols 11 and 17)
# Cols 5-10 = jan-juin 2025, 12-16 = juillet-nov 2025, 18 = dec 2025, 19 = total 2025
# 20-23 = jan-avril 2026, 24 = total 2026, 25 = total general
ebp["total_2025"] = pd.to_numeric(raw.loc[mask, 19], errors="coerce")
ebp["total_2026"] = pd.to_numeric(raw.loc[mask, 24], errors="coerce")

RE_ML = re.compile(r"\d{2,4}\s*ML", re.IGNORECASE)
ebp["has_ml"] = ebp["libelle"].apply(lambda s: bool(RE_ML.search(str(s))))

# Hors format = no ml in name
hf = ebp[~ebp["has_ml"]].copy()
print(f"Articles HORS FORMAT: {len(hf)}")
print(f"Marge totale hors format: {hf['marge_totale_eur'].sum():,.2f} EUR")
print(f"  Marge 2025 : {hf['total_2025'].sum():,.2f}")
print(f"  Marge 2026 : {hf['total_2026'].sum():,.2f}")

# Categorize by name patterns
def categorize(name: str) -> str:
    n = str(name).upper()
    if "FRAIS" in n or "PORT" in n or "EXPED" in n or "LIVRAISON" in n:
        return "Frais / Port"
    if "ETIQUETTE" in n or "IMPRESSION" in n or "PERSONNAL" in n:
        return "Etiquettes / Personnalisation"
    if "COFFRET" in n or "PACK" in n or "DECOUVERTE" in n or "DUO" in n or "KIT" in n:
        return "Coffrets / Packs"
    if "DOSSIER" in n or "COSMETOLOG" in n or "DIP" in n or "CPNP" in n:
        return "Service réglementaire (dossier)"
    if "FORMATION" in n or "CONSEIL" in n or "CONSULT" in n:
        return "Conseil / Formation"
    if "POMPE" in n or "FLACON" in n or "BOUCHON" in n or "VAPO" in n:
        return "Accessoires (pompes/flacons)"
    if "TESTEUR" in n or "ECHANTILLON" in n:
        return "Testeurs"
    if "HUILE" in n or "SERUM" in n or "BAIN" in n:
        return "Produit petit format (sans suffixe)"
    if "DIVERS" in n:
        return "DIVERS"
    return "Autre (à classer)"


hf["categorie"] = hf["libelle"].apply(categorize)

# Aggregate by category
by_cat = hf.groupby("categorie").agg(
    nb_articles=("sku", "count"),
    marge_totale=("marge_totale_eur", "sum"),
    marge_moyenne=("marge_totale_eur", "mean"),
    pire=("marge_totale_eur", "min"),
    meilleur=("marge_totale_eur", "max"),
).round(2).reset_index().sort_values("marge_totale")

print("\n=== HORS FORMAT PAR CATEGORIE ===")
print(by_cat.to_string(index=False))

# Top bleeders
print("\n=== TOP 20 ARTICLES QUI SAIGNENT LE PLUS ===")
worst = hf.sort_values("marge_totale_eur").head(20)
print(worst[["sku", "libelle", "famille", "categorie",
             "marge_totale_eur", "total_2025", "total_2026"]].to_string(index=False))

# Top winners (just for context)
print("\n=== TOP 10 HORS FORMAT RENTABLES (contraste) ===")
best = hf.sort_values("marge_totale_eur", ascending=False).head(10)
print(best[["sku", "libelle", "categorie", "marge_totale_eur"]].to_string(index=False))

# Recent trend: 2026 only (since 4 months it's a strong signal)
print("\n=== ARTICLES HORS FORMAT QUI SAIGNENT EN 2026 (4 derniers mois) ===")
recent = hf[hf["total_2026"] < -100].sort_values("total_2026")
print(recent[["sku", "libelle", "categorie", "total_2026", "total_2025"]].to_string(index=False))

# Write Excel
with pd.ExcelWriter(OUT_PATH, engine="openpyxl") as xl:
    by_cat.to_excel(xl, sheet_name="Par categorie", index=False)
    hf.sort_values("marge_totale_eur").to_excel(xl, sheet_name="Tous articles HF", index=False)
    worst.to_excel(xl, sheet_name="Top 20 pertes", index=False)
    best.to_excel(xl, sheet_name="Top 10 rentables", index=False)
    recent.to_excel(xl, sheet_name="Saignement 2026", index=False)

print(f"\nOutput: {OUT_PATH}")
