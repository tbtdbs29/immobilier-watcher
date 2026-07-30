from typing import List

import httpx

from models.property import Property
from providers.base import BaseProvider


class SelogerProvider(BaseProvider):

    BASE_URL = "https://www.seloger.com/list.htm"


    @property
    def name(self):
        return "seloger"


    async def fetch(self) -> List[Property]:

        properties = []

        params = {
            "projects": "2",
            "types": "2",
            "natures": "1",
            "places": "[{\"inseeCodes\":[\"29019\"]}]",
            "priceMax": self.config.get(
                "max_price",
                500
            )
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


            if response.status_code != 200:
                return properties


            data = response.json()


        for ad in data.get(
            "ads",
            []
        ):

            obj = self.parse_ad(ad)

            if obj:
                properties.append(obj)


        return properties



    def parse_ad(
        self,
        ad
    ):

        try:

            return Property(

                source=self.name,

                external_id=str(
                    ad.get("id")
                ),

                title=ad.get(
                    "title",
                    ""
                ),

                url=ad.get(
                    "url",
                    ""
                ),

                city="Brest",

                property_type="Appartement",

                rooms=ad.get(
                    "rooms"
                ),

                surface=ad.get(
                    "surface"
                ),

                price=ad.get(
                    "price"
                )

            )

        except Exception:

            return None