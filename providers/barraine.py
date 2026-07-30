from typing import List
import re
import hashlib

from playwright.async_api import async_playwright

from models.property import Property
from providers.base import BaseProvider


class BarraineProvider(BaseProvider):

    BASE_URL = "https://www.barraine-immo.com/location/"

    @property
    def name(self):
        return "barraine"

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

                await page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=25000)
                await page.wait_for_timeout(5000)

                # Trouver les liens vers les annonces individuelles
                # Format: /location/annonce-XXXXX/
                links = await page.query_selector_all("a[href*='/location/annonce-']")

                seen_ids = set()
                for link_el in links:
                    href = await link_el.get_attribute("href") or ""
                    # Extraire l'ID: annonce-60829399
                    id_match = re.search(r'annonce-(\d+)', href)
                    if not id_match:
                        continue

                    ext_id = id_match.group(1)
                    if ext_id in seen_ids:
                        continue
                    seen_ids.add(ext_id)

                    # Remonter au parent pour récupérer les infos
                    card_text = await page.evaluate("""(el) => {
                        let parent = el;
                        for (let i = 0; i < 8; i++) {
                            parent = parent.parentElement;
                            if (!parent) break;
                            const text = parent.innerText;
                            if (text && text.includes('€') && text.length < 800 && text.length > 20) {
                                return text;
                            }
                        }
                        return el.innerText || '';
                    }""", link_el)

                    prop = self._parse_card(ext_id, href, card_text)
                    if prop:
                        properties.append(prop)

                await browser.close()

            print(f"[barraine] {len(properties)} annonces trouvées")

        except Exception as e:
            print(f"[barraine] erreur: {e}")

        return properties

    def _parse_card(self, ext_id: str, href: str, text: str):
        try:
            if not href.startswith("http"):
                href = f"https://www.barraine-immo.com{href}"

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

            # Ville
            city = "Brest"
            if "brest" not in text.lower():
                city_match = re.search(r'(?:à|,)\s*([A-ZÀ-Ü][a-zà-ü]+(?:\s[A-ZÀ-Ü][a-zà-ü]+)*)', text)
                if city_match:
                    city = city_match.group(1)

            # Titre
            lines = [l.strip() for l in text.split("\n") if l.strip() and len(l.strip()) > 5]
            title = ""
            for line in lines:
                if "€" not in line and "VOIR" not in line.upper() and len(line) > 10:
                    title = line[:120]
                    break
            if not title:
                parts = []
                if rooms:
                    parts.append(f"T{rooms}")
                if surface:
                    parts.append(f"{surface} m²")
                parts.append(city)
                title = " - ".join(parts) if parts else f"Appartement {city}"

            return Property(
                source="barraine",
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
            print(f"[barraine] erreur parsing: {e}")
            return None
