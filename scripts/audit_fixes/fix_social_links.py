"""Nettoie les URLs sociales 'https://facebook.com/shopify' (démo Shopify)
   dans config/settings_data.json. Remplace par les vraies URLs MY.LAB
   identifiées dans les pages/footer, ou vide si inconnues."""
import json
import os
import sys
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TOKEN = os.environ["TOKEN"]
THEME = "184014340430"
SHOP = "mylab-shop-3.myshopify.com"
KEY = "config/settings_data.json"

# URLs confirmées via le contenu de la page jeu-concours et l'ancien site WordPress
REAL_SOCIALS = {
    "social_facebook_link": "https://www.facebook.com/mylabfrance",
    "social_instagram_link": "https://www.instagram.com/mylab_shop/",
    # Pas d'URL confirmée pour les autres — on nettoie à vide plutôt que Shopify default
    "social_twitter_link": "",
    "social_pinterest_link": "",
    "social_tiktok_link": "",
    "social_tumblr_link": "",
    "social_snapchat_link": "",
    "social_youtube_link": "",
    "social_vimeo_link": "",
    "social_linkedin_link": "",
}

# Fetch
url = f"https://{SHOP}/admin/api/2024-10/themes/{THEME}/assets.json?asset%5Bkey%5D={KEY.replace('/', '%2F')}"
r = urllib.request.Request(url)
r.add_header("X-Shopify-Access-Token", TOKEN)
with urllib.request.urlopen(r) as resp:
    raw = json.loads(resp.read())["asset"]["value"]

parsed = json.loads(raw)

def fix_node(node, path=""):
    """Recursively fix social_*_link values at any depth."""
    if isinstance(node, dict):
        for k, v in list(node.items()):
            if k in REAL_SOCIALS and isinstance(v, str) and "shopify" in v.lower():
                new_val = REAL_SOCIALS[k]
                if new_val != v:
                    print(f"  {path}.{k}: {v!r} -> {new_val!r}")
                    node[k] = new_val
            else:
                fix_node(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, item in enumerate(node):
            fix_node(item, f"{path}[{i}]")

fix_node(parsed)

# Serialize & PUT
new_value = json.dumps(parsed, ensure_ascii=False, indent=2)
put_url = f"https://{SHOP}/admin/api/2024-10/themes/{THEME}/assets.json"
payload = json.dumps({"asset": {"key": KEY, "value": new_value}}).encode()
req = urllib.request.Request(put_url, data=payload, method="PUT")
req.add_header("X-Shopify-Access-Token", TOKEN)
req.add_header("Content-Type", "application/json")
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read())
    print(f"\nPUT status={resp.status} updated={res['asset'].get('updated_at')}")
