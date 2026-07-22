import json, re, pathlib, urllib.request

ROOT = pathlib.Path(__file__).parent
IMG = ROOT / "img"; IMG.mkdir(parents=True, exist_ok=True)
SRC = ROOT.parents[2] / "assets" / "bulk-product-images.json"

data = json.loads(SRC.read_text(encoding="utf-8"))
WANT = {  # handle -> nom de fichier local
    "shampoing-coloristeur-blond-soleil": "shampoing-blond-soleil",
    "shampoing-coloristeur-blond-vanille": "shampoing-blond-vanille",
    "shampoing-coloristeur-chocolat": "shampoing-chocolat",
    "shampoing-coloristeur-cuivre": "shampoing-cuivre",
    "shampoing-coloristeur-marron-noisette": "shampoing-marron-noisette",
    "shampoing-dejaunisseur-platine": "shampoing-platine",
    "masque-coloristeur-blond-soleil": "masque-blond-soleil",
    "masque-coloristeur-blond-vanille": "masque-blond-vanille",
    "masque-coloristeur-chocolat": "masque-chocolat",
    "masque-coloristeur-cuivre": "masque-cuivre",
    "masque-coloristeur-marron-noisette": "masque-marron-noisette",
    "masque-dejaunisseur-platine": "masque-platine",
}
ok = 0
for handle, fname in WANT.items():
    url = data.get(handle)
    if not url:
        print("MANQUE", handle); continue
    url = re.sub(r"_200x200(\.\w+)", r"_800x800\1", url)
    dest = IMG / (fname + ".jpg")
    urllib.request.urlretrieve(url, dest)
    sz = dest.stat().st_size
    print(f"{fname}: {sz} octets")
    if sz > 3000: ok += 1
print(f"OK {ok}/12")
