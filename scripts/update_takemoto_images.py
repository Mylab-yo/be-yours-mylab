#!/usr/bin/env python3
"""
MY.LAB — Update Takemoto bottle images in bulk-data-bottles.json
Fetches high-res image URLs from Takemoto Shopify API.
"""

import json
import time
import shutil
import logging
from pathlib import Path

import requests

BASE_URL = "https://eu.store.takemotopkg.com"
PRODUCTS_JSON = f"{BASE_URL}/collections/products/products.json"
BOTTLES_FILE = Path("assets/bulk-data-bottles.json")
BACKUP_FILE = Path("assets/bulk-data-bottles.images-backup.json")
DELAY = 0.3
MAX_RETRIES = 3

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

session = requests.Session()
session.headers.update({"User-Agent": "MyLab Image Updater"})


def fetch_json(url, params=None):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = session.get(url, params=params, timeout=15)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            log.warning(f"Attempt {attempt}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(DELAY * attempt)
    return None


def make_600_url(src):
    """Insert _grande before file extension for 600x600."""
    if not src:
        return ""
    # Handle Shopify CDN URLs: insert _grande before .ext
    import re
    return re.sub(r'\.(\w+)(\?.*)?$', r'_grande.\1\2', src)


def check_image(url):
    """HEAD request to verify image exists."""
    try:
        r = session.head(url, timeout=5, allow_redirects=True)
        return r.status_code == 200
    except:
        return False


def main():
    log.info("=" * 50)
    log.info("Updating Takemoto bottle images")
    log.info("=" * 50)

    # Backup
    if BOTTLES_FILE.exists():
        shutil.copy2(BOTTLES_FILE, BACKUP_FILE)
        log.info(f"Backup: {BACKUP_FILE}")

    # Fetch all products
    log.info("Fetching products...")
    image_map = {}  # handle → { images, image_main, image_600 }
    page = 1
    total = 0

    while True:
        data = fetch_json(PRODUCTS_JSON, {"limit": 250, "page": page})
        if not data or not data.get("products"):
            break
        for p in data["products"]:
            handle = p.get("handle", "")
            images = []
            for img in p.get("images", []):
                src = img.get("src", "")
                if src:
                    images.append(src)

            if images:
                image_map[handle] = {
                    "image_main": images[0],
                    "image_600": make_600_url(images[0]),
                    "images_all": images
                }
            total += 1

        log.info(f"Page {page}: {len(data['products'])} products")
        page += 1
        time.sleep(DELAY)

    log.info(f"Total products: {total}, with images: {len(image_map)}")

    # Load bottles
    bottles_data = json.loads(BOTTLES_FILE.read_text(encoding="utf-8"))
    updated = 0
    no_match = 0
    no_image = 0
    errors = 0

    for bottle in bottles_data.get("bottles", []):
        handle = bottle.get("_raw_handle", "")
        if not handle and bottle.get("takemoto_url"):
            handle = bottle["takemoto_url"].rstrip("/").split("/")[-1]

        if handle not in image_map:
            no_match += 1
            continue

        img_data = image_map[handle]

        if not img_data["image_main"]:
            no_image += 1
            continue

        # Don't overwrite manual image_url_local
        bottle["image_url"] = img_data["image_main"]
        bottle["image_url_600"] = img_data["image_600"]
        bottle["image_url_external"] = img_data["image_main"]
        bottle["images_all"] = img_data["images_all"]
        bottle.pop("image_needs_review", None)
        updated += 1

    # Verify a sample of images
    log.info("Verifying images (sample)...")
    sample = [b for b in bottles_data["bottles"] if b.get("image_url_600")][:20]
    for b in sample:
        ok = check_image(b["image_url_600"])
        if not ok:
            b["image_needs_review"] = True
            errors += 1
            log.warning(f"Image error: {b['name']}")
        time.sleep(DELAY)

    # Save
    BOTTLES_FILE.write_text(json.dumps(bottles_data, ensure_ascii=False, indent=2), encoding="utf-8")

    log.info(f"\nRESULTS:")
    log.info(f"  Updated: {updated}")
    log.info(f"  No match: {no_match}")
    log.info(f"  No image: {no_image}")
    log.info(f"  Image errors: {errors}")
    log.info(f"  Total bottles: {len(bottles_data['bottles'])}")


if __name__ == "__main__":
    main()
