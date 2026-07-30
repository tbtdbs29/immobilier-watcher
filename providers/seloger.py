from typing import List

import httpx

from models.property import Property
from providers.base import BaseProvider


class SelogerProvider(BaseProvider):
    """
    SeLoger est très protégé (Datadome/Captcha).
    On utilise leur API interne avec les bons headers.
    Si ça ne marche plus, il faudra Playwright.
    """

    API_URL = "https://www.seloger.com/list.htm"

    @property
    def name(self):
        return "seloger"

    async def fetch(self) -> List[Property]:
        properties = []
        search = self.config["search"]

        params = {
            "projects": "1",
            "types": "1",
            "natures": "1,2",
            "places": '[{"inseeCodes":["290019"]}]',
            "price": f"NaN/{search['max_price']}",
            "rooms": f"{search['min_rooms']}/NaN",
            "surface": f"{search['min_surface']}/NaN",
            "enterprise": "0",
            "qsVersion": "1.0",
            "LISTING-LISTpg": "1"
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "fr-FR,fr;q=0.9",
            "Referer": "https://www.seloger.com/"
        }

        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                response = await client.get(
                    self.API_URL,
                    params=params,
                    headers=headers
                )

            print(f"[seloger] status: {response.status_code}")

            if response.status_code != 200:
                print(f"[seloger] bloqué (anti-bot probable), skip")
                return properties

            # SeLoger redirige souvent vers un captcha
            if "captcha" in response.text.lower() or "datadome" in response.text.lower():
                print("[seloger] captcha détecté, skip")
                return properties

            print(f"[seloger] réponse reçue mais parsing non implémenté (site trop protégé)")
            return properties

        except Exception as e:
            print(f"[seloger] erreur: {e}")
            return properties