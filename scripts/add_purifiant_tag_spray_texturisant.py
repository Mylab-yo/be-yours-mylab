"""Add the 'purifiant' tag to Shopify product Spray Texturisant 200ml.

The page /pages/la-boutique-my-lab filter "Purifiant" matches tag 'purifiant'
(handleized lowercase singular). The product already had 'Les Purifiants'
(display tag) but missed the matching filter tag.

Companion to update_spray_texturisant_pricelist.py (Odoo pricing update).
"""
import os
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(r"D:\Configurateur Designs MyLab\mylab-configurateur\.env.local"))

TOKEN = os.environ["SHOPIFY_ADMIN_TOKEN"]  # full-scope (read_products/orders); n8n token
STORE = "mylab-shop-3.myshopify.com"
PRODUCT_ID = 10898490163534

HDR = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

# 1) Fetch current tags
r = requests.get(
    f"https://{STORE}/admin/api/2024-10/products/{PRODUCT_ID}.json",
    params={"fields": "id,title,tags"},
    headers=HDR,
)
r.raise_for_status()
p = r.json()["product"]
current = [t.strip() for t in p["tags"].split(",") if t.strip()]
print(f"Before: {p['title']}  tags={current}")

# 2) Add 'purifiant' if missing
if "purifiant" in (t.lower() for t in current):
    print("Tag 'purifiant' already present, nothing to do.")
else:
    new_tags = current + ["purifiant"]
    new_csv = ", ".join(new_tags)
    r = requests.put(
        f"https://{STORE}/admin/api/2024-10/products/{PRODUCT_ID}.json",
        json={"product": {"id": PRODUCT_ID, "tags": new_csv}},
        headers=HDR,
    )
    r.raise_for_status()
    after = [t.strip() for t in r.json()["product"]["tags"].split(",") if t.strip()]
    print(f"After:  tags={after}")
