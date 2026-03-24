#!/usr/bin/env python3
"""
MY.LAB — Enrich Takemoto bottles with real colors via Playwright
================================================================
Fetches each product page, extracts swatch colors, MOQ, and shape.
Removes non-round bottles. Updates assets/bulk-data-bottles.json.

Usage:
  pip install playwright
  playwright install chromium
  python enrich_colors.py
"""

import asyncio
import json
import shutil
import time
import logging
import re
from pathlib import Path
from collections import Counter

from playwright.async_api import async_playwright

# ── CONFIG ──
BOTTLES_FILE = Path("assets/bulk-data-bottles.json")
BACKUP_FILE = Path("assets/bulk-data-bottles.backup3.json")
CHECKPOINT_FILE = Path("enrich_checkpoint.json")
ERROR_LOG = Path("enrich_errors.log")
DELAY = 1.5

# ── LOGGING ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(ERROR_LOG, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ── COLOR MAPPING ──
COLOR_MAP = {
    "natural": "clear",
    "clear": "clear",
    "transparent": "clear",
    "amber": "amber",
    "ambré": "amber",
    "butter yellow": "butter_yellow",
    "yellow": "butter_yellow",
    "white": "white",
    "blanc": "white",
    "black": "black",
    "noir": "black",
    "frosted": "frosted",
    "givré": "frosted",
    "frost": "frosted",
    "green": "green",
    "vert": "green",
    "blue": "blue",
    "bleu": "blue",
    "brown": "amber",
    "grey": "grey",
    "gray": "grey",
    "pink": "pink",
    "smoke": "smoke",
}


def normalize_color(raw):
    """Normalize a color name to a standard code."""
    clean = raw.strip().lower()
    return COLOR_MAP.get(clean, clean.replace(" ", "_"))


def should_exclude(bottle):
    """Check if bottle should be excluded (non-round shape)."""
    handle = (bottle.get("_raw_handle") or "").lower()
    name = (bottle.get("name") or "").lower()

    # AMBE prefix = square bottles on Takemoto
    if handle.startswith("ambe-"):
        return True

    exclude_words = ["square", "oval", "rectangular", "flat", "oblong"]
    for word in exclude_words:
        if word in name:
            return True

    return False


def load_checkpoint():
    """Load checkpoint of already-processed handles."""
    if CHECKPOINT_FILE.exists():
        data = json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
        return data.get("processed", {})
    return {}


def save_checkpoint(processed):
    """Save checkpoint."""
    CHECKPOINT_FILE.write_text(
        json.dumps({"processed": processed}, ensure_ascii=False),
        encoding="utf-8"
    )


async def extract_colors(page, url):
    """Extract color swatches, MOQ, and accessory options from a Takemoto product page."""
    try:
        await page.goto(url, wait_until="networkidle", timeout=20000)
        await page.wait_for_timeout(2000)
    except Exception as e:
        log.error(f"Failed to load {url}: {e}")
        return None

    result = await page.evaluate("""() => {
        const data = { groups: [], moq: null, moq_raw: null };

        // Extract MOQ from .product-quantity__count
        const qtyEl = document.querySelector('.product-quantity__count');
        if (qtyEl) {
            data.moq_raw = qtyEl.textContent.trim();
            const match = data.moq_raw.match(/(\\d[\\d,]*)/);
            if (match) data.moq = parseInt(match[1].replace(',', ''));
        }

        // Find all swatch groups
        // The structure is: parent contains a label + div.product__swatches
        const swatchContainers = document.querySelectorAll('.product__swatches');

        swatchContainers.forEach((container, idx) => {
            const group = { label: '', colors: [], raw_colors: [] };

            // Try to find the group label (accordion trigger or preceding text)
            const accordion = container.closest('.accordion') || container.closest('[class*="accordion"]');
            if (accordion) {
                const trigger = accordion.querySelector('.accordion-trigger, [class*="trigger"]');
                if (trigger) {
                    // Extract just the component name (Bottle, Spray, Cap, etc.)
                    const titleEl = trigger.querySelector('[class*="title"]') || trigger;
                    group.label = titleEl.textContent.trim().split('\\n')[0].trim();
                }
            }

            // If no label found, use index
            if (!group.label) group.label = idx === 0 ? 'Bottle' : 'Accessory ' + idx;

            // Extract swatch colors
            const cards = container.querySelectorAll('.product-swatch__card');
            cards.forEach(card => {
                const labelEl = card.querySelector('.product-swatch__label');
                const colorName = labelEl ? labelEl.textContent.trim() : (card.getAttribute('title') || '');
                if (colorName) {
                    group.raw_colors.push(colorName);
                    group.colors.push(colorName);
                }
            });

            if (group.colors.length > 0) {
                data.groups.push(group);
            }
        });

        return data;
    }""")

    return result


