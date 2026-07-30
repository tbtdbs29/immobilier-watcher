from typing import List
import json
import os

from playwright.async_api import async_playwright

from models.property import Property
from providers.base import BaseProvider


class LeboncoinProvider(BaseProvider):

    SEARCH_URL = (
        "https://www.leboncoin.fr/recherche"
        "?category=10"
        "&locations=Brest_29200"
        "&real_estate_type=2"
    )

    @property
    def name(self):
        return "leboncoin"

    async def fetch(self) -> List[Property]:
        properties = []
        search = self.config["search"]

        url = (
            f"{self.SEARCH_URL}"
            f"&price=0-{search['max_price']}"
            f"&rooms={search['min_rooms']}-all"
            f"&square={search['min_surface']}-all"
        )

        # Essayer curl_cffi d'abord (marche sur CI sans Chrome)
        ads_data = await self._fetch_curl_cffi(url)

        # Fallback Playwright + Chrome (marche en local)
        if not ads_data:
            ads_data = await self._fetch_playwright(url)

        print(f"[leboncoin] {len(ads_data)} annonces trouvées")

        for ad in ads_data:
            prop = self._parse_ad(ad)
            if prop:
                properties.append(prop)

        return properties

    async def _fetch_curl_cffi(self, url: str) -> list:
        """Fetch via curl_cffi (impersonne Chrome TLS fingerprint)."""
        try:
            from curl_cffi.requests import AsyncSession

            async with AsyncSession(impersonate="chrome") as session:
                resp = await session.get(
                    url,
                    headers={
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8",
                        "Cache-Control": "no-cache",
                        "Sec-Fetch-Dest": "document",
                        "Sec-Fetch-Mode": "navigate",
                        "Sec-Fetch-Site": "none",
                    },
                    timeout=20,
                )

            if resp.status_code != 200:
                return []

            # Extraire __NEXT_DATA__ du HTML
            html = resp.text
            marker = '<script id="__NEXT_DATA__" type="application/json">'
            start = html.find(marker)
            if start == -1:
                return []
            start += len(marker)
            end = html.find("</script>", start)
            if end == -1:
                return []

            data = json.loads(html[start:end])
            return (
                data.get("props", {})
                .get("pageProps", {})
                .get("searchData", {})
                .get("ads", [])
            )
        except ImportError:
            return []
        except Exception as e:
            print(f"[leboncoin] curl_cffi: {e}")
            return []

    async def _fetch_playwright(self, url: str) -> list:
        """Fetch via Playwright + Chrome (pour local avec IP résidentielle)."""
        ads_data = []
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    channel="chrome",
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox"
                    ]
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    locale="fr-FR",
                    viewport={"width": 1920, "height": 1080}
                )

                # Anti-detection
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    window.chrome = {runtime: {}};
                """)
                page = await context.new_page()

                async def handle_response(response):
                    if "finder/search" in response.url or "api.leboncoin" in response.url:
                        try:
                            data = await response.json()
                            if "ads" in data:
                                ads_data.extend(data["ads"])
                        except Exception:
                            pass

                page.on("response", handle_response)

                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(5000)

                # Si pas d'interception API, essayer __NEXT_DATA__
                if not ads_data:
                    try:
                        script = await page.query_selector("script#__NEXT_DATA__")
                        if script:
                            content = await script.inner_text()
                            data = json.loads(content)
                            ads_data = (
                                data.get("props", {})
                                .get("pageProps", {})
                                .get("searchData", {})
                                .get("ads", [])
                            )
                    except Exception:
                        pass

                await browser.close()
        except Exception as e:
            print(f"[leboncoin] playwright: {e}")

        return ads_data

    def _parse_ad(self, ad: dict):
        try:
            attrs = {}
            for attr in ad.get("attributes", []):
                attrs[attr["key"]] = attr.get("value", "")

            # Rejeter les annonces hors zone (sponsorisées)
            location = ad.get("location", {})
            zipcode = location.get("zipcode", "")
            if zipcode and not zipcode.startswith("29"):
                return None

            price = None
            if ad.get("price"):
                price = ad["price"][0] if isinstance(ad["price"], list) else ad["price"]

            return Property(
                source="leboncoin",
                external_id=str(ad["list_id"]),
                title=ad.get("subject", ""),
                url=ad.get("url", f"https://www.leboncoin.fr/locations/{ad['list_id']}.htm"),
                city=ad.get("location", {}).get("city", ""),
                property_type="Appartement",
                rooms=int(attrs.get("rooms", 0)) or None,
                surface=float(attrs.get("square", 0)) or None,
                price=price,
                furnished=attrs.get("furnished") == "1",
                dpe=attrs.get("energy_rate"),
                image_url=ad.get("images", {}).get("urls", [None])[0] if ad.get("images") else None
            )
        except Exception as e:
            print(f"[leboncoin] erreur parsing: {e}")
            return None