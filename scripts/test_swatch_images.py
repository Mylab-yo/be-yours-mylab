#!/usr/bin/env python3
"""Quick test: does Takemoto expose per-color images in swatch cards?"""
import asyncio
from playwright.async_api import async_playwright

URL = "https://eu.store.takemotopkg.com/products/s-pepin-200a-p-27-cap-with-inner-ring"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(URL, wait_until="networkidle", timeout=20000)
        await page.wait_for_timeout(2000)

        data = await page.evaluate("""() => {
            const out = [];
            document.querySelectorAll('.product-swatch__card').forEach(card => {
                const labelEl = card.querySelector('.product-swatch__label');
                const img = card.querySelector('img');
                out.push({
                    label: labelEl ? labelEl.textContent.trim() : '',
                    img_src: img ? img.src : null,
                    html_sample: card.outerHTML.slice(0, 300)
                });
            });
            // Also check main image
            const mainImg = document.querySelector('.product-gallery__media img, .product__media img, .Gallery__Media img');
            out.push({main_img: mainImg ? mainImg.src : 'not found'});
            return out;
        }""")

        for d in data:
            print(d)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
