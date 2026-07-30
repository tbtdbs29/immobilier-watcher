from typing import List

import httpx

from models.property import Property
from providers.base import BaseProvider


class BieniciProvider(BaseProvider):
    """
    Provider Bien'ici.

    Récupère les annonces via les données
    JSON utilisées par le site.
    """

    BASE_URL = (
        "https://www.bienici.com"
        "/realEstateAds.json"
    )


    @property
    def name(self) -> str:
        return "bienici"



    async def fetch(self) -> List[Property]:
        """
        Récupère les annonces Bien'ici.
        """

        properties = []


        params = self.build_params()


        headers = {

            "User-Agent":
                (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64)"
                ),

            "Accept":
                "application/json",

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
            print("BIENICI TOTAL")
            print(data.get("total"))

            print("PREMIERE ANNONCE")
            print(
                data.get("realEstateAds", [])[:1]
            )


        ads = data.get(
            "realEstateAds",
            []
        )


        for ad in ads:

            property_obj = self.parse_ad(ad)


            if property_obj:

                properties.append(
                    property_obj
                )


        return properties



    def build_params(self) -> dict:
        """
        Paramètres de recherche.

        Ici on demande Brest.
        Les filtres précis seront faits
        plus tard dans filters.py.
        """

        return {

            "page":
                1,

            "size":
                30,


            "filters":

                (
                    '{"city":"Brest",'
                    '"propertyType":"APARTMENT"}'
                )

        }



    def parse_ad(
        self,
        ad: dict
    ) -> Property | None:

        """
        Convertit une annonce Bien'ici
        vers notre modèle Property.
        """

        try:


            price = ad.get(
                "price"
            )


            surface = ad.get(
                "surface"
            )


            rooms = ad.get(
                "rooms"
            )


            return Property(

                source=self.name,


                external_id=str(
                    ad.get(
                        "id"
                    )
                ),


                title=ad.get(
                    "title",
                    "Appartement Bien'ici"
                ),


                url=(
                    "https://www.bienici.com"
                    "/annonce/"
                    +
                    str(
                        ad.get("id")
                    )
                ),


                city=(
                    ad.get(
                        "city",
                        "Brest"
                    )
                ),


                district=(
                    ad.get(
                        "district"
                    )
                ),


                property_type=(
                    "Appartement"
                ),


                rooms=self.to_int(
                    rooms
                ),


                bedrooms=self.extract_bedrooms(
                    ad
                ),


                surface=self.to_float(
                    surface
                ),


                price=self.to_int(
                    price
                ),


                parking=self.has_parking(
                    ad
                )

            )


        except Exception as error:

            print(
                "Erreur parsing Bien'ici :",
                error
            )

            return None



    def extract_bedrooms(
        self,
        ad: dict
    ) -> int | None:

        """
        Bien'ici donne parfois seulement
        le nombre de pièces.

        Estimation simple :
        T2 => 1 chambre
        """

        rooms = self.to_int(
            ad.get("rooms")
        )


        if rooms and rooms >= 2:

            return rooms - 1


        return None



    def has_parking(
        self,
        ad: dict
    ) -> bool:

        """
        Recherche parking dans
        les caractéristiques.
        """

        text = str(
            ad
        ).lower()


        return (
            "parking" in text
            or
            "garage" in text
        )



    @staticmethod
    def to_int(value):

        try:
            return int(value)

        except:

            return None



    @staticmethod
    def to_float(value):

        try:
            return float(value)

        except:

            return None