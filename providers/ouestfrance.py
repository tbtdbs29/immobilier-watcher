from typing import List

import httpx
from bs4 import BeautifulSoup

from models.property import Property
from providers.base import BaseProvider


class OuestFranceProvider(BaseProvider):
    """
    Provider Ouest France Immo.

    Version HTML.
    Le site ne semble pas exposer facilement
    une API publique exploitable.
    """

    URL = (
        "https://www.ouestfrance-immo.com/"
        "immobilier-location/appartement-brest-29200/"
    )


    @property
    def name(self) -> str:
        return "ouestfrance"



    async def fetch(self) -> List[Property]:

        properties = []


        headers = {

            "User-Agent":
                (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "Chrome/120 Safari/537.36"
                ),

            "Accept-Language":
                "fr-FR,fr;q=0.9"

        }



        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=True
        ) as client:


            response = await client.get(
                self.URL,
                headers=headers
            )


            response.raise_for_status()


        soup = BeautifulSoup(
            response.text,
            "lxml"
        )


        # DEBUG TEMPORAIRE
        print("======== OUEST FRANCE DEBUG ========")

        print(
            "Titre page :",
            soup.title
        )

        print(
            soup.get_text(
                separator=" ",
                strip=True
            )[:500]
        )

        print(
            "===================================="
        )


        #
        # Les sélecteurs seront ajustés
        # après observation du HTML réel.
        #

        cards = soup.select(
            "article"
        )


        for index, card in enumerate(cards):

            text = card.get_text(
                " ",
                strip=True
            )


            if not text:

                continue



            properties.append(

                Property(

                    source=self.name,

                    external_id=f"ouestfrance-{index}",

                    title=text[:200],

                    url=self.URL,

                    city="Brest",

                    property_type="Appartement"

                )

            )


        return properties