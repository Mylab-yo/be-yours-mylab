#!/usr/bin/env python3
"""
MY.LAB — Scraper catalogue flacons Takemoto
============================================
Extrait les données depuis eu.store.takemotopkg.com (Shopify store)
et génère :
  1. takemoto_raw_data.json — données brutes complètes
  2. assets/bulk-data-bottles.json — formaté pour le configurateur
  3. takemoto_catalog_review.csv — pour validation manuelle
  4. bottle_images/ — images téléchargées
  5. upload_bottle_images.sh — script d'upload Shopify CLI

Usage:
  pip install requests beautifulsoup4
  python scrape_takemoto.py
"""

import json
import csv
import os
import re
import time
import logging
import hashlib
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# ── CONFIG ──
BASE_URL = "https://eu.store.takemotopkg.com"
PRODUCTS_JSON = f"{BASE_URL}/collections/products/products.json"
DELAY = 1.5  # seconds between requests
MAX_RETRIES = 3
OUTPUT_DIR = Path(".")
IMAGES_DIR = OUTPUT_DIR / "bottle_images"
CHECKPOINT_FILE = OUTPUT_DIR / "scrape_checkpoint.json"
LOG_FILE = OUTPUT_DIR / "scrape_errors.log"

# Filtrage cosmétique capillaire
MIN_CAPACITY_ML = 30
MAX_CAPACITY_ML = 1100
RELEVANT_TYPES = {"bottle", "jar"}
EXCLUDE_TAGS = {"food", "pet", "garden", "jardin", "alimentaire", "animal"}

# ── LOGGING ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ── SESSION ──
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (MyLab Catalog Bot; +https://mylab-shop-3.myshopify.com)"
})


def fetch_json(url, params=None):
    """Fetch JSON with retries."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            log.warning(f"Attempt {attempt}/{MAX_RETRIES} failed for {url}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(DELAY * attempt)
            else:
                log.error(f"Failed after {MAX_RETRIES} attempts: {url}")
                return None


def fetch_html(url):
    """Fetch HTML with retries."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, timeout=15)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            log.warning(f"Attempt {attempt}/{MAX_RETRIES} failed for {url}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(DELAY * attempt)
            else:
                log.error(f"Failed after {MAX_RETRIES} attempts: {url}")
                return None


