"""Fix du mega_menu du header-group : lien externe Vercel + libellé cassé."""
import json
import os
import sys
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TOKEN = os.environ["TOKEN"]
THEME = "184014340430"
SHOP = "mylab-shop-3.myshopify.com"
KEY = "sections/header-group.json"

# Fetch
url = f"https://{SHOP}/admin/api/2024-10/themes/{THEME}/assets.json?asset%5Bkey%5D={KEY.replace('/', '%2F')}"
r = urllib.request.Request(url)
r.add_header("X-Shopify-Access-Token", TOKEN)
with urllib.request.urlopen(r) as resp:
    raw = json.loads(resp.read())["asset"]["value"]

parsed = json.loads(raw)

# Update mega_menu block
for sk, section in parsed["sections"].items():
    if section["type"] != "header":
        continue
    for bk, block in section.get("blocks", {}).items():
        if block["type"] != "mega_menu":
            continue
        settings = block.get("settings", {})
        # Fix promo 1: external Vercel link → internal Shopify page
        if "vercel.app" in settings.get("promo_link_1", ""):
            print(f"  promo_link_1: {settings['promo_link_1']!r} → /pages/designs-etiquettes")
            settings["promo_link_1"] = "shopify://pages/designs-etiquettes"
        # Fix promo 2: clean broken subtitle
        if settings.get("promo_text_2") == "Vous souhaitez changer de flacon ? commander en gros volumes ?":
            new_text = "Dès 50 kg · Packaging Takemoto · Devis sous 72h"
            print(f"  promo_text_2: cleaning")
            settings["promo_text_2"] = new_text
        break

# PUT back
new_value = json.dumps(parsed, indent=2, ensure_ascii=False)
put_url = f"https://{SHOP}/admin/api/2024-10/themes/{THEME}/assets.json"
payload = json.dumps({"asset": {"key": KEY, "value": new_value}}).encode()
req = urllib.request.Request(put_url, data=payload, method="PUT")
req.add_header("X-Shopify-Access-Token", TOKEN)
req.add_header("Content-Type", "application/json")
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read())
    print(f"  PUT {KEY} status={resp.status} updated_at={res['asset'].get('updated_at')}")
