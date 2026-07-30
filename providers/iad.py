from typing import List
import re
import json

from playwright.async_api import async_playwright

from models.property import Property
from providers.base import BaseProvider


class IadProvider(BaseProvider):
    """IAD France - réseau de mandataires immobiliers. API JSON interceptable."""

    URL = "https://www.iadfrance.fr/annonces/location/appartement/brest-29200"

    @property
    def name(self):
        return "iad"

    async def fetch(self) -> List[Property]:
        properties = []

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True, channel="chrome",
                    args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    locale="fr-FR", viewport={"width": 1920, "height": 1080}
                )
                await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                page = await context.new_page()

                api_ads = []
                async def handle_response(response):
                    ct = response.headers.get("content-type", "")
                    if "json" in ct and response.status == 200:
                        try:
                            data = await response.json()
                            text = json.dumps(data)
                            if any(w in text.lower() for w in ["brest", "location"]) and "price" in text.lower():
                                if isinstance(data, dict):
                                    # Chercher les listings dans la réponse
                                    for key, val in data.items():
                                        if isinstance(val, list) and val and isinstance(val[0], dict):
                                            api_ads.extend(val)
                                    if not api_ads and "price" in data:
                                        api_ads.append(data)
                                elif isinstance(data, list):
                                    api_ads.extend(data)
                        except Exception:
                            pass
                page.on("response", handle_response)

                await page.goto(self.URL, wait_until="domcontentloaded", timeout=25000)
                await page.wait_for_timeout(6000)

                # Si pas d'API, parse le DOM
                if not api_ads:
                    cards = await page.query_selector_all("[class*='card'], [class*='annonce'], article, [class*='property']")
                    for card in cards:
                        text = await card.inner_text()
                        if "€" not in text:
                            continue
                        link_el = await card.query_selector("a[href]")
                        href = ""
                        if link_el:
                            href = await link_el.get_attribute("href") or ""
                        prop = self._parse_card_text(href, text)
                        if prop:
                            properties.append(prop)
                else:
                    for ad in api_ads:
                        prop = self._parse_api_ad(ad)
                        if prop:
                            properties.append(prop)

                await browser.close()

            print(f"[iad] {len(properties)} annonces trouvées")

        except Exception as e:
            print(f"[iad] erreur: {e}")

        return properties

    def _parse_api_ad(self, ad):
        try:
            ext_id = str(ad.get("id", ad.get("reference", ad.get("_id", ""))))
            price = ad.get("price", ad.get("rent", ad.get("loyer")))
            if isinstance(price, dict):
                price = price.get("value", price.get("amount"))
            if price:
                price = int(float(price))

            surface = ad.get("surface", ad.get("area", ad.get("livingArea")))
            rooms = ad.get("rooms", ad.get("nbRooms", ad.get("roomsQuantity")))
            title = ad.get("title", ad.get("name", "Appartement Brest"))
            url = ad.get("url", ad.get("link", ""))
            if url and not url.startswith("http"):
                url = f"https://www.iadfrance.fr{url}"

            if not ext_id:
                return None

            return Property(
                source="iad",
                external_id=ext_id,
                title=str(title)[:120],
                url=url or self.URL,
                city=ad.get("city", "Brest"),
                property_type="Appartement",
                rooms=int(rooms) if rooms else None,
                surface=float(surface) if surface else None,
                price=price
            )
        except Exception:
            return None

    def _parse_card_text(self, href, text):
        try:
            import hashlib
            ext_id = hashlib.md5(text[:50].encode()).hexdigest()[:12]

            if href and not href.startswith("http"):
                href = f"https://www.iadfrance.fr{href}"

            price = None
            pm = re.search(r'(\d[\d\s\xa0]*)\s*€', text)
            if pm:
                ps = pm.group(1).replace(" ", "").replace("\xa0", "")
                if ps.isdigit() and 100 <= int(ps) <= 3000:
                    price = int(ps)

            surface = None
            sm = re.search(r'([\d,\.]+)\s*m[²2]', text)
            if sm:
                surface = float(sm.group(1).replace(",", "."))

            rooms = None
            rm = re.search(r'(\d+)\s*(?:pièce|p\.)', text, re.IGNORECASE)
            if not rm:
                rm = re.search(r'T(\d)', text)
            if rm:
                rooms = int(rm.group(1))

            title = ""
            for line in text.split("\n"):
                line = line.strip()
                if len(line) > 10 and "€" not in line:
                    title = line[:120]
                    break
            if not title:
                title = f"Appartement Brest - {price}€" if price else "Appartement Brest"

            return Property(
                source="iad",
                external_id=ext_id,
                title=title,
                url=href or self.URL,
                city="Brest",
                property_type="Appartement",
                rooms=rooms,
                surface=surface,
                price=price
            )
        except Exception:
            return None
