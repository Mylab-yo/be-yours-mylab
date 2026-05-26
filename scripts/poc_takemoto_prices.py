#!/usr/bin/env python3
"""POC : extraire la décomposition prix flacon + accessoires depuis la page
produit Takemoto. Test sur HAIRDEX (s-apin-300-pb-v35-cap).

Si les sélecteurs DOM marchent ici, on intègre dans sync_takemoto.py.

Usage : python3 scripts/poc_takemoto_prices.py [handle ...]
Default handle : s-apin-300-pb-v35-cap
"""
import asyncio
import sys
import io
from playwright.async_api import async_playwright

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE_URL = "https://eu.store.takemotopkg.com"

EXTRACT_JS = r"""() => {
  const out = { unit_price_total: null, set_size: null, set_price: null, accessories: [], debug: [] };

  // 1. Bandeau prix : "Unit price (total) €1,30 1 Set (100 units) €130,00"
  const allText = document.body.innerText || "";
  // Cap to 2 decimals to avoid swallowing "1 Set" digits.
  const totalMatch = allText.match(/Unit price\s*\(?total\)?\s*€\s*(\d+[,.]\d{1,2})/i);
  if (totalMatch) out.unit_price_total = totalMatch[1].replace(",", ".");
  const setMatch = allText.match(/(\d+)\s*Set\s*\((\d+)\s*units?\)\s*€\s*(\d+[,.]?\d{0,2})/i);
  if (setMatch) { out.set_size = parseInt(setMatch[2]); out.set_price = setMatch[3].replace(",", "."); }

  // 2. Components : .accordion sections sont les vrais composants (Bottle,
  //    Cap, Plug, Sprayer, etc.). Filtre sur labels valides — le reste
  //    (recommandations "Other attachments" / "From the same collection")
  //    a été observé via section/[class*="accordion"] et est rejeté.
  document.querySelectorAll('.accordion').forEach(el => {
    const text = (el.innerText || '').slice(0, 500);
    const pm = text.match(/€\s*(\d+[,.]?\d{0,2})\s*\/\s*unit/i);
    if (!pm) return;
    const lines = text.split('\n').map(l => l.trim()).filter(Boolean);
    const label = lines[0] || '';
    const partName = lines.length > 1 ? lines[1] : '';
    out.accessories.push({ label, part_name: partName, price_eur: pm[1].replace(",", ".") });
  });

  // 3. Fallback debug: list all '€<num>/unit' occurrences in the page
  const allMatches = [...allText.matchAll(/€\s*(\d+[,.]?\d{0,2})\s*\/\s*unit/gi)];
  out.debug.push("Total €/unit matches in body: " + allMatches.length);
  allMatches.forEach((m, i) => {
    const idx = m.index;
    out.debug.push(`  [${i}] €${m[1]}/unit @ char ${idx}: "${allText.slice(Math.max(0, idx-40), idx+30).replace(/\n/g, ' | ')}"`);
  });

  return out;
}"""


async def main():
    handles = sys.argv[1:] or ["s-apin-300-pb-v35-cap"]
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent="Mozilla/5.0 (MyLab POC)")
        page = await ctx.new_page()
        for h in handles:
            url = f"{BASE_URL}/products/{h}"
            print(f"\n=== {h} ===")
            print(f"URL: {url}")
            try:
                await page.goto(url, wait_until="networkidle", timeout=20000)
                await page.wait_for_timeout(1500)
                data = await page.evaluate(EXTRACT_JS)
                print(f"  Unit price (total): {data['unit_price_total']} EUR")
                print(f"  Set: {data['set_size']} units / {data['set_price']} EUR")
                total_check = sum(float(a["price_eur"]) for a in data["accessories"] if a["price_eur"])
                print(f"  Components ({len(data['accessories'])}):")
                for i, acc in enumerate(data["accessories"]):
                    print(f"    [{i}] {acc['label']:10} part='{acc['part_name']:30}' price={acc['price_eur']:>5} EUR/unit")
                print(f"  Sum check: components={total_check:.2f}  total={data['unit_price_total']}  match={'OK' if abs(total_check - float(data['unit_price_total'] or 0)) < 0.01 else 'MISMATCH'}")
            except Exception as e:
                print(f"  ERROR: {e}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
