from __future__ import annotations

import argparse
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright


PAGES = [
    "/",
    "/learn/cube/why-is-25-percent-the-basic-take-point.html",
    "/research/",
    "/licensing.html",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Smoke-test rendered website metadata and keyboard basics"
    )
    parser.add_argument("base_url", help="URL of the rendered site root")
    args = parser.parse_args()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})

        for route in PAGES:
            url = urljoin(args.base_url.rstrip("/") + "/", route.lstrip("/"))
            response = page.goto(url, wait_until="networkidle")
            require(response is not None and response.ok, f"Page failed: {url}")

            require(
                page.locator('meta[property="og:image"]').count() == 1,
                f"Missing Open Graph image: {route}",
            )
            require(
                page.locator('meta[name="twitter:card"][content="summary_large_image"]').count()
                == 1,
                f"Missing large Twitter card: {route}",
            )
            require(
                page.locator('link[rel="manifest"]').count() == 1,
                f"Missing web manifest: {route}",
            )
            require(
                page.locator('link[rel="apple-touch-icon"]').count() == 1,
                f"Missing Apple touch icon: {route}",
            )
            require(
                page.locator('footer a[href$="licensing.html"]').count() == 1,
                f"Missing global licensing link: {route}",
            )
            require(
                page.locator("img:not([alt])").count() == 0,
                f"Image without alt attribute: {route}",
            )

            for index in range(8):
                page.keyboard.press("Tab")
                focused = page.locator(":focus")
                require(focused.count() == 1, f"No focus target after Tab {index + 1}: {route}")
                require(
                    focused.evaluate("element => element !== document.body"),
                    f"Focus stayed on body after Tab {index + 1}: {route}",
                )

            print(f"Rendered-page smoke test passed: {route}")

        browser.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