def download_image(url, filepath):
    """Download image with retries."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, timeout=30, stream=True)
            resp.raise_for_status()
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
            return True
        except Exception as e:
            log.warning(f"Image download attempt {attempt}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(DELAY)
    return False


# ── CHECKPOINT ──
def load_checkpoint():
    if CHECKPOINT_FILE.exists():
        return json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
    return {"page": 1, "products_fetched": 0, "products": []}


def save_checkpoint(data):
    CHECKPOINT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── DETECTION HELPERS ──
def detect_capacity(product):
    """Extract capacity in ml from title, tags, or variants."""
    title = product.get("title", "").lower()
    tags = " ".join(product.get("tags", [])).lower() if isinstance(product.get("tags"), list) else product.get("tags", "").lower()
    combined = f"{title} {tags}"

    # Match patterns like "200ml", "200 ml", "0.2L"
    patterns = [
        (r"(\d+)\s*ml\b", 1),           # 200ml
        (r"(\d+(?:\.\d+)?)\s*l\b", 1000),  # 0.2L, 1L
        (r"(\d+)\s*oz\b", 29.5735),     # oz to ml
    ]
    for pattern, multiplier in patterns:
        match = re.search(pattern, combined)
        if match:
            val = float(match.group(1)) * multiplier
            return int(round(val))

    # Check variants
    for variant in product.get("variants", []):
        vtitle = variant.get("title", "").lower()
        for pattern, multiplier in patterns:
            match = re.search(pattern, vtitle)
            if match:
                return int(round(float(match.group(1)) * multiplier))

    return None


def detect_type(product):
    """Detect container type: bottle, jar, tube."""
    combined = f"{product.get('title', '')} {product.get('body_html', '')} {' '.join(product.get('tags', []))}".lower()
    if "jar" in combined or "pot" in combined:
        return "jar"
    if "tube" in combined:
        return "tube"
    return "bottle"


def detect_closure(product):
    """Detect closure type."""
    combined = f"{product.get('title', '')} {product.get('body_html', '')} {' '.join(product.get('tags', []))}".lower()
    if "pump" in combined or "pompe" in combined:
        return "pump"
    if "spray" in combined or "trigger" in combined or "mist" in combined:
        return "spray"
    if "dropper" in combined or "pipette" in combined:
        return "dropper"
    if "dispensing" in combined or "disc" in combined or "flip" in combined:
        return "dispensing_cap"
    return "screw_cap"


def detect_material(product):
    """Detect material."""
    combined = f"{product.get('title', '')} {product.get('body_html', '')} {' '.join(product.get('tags', []))}".lower()
    if "rpet" in combined or "r-pet" in combined:
        return "rPET"
    if "pcr" in combined or "post-consumer" in combined:
        return "PCR"
    if "biomass" in combined or "bio-pet" in combined or "plant" in combined:
        return "biomass_PET"
    if "glass" in combined or "verre" in combined:
        return "glass"
    if "pet" in combined:
        return "PET"
    if "pp" in combined:
        return "PP"
    if "hdpe" in combined:
        return "HDPE"
    return "PET"


def detect_color(product):
    """Detect bottle color."""
    combined = f"{product.get('title', '')} {' '.join(product.get('tags', []))}".lower()
    if "amber" in combined or "ambr" in combined or "brown" in combined:
        return "amber"
    if "frost" in combined or "givr" in combined:
        return "frosted"
    if "white" in combined or "blanc" in combined:
        return "white"
    if "black" in combined or "noir" in combined:
        return "black"
    if "green" in combined or "vert" in combined:
        return "green"
    if "blue" in combined or "bleu" in combined:
        return "blue"
    if "clear" in combined or "transparent" in combined:
        return "clear"
    return "clear"


def detect_eco(product):
    """Detect if eco-responsible."""
    combined = f"{product.get('title', '')} {product.get('body_html', '')} {' '.join(product.get('tags', []))}".lower()
    eco_keywords = ["eco", "recycl", "rpet", "pcr", "biomass", "bio-pet", "sustainable", "green", "plant-based"]
    return any(kw in combined for kw in eco_keywords)


def detect_compatible_products(closure_type, capacity):
    """Determine which MY.LAB product types are compatible."""
    compat = []
    if closure_type in ("pump", "screw_cap") and capacity >= 200:
        compat.append("shampoing")
    if closure_type in ("pump", "dispensing_cap") and capacity >= 200:
        compat.extend(["creme_coiffage", "masque"])
    if closure_type == "spray" and capacity <= 300:
        compat.append("spray")
    if closure_type in ("dropper", "pump") and capacity <= 100:
        compat.extend(["serum", "huile"])
    if closure_type == "screw_cap" and capacity >= 200:
        compat.append("masque")
    return list(set(compat))


def is_relevant(product, capacity):
    """Check if product is relevant for hair care cosmetics."""
    if capacity is None:
        return False
    if capacity < MIN_CAPACITY_ML or capacity > MAX_CAPACITY_ML:
        return False
    tags = " ".join(product.get("tags", [])).lower() if isinstance(product.get("tags"), list) else ""
    title = product.get("title", "").lower()
    combined = f"{tags} {title}"
    if any(excl in combined for excl in EXCLUDE_TAGS):
        return False
    return True


def get_compatible_formats(capacity):
    """Map capacity to MY.LAB compatible formats."""
    formats = []
    if 25 <= capacity <= 60:
        formats.append(50)
    if 180 <= capacity <= 250:
        formats.append(200)
    if 280 <= capacity <= 350:
        formats.append(300)
    if 450 <= capacity <= 550:
        formats.append(500)
    if 900 <= capacity <= 1100:
        formats.append(1000)
    return formats


# ── MAIN SCRAPER ──
def scrape_all_products():
    """Fetch all products from Takemoto Shopify store via JSON API."""
    checkpoint = load_checkpoint()
    all_products = checkpoint.get("products", [])
    seen_ids = {p["id"] for p in all_products}
    page = checkpoint.get("page", 1)

    log.info(f"Starting scrape from page {page} ({len(all_products)} products in checkpoint)")

    while True:
        log.info(f"Fetching page {page}...")
        data = fetch_json(PRODUCTS_JSON, params={"limit": 250, "page": page})

        if data is None:
            log.error(f"Failed to fetch page {page}, stopping.")
            break

        products = data.get("products", [])
        if not products:
            log.info(f"No more products on page {page}, scraping complete.")
            break

        for p in products:
            if p["id"] not in seen_ids:
                all_products.append(p)
                seen_ids.add(p["id"])

        log.info(f"Page {page}: {len(products)} products fetched (total: {len(all_products)})")

        # Save checkpoint
        save_checkpoint({"page": page + 1, "products_fetched": len(all_products), "products": all_products})
        page += 1
        time.sleep(DELAY)

    return all_products


def process_products(raw_products):
    """Process raw Shopify products into structured bottle data."""
    bottles = []
    skipped = 0

    for p in raw_products:
        capacity = detect_capacity(p)
        if not is_relevant(p, capacity):
            skipped += 1
            continue

        container_type = detect_type(p)
        closure = detect_closure(p)
        material = detect_material(p)
        color = detect_color(p)
        eco = detect_eco(p)
        compat = detect_compatible_products(closure, capacity)
        formats = get_compatible_formats(capacity)

        # Get image
        image_url = ""
        if p.get("images") and len(p["images"]) > 0:
            image_url = p["images"][0].get("src", "")
        elif p.get("image") and p["image"].get("src"):
            image_url = p["image"]["src"]

        # Get price
        price = None
        if p.get("variants") and len(p["variants"]) > 0:
            price_str = p["variants"][0].get("price")
            if price_str:
                try:
                    price = float(price_str)
                except (ValueError, TypeError):
                    pass

        # SKU
        sku = ""
        if p.get("variants") and len(p["variants"]) > 0:
            sku = p["variants"][0].get("sku", "") or ""

        # Generate ID
        slug = re.sub(r"[^a-z0-9]+", "-", p.get("handle", p["title"]).lower()).strip("-")
        bottle_id = f"tk-{slug}"

        # MOQ from description
        moq = 100  # default
        body = p.get("body_html", "") or ""
        moq_match = re.search(r"(?:moq|minimum)[:\s]*(\d+)", body.lower())
        if moq_match:
            moq = int(moq_match.group(1))

        # Clean description
        desc_text = ""
        if body:
            soup = BeautifulSoup(body, "html.parser")
            desc_text = soup.get_text(separator=" ", strip=True)[:200]

        bottle = {
            "id": bottle_id,
            "name": p["title"],
            "brand": "Takemoto",
            "sku": sku,
            "type": container_type,
            "closure_type": closure,
            "material": material,
            "capacity_ml": capacity,
            "compatible_formats": formats,
            "compatible_products": compat,
            "color": color,
            "eco_label": eco,
            "image_url_external": image_url,
            "image_url_local": f"/files/takemoto-{sku or slug}-{capacity}ml.webp" if image_url else "",
            "takemoto_url": f"{BASE_URL}/products/{p.get('handle', '')}",
            "price_estimate": int(price * 100) if price else None,
            "dimensions": {"height_mm": None, "diameter_mm": None},
            "min_order_qty": moq,
            "notes": desc_text,
            "tags": p.get("tags", []),
            "shopify_id": p["id"],
            "_raw_handle": p.get("handle", "")
        }
        bottles.append(bottle)

    log.info(f"Processed {len(bottles)} relevant bottles, skipped {skipped}")
    return bottles


def download_images(bottles):
    """Download product images."""
    IMAGES_DIR.mkdir(exist_ok=True)
    downloaded = 0
    failed = 0

    for b in bottles:
        url = b.get("image_url_external")
        if not url:
            continue

        ext = "jpg"
        if ".png" in url.lower():
            ext = "png"
        elif ".webp" in url.lower():
            ext = "webp"

        slug = b["id"].replace("tk-", "")
        filename = f"takemoto-{b.get('sku') or slug}-{b['capacity_ml']}ml.{ext}"
        filepath = IMAGES_DIR / filename

        if filepath.exists():
            log.info(f"Image already exists: {filename}")
            downloaded += 1
            continue

        log.info(f"Downloading: {filename}")
        if download_image(url, filepath):
            downloaded += 1
        else:
            failed += 1
            log.error(f"Failed to download: {url}")

        time.sleep(0.5)

    log.info(f"Images: {downloaded} downloaded, {failed} failed")
    return downloaded


def generate_upload_script(bottles):
    """Generate Shopify CLI upload script."""
    lines = [
        "#!/bin/bash",
        "# MY.LAB — Upload Takemoto bottle images to Shopify Files",
        "# Generated by scrape_takemoto.py",
        f"# {len(bottles)} images to upload",
        "",
        'STORE="mylab-shop-3.myshopify.com"',
        "",
    ]

    for b in bottles:
        if not b.get("image_url_external"):
            continue
        slug = b["id"].replace("tk-", "")
        sku = b.get("sku") or slug
        ext = "jpg"
        if ".png" in b["image_url_external"].lower():
            ext = "png"
        filename = f"takemoto-{sku}-{b['capacity_ml']}ml.{ext}"
        filepath = f"bottle_images/{filename}"
        lines.append(f'echo "Uploading {filename}..."')
        lines.append(f'# shopify theme push --store $STORE --only "assets/{filename}" 2>/dev/null')
        lines.append("")

    lines.append('echo "Upload complete!"')

    script_path = OUTPUT_DIR / "upload_bottle_images.sh"
    script_path.write_text("\n".join(lines), encoding="utf-8")
    log.info(f"Upload script generated: {script_path}")


def generate_bulk_data_bottles(bottles):
    """Generate the bulk-data-bottles.json for the configurator."""
    # Color and material labels
    COLOR_LABELS = {"amber": "Ambré", "clear": "Transparent", "white": "Blanc",
                    "black": "Noir", "frosted": "Givré", "green": "Vert", "blue": "Bleu"}
    MATERIAL_LABELS = {"PET": "PET", "rPET": "rPET", "PCR": "PCR",
                       "biomass_PET": "Bio PET", "glass": "Verre", "PP": "PP", "HDPE": "HDPE"}
    CLOSURE_LABELS = {"pump": "Pompe", "screw_cap": "Bouchon vis",
                      "dispensing_cap": "Clapet", "spray": "Spray", "dropper": "Pipette"}

    formatted = {
        "_doc": "MY.LAB — Catalogue flacons Takemoto. Généré automatiquement par scrape_takemoto.py. Données à valider manuellement.",
        "_source": f"eu.store.takemotopkg.com — scrappé le {time.strftime('%Y-%m-%d')}",
        "_compatibility_rules": {
            "shampoing": "Viscosité basse/moyenne → Pump + Bottle ou Screw Cap + Bottle",
            "creme_coiffage": "Viscosité haute → Dispensing Cap + Bottle ou Pump + Bottle",
            "masque": "Viscosité haute → Jar ou Dispensing Cap + Bottle",
            "spray": "Viscosité basse → Spray + Bottle",
            "serum": "Viscosité basse → Dropper + Bottle ou Pump + Bottle (petit format)",
            "huile": "Viscosité basse → Dropper + Bottle ou Pump + Bottle (petit format)"
        },
        "bottles": [],
        "closures": [
            {"id": "screw-black", "label": "Bouchon noir à vis", "compatible_types": ["bottle"], "color": "black"},
            {"id": "screw-white", "label": "Bouchon blanc à vis", "compatible_types": ["bottle"], "color": "white"},
            {"id": "pump-black", "label": "Pompe noire", "compatible_types": ["bottle"], "color": "black"},
            {"id": "pump-white", "label": "Pompe blanche", "compatible_types": ["bottle"], "color": "white"},
            {"id": "spray-black", "label": "Spray gâchette noire", "compatible_types": ["bottle"], "color": "black"},
            {"id": "dropper-black", "label": "Pipette tétine noire", "compatible_types": ["bottle"], "color": "black"},
            {"id": "dispensing-black", "label": "Bouchon clapet noir", "compatible_types": ["bottle"], "color": "black"},
            {"id": "jar-lid-black", "label": "Couvercle pot noir", "compatible_types": ["jar"], "color": "black"}
        ]
    }

    for b in bottles:
        entry = {
            "id": b["id"],
            "name": b["name"],
            "brand": "Takemoto",
            "type": b["type"],
            "closure_type": b["closure_type"],
            "material": b["material"],
            "capacity_ml": b["capacity_ml"],
            "compatible_formats": b["compatible_formats"],
            "compatible_products": b["compatible_products"],
            "color": b["color"],
            "eco_label": b["eco_label"],
            "image_url": b.get("image_url_local", ""),
            "image_url_external": b.get("image_url_external", ""),
            "takemoto_url": b["takemoto_url"],
            "price_estimate": b["price_estimate"],
            "dimensions": b["dimensions"],
            "min_order_qty": b["min_order_qty"],
            "notes": b["notes"]
        }
        formatted["bottles"].append(entry)

    output_path = OUTPUT_DIR / "assets" / "bulk-data-bottles.json"
    output_path.write_text(json.dumps(formatted, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info(f"Generated: {output_path} ({len(formatted['bottles'])} bottles)")
    return formatted


def generate_csv(bottles):
    """Generate review CSV."""
    csv_path = OUTPUT_DIR / "takemoto_catalog_review.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow([
            "Nom", "SKU", "Contenance (ml)", "Type", "Fermeture", "Matériau",
            "Couleur", "Éco", "Prix (€)", "MOQ", "URL",
            "Compatible Shampoing", "Compatible Crème", "Compatible Masque",
            "Compatible Spray", "Compatible Sérum/Huile", "Notes"
        ])
        for b in bottles:
            compat = b.get("compatible_products", [])
            writer.writerow([
                b["name"],
                b.get("sku", ""),
                b["capacity_ml"],
                b["type"],
                b["closure_type"],
                b["material"],
                b["color"],
                "Oui" if b["eco_label"] else "Non",
                f"{b['price_estimate']/100:.2f}" if b.get("price_estimate") else "",
                b["min_order_qty"],
                b["takemoto_url"],
                "X" if "shampoing" in compat else "",
                "X" if "creme_coiffage" in compat else "",
                "X" if "masque" in compat else "",
                "X" if "spray" in compat else "",
                "X" if "serum" in compat or "huile" in compat else "",
                b.get("notes", "")[:100]
            ])
    log.info(f"Generated: {csv_path}")


# ── MAIN ──
def main():
    log.info("=" * 60)
    log.info("MY.LAB — Takemoto Catalog Scraper")
    log.info("=" * 60)

    # Step 1: Scrape all products
    log.info("\n[1/6] Fetching products from Takemoto...")
    raw_products = scrape_all_products()
    log.info(f"Total raw products: {len(raw_products)}")

    # Save raw data
    raw_path = OUTPUT_DIR / "takemoto_raw_data.json"
    raw_path.write_text(json.dumps(raw_products, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info(f"Raw data saved: {raw_path}")

    # Step 2: Process and filter
    log.info("\n[2/6] Processing and filtering...")
    bottles = process_products(raw_products)

    # Step 3: Download images
    log.info("\n[3/6] Downloading images...")
    download_images(bottles)

    # Step 4: Generate bulk-data-bottles.json
    log.info("\n[4/6] Generating bulk-data-bottles.json...")
    generate_bulk_data_bottles(bottles)

    # Step 5: Generate CSV
    log.info("\n[5/6] Generating review CSV...")
    generate_csv(bottles)

    # Step 6: Generate upload script
    log.info("\n[6/6] Generating upload script...")
    generate_upload_script(bottles)

    # Cleanup checkpoint
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()

    log.info("\n" + "=" * 60)
    log.info(f"DONE! {len(bottles)} bottles extracted.")
    log.info(f"  → takemoto_raw_data.json")
    log.info(f"  → assets/bulk-data-bottles.json")
    log.info(f"  → takemoto_catalog_review.csv")
    log.info(f"  → bottle_images/ ({len(list(IMAGES_DIR.glob('*')))} files)")
    log.info(f"  → upload_bottle_images.sh")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
