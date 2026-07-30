from typing import List
import re
import json

from playwright.async_api import async_playwright

from models.property import Property
from providers.base import BaseProvider


class FonciaProvider(BaseProvider):

    BASE_URL = "https://fr.foncia.com/location/brest-29200/appartement"

    @property
    def name(self):
        return "foncia"

    async def fetch(self) -> List[Property]:
        properties = []

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    locale="fr-FR",
                    viewport={"width": 1920, "height": 1080}
                )
                await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                page = await context.new_page()

                # Intercepter les réponses API
                api_ads = []

                async def handle_response(response):
                    ct = response.headers.get("content-type", "")
                    if "json" in ct and response.status == 200:
                        try:
                            data = await response.json()
                            text = json.dumps(data)
                            if "brest" in text.lower() and ("surface" in text.lower() or "price" in text.lower()):
                                api_ads.append(data)
                        except Exception:
                            pass

                page.on("response", handle_response)

                await page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(8000)

                # Méthode 1: données API interceptées
                if api_ads:
                    for data in api_ads:
                        self._extract_from_api(data, properties)

                # Méthode 2: fallback DOM
                if not properties:
                    listing_links = await page.query_selector_all("a[href*='/location/brest-29200/appartement/'][href$='.htm']")

                    seen_ids = set()
                    for link_el in listing_links:
                        href = await link_el.get_attribute("href") or ""
                        ext_id = href.split("/")[-1].replace(".htm", "")
                        if ext_id in seen_ids:
                            continue
                        seen_ids.add(ext_id)

                        # JS: remonter dans le DOM pour trouver le texte de la carte
                        card_text = await page.evaluate("""(el) => {
                            let parent = el;
                            for (let i = 0; i < 10; i++) {
                                parent = parent.parentElement;
                                if (!parent) break;
                                const text = parent.innerText;
                                if (text && text.includes('\u20ac') && (text.includes('m\u00b2') || text.includes('pi\u00e8ce'))) {
                                    if (text.length < 500) return text;
                                }
                            }
                            return '';
                        }""", link_el)

                        if card_text:
                            prop = self._parse_card_text(ext_id, href, card_text)
                            if prop:
                                properties.append(prop)

                await browser.close()

            print(f"[foncia] {len(properties)} annonces trouvées")

        except Exception as e:
            print(f"[foncia] erreur: {e}")

        return properties

    def _extract_from_api(self, data, properties):
        if isinstance(data, dict):
            for key, val in data.items():
                if isinstance(val, list) and val and isinstance(val[0], dict):
                    for item in val:
                        prop = self._parse_api_ad(item)
                        if prop:
                            properties.append(prop)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    prop = self._parse_api_ad(item)
                    if prop:
                        properties.append(prop)

    def _parse_api_ad(self, ad):
        try:
            ext_id = str(ad.get("id", ad.get("reference", "")))
            if not ext_id:
                return None
            price = ad.get("price", ad.get("rent", ad.get("loyer")))
            if isinstance(price, dict):
                price = price.get("value", price.get("amount"))
            if price:
                price = int(float(price))

            return Property(
                source="foncia",
                external_id=ext_id,
                title=ad.get("title", "Appartement Brest"),
                url=ad.get("url", f"https://fr.foncia.com/location/brest-29200/appartement/{ext_id}.htm"),
                city=ad.get("city", "Brest"),
                property_type="Appartement",
                rooms=ad.get("rooms", ad.get("nbRooms")),
                surface=ad.get("surface", ad.get("area")),
                price=price
            )
        except Exception:
            return None

    def _parse_card_text(self, ext_id: str, href: str, text: str):
        try:
            if not href.startswith("http"):
                href = f"https://fr.foncia.com{href}"

            # Prix
            price = None
            price_matches = re.findall(r'([\d\s\xa0\.]+)\s*\u20ac', text)
            for pm in price_matches:
                price_str = pm.replace(" ", "").replace("\xa0", "").replace(".", "")
                if price_str.isdigit():
                    val = int(price_str)
                    if 100 <= val <= 3000:
                        price = val
                        break

            # Surface
            surface = None
            surface_match = re.search(r'([\d,\.]+)\s*m[\u00b22]', text)
            if surface_match:
                surface = float(surface_match.group(1).replace(",", "."))

            # Pièces
            rooms = None
            rooms_match = re.search(r'(\d+)\s*(?:pi\u00e8ce|p\.)', text, re.IGNORECASE)
            if rooms_match:
                rooms = int(rooms_match.group(1))

            title_parts = []
            if rooms:
                title_parts.append(f"T{rooms}")
            if surface:
                title_parts.append(f"{surface} m\u00b2")
            title_parts.append("Brest")
            title = " - ".join(title_parts) if title_parts else "Appartement Brest"

            return Property(
                source="foncia",
                external_id=ext_id,
                title=title,
                url=href,
                city="Brest",
                property_type="Appartement",
                rooms=rooms,
                surface=surface,
                price=price
            )
        except Exception as e:
            print(f"[foncia] erreur parsing: {e}")
            return None
