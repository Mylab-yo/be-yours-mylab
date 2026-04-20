#!/usr/bin/env python3
"""
MY.LAB — Synchronisation hebdomadaire catalogue Takemoto
=========================================================
Script unifié qui :
  1. Fetch les produits depuis eu.store.takemotopkg.com (Shopify JSON API)
  2. Filtre par contenance (INCHANGÉ)
  3. Enrichit via Playwright : couleurs disponibles, accessoires, MOQ
  4. Expanse en 1 entrée par couleur (TOUTES les références)
  5. Préserve les overrides manuels
  6. Upload sur le theme live Shopify via Admin API
  7. Logs + rapport CSV pour review

Usage:
  python scripts/sync_takemoto.py            # run complet avec upload
  python scripts/sync_takemoto.py --dry-run  # pas d'upload Shopify
  python scripts/sync_takemoto.py --skip-fetch  # utilise les données cachées

Dépendances:
  pip install requests beautifulsoup4 playwright
  playwright install chromium
"""

import argparse
import csv
import json
import logging
import os
import re
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

import requests

# ── CONFIG ──
BASE_URL = "https://eu.store.takemotopkg.com"
PRODUCTS_JSON = f"{BASE_URL}/collections/products/products.json"

# Shopify live theme upload
SHOPIFY_STORE = os.environ.get("SHOPIFY_STORE", "mylab-shop-3.myshopify.com")
SHOPIFY_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")
SHOPIFY_THEME_ID = os.environ.get("SHOPIFY_THEME_ID", "184014340430")  # Live theme

# File paths (resolved relative to repo root)
REPO_ROOT = Path(__file__).resolve().parent.parent
BOTTLES_FILE = REPO_ROOT / "assets" / "bulk-data-bottles.json"
RAW_CACHE = REPO_ROOT / "takemoto_raw_data.json"
CHECKPOINT_FILE = REPO_ROOT / "scripts" / ".sync_takemoto_checkpoint.json"
REPORT_CSV = REPO_ROOT / "scripts" / "sync_takemoto_report.csv"
LOG_FILE = REPO_ROOT / "scripts" / "sync_takemoto.log"

# Sanity-check thresholds
MIN_BOTTLES_EXPECTED = 500      # abort if final count < this
MAX_DROP_PCT = 0.30             # abort if new count drops >30% vs previous

# Throttling
DELAY = 1.5
MAX_RETRIES = 3

# ── CONTENANCE FILTER (INCHANGÉ — NE PAS MODIFIER) ──
MIN_CAPACITY_ML = 30
MAX_CAPACITY_ML = 1100
EXCLUDE_TAGS = {"food", "pet", "garden", "jardin", "alimentaire", "animal"}


def get_compatible_formats(capacity):
    """Map capacity to MY.LAB compatible formats.

    Le filtre actuel dans bulk-data-bottles.json utilise la capacité exacte
    (ex: 100ml → [100], 220ml → [220]). Inchangé par rapport au comportement prod.
    """
    if capacity is None:
        return []
    if MIN_CAPACITY_ML <= capacity <= MAX_CAPACITY_ML:
        return [capacity]
    return []


# ── LOGGING ──
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (MyLab Sync Bot; +https://mylab-shop-3.myshopify.com)"
})


# ── COLOR NORMALIZATION ──
COLOR_MAP = {
    "natural": "clear", "clear": "clear", "transparent": "clear",
    "amber": "amber", "ambre": "amber", "ambré": "amber", "brown": "amber",
    "butter yellow": "butter_yellow", "butter": "butter_yellow", "yellow": "butter_yellow",
    "white": "white", "blanc": "white",
    "black": "black", "noir": "black",
    "frosted": "frosted", "givre": "frosted", "givré": "frosted", "frost": "frosted",
    "green": "green", "vert": "green",
    "blue": "blue", "bleu": "blue",
    "grey": "mist", "gray": "mist", "smoke": "mist", "mist": "mist",
    "pink": "blush", "blush": "blush",
    "teal": "teal",
    "red": "red",
}


def normalize_color(raw):
    if not raw:
        return "clear"
    clean = raw.strip().lower()
    return COLOR_MAP.get(clean, re.sub(r"[^a-z0-9]+", "_", clean).strip("_") or "clear")


