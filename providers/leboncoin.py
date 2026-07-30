from typing import List

import httpx
from bs4 import BeautifulSoup

from models.property import Property
from providers.base import BaseProvider



class LeboncoinProvider(BaseProvider):


    URL = (
        "https://www.leboncoin.fr"
        "/recherche?category=10"
        "&locations=Brest_29200"
    )


    @property
    def name(self):

        return "leboncoin"



    async def fetch(self) -> List[Property]:

        properties = []


        headers = {

            "User-Agent":
            (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64)"
            )

        }


        async with httpx.AsyncClient(
            timeout=30,
            follow_redirects=True
        ) as client:


            response = await client.get(
                self.URL,
                headers=headers
            )


        print(
            "LEBONCOIN STATUS:",
            response.status_code
        )


        if response.status_code != 200:

            return properties



        soup = BeautifulSoup(
            response.text,
            "lxml"
        )


        print(
            "LEBONCOIN HTML:",
            soup.title
        )


        return properties