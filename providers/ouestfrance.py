from typing import List

import httpx
from bs4 import BeautifulSoup, soup

from models.property import Property
from providers.base import BaseProvider



class OuestFranceProvider(BaseProvider):

    URL = (
        "https://www.ouestfrance-immo.com"
        "/immobilier-location/appartement-brest-29200/"
    )


    @property
    def name(self):
        return "ouestfrance"



    async def fetch(self) -> List[Property]:

        result = []


        headers = {
            "User-Agent":
            "Mozilla/5.0"
        }


        async with httpx.AsyncClient(
            timeout=20
        ) as client:


            response = await client.get(
                self.URL,
                headers=headers
            )


        soup = BeautifulSoup(
            response.text,
            "lxml"
        )
        print(
            soup.title
        )

        print(
            soup.text[:500]
        )


        cards = soup.select(
            ".listing-item"
        )


        for card in cards:

            title = card.text.strip()


            result.append(

                Property(

                    source=self.name,

                    external_id=str(
                        hash(title)
                    ),

                    title=title,

                    url=self.URL,

                    city="Brest",

                    property_type="Appartement"

                )

            )


        return result