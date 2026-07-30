from typing import List
import re
import hashlib

from playwright.async_api import async_playwright

from models.property import Property
from providers.base import BaseProvider


class LaforetProvider(BaseProvider):

    SEARCH_URL = "https://www.laforet.com/louer/rechercher"

    @property
    def name(self):
        return "laforet"

    async def fetch(self) -> List[Property]:
        properties = []
        search = self.config["search"]

        url = (
            f"{self.SEARCH_URL}"
            f"?localisation=brest-29200"
            f"&type_bien=appartement"
            f"&budget_max={search['max_price']}"
            f"&nb_pieces_min={search['min_rooms']}"
        )

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

                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(8000)

                # Scroll pour charger le lazy loading
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                await page.wait_for_timeout(2000)

                # Extraire les données des cards visibles
                cards = await page.query_selector_all("[class*='card'], [class*='Card'], article")

                for card in cards:
                    text = await card.inner_text()
                    # Vérifier que c'est une vraie annonce (contient un prix)
                    if "€" not in text:
                        continue

                    # Chercher un lien dans la carte
                    link_el = await card.query_selector("a[href*='/louer/'], a[href*='/location/']")
                    href = ""
                    if link_el:
                        href = await link_el.get_attribute("href") or ""

                    prop = self._parse_card_text(text, href)
                    if prop:
                        properties.append(prop)

                await browser.close()

            print(f"[laforet] {len(properties)} annonces trouvées")

        except Exception as e:
            print(f"[laforet] erreur: {e}")

        return properties

    def _parse_card_text(self, text: str, href: str):
        """Parse le texte d'une carte d'annonce LaForet."""
        try:
            lines = [l.strip() for l in text.split("\n") if l.strip()]

            # Prix
            price = None
            for line in lines:
                price_match = re.search(r'([\d\s]+)\s*€', line)
                if price_match:
                    price_str = price_match.group(1).replace(" ", "").replace("\xa0", "")
                    if price_str.isdigit():
                        price = int(price_str)
                        break

            if not price:
                return None

            # Titre - premier texte significatif (ignorer les textes navigateur)
            skip_words = ["nouvel onglet", "voir", "retour", "fermer", "menu", "recherch", "cookie"]
            title = ""
            for line in lines:
                line_lower = line.lower()
                if (
                    len(line) > 10
                    and "€" not in line
                    and not any(w in line_lower for w in skip_words)
                    and not line.startswith("(")
                ):
                    title = line[:120]
                    break
            if not title:
                parts = []
                if rooms:
                    parts.append(f"T{rooms}")
                if surface:
                    parts.append(f"{surface} m²")
                parts.append(f"{price}€")
                title = " - ".join(parts) if parts else f"Appartement Brest - {price}€"

            # Surface
            surface = None
            surface_match = re.search(r'([\d,\.]+)\s*m[²2]', text)
            if surface_match:
                surface = float(surface_match.group(1).replace(",", "."))

            # Pièces
            rooms = None
            rooms_match = re.search(r'(\d+)\s*pièce', text, re.IGNORECASE)
            if rooms_match:
                rooms = int(rooms_match.group(1))

            # URL
            if href and not href.startswith("http"):
                href = f"https://www.laforet.com{href}"
            elif not href:
                href = f"https://www.laforet.com/louer/rechercher?localisation=brest-29200"

            # ID
            external_id = ""
            if href:
                id_match = re.search(r'/(\d+)', href)
                if id_match:
                    external_id = id_match.group(1)
            if not external_id:
                # ID stable basé sur titre+prix (hashlib est déterministe contrairement à hash())
                stable = f"{title}_{price}_{surface}"
                external_id = hashlib.md5(stable.encode()).hexdigest()[:12]

            return Property(
                source="laforet",
                external_id=external_id,
                title=title,
                url=href,
                city="Brest",
                property_type="Appartement",
                rooms=rooms,
                surface=surface,
                price=price
            )
        except Exception as e:
            print(f"[laforet] erreur parsing: {e}")
            return None
