#!/usr/bin/env python3
"""
Test script: Extract color options from a Takemoto product page using Playwright.
"""

import asyncio
from playwright.async_api import async_playwright


URL = "https://eu.store.takemotopkg.com/products/ph-200-z-155-c110-1-290-spray"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print(f"Opening: {URL}")
        await page.goto(URL, wait_until="networkidle", timeout=30000)

        # Wait a bit more for JS widgets to render
        await page.wait_for_timeout(3000)

        print("\n" + "=" * 60)
        print("1. SWATCH / COLOR ELEMENTS")
        print("=" * 60)

        # Search for various swatch/color selectors
        selectors = [
            "[data-color]",
            "[data-value]",
            ".swatch",
            ".color-swatch",
            "[class*='swatch']",
            "[class*='color']",
            "[class*='option'] input",
            "[class*='option'] button",
            "[class*='option'] label",
            "select[name*='color' i]",
            "select[name*='Color' i]",
            "select option",
            "[class*='variant'] button",
            "[class*='variant'] label",
            "fieldset",
            "legend",
            "[role='radiogroup']",
            "[role='listbox']",
            "input[type='radio']",
        ]

        for sel in selectors:
            elements = await page.query_selector_all(sel)
            if elements:
                print(f"\n  {sel}: {len(elements)} elements")
                for el in elements[:10]:
                    text = await el.text_content()
                    attrs = await el.evaluate("""el => {
                        const obj = {};
                        for (const attr of el.attributes) obj[attr.name] = attr.value;
                        return obj;
                    }""")
                    tag = await el.evaluate("el => el.tagName.toLowerCase()")
                    print(f"    <{tag}> text='{(text or '').strip()[:60]}' attrs={attrs}")

        print("\n" + "=" * 60)
        print("2. PRODUCT OPTIONS SECTIONS (HTML)")
        print("=" * 60)

        # Look for product form or options container
        option_selectors = [
            ".product-form",
            ".product__options",
            ".product-options",
            "[class*='product-form']",
            "[class*='ProductForm']",
            "form[action*='cart']",
            "[class*='option-selector']",
            "[class*='selector-wrapper']",
        ]

        for sel in option_selectors:
            el = await page.query_selector(sel)
            if el:
                html = await el.inner_html()
                print(f"\n  {sel} (first {min(len(html), 1500)} chars):")
                print(f"  {html[:1500]}")
                break

        print("\n" + "=" * 60)
        print("3. JAVASCRIPT PRODUCT DATA")
        print("=" * 60)

        # Extract product data from JS context
        js_data = await page.evaluate("""() => {
            const results = {};

            // Check for Shopify product object
            if (window.ShopifyAnalytics && window.ShopifyAnalytics.meta && window.ShopifyAnalytics.meta.product) {
                results.shopifyMeta = window.ShopifyAnalytics.meta.product;
            }

            // Check for product JSON in script tags
            const scripts = document.querySelectorAll('script[type="application/json"]');
            results.jsonBlocks = [];
            scripts.forEach((s, i) => {
                try {
                    const obj = JSON.parse(s.textContent);
                    if (obj.product || obj.variants || obj.options || obj.id) {
                        results.jsonBlocks.push({
                            index: i,
                            id: s.id || '',
                            dataAttr: s.dataset ? Object.fromEntries(Object.entries(s.dataset)) : {},
                            keys: Object.keys(obj),
                            hasProduct: !!obj.product,
                            hasVariants: !!(obj.variants || (obj.product && obj.product.variants)),
                            optionNames: obj.product ? obj.product.options?.map(o => o.name) : (obj.options?.map(o => o.name || o) || []),
                            variantCount: obj.product ? obj.product.variants?.length : (obj.variants?.length || 0),
                            sampleVariants: (obj.product?.variants || obj.variants || []).slice(0, 5).map(v => ({
                                title: v.title,
                                option1: v.option1,
                                option2: v.option2,
                                option3: v.option3,
                                price: v.price,
                                available: v.available
                            }))
                        });
                    }
                } catch(e) {}
            });

            // Check for any global product variable
            if (window.product) results.windowProduct = { title: window.product.title, options: window.product.options };
            if (window.theme && window.theme.product) results.themeProduct = { title: window.theme.product.title };
            if (window.Shopify && window.Shopify.product) results.shopifyProduct = window.Shopify.product;

            // Check for custom color picker widgets
            const colorPickers = document.querySelectorAll('[class*="color"], [class*="swatch"], [data-option-name]');
            results.colorPickerElements = [];
            colorPickers.forEach(el => {
                results.colorPickerElements.push({
                    tag: el.tagName,
                    className: el.className.substring(0, 100),
                    dataAttrs: Object.fromEntries(
                        Array.from(el.attributes)
                            .filter(a => a.name.startsWith('data-'))
                            .map(a => [a.name, a.value.substring(0, 50)])
                    ),
                    text: el.textContent.trim().substring(0, 60)
                });
            });

            return results;
        }""")

        import json
        print(json.dumps(js_data, indent=2, ensure_ascii=False))

        print("\n" + "=" * 60)
        print("4. OG DESCRIPTION (shape, material, MOQ)")
        print("=" * 60)

        og_desc = await page.evaluate("""() => {
            const meta = document.querySelector('meta[property="og:description"]');
            return meta ? meta.content : 'NOT FOUND';
        }""")
        print(f"  {og_desc}")

        print("\n" + "=" * 60)
        print("5. ALL VISIBLE TEXT IN PRODUCT OPTIONS AREA")
        print("=" * 60)

        # Get all text from the main product section
        visible_text = await page.evaluate("""() => {
            const main = document.querySelector('.product') || document.querySelector('[class*="product"]') || document.querySelector('main');
            if (!main) return 'No product section found';
            return main.innerText.substring(0, 2000);
        }""")
        print(f"  {visible_text}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
