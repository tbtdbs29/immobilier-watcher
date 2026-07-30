from typing import List

import httpx

from models.property import Property
from providers.base import BaseProvider


class LeboncoinProvider(BaseProvider):
    """
    Provider LeBonCoin.

    Utilise l'API interne de recherche.
    """

    BASE_URL = "https://api.leboncoin.fr/finder/search"

    @property
    def name(self) -> str:
        return "leboncoin"


    async def fetch(self) -> List[Property]:
        """
        Récupère les annonces LeBonCoin.
        """

        results = []


        payload = self.build_payload()


        headers = {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64)"
            ),
            "Accept": "application/json",
            "Content-Type": "application/json",
        }


        async with httpx.AsyncClient(
            timeout=20
        ) as client:

            response = await client.post(
                self.BASE_URL,
                json=payload,
                headers=headers
            )


            response.raise_for_status()


            data = response.json()



        for item in data.get("ads", []):

            property_obj = self.parse_ad(item)


            if property_obj:
                results.append(property_obj)


        return results



    def build_payload(self) -> dict:
        """
        Construit la requête de recherche.

        Pour commencer on limite à Brest.
        Les filtres précis seront appliqués
        plus tard dans core/filters.py.
        """

        return {

            "limit": 35,

            "filters": {

                "location": {

                    "locations": [

                        {
                            "city": "Brest"
                        }

                    ]

                },


                "category": {

                    "id": "10"

                },


                "keywords": {

                    "text": "appartement"

                }

            },


            "owner_type": "all",

            "sort_by": "time",

            "sort_order": "desc"

        }



    def parse_ad(
        self,
        ad: dict
    ) -> Property | None:
        """
        Transforme une annonce JSON
        en objet Property.
        """

        try:

            price = None

            if ad.get("price"):
                price = int(
                    ad["price"][0]
                )


            attributes = {
                x["key"]: x.get("value")
                for x in ad.get(
                    "attributes",
                    []
                )
            }


            return Property(

                source=self.name,

                external_id=str(
                    ad.get("list_id")
                ),

                title=ad.get(
                    "subject",
                    ""
                ),

                url=ad.get(
                    "url",
                    ""
                ),

                city="Brest",

                district=None,

                property_type="Appartement",

                rooms=self.extract_int(
                    attributes.get("rooms")
                ),

                bedrooms=self.extract_int(
                    attributes.get("bedrooms")
                ),

                surface=self.extract_float(
                    attributes.get("square")
                ),

                price=price,

            )


        except Exception as error:

            print(
                f"Erreur parsing LeBonCoin : {error}"
            )

            return None



    @staticmethod
    def extract_int(value):

        try:
            return int(value)

        except:
            return None



    @staticmethod
    def extract_float(value):

        try:
            return float(value)

        except:
            return None