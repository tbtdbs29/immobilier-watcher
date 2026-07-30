from typing import List
import re

import httpx
from bs4 import BeautifulSoup

from models.property import Property
from providers.base import BaseProvider


class FonciaProvider(BaseProvider):

    BASE_URL = "https://fr.foncia.com/location/brest-29200/appartement"

    @property
    def name(self):
        return "foncia"

    async def fetch(self) -> List[Property]:
        properties = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "fr-FR,fr;q=0.9",
        }

        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                resp = await client.get(self.BASE_URL, headers=headers)

            if resp.status_code != 200:
                print(f"[foncia] status {resp.status_code}")
                return properties

            soup = BeautifulSoup(resp.text, "lxml")

            # Trouver tous les liens d'annonces
            links = soup.find_all("a", href=re.compile(r"/location/brest-29200/appartement/\d+\.htm"))
            seen_ids = set()

            for link in links:
                href = link.get("href", "")
                ext_id = re.search(r"/(\d+)\.htm", href)
                if not ext_id:
                    continue
                ext_id = ext_id.group(1)
                if ext_id in seen_ids:
                    continue
                seen_ids.add(ext_id)

                # Extraire le titre du lien
                title = link.get_text(strip=True)
                if not title or len(title) < 10:
                    continue

                # Chercher le prix dans le contexte parent
                parent = link.parent
                for _ in range(5):
                    if parent is None:
                        break
                    parent = parent.parent

                context_text = parent.get_text(" ", strip=True) if parent else ""

                # Prix
                price = None
                price_match = re.search(r"([\d\s,.]+)\s*€\s*/\s*mois", context_text)
                if price_match:
                    price_str = price_match.group(1).replace(" ", "").replace(",", ".").replace("\xa0", "")
                    try:
                        price = int(float(price_str))
                    except ValueError:
                        pass

                # Surface
                surface = None
                surface_match = re.search(r"([\d,\.]+)\s*m[²2]", title)
                if surface_match:
                    surface = float(surface_match.group(1).replace(",", "."))

                # Pièces
                rooms = None
                rooms_match = re.search(r"(\d+)\s*pièce", title)
                if rooms_match:
                    rooms = int(rooms_match.group(1))

                url = href if href.startswith("http") else f"https://fr.foncia.com{href}"

                properties.append(Property(
                    source="foncia",
                    external_id=ext_id,
                    title=title[:256],
                    url=url,
                    city="Brest",
                    property_type="Appartement",
                    rooms=rooms,
                    surface=surface,
                    price=price,
                ))

        except Exception as e:
            print(f"[foncia] erreur: {e}")

        print(f"[foncia] {len(properties)} annonces trouvées")
        return properties