# ── DETECTION HELPERS (INCHANGÉ depuis scrape_takemoto.py) ──
def detect_capacity(product):
    title = product.get("title", "")
    title_lower = title.lower()
    tags = " ".join(product.get("tags", [])).lower() if isinstance(product.get("tags"), list) else product.get("tags", "").lower()
    combined = f"{title_lower} {tags}"

    patterns = [
        (r"(\d+)\s*ml\b", 1),
        (r"(\d+(?:\.\d+)?)\s*l\b", 1000),
        (r"(\d+)\s*oz\b", 29.5735),
    ]
    for pattern, multiplier in patterns:
        match = re.search(pattern, combined)
        if match:
            val = float(match.group(1)) * multiplier
            return int(round(val))

    code_match = re.search(r"[A-Z]+-(\d+)", title)
    if code_match:
        val = int(code_match.group(1))
        if 30 <= val <= 5000:
            return val

    num_match = re.findall(r"\b(\d+)\b", title)
    for n in num_match:
        val = int(n)
        if 30 <= val <= 5000:
            return val

    return None


def detect_type(product):
    combined = f"{product.get('title', '')} {product.get('body_html', '')} {' '.join(product.get('tags', []))}".lower()
    if "jar" in combined or "pot" in combined:
        return "jar"
    if "tube" in combined:
        return "tube"
    return "bottle"


def detect_closure(product):
    combined = f"{product.get('title', '')} {product.get('body_html', '')} {' '.join(product.get('tags', []))}".lower()
    if "pump" in combined or "pompe" in combined:
        return "pump"
    if "spray" in combined or "trigger" in combined or "mist" in combined:
        return "spray"
    if "dropper" in combined or "pipette" in combined:
        return "dropper"
    if "flip" in combined or "dispensing" in combined:
        return "flip_top"
    return "screw_cap"


def detect_material(product):
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


def detect_compatible_products(closure_type, capacity):
    """UI attend 'creme' (pas 'creme_coiffage') dans compatible_products.
    Cf. bulk-order-bottles.js: productFilter = category === 'creme_coiffage' ? 'creme' : category"""
    compat = []
    if closure_type in ("pump", "screw_cap") and capacity >= 200:
        compat.append("shampoing")
    if closure_type in ("pump", "flip_top") and capacity >= 200:
        compat.extend(["creme", "masque"])
    if closure_type == "spray" and capacity <= 300:
        compat.append("spray")
    if closure_type in ("dropper", "pump") and capacity <= 100:
        compat.extend(["serum", "huile"])
    if closure_type == "screw_cap" and capacity >= 200:
        compat.append("masque")
    return sorted(set(compat))


def detect_eco(product):
    combined = f"{product.get('title', '')} {product.get('body_html', '')} {' '.join(product.get('tags', []))}".lower()
    return any(kw in combined for kw in ["rpet", "pcr", "biomass", "bio-pet", "recycl", "sustainable", "plant-based"])


def is_relevant(product, capacity):
    """Filtre contenance — INCHANGÉ.
    Takemoto utilise des tags multi-catégorie ('PET CARE', 'HAIR CARE', etc.),
    donc exclure sur tag génère trop de faux positifs. On se limite à la contenance
    + à l'exclusion de forme (should_exclude_shape).
    """
    if capacity is None:
        return False
    return MIN_CAPACITY_ML <= capacity <= MAX_CAPACITY_ML


def should_exclude_shape(handle, name):
    """Exclude non-round bottles (square, oval, etc.) — same rule as enrich_colors.py."""
    if handle.lower().startswith("ambe-"):
        return True
    name_lower = name.lower()
    return any(w in name_lower for w in ("square", "oval", "rectangular", "flat", "oblong"))


# ── FETCH TAKEMOTO PRODUCTS ──
def fetch_products():
    all_products = []
    page = 1
    while True:
        log.info(f"Fetching Takemoto products page {page}...")
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = session.get(PRODUCTS_JSON, params={"limit": 250, "page": page}, timeout=20)
                resp.raise_for_status()
                data = resp.json()
                break
            except Exception as e:
                log.warning(f"  attempt {attempt}/{MAX_RETRIES}: {e}")
                if attempt == MAX_RETRIES:
                    log.error(f"Failed to fetch page {page}, stopping.")
                    return all_products
                time.sleep(DELAY * attempt)

        products = data.get("products", [])
        if not products:
            break
        all_products.extend(products)
        log.info(f"  page {page}: +{len(products)} (total {len(all_products)})")
        page += 1
        time.sleep(DELAY)

    return all_products


