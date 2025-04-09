
import asyncio
from playwright.async_api import async_playwright

# Define which components to check
CHECK_SELECTORS = [
    "header",
    "nav",
    "footer",
    "main",
    "button",
    "a[href]",
    "input",
    "form"
]

async def check_components(url: str) -> list[dict]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, timeout=10000)

            results = []
            for selector in CHECK_SELECTORS:
                try:
                    found = await page.query_selector(selector)
                    status = "✅" if found else "❌"
                except Exception:
                    status = "❌"
                results.append({
                    "selector": selector,
                    "status": status
                })

            await browser.close()
            return results

        except Exception as e:
            await browser.close()
            raise RuntimeError(f"Component check failed: {e}")