#!/usr/bin/env python3
"""
MY.LAB — Takemoto Pricing & MOQ Scraper
========================================
Récupère les prix et MOQ depuis eu.store.takemotopkg.com
Met à jour assets/bulk-data-bottles.json sans écraser les données manuelles.

Usage:
  python scrape_takemoto_pricing.py
"""

import json
import csv
import os
import re
import time
import shutil
import logging
from pathlib import Path
from collections import Counter

import requests
from bs4 import BeautifulSoup

# ── CONFIG ──
BASE_URL = "https://eu.store.takemotopkg.com"
PRODUCTS_JSON = f"{BASE_URL}/collections/products/products.json"
BOTTLES_FILE = Path("assets/bulk-data-bottles.json")
BACKUP_FILE = Path("assets/bulk-data-bottles.backup.json")
REPORT_CSV = Path("takemoto_pricing_report.csv")
LOG_FILE = Path("scrape_pricing.log")
DELAY = 1.5
MAX_RETRIES = 3

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

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (MyLab Pricing Bot; +https://mylab-shop-3.myshopify.com)"
})


def fetch_json(url, params=None):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            log.warning(f"Attempt {attempt}/{MAX_RETRIES} failed for {url}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(DELAY * attempt)
    return None


def fetch_html(url):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, timeout=15)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            log.warning(f"HTML attempt {attempt}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(DELAY * attempt)
    return None


# ── MOQ EXTRACTION ──
def extract_moq_from_tags(tags):
    """Check tags for MOQ patterns."""
    if not tags:
        return None, None
    tag_str = " ".join(tags) if isinstance(tags, list) else str(tags)
    tag_lower = tag_str.lower()

    patterns = [
        r"moq[:\s-]*(\d+)",
        r"min[:\s-]*(\d+)",
        r"minimum[:\s-]*(\d+)",
    ]
    for p in patterns:
        m = re.search(p, tag_lower)
        if m:
            return int(m.group(1)), "api_tags"
    return None, None


def extract_moq_from_body(body_html):
    """Extract MOQ from product description HTML."""
    if not body_html:
        return None, None

    soup = BeautifulSoup(body_html, "html.parser")
    text = soup.get_text(separator=" ", strip=True).lower()

    patterns = [
        (r"minimum\s*(?:order\s*)?(?:quantity)?[:\s]*(\d[\d,]*)", "body_html"),
        (r"moq[:\s]*(\d[\d,]*)", "body_html"),
        (r"min(?:imum)?\s*order[:\s]*(\d[\d,]*)", "body_html"),
        (r"from\s+(\d[\d,]*)\s*(?:units?|pcs?|pieces?)", "body_html"),
        (r"à partir de\s+(\d[\d,]*)\s*(?:unités?|pièces?)", "body_html"),
        (r"order\s*minimum[:\s]*(\d[\d,]*)", "body_html"),
    ]
    for p, source in patterns:
        m = re.search(p, text)
        if m:
            val = int(m.group(1).replace(",", ""))
            if 1 <= val <= 100000:
                return val, source
    return None, None


def extract_moq_from_page(handle):
    """Scrape product page HTML for MOQ if API doesn't have it."""
    url = f"{BASE_URL}/products/{handle}"
    soup = fetch_html(url)
    if not soup:
        return None, None

    text = soup.get_text(separator=" ", strip=True).lower()

    patterns = [
        (r"minimum\s*(?:order\s*)?(?:quantity)?[:\s]*(\d[\d,]*)", "page_scrape"),
        (r"moq[:\s]*(\d[\d,]*)", "page_scrape"),
        (r"min(?:imum)?\s*order[:\s]*(\d[\d,]*)", "page_scrape"),
        (r"from\s+(\d[\d,]*)\s*(?:units?|pcs?|pieces?)", "page_scrape"),
        (r"(\d[\d,]*)\s*(?:units?|pcs?|pieces?)\s*minimum", "page_scrape"),
    ]
    for p, source in patterns:
        m = re.search(p, text)
        if m:
            val = int(m.group(1).replace(",", ""))
            if 1 <= val <= 100000:
                return val, source

    # Check for MOQ in structured data or meta tags
    for meta in soup.find_all("meta"):
        content = (meta.get("content") or "").lower()
        for p, source in patterns:
            m = re.search(p, content)
            if m:
                val = int(m.group(1).replace(",", ""))
                if 1 <= val <= 100000:
                    return val, "page_meta"

    return None, None


def extract_price_tiers(body_html):
    """Extract price tier tables from description."""
    if not body_html:
        return []

    soup = BeautifulSoup(body_html, "html.parser")
    tiers = []

    # Look for table patterns
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                text = " ".join(c.get_text(strip=True) for c in cells).lower()
                # Pattern: "100-499 | 1.50€" or "100+ | €1.30"
                m = re.search(r"(\d+)\s*[-–]\s*(\d+).*?(\d+[.,]\d+)", text)
                if m:
                    tiers.append({
                        "min_qty": int(m.group(1)),
                        "max_qty": int(m.group(2)),
                        "price": float(m.group(3).replace(",", "."))
                    })
                else:
                    m = re.search(r"(\d+)\s*\+.*?(\d+[.,]\d+)", text)
                    if m:
                        tiers.append({
                            "min_qty": int(m.group(1)),
                            "max_qty": None,
                            "price": float(m.group(2).replace(",", "."))
                        })

    # Also check plain text for tier patterns
    text = soup.get_text(separator="\n", strip=True)
    for line in text.split("\n"):
        line_lower = line.lower().strip()
        m = re.search(r"(\d+)\s*[-–]\s*(\d+)\s*(?:units?|pcs?)?\s*[:|→]\s*€?\s*(\d+[.,]\d+)", line_lower)
        if m:
            tier = {
                "min_qty": int(m.group(1)),
                "max_qty": int(m.group(2)),
                "price": float(m.group(3).replace(",", "."))
            }
            if tier not in tiers:
                tiers.append(tier)

    return sorted(tiers, key=lambda t: t["min_qty"]) if tiers else []


# ── MAIN LOGIC ──
def fetch_all_products():
    """Fetch all Takemoto products via JSON API."""
    all_products = []
    page = 1

    while True:
        log.info(f"Fetching products page {page}...")
        data = fetch_json(PRODUCTS_JSON, params={"limit": 250, "page": page})
        if not data:
            break

        products = data.get("products", [])
        if not products:
            break

        all_products.extend(products)
        log.info(f"Page {page}: {len(products)} products (total: {len(all_products)})")
        page += 1
        time.sleep(DELAY)

    return all_products


def build_pricing_map(products):
    """Build a map of handle → pricing data."""
    pricing = {}
    moq_sources = Counter()
    prices_found = 0
    moq_found = 0
    needs_review = 0
    page_scrapes = 0

    for i, p in enumerate(products):
        handle = p.get("handle", "")
        title = p.get("title", "")
        tags = p.get("tags", [])
        body = p.get("body_html", "")

        # Extract price from variants
        variants = []
        min_price = None
        compare_price = None

        for v in p.get("variants", []):
            price = None
            try:
                price = float(v.get("price", "0"))
            except (ValueError, TypeError):
                pass

            cp = None
            try:
                cp = float(v.get("compare_at_price")) if v.get("compare_at_price") else None
            except (ValueError, TypeError):
                pass

            variants.append({
                "variant_id": str(v.get("id", "")),
                "title": v.get("title", "Default"),
                "sku": v.get("sku", ""),
                "price": price,
                "compare_at_price": cp,
                "available": v.get("available", True)
            })

            if price and price > 0:
                if min_price is None or price < min_price:
                    min_price = price
                if cp and (compare_price is None or cp < compare_price):
                    compare_price = cp

        if min_price and min_price > 0:
            prices_found += 1

        # Extract MOQ — cascade strategy
        moq, moq_source = extract_moq_from_tags(tags)

        if moq is None:
            moq, moq_source = extract_moq_from_body(body)

        if moq is None and page_scrapes < 50:
            # Limit page scrapes to avoid hammering the server
            log.info(f"  [{i+1}/{len(products)}] Scraping page for MOQ: {handle}")
            moq, moq_source = extract_moq_from_page(handle)
            page_scrapes += 1
            time.sleep(DELAY)

        moq_needs_review = moq is None
        if moq is not None:
            moq_found += 1
            moq_sources[moq_source] += 1
        else:
            needs_review += 1
            moq_source = None

        # Extract price tiers
        price_tiers = extract_price_tiers(body)

        pricing[handle] = {
            "handle": handle,
            "title": title,
            "price_unit": min_price,
            "price_currency": "EUR",
            "compare_at_price": compare_price,
            "moq": moq,
            "moq_source": moq_source,
            "moq_needs_review": moq_needs_review,
            "variants": variants,
            "price_tiers": price_tiers,
            "price_last_updated": time.strftime("%Y-%m-%d"),
            "pricing_notes": "",
            "tags": tags
        }

        if (i + 1) % 50 == 0:
            log.info(f"  Processed {i+1}/{len(products)} products...")

    log.info(f"\nPricing extraction complete:")
    log.info(f"  Products with price: {prices_found}/{len(products)}")
    log.info(f"  Products with MOQ: {moq_found}/{len(products)}")
    log.info(f"  Products needing review: {needs_review}")
    log.info(f"  MOQ sources: {dict(moq_sources)}")
    log.info(f"  Page scrapes performed: {page_scrapes}")

    if prices_found > 0:
        all_prices = [v["price_unit"] for v in pricing.values() if v["price_unit"]]
        log.info(f"  Price range: {min(all_prices):.2f}€ — {max(all_prices):.2f}€")

    if moq_found > 0:
        all_moqs = [v["moq"] for v in pricing.values() if v["moq"]]
        moq_counts = Counter(all_moqs)
        log.info(f"  Most common MOQs: {moq_counts.most_common(5)}")

    return pricing


def update_bottles_json(pricing_map):
    """Update bulk-data-bottles.json with pricing data."""
    # Backup
    if BOTTLES_FILE.exists():
        shutil.copy2(BOTTLES_FILE, BACKUP_FILE)
        log.info(f"Backup saved: {BACKUP_FILE}")

    data = json.loads(BOTTLES_FILE.read_text(encoding="utf-8"))
    updated = 0
    new_products = 0
    skipped_manual = 0
    existing_handles = set()

    for bottle in data.get("bottles", []):
        # Match by handle (from _raw_handle or construct from takemoto_url)
        handle = bottle.get("_raw_handle", "")
        if not handle and bottle.get("takemoto_url"):
            handle = bottle["takemoto_url"].rstrip("/").split("/")[-1]

        existing_handles.add(handle)

        if handle not in pricing_map:
            log.debug(f"No pricing data for: {bottle.get('name', handle)}")
            continue

        pm = pricing_map[handle]

        # Don't overwrite manually-set prices
        if bottle.get("price_estimate") is not None and bottle.get("_price_manual"):
            skipped_manual += 1
            log.debug(f"Skipping manual price: {bottle['name']}")
            continue

        # Update pricing fields
        if pm["price_unit"] is not None and pm["price_unit"] > 0:
            bottle["price_estimate"] = int(round(pm["price_unit"] * 100))  # centimes

        bottle["compare_at_price"] = int(round(pm["compare_at_price"] * 100)) if pm["compare_at_price"] else None
        bottle["price_currency"] = pm["price_currency"]

        if pm["moq"] is not None:
            bottle["min_order_qty"] = pm["moq"]

        bottle["moq_source"] = pm["moq_source"]
        bottle["moq_needs_review"] = pm["moq_needs_review"]
        bottle["variants"] = pm["variants"]
        bottle["price_tiers"] = pm["price_tiers"]
        bottle["price_last_updated"] = pm["price_last_updated"]
        bottle["_raw_handle"] = handle

        updated += 1

    # Check for new products not yet in bottles
    for handle, pm in pricing_map.items():
        if handle in existing_handles:
            continue

        # Only add if it looks relevant (has a capacity we can detect)
        title = pm["title"]
        capacity = None
        code_match = re.search(r"[A-Z]+-(\d+)", title)
        if code_match:
            val = int(code_match.group(1))
            if 30 <= val <= 1100:
                capacity = val

        if capacity is None:
            continue

        # Determine compatible formats
        formats = []
        if 25 <= capacity <= 60:
            formats.append(50)
        if 180 <= capacity <= 250:
            formats.append(200)
        if 450 <= capacity <= 550:
            formats.append(500)
        if 900 <= capacity <= 1100:
            formats.append(1000)

        if not formats:
            continue

        slug = re.sub(r"[^a-z0-9]+", "-", handle.lower()).strip("-")

        new_bottle = {
            "id": f"tk-{slug}",
            "name": pm["title"],
            "brand": "Takemoto",
            "type": "bottle",
            "closure_type": "screw_cap",
            "material": "PET",
            "capacity_ml": capacity,
            "compatible_formats": formats,
            "compatible_products": [],
            "color": "clear",
            "eco_label": False,
            "image_url": "",
            "image_url_external": "",
            "takemoto_url": f"{BASE_URL}/products/{handle}",
            "price_estimate": int(round(pm["price_unit"] * 100)) if pm["price_unit"] else None,
            "price_currency": "EUR",
            "dimensions": {"height_mm": None, "diameter_mm": None},
            "min_order_qty": pm["moq"] or 100,
            "moq_source": pm["moq_source"],
            "moq_needs_review": pm["moq_needs_review"],
            "variants": pm["variants"],
            "price_tiers": pm["price_tiers"],
            "price_last_updated": pm["price_last_updated"],
            "notes": "",
            "new_product": True,
            "_raw_handle": handle
        }
        data["bottles"].append(new_bottle)
        new_products += 1

    # Save
    BOTTLES_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    log.info(f"\nUpdated bulk-data-bottles.json:")
    log.info(f"  Updated: {updated}")
    log.info(f"  New products added: {new_products}")
    log.info(f"  Skipped (manual): {skipped_manual}")
    log.info(f"  Total bottles: {len(data['bottles'])}")

    return data


def generate_report(data):
    """Generate CSV report for manual review."""
    with open(REPORT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow([
            "Handle", "Nom", "Contenance (ml)", "Prix (€)",
            "MOQ", "MOQ Source", "Review nécessaire",
            "Nb variantes", "Paliers de prix", "URL",
            "Nouveau"
        ])
        for b in data.get("bottles", []):
            price_str = f"{b['price_estimate']/100:.2f}" if b.get("price_estimate") else ""
            writer.writerow([
                b.get("_raw_handle", ""),
                b["name"],
                b.get("capacity_ml", ""),
                price_str,
                b.get("min_order_qty", ""),
                b.get("moq_source", ""),
                "OUI" if b.get("moq_needs_review") else "",
                len(b.get("variants", [])),
                "OUI" if b.get("price_tiers") else "",
                b.get("takemoto_url", ""),
                "NOUVEAU" if b.get("new_product") else ""
            ])
    log.info(f"Report saved: {REPORT_CSV}")


# ── MAIN ──
def main():
    log.info("=" * 60)
    log.info("MY.LAB — Takemoto Pricing & MOQ Scraper")
    log.info("=" * 60)

    # Step 1: Fetch all products
    log.info("\n[1/4] Fetching products from Takemoto...")
    products = fetch_all_products()
    log.info(f"Total products fetched: {len(products)}")

    # Step 2: Extract pricing
    log.info("\n[2/4] Extracting pricing and MOQ...")
    pricing_map = build_pricing_map(products)

    # Step 3: Update bottles JSON
    log.info("\n[3/4] Updating bulk-data-bottles.json...")
    updated_data = update_bottles_json(pricing_map)

    # Step 4: Generate report
    log.info("\n[4/4] Generating report...")
    generate_report(updated_data)

    # Summary
    bottles = updated_data.get("bottles", [])
    with_price = sum(1 for b in bottles if b.get("price_estimate"))
    with_moq = sum(1 for b in bottles if b.get("min_order_qty") and not b.get("moq_needs_review"))
    review_needed = sum(1 for b in bottles if b.get("moq_needs_review"))

    log.info("\n" + "=" * 60)
    log.info("RÉSUMÉ")
    log.info("=" * 60)
    log.info(f"  Total flacons : {len(bottles)}")
    log.info(f"  Avec prix     : {with_price}")
    log.info(f"  Avec MOQ      : {with_moq}")
    log.info(f"  Review requise: {review_needed}")

    if with_price > 0:
        prices = [b["price_estimate"]/100 for b in bottles if b.get("price_estimate")]
        log.info(f"  Fourchette    : {min(prices):.2f}€ — {max(prices):.2f}€")

    log.info(f"\nFichiers générés :")
    log.info(f"  → {BOTTLES_FILE} (mis à jour)")
    log.info(f"  → {BACKUP_FILE} (backup)")
    log.info(f"  → {REPORT_CSV} (pour validation)")
    log.info(f"  → {LOG_FILE} (logs)")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
