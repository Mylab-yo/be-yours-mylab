"""
Regenerate shopify-functions/tier-discount/src/tier-map.js from assets/ml-product-map.json.

Le tier map est la source de vérité pour les paliers de prix MY.LAB :
- Côté front : lu par mylab-product.js (cart drawer affiche les prix paliers)
- Côté checkout : compilé dans la Shopify Function tier-discount

Lance ce script chaque fois que tu modifies ml-product-map.json, puis redéploie
la function avec : cd shopify-functions/tier-discount && shopify app deploy
"""
import json
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO_ROOT, "assets", "ml-product-map.json")
DST = os.path.join(
    REPO_ROOT,
    "shopify-functions",
    "tier-discount",
    "extensions",
    "tier-discount",
    "src",
    "tier-map.js",
)


def main():
    with open(SRC, encoding="utf-8") as f:
        m = json.load(f)

    tier_map = {}
    for h, data in m.items():
        if h.startswith("_"):
            continue
        sizes = data.get("sizes", {})
        tiers = data.get("tiers", {})
        for size, handle in sizes.items():
            tier_str = tiers.get(size)
            if not tier_str:
                continue
            parsed = []
            for entry in tier_str.split(","):
                q, c = entry.split(":")
                parsed.append([int(q), int(c)])
            parsed.sort(key=lambda x: x[0])
            tier_map[handle] = parsed

    os.makedirs(os.path.dirname(DST), exist_ok=True)
    with open(DST, "w", encoding="utf-8") as f:
        f.write("// Auto-generated from assets/ml-product-map.json — DO NOT EDIT BY HAND\n")
        f.write("// Run: python scripts/build_tier_map.py to regenerate\n\n")
        f.write("export const TIER_MAP = ")
        f.write(json.dumps(tier_map, indent=2))
        f.write(";\n")

    print(f"OK — wrote {len(tier_map)} entries to {DST}")


if __name__ == "__main__":
    main()
