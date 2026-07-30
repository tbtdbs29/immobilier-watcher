from typing import List

import httpx

from models.property import Property
from providers.base import BaseProvider


class BieniciProvider(BaseProvider):

    BASE_URL = "https://www.bienici.com/realEstateAds.json"


    @property
    def name(self):
        return "bienici"


    async def fetch(self) -> List[Property]:

        properties = []

        params = {
            "page": 1,
            "size": 30
        }


        headers = {
            "User-Agent":
                "Mozilla/5.0",
            "Accept":
                "application/json"
        }


        async with httpx.AsyncClient(
            timeout=20
        ) as client:

            response = await client.get(
                self.BASE_URL,
                params=params,
                headers=headers
            )


            response.raise_for_status()


            data = response.json()


        print(
            "BIENICI TOTAL:",
            data.get("total")
        )


        ads = data.get(
            "realEstateAds",
            []
        )


        for ad in ads:

            prop = self.parse_ad(ad)

            if prop:
                properties.append(prop)


        return properties



    def parse_ad(self, ad):

        try:

            return Property(

                source="bienici",

                external_id=str(
                    ad.get("id")
                ),

                title=ad.get(
                    "title",
                    "Appartement Bien'ici"
                ),

                url=(
                    "https://www.bienici.com"
                    "/annonce/"
                    +
                    str(ad.get("id"))
                ),

                city="Brest",

                property_type="Appartement",

                surface=ad.get(
                    "surface"
                ),

                rooms=ad.get(
                    "rooms"
                ),

                price=ad.get(
                    "price"
                )

            )


        except Exception as e:

            print(
                "Erreur Bien'ici:",
                e
            )

            return None