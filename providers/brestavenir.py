from typing import List
import re
import hashlib

from playwright.async_api import async_playwright

from models.property import Property
from providers.base import BaseProvider


class BrestAvenirProvider(BaseProvider):

    BASE_URL = "https://www.brest-avenir-immobilier.fr/location/"

    @property
    def name(self):
        return "brest_avenir"

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

                await page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(5000)

                # Chercher les cartes d'annonces avec prix
                cards = await page.query_selector_all("[class*='card'], [class*='annonce'], [class*='bien'], article, [class*='property'], [class*='item']")

                seen_ids = set()
                for card in cards:
                    text = await card.inner_text()
                    if "€" not in text:
                        continue

                    # Chercher un lien dans la carte
                    link_el = await card.query_selector("a[href]")
                    href = ""
                    if link_el:
                        href = await link_el.get_attribute("href") or ""

                    # ID stable
                    price_match = re.search(r'(\d{3,4})\s*€', text)
                    surface_match = re.search(r'([\d,\.]+)\s*m[²2]', text)
                    key = f"{price_match.group(1) if price_match else ''}_{''.join(text.split()[:5])}"
                    ext_id = hashlib.md5(key.encode()).hexdigest()[:12]

                    if ext_id in seen_ids:
                        continue
                    seen_ids.add(ext_id)

                    prop = self._parse_card(ext_id, href, text)
                    if prop:
                        properties.append(prop)

                await browser.close()

            print(f"[brest_avenir] {len(properties)} annonces trouvées")

        except Exception as e:
            print(f"[brest_avenir] erreur: {e}")

        return properties

    def _parse_card(self, ext_id: str, href: str, text: str):
        try:
            if href and not href.startswith("http"):
                href = f"https://www.brest-avenir-immobilier.fr{href}"
            elif not href:
                href = self.BASE_URL

            # Prix
            price = None
            price_matches = re.findall(r'(\d[\d\s\xa0]*)\s*€', text)
            for pm in price_matches:
                price_str = pm.replace(" ", "").replace("\xa0", "")
                if price_str.isdigit():
                    val = int(price_str)
                    if 100 <= val <= 3000:
                        price = val
                        break

            if not price:
                return None

            # Surface
            surface = None
            surface_match = re.search(r'([\d,\.]+)\s*m[²2]', text)
            if surface_match:
                surface = float(surface_match.group(1).replace(",", "."))

            # Pièces
            rooms = None
            rooms_match = re.search(r'(\d+)\s*(?:pièce|p\.)', text, re.IGNORECASE)
            if not rooms_match:
                rooms_match = re.search(r'T(\d)', text)
            if rooms_match:
                rooms = int(rooms_match.group(1))

            # Titre
            lines = [l.strip() for l in text.split("\n") if l.strip() and len(l.strip()) > 5]
            title = ""
            for line in lines:
                if "€" not in line and len(line) > 10 and "VOIR" not in line.upper():
                    title = line[:120]
                    break
            if not title:
                parts = []
                if rooms:
                    parts.append(f"T{rooms}")
                if surface:
                    parts.append(f"{surface} m²")
                parts.append("Brest")
                title = " - ".join(parts) if parts else f"Appartement Brest - {price}€"

            return Property(
                source="brest_avenir",
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
            print(f"[brest_avenir] erreur parsing: {e}")
            return None
