from typing import List

from models.property import Property
from providers.base import BaseProvider


class OuestFranceProvider(BaseProvider):


    URL = (
        "https://www.ouestfrance-immo.com/"
    )


    @property
    def name(self):

        return "ouestfrance"



    async def fetch(self) -> List[Property]:

        print(
            "OUEST FRANCE : non actif pour le moment"
        )


        return []