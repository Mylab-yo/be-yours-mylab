"""Ajoute un slide 'gros volume' au slideshow hero de la home.
   Patch ciblé sur templates/index.json : ajoute un block 'slide_gros_volume'
   dans slideshow_hero.blocks et l'insère dans block_order."""
import json
import os
import sys
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TOKEN = os.environ["TOKEN"]
THEME = "184014340430"
SHOP = "mylab-shop-3.myshopify.com"
KEY = "templates/index.json"

# Fetch live
url = f"https://{SHOP}/admin/api/2024-10/themes/{THEME}/assets.json?asset%5Bkey%5D={KEY.replace('/', '%2F')}"
r = urllib.request.Request(url)
r.add_header("X-Shopify-Access-Token", TOKEN)
with urllib.request.urlopen(r) as resp:
    raw = json.loads(resp.read())["asset"]["value"]

parsed = json.loads(raw)

# Build new slide mirroring structure of existing ones
NEW_BLOCK_KEY = "slide_gros_volume"

new_block = {
    "type": "image",
    "settings": {
        "image": "shopify://shop_images/photo-bouteille-home-scaled.jpg",
        "image_mobile": "shopify://shop_images/photo-bouteille-home-scaled.jpg",
        "image_position": "center center",
        "text_box_position": "middle-right",
        "subheading": "COMMANDES GROS VOLUME",
        "subheading_size": "h5",
        "heading": "Lancez votre <strong>production en série</strong>",
        "heading_size": "h0",
        "heading_tag": "h2",
        "text": "Dès 50 kg par référence. Packaging Takemoto, tarifs dégressifs, devis sous 72h.",
        "text_size": "typeset2",
        "button_label": "Configurer ma commande",
        "button_link": "shopify://pages/vous-cherchez-a-commander-en-gros-volume-cest-par-ici",
        "button_size": "medium",
        "button_style_secondary": False,
        "button_alt_label": "Parler à un conseiller",
        "button_alt_link": "shopify://pages/contact",
        "button_alt_size": "medium",
        "button_alt_style_secondary": True,
        "enable_highlight": False,
        "highlight_style": "solid-color",
    },
}

sh = parsed["sections"]["slideshow_hero"]
blocks = sh.setdefault("blocks", {})
if NEW_BLOCK_KEY in blocks:
    print(f"Block {NEW_BLOCK_KEY!r} already exists — updating in place")
else:
    print(f"Adding new block {NEW_BLOCK_KEY!r}")
blocks[NEW_BLOCK_KEY] = new_block

# Update block_order — insert after slide_main but before slide_formules (so order: main, bulk, formules)
order = sh.get("block_order", [])
if NEW_BLOCK_KEY in order:
    print(f"Block order already includes {NEW_BLOCK_KEY!r}")
else:
    # Insert after slide_main if present
    if "slide_main" in order:
        idx = order.index("slide_main")
        order.insert(idx + 1, NEW_BLOCK_KEY)
    else:
        order.append(NEW_BLOCK_KEY)
sh["block_order"] = order
print(f"Final block_order: {order}")

# Serialize
new_value = json.dumps(parsed, indent=2, ensure_ascii=False)

# PUT
put_url = f"https://{SHOP}/admin/api/2024-10/themes/{THEME}/assets.json"
payload = json.dumps({"asset": {"key": KEY, "value": new_value}}).encode()
req = urllib.request.Request(put_url, data=payload, method="PUT")
req.add_header("X-Shopify-Access-Token", TOKEN)
req.add_header("Content-Type", "application/json")
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read())
    print(f"\nPUT status={resp.status} updated_at={res['asset'].get('updated_at')}")
