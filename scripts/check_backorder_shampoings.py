"""LECTURE SEULE : les shampoings des 4 gammes sont-ils commandables sur Shopify ?

Pour chaque variante : inventory_quantity + inventory_policy (continue=backorder ON,
commandable meme a 0/negatif ; deny=bloque des que <=0).

Teste automatiquement les differents SHOPIFY_ADMIN_TOKEN du .env.local (sans jamais
afficher leur valeur) et utilise le premier qui a le scope read_products.
"""
import re
import unicodedata
import requests
from pathlib import Path

ENV = Path(r"d:\Configurateur Designs MyLab\mylab-configurateur\.env.local")
STORE = "mylab-shop-3.myshopify.com"


def load_admin_tokens():
    """-> list of (label, token) uniques, dans l'ordre du fichier."""
    tokens, label = [], "?"
    for line in ENV.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if s.startswith("#"):
            label = s.lstrip("# ").strip() or label
        m = re.match(r"SHOPIFY_ADMIN_TOKEN\s*=\s*(.+)", s)
        if m:
            tok = m.group(1).strip().strip('"').strip("'")
            if tok and tok not in {t for _, t in tokens}:
                tokens.append((label, tok))
    return tokens


def pick_token():
    for label, tok in load_admin_tokens():
        hdr = {"X-Shopify-Access-Token": tok, "Content-Type": "application/json"}
        try:
            r = requests.get(f"https://{STORE}/admin/api/2024-10/products.json",
                             params={"limit": 1, "fields": "id"}, headers=hdr, timeout=20)
        except Exception as e:
            print(f"  [{label}] erreur reseau: {e}")
            continue
        print(f"  [{label}] -> HTTP {r.status_code}")
        if r.status_code == 200:
            return label, hdr
    raise SystemExit("Aucun token avec scope read_products.")


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn").lower()


TERMS = ["purifiant", "nourrissant", "gel douche", "jauniss"]


def matches(title):
    t = strip_accents(title)
    return "shampoing" in t and any(term in t for term in TERMS)


print("=== Selection du token (scope read_products) ===")
label, HDR = pick_token()
print(f"-> token utilise : [{label}]\n")

url = f"https://{STORE}/admin/api/2024-10/products.json"
params = {"limit": 250, "fields": "id,title,handle,status,variants"}
hits = []
while url:
    r = requests.get(url, params=params, headers=HDR, timeout=30)
    r.raise_for_status()
    for p in r.json().get("products", []):
        if matches(p["title"]):
            hits.append(p)
    link, url, params = r.headers.get("Link", ""), None, None
    for part in link.split(","):
        if 'rel="next"' in part:
            url = part[part.find("<") + 1:part.find(">")]

print(f"=== {len(hits)} produits shampoing (4 gammes) ===\n")
n_ok, n_deny, deny_list = 0, 0, []
for p in sorted(hits, key=lambda x: x["title"]):
    print(f"[{p['status']}] {p['title']}  (handle={p['handle']})")
    for v in p["variants"]:
        pol, qty = v.get("inventory_policy"), v.get("inventory_quantity")
        commandable = "OUI" if (pol == "continue" or (qty or 0) > 0) else "NON (bloque)"
        if pol == "continue":
            n_ok += 1
        else:
            n_deny += 1
            if (qty or 0) <= 0:
                deny_list.append(f"{p['title']} / {v.get('title')} (qty={qty})")
        flag = "" if pol == "continue" else "  <-- deny"
        print(f"    {str(v.get('title')):<18} sku={str(v.get('sku')):<30} qty={qty} "
              f"policy={pol}{flag}  -> {commandable}")
    print()

print(f"=== RESUME : {n_ok} variantes backorder(continue) / {n_deny} deny ===")
if deny_list:
    print(f"\n!! {len(deny_list)} variantes NON commandables (deny + stock<=0) :")
    for d in deny_list:
        print(f"   - {d}")
else:
    print("Toutes commandables (backorder actif ou stock>0).")
