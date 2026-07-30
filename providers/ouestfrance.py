from typing import List

import httpx
from bs4 import BeautifulSoup

from models.property import Property
from providers.base import BaseProvider


class OuestFranceProvider(BaseProvider):

    BASE_URL = "https://www.ouestfrance-immo.com/immobilier/location/appartement/brest-29-29019/"

    @property
    def name(self):
        return "ouestfrance"

    async def fetch(self) -> List[Property]:
        properties = []
        search = self.config["search"]

        params = {
            "prix": f"0_{search['max_price']}",
            "pieces": f"{search['min_rooms']}_",
            "surface": f"{search['min_surface']}_",
            "tri": "DATE_DECROISSANT"
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html",
            "Accept-Language": "fr-FR,fr;q=0.9"
        }

        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(
                self.BASE_URL,
                params=params,
                headers=headers
            )

        print(f"[ouestfrance] status: {response.status_code}")

        if response.status_code != 200:
            return properties

        soup = BeautifulSoup(response.text, "lxml")

        # OuestFrance-immo utilise des annonces en cartes
        cards = soup.select("a.annLink, div.annonce, article.annonce")

        if not cards:
            # Fallback: chercher les liens d'annonces
            cards = soup.find_all("a", href=lambda h: h and "/louer/" in h and "annonce" in h)

        print(f"[ouestfrance] {len(cards)} cartes trouvées")

        for card in cards:
            prop = self._parse_card(card)
            if prop:
                properties.append(prop)

        return properties

    def _parse_card(self, card):
        try:
            # Extraire le lien
            if card.name == "a":
                href = card.get("href", "")
            else:
                link = card.find("a")
                href = link.get("href", "") if link else ""

            if not href:
                return None

            if not href.startswith("http"):
                href = f"https://www.ouestfrance-immo.com{href}"

            # ID depuis l'URL
            external_id = href.rstrip("/").split("/")[-1].split("-")[-1]

            # Titre
            title_el = card.find(class_=lambda c: c and "title" in c.lower()) if card.name != "a" else card
            title = title_el.get_text(strip=True) if title_el else "Appartement Brest"

            # Prix
            price = None
            price_el = card.find(class_=lambda c: c and "prix" in c.lower()) or card.find(string=lambda s: s and "€" in s)
            if price_el:
                price_text = price_el.get_text() if hasattr(price_el, "get_text") else str(price_el)
                digits = "".join(c for c in price_text if c.isdigit())
                if digits:
                    price = int(digits)

            # Surface
            surface = None
            surface_el = card.find(string=lambda s: s and "m²" in s)
            if surface_el:
                surface_text = str(surface_el)
                parts = surface_text.split("m²")[0].strip().split()
                if parts:
                    try:
                        surface = float(parts[-1].replace(",", "."))
                    except ValueError:
                        pass

            if not external_id or external_id == href:
                return None

            return Property(
                source="ouestfrance",
                external_id=external_id,
                title=title[:120],
                url=href,
                city="Brest",
                property_type="Appartement",
                surface=surface,
                price=price
            )
        except Exception as e:
            print(f"[ouestfrance] erreur parsing: {e}")
            return None