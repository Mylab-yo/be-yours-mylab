// @ts-check
import { TIER_MAP } from "./tier-map.js";

/**
 * MyLab Tier Discount — Shopify Product Discount Function.
 *
 * Backup non déployé. La voie de production actuelle = BSS B2B
 * Volume Pricing avec règles configurées dans leur dashboard.
 * Cette function existe au cas où BSS ne suffirait plus :
 * elle applique les paliers depuis assets/ml-product-map.json
 * (regénérer src/tier-map.js avec scripts/build_tier_map.py).
 */
const EMPTY_DISCOUNT = {
  discounts: [],
  discountApplicationStrategy: "FIRST",
};

export function run(input) {
  const discounts = [];

  for (const line of input.cart.lines) {
    const merch = line.merchandise;
    if (!merch || merch.__typename !== "ProductVariant") continue;

    const handle = merch.product?.handle;
    if (!handle) continue;

    const tiers = TIER_MAP[handle];
    if (!tiers) continue;

    const qty = line.quantity;
    let tierPriceCents = null;
    for (const [tQty, tCents] of tiers) {
      if (qty >= tQty) tierPriceCents = tCents;
      else break;
    }
    if (tierPriceCents == null) continue;

    const unitPriceAmount = parseFloat(line.cost.amountPerQuantity.amount);
    const unitPriceCents = Math.round(unitPriceAmount * 100);

    const discountPerUnitCents = unitPriceCents - tierPriceCents;
    if (discountPerUnitCents <= 0) continue;

    const discountPerUnit = (discountPerUnitCents / 100).toFixed(2);

    discounts.push({
      message: `Palier MY.LAB ×${qty}`,
      targets: [{ productVariant: { id: merch.id, quantity: qty } }],
      value: { fixedAmount: { amount: discountPerUnit } },
    });
  }

  if (discounts.length === 0) return EMPTY_DISCOUNT;
  return { discounts, discountApplicationStrategy: "FIRST" };
}
