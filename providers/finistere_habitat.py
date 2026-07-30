from typing import List
import re
import hashlib

from playwright.async_api import async_playwright

from models.property import Property
from providers.base import BaseProvider


class FinistereHabitatProvider(BaseProvider):
    """Finistère Habitat - bailleur social, logements abordables."""

    URL = "https://www.finistere-habitat.fr/nos-offres-de-logements/"

    @property
    def name(self):
        return "finistere_habitat"

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

                await page.goto(self.URL, wait_until="domcontentloaded", timeout=25000)
                await page.wait_for_timeout(5000)

                # Extraire les cartes d'annonces
                cards = await page.query_selector_all("[class*='card'], [class*='annonce'], [class*='logement'], article, [class*='offre'], [class*='item']")

                seen_ids = set()
                for card in cards:
                    text = await card.inner_text()
                    if "€" not in text and "EUR" not in text.upper():
                        continue

                    link_el = await card.query_selector("a[href]")
                    href = ""
                    if link_el:
                        href = await link_el.get_attribute("href") or ""

                    # ID stable
                    key = re.sub(r'\s+', '', text[:80])
                    ext_id = hashlib.md5(key.encode()).hexdigest()[:12]
                    if ext_id in seen_ids:
                        continue
                    seen_ids.add(ext_id)

                    prop = self._parse_card(ext_id, href, text)
                    if prop:
                        properties.append(prop)

                await browser.close()

            print(f"[finistere_habitat] {len(properties)} annonces trouvées")

        except Exception as e:
            print(f"[finistere_habitat] erreur: {e}")

        return properties

    def _parse_card(self, ext_id: str, href: str, text: str):
        try:
            if href and not href.startswith("http"):
                href = f"https://www.finistere-habitat.fr{href}"
            if not href:
                href = self.URL

            # Prix (loyer)
            price = None
            price_matches = re.findall(r'(\d[\d\s\xa0,\.]*)\s*(?:€|EUR)', text)
            for pm in price_matches:
                price_str = pm.replace(" ", "").replace("\xa0", "").replace(",", ".").split(".")[0]
                if price_str.isdigit():
                    val = int(price_str)
                    if 50 <= val <= 2000:
                        price = val
                        break

            if not price:
                return None

            # Ville - vérifier si c'est à Brest
            city = "Brest"
            text_lower = text.lower()
            if "brest" not in text_lower:
                # Essayer de trouver la ville
                city_match = re.search(r'(?:à|,)\s*([A-ZÀ-Ü][a-zà-ü\-]+(?:\s[A-ZÀ-Ü][a-zà-ü\-]+)*)', text)
                if city_match:
                    city = city_match.group(1)

            # Surface
            surface = None
            sm = re.search(r'([\d,\.]+)\s*m[²2]', text)
            if sm:
                surface = float(sm.group(1).replace(",", "."))

            # Pièces
            rooms = None
            rm = re.search(r'(\d+)\s*(?:pièce|p\.)', text, re.IGNORECASE)
            if not rm:
                rm = re.search(r'T(\d)', text, re.IGNORECASE)
            if rm:
                rooms = int(rm.group(1))

            # Titre
            lines = [l.strip() for l in text.split("\n") if l.strip() and len(l.strip()) > 5]
            title = ""
            for line in lines:
                if "€" not in line and "EUR" not in line.upper() and len(line) > 10:
                    title = line[:120]
                    break
            if not title:
                parts = []
                if rooms:
                    parts.append(f"T{rooms}")
                if surface:
                    parts.append(f"{surface} m²")
                parts.append(city)
                title = " - ".join(parts) if parts else f"Logement {city}"

            return Property(
                source="finistere_habitat",
                external_id=ext_id,
                title=title,
                url=href,
                city=city,
                property_type="Appartement",
                rooms=rooms,
                surface=surface,
                price=price
            )
        except Exception as e:
            print(f"[finistere_habitat] erreur parsing: {e}")
            return None