# ── ENRICHMENT VIA PLAYWRIGHT ──
async def enrich_with_playwright(product_urls, checkpoint):
    """Fetch color swatches + MOQ for each product URL.
    Returns: {handle: {available_colors, accessory_options, moq}}
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        log.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    results = dict(checkpoint)
    stats = {"fetched": 0, "cached": 0, "errors": 0}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (MyLab Sync)")
        page = await context.new_page()

        for i, (handle, url) in enumerate(product_urls):
            if handle in results and not results[handle].get("error"):
                stats["cached"] += 1
                continue

            log.info(f"[{i+1}/{len(product_urls)}] Enriching: {handle}")
            try:
                await page.goto(url, wait_until="networkidle", timeout=20000)
                await page.wait_for_timeout(1500)

                data = await page.evaluate("""() => {
                    const out = { groups: [], moq: null };

                    // MOQ
                    const qtyEl = document.querySelector('.product-quantity__count');
                    if (qtyEl) {
                        const m = qtyEl.textContent.trim().match(/(\\d[\\d,]*)/);
                        if (m) out.moq = parseInt(m[1].replace(/,/g, ''));
                    }

                    // Swatch groups
                    document.querySelectorAll('.product__swatches').forEach((container, idx) => {
                        const group = { label: '', colors: [] };
                        const accordion = container.closest('.accordion, [class*="accordion"]');
                        if (accordion) {
                            const trigger = accordion.querySelector('.accordion-trigger, [class*="trigger"]');
                            if (trigger) {
                                const titleEl = trigger.querySelector('[class*="title"]') || trigger;
                                group.label = titleEl.textContent.trim().split('\\n')[0].trim();
                            }
                        }
                        if (!group.label) group.label = idx === 0 ? 'Bottle' : 'Accessory ' + idx;

                        container.querySelectorAll('.product-swatch__card').forEach(card => {
                            const labelEl = card.querySelector('.product-swatch__label');
                            const name = labelEl ? labelEl.textContent.trim() : (card.getAttribute('title') || '');
                            if (name) group.colors.push(name);
                        });

                        if (group.colors.length > 0) out.groups.push(group);
                    });

                    return out;
                }""")

                available = [normalize_color(c) for c in data["groups"][0]["colors"]] if data["groups"] else []
                accessories = [
                    {"label": g["label"], "colors": [normalize_color(c) for c in g["colors"]], "raw_colors": g["colors"]}
                    for g in data["groups"][1:]
                ]

                results[handle] = {
                    "available_colors": available or ["clear"],
                    "accessory_options": accessories,
                    "moq": data.get("moq"),
                }
                stats["fetched"] += 1

            except Exception as e:
                log.warning(f"  enrichment failed: {e}")
                results[handle] = {"available_colors": ["clear"], "accessory_options": [], "moq": None, "error": True}
                stats["errors"] += 1

            # Incremental checkpoint every 25
            if (stats["fetched"] + stats["errors"]) % 25 == 0:
                CHECKPOINT_FILE.write_text(json.dumps(results, ensure_ascii=False), encoding="utf-8")
                log.info(f"  checkpoint saved ({len(results)} entries)")

            await page.wait_for_timeout(int(DELAY * 1000))

        await browser.close()

    CHECKPOINT_FILE.write_text(json.dumps(results, ensure_ascii=False), encoding="utf-8")
    log.info(f"Enrichment done: {stats}")
    return results


# ── BUILD BOTTLES (1 ENTRY PER COLOR) ──
def build_bottles(products, enrichment_map, existing_index):
    """Transform raw products into expanded bottle entries (1 per color).
    Preserves manual overrides from existing_index (keyed by base_id).
    """
    bottles = []
    skipped_contenance = 0
    skipped_shape = 0
    total_variants = 0

    for p in products:
        handle = p.get("handle", "")
        title = p.get("title", "")

        # Contenance filter — UNCHANGED
        capacity = detect_capacity(p)
        if not is_relevant(p, capacity):
            skipped_contenance += 1
            continue

        formats = get_compatible_formats(capacity)
        if not formats:
            skipped_contenance += 1
            continue

        if should_exclude_shape(handle, title):
            skipped_shape += 1
            continue

        closure = detect_closure(p)
        material = detect_material(p)
        compat = detect_compatible_products(closure, capacity)
        eco = detect_eco(p)

        # Images
        images_all = [img.get("src", "") for img in p.get("images", []) if img.get("src")]
        image_main = images_all[0] if images_all else ""

        # Price + SKU from the (single) variant
        price = None
        sku = ""
        if p.get("variants"):
            v = p["variants"][0]
            try:
                price_f = float(v.get("price", "0"))
                price = int(round(price_f * 100)) if price_f > 0 else None
            except (ValueError, TypeError):
                pass
            sku = v.get("sku") or ""

        # Description
        from bs4 import BeautifulSoup  # lazy import
        desc = ""
        if p.get("body_html"):
            desc = BeautifulSoup(p["body_html"], "html.parser").get_text(separator=" ", strip=True)[:300]

        # MOQ: enrichment first, else from description, else default 100
        enriched = enrichment_map.get(handle, {})
        moq = enriched.get("moq")
        if moq is None:
            moq_match = re.search(r"(?:minimum|moq|sets? of)[:\s]*(\d[\d,]*)", (p.get("body_html") or "").lower())
            if moq_match:
                try:
                    moq = int(moq_match.group(1).replace(",", ""))
                except ValueError:
                    pass
        if moq is None:
            moq = 100

        # Re-normalize colors from checkpoint (legacy data may have non-canonical names)
        colors = [normalize_color(c) for c in (enriched.get("available_colors") or ["clear"])]
        colors = list(dict.fromkeys(colors))  # dedupe, preserve order
        accessory_options = [
            {**ao, "colors": [normalize_color(c) for c in ao.get("colors", [])]}
            for ao in enriched.get("accessory_options", [])
        ]

        base_slug = re.sub(r"[^a-z0-9]+", "-", handle.lower()).strip("-")
        base_id = f"tk-{base_slug}"

        # Emit 1 entry per color variant
        for color in colors:
            entry_id = base_id if len(colors) == 1 else f"{base_id}--{color}"
            display_name = title if len(colors) == 1 else f"{title} — {color.replace('_', ' ').title()}"

            # Preserve manual overrides if present
            manual = existing_index.get(entry_id, {})

            bottle = {
                "id": entry_id,
                "name": display_name,
                "brand": "Takemoto",
                "type": detect_type(p),
                "closure_type": closure,
                "material": material,
                "capacity_ml": capacity,
                "compatible_formats": formats,
                "compatible_products": compat,
                "color": color,
                "available_colors": colors,
                "eco_label": eco,
                "image_url_external": image_main,
                "image_url_600": manual.get("image_url_600", image_main),
                "images_all": images_all[:4],
                "takemoto_url": f"{BASE_URL}/products/{handle}",
                "price_estimate": manual.get("price_estimate") if manual.get("_price_manual") else price,
                "min_order_qty": manual.get("min_order_qty") if manual.get("_moq_manual") else moq,
                "_raw_handle": handle,
                "_base_id": base_id,
            }
            if accessory_options:
                bottle["accessory_options"] = accessory_options

            # Preserve manual flags
            if manual.get("_price_manual"):
                bottle["_price_manual"] = True
            if manual.get("_moq_manual"):
                bottle["_moq_manual"] = True

            bottles.append(bottle)

            total_variants += 1

    log.info(f"Built {total_variants} bottle entries from {len(products)} products")
    log.info(f"  skipped (contenance): {skipped_contenance}")
    log.info(f"  skipped (shape):      {skipped_shape}")

    return bottles


# ── SANITY CHECK ──
def sanity_check(new_bottles, existing_bottles):
    new_count = len(new_bottles)
    old_count = len(existing_bottles)

    if new_count < MIN_BOTTLES_EXPECTED:
        log.error(f"ABORT: new count {new_count} < threshold {MIN_BOTTLES_EXPECTED}")
        return False

    if old_count > 0:
        drop_pct = (old_count - new_count) / old_count
        if drop_pct > MAX_DROP_PCT:
            log.error(f"ABORT: count dropped {drop_pct*100:.1f}% ({old_count} → {new_count}), max allowed {MAX_DROP_PCT*100:.0f}%")
            return False

    log.info(f"Sanity check OK: {old_count} → {new_count} ({'+' if new_count >= old_count else ''}{new_count - old_count})")
    return True


# ── UPLOAD TO SHOPIFY ──
def upload_to_shopify(json_content):
    if not SHOPIFY_TOKEN:
        log.error("SHOPIFY_ACCESS_TOKEN not set — skipping upload")
        return False

    url = f"https://{SHOPIFY_STORE}/admin/api/2024-01/themes/{SHOPIFY_THEME_ID}/assets.json"
    payload = {"asset": {"key": "assets/bulk-data-bottles.json", "value": json_content}}
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_TOKEN,
        "Content-Type": "application/json",
    }

    log.info(f"Uploading to Shopify theme {SHOPIFY_THEME_ID}...")
    resp = requests.put(url, json=payload, headers=headers, timeout=60)

    if resp.status_code >= 400:
        log.error(f"Shopify upload failed: {resp.status_code} {resp.text[:500]}")
        return False

    log.info("Shopify upload OK")
    return True


# ── REPORT CSV ──
def generate_report(bottles):
    with REPORT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["id", "name", "handle", "capacity_ml", "color", "material", "closure", "moq", "price_eur", "eco"])
        for b in bottles:
            price = f"{b['price_estimate']/100:.2f}" if b.get("price_estimate") else ""
            w.writerow([b["id"], b["name"], b["_raw_handle"], b["capacity_ml"], b["color"],
                        b["material"], b["closure_type"], b["min_order_qty"], price,
                        "oui" if b["eco_label"] else "non"])
    log.info(f"Report: {REPORT_CSV}")


# ── MAIN ──
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Pas d'upload Shopify")
    parser.add_argument("--skip-fetch", action="store_true", help="Utiliser le cache de produits")
    parser.add_argument("--skip-enrich", action="store_true", help="Pas d'enrichissement Playwright (utilise checkpoint seul)")
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("MY.LAB — Sync Takemoto")
    log.info("=" * 60)
    import asyncio

    # Step 1: Fetch products
    if args.skip_fetch and RAW_CACHE.exists():
        log.info(f"Using cached raw data: {RAW_CACHE}")
        products = json.loads(RAW_CACHE.read_text(encoding="utf-8"))
    else:
        products = fetch_products()
        RAW_CACHE.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")

    log.info(f"Total Takemoto products: {len(products)}")

    # Step 2: Filter by contenance first (only enrich relevant ones)
    relevant_urls = []
    for p in products:
        cap = detect_capacity(p)
        if not is_relevant(p, cap):
            continue
        if not get_compatible_formats(cap):
            continue
        handle = p.get("handle", "")
        if should_exclude_shape(handle, p.get("title", "")):
            continue
        relevant_urls.append((handle, f"{BASE_URL}/products/{handle}"))

    log.info(f"Relevant products (after contenance filter): {len(relevant_urls)}")

    # Step 3: Enrich with Playwright (colors, MOQ)
    checkpoint = {}
    if CHECKPOINT_FILE.exists():
        try:
            checkpoint = json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
            log.info(f"Loaded checkpoint: {len(checkpoint)} entries")
        except json.JSONDecodeError:
            checkpoint = {}

    if args.skip_enrich:
        log.info("Skipping enrichment (using checkpoint only)")
        enrichment = checkpoint
    else:
        enrichment = asyncio.run(enrich_with_playwright(relevant_urls, checkpoint))

    # Step 4: Build bottles with color variant expansion
    existing_index = {}
    if BOTTLES_FILE.exists():
        existing = json.loads(BOTTLES_FILE.read_text(encoding="utf-8"))
        existing_index = {b["id"]: b for b in existing.get("bottles", [])}
        log.info(f"Existing bottles: {len(existing_index)}")

    new_bottles = build_bottles(products, enrichment, existing_index)

    # Step 5: Sanity check
    if not sanity_check(new_bottles, list(existing_index.values())):
        log.error("Sanity check failed, not writing output.")
        return 1

    # Step 6: Write new JSON (with backup)
    if BOTTLES_FILE.exists():
        backup = BOTTLES_FILE.with_suffix(f".backup-{time.strftime('%Y%m%d')}.json")
        shutil.copy2(BOTTLES_FILE, backup)
        log.info(f"Backup: {backup.name}")

    # Preserve any top-level keys (color_labels etc.) from existing
    output = {}
    if BOTTLES_FILE.exists():
        output = json.loads(BOTTLES_FILE.read_text(encoding="utf-8"))
    output["_doc"] = "MY.LAB — Catalogue flacons Takemoto. Synchronisé automatiquement."
    output["_last_sync"] = time.strftime("%Y-%m-%d %H:%M:%S")
    output["_source"] = BASE_URL
    output["bottles"] = new_bottles

    # Compact JSON (no indent) — stays under Shopify's 5MB theme asset limit
    json_content = json.dumps(output, ensure_ascii=False, separators=(",", ":"))
    BOTTLES_FILE.write_text(json_content, encoding="utf-8")
    log.info(f"Wrote: {BOTTLES_FILE} ({len(new_bottles)} bottles, {len(json_content.encode())/1024/1024:.2f} MB)")

    # Step 7: Report CSV
    generate_report(new_bottles)

    # Step 8: Color distribution stats
    color_count = Counter(b["color"] for b in new_bottles)
    log.info(f"Color distribution: {dict(color_count.most_common())}")

    # Step 9: Upload to Shopify
    if args.dry_run:
        log.info("--dry-run: skipping Shopify upload")
    else:
        if not upload_to_shopify(json_content):
            return 2

    log.info("=" * 60)
    log.info(f"DONE — {len(new_bottles)} bottles")
    log.info("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