async def main():
    log.info("=" * 60)
    log.info("MY.LAB — Enrich Takemoto Bottles (Colors + Shape)")
    log.info("=" * 60)

    # Step 1: Backup
    if BOTTLES_FILE.exists():
        shutil.copy2(BOTTLES_FILE, BACKUP_FILE)
        log.info(f"Backup saved: {BACKUP_FILE}")

    data = json.loads(BOTTLES_FILE.read_text(encoding="utf-8"))
    bottles = data.get("bottles", [])
    log.info(f"Total bottles: {len(bottles)}")

    # Step 2A: Mark excluded (non-round) bottles
    excluded = 0
    kept = 0
    to_fetch = []

    for b in bottles:
        if should_exclude(b):
            b["shape"] = "excluded"
            excluded += 1
        else:
            b["shape"] = "round"
            kept += 1
            to_fetch.append(b)

    log.info(f"Round (kept): {kept}, Excluded (non-round): {excluded}")

    # Step 2B: Fetch colors with Playwright
    checkpoint = load_checkpoint()
    log.info(f"Checkpoint: {len(checkpoint)} already processed")

    stats = {
        "fetched": 0,
        "skipped_checkpoint": 0,
        "errors": 0,
        "colors_found": 0,
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (MyLab Color Enricher)"
        )
        page = await context.new_page()

        for i, b in enumerate(to_fetch):
            handle = b.get("_raw_handle", b.get("id", ""))
            url = b.get("takemoto_url", "")

            if not url:
                continue

            # Check checkpoint
            if handle in checkpoint:
                cached = checkpoint[handle]
                b["available_colors"] = cached.get("available_colors", [])
                b["color"] = cached.get("color", b.get("color", "clear"))
                b["accessory_options"] = cached.get("accessory_options", [])
                if cached.get("moq"):
                    b["min_order_qty"] = cached["moq"]
                stats["skipped_checkpoint"] += 1
                continue

            log.info(f"[{i+1}/{len(to_fetch)}] Fetching: {handle}")

            result = await extract_colors(page, url)

            if result is None:
                stats["errors"] += 1
                checkpoint[handle] = {"error": True}
            else:
                # Process color groups
                available_colors = []
                accessory_options = []

                for gi, group in enumerate(result.get("groups", [])):
                    normalized = [normalize_color(c) for c in group.get("colors", [])]

                    if gi == 0:
                        # First group = bottle colors
                        available_colors = normalized
                        if normalized:
                            b["color"] = normalized[0]
                            b["available_colors"] = normalized
                    else:
                        # Subsequent groups = accessories
                        accessory_options.append({
                            "label": group.get("label", f"Accessory {gi}"),
                            "colors": normalized,
                            "raw_colors": group.get("raw_colors", [])
                        })

                b["accessory_options"] = accessory_options

                # Update MOQ
                if result.get("moq"):
                    b["min_order_qty"] = result["moq"]

                stats["fetched"] += 1
                if available_colors:
                    stats["colors_found"] += 1

                # Save to checkpoint
                checkpoint[handle] = {
                    "available_colors": available_colors,
                    "color": b.get("color", "clear"),
                    "accessory_options": accessory_options,
                    "moq": result.get("moq"),
                }

            # Checkpoint save every 25
            if (stats["fetched"] + stats["errors"]) % 25 == 0:
                save_checkpoint(checkpoint)
                log.info(f"  Checkpoint saved ({len(checkpoint)} entries)")

            await asyncio.sleep(DELAY)

        await browser.close()

    # Final checkpoint save
    save_checkpoint(checkpoint)

    # Step 4: Remove excluded bottles
    before_count = len(bottles)
    data["bottles"] = [b for b in bottles if b.get("shape") != "excluded"]
    after_count = len(data["bottles"])
    log.info(f"Removed {before_count - after_count} non-round bottles")

    # Clean up temp fields
    for b in data["bottles"]:
        b.pop("shape", None)

    # Save
    BOTTLES_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    # Step 5: Summary
    color_counter = Counter()
    unknown_colors = set()
    all_raw = set()

    for b in data["bottles"]:
        c = b.get("color", "clear")
        color_counter[c] += 1
        for ac in b.get("available_colors", []):
            if ac not in COLOR_MAP.values() and ac not in [v for v in COLOR_MAP.values()]:
                unknown_colors.add(ac)

    log.info("\n" + "=" * 60)
    log.info("RÉCAPITULATIF")
    log.info("=" * 60)
    log.info(f"  Flacons conservés (ronds) : {after_count}")
    log.info(f"  Flacons exclus (non-ronds): {excluded}")
    log.info(f"  Pages fetchées            : {stats['fetched']}")
    log.info(f"  Pages en cache (checkpoint): {stats['skipped_checkpoint']}")
    log.info(f"  Erreurs d'accès           : {stats['errors']}")
    log.info(f"  Couleurs trouvées         : {stats['colors_found']}")

    log.info(f"\n  Répartition par couleur :")
    for color, count in color_counter.most_common():
        log.info(f"    {color}: {count}")

    if unknown_colors:
        log.info(f"\n  Couleurs non reconnues (à vérifier) :")
        for uc in sorted(unknown_colors):
            log.info(f"    → {uc}")

    log.info("=" * 60)
    log.info("DONE!")


if __name__ == "__main__":
    asyncio.run(main())
