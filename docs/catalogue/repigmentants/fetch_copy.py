import json, re, urllib.request

STORE = "https://mylab-shop-3.myshopify.com"
HANDLES = [
    "shampoing-coloristeur-chocolat",
    "masque-coloristeur-chocolat",
    "shampoing-coloristeur-cuivre",
]

def strip_html(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = re.sub(r"&nbsp;", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

for h in HANDLES:
    try:
        with urllib.request.urlopen(f"{STORE}/products/{h}.js", timeout=15) as r:
            p = json.loads(r.read())
        print("##", h, "—", p.get("title"))
        print(strip_html(p.get("description"))[:1400])
        print()
    except Exception as e:
        print("ECHEC", h, e)
