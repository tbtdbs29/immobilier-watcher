from typing import List
import json

from playwright.async_api import async_playwright

from models.property import Property
from providers.base import BaseProvider


class BieniciProvider(BaseProvider):

    @property
    def name(self):
        return "bienici"

    async def fetch(self) -> List[Property]:
        properties = []
        search = self.config["search"]

        url = (
            f"https://www.bienici.com/recherche/location/brest-29019"
            f"?prix-max={search['max_price']}"
            f"&nb-pieces-min={search['min_rooms']}"
            f"&surface-min={search['min_surface']}"
            f"&tri=publication-desc"
        )

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    locale="fr-FR"
                )
                page = await context.new_page()

                # Intercepter les réponses API de BienIci
                ads_data = []

                async def handle_response(response):
                    if "realEstateAds.json" in response.url:
                        try:
                            data = await response.json()
                            ads = data.get("realEstateAds", [])
                            ads_data.extend(ads)
                        except Exception:
                            pass

                page.on("response", handle_response)

                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(8000)

                # Si pas de résultat, scroll + attente
                if not ads_data:
                    await page.evaluate("window.scrollTo(0, 400)")
                    await page.wait_for_timeout(3000)

                await browser.close()

            print(f"[bienici] {len(ads_data)} annonces trouvées")

            for ad in ads_data:
                prop = self._parse_ad(ad)
                if prop:
                    properties.append(prop)

        except Exception as e:
            print(f"[bienici] erreur: {e}")

        return properties

    def _parse_ad(self, ad: dict):
        try:
            ad_id = ad.get("id", "")

            return Property(
                source="bienici",
                external_id=str(ad_id),
                title=ad.get("title", f"Appartement {ad.get('roomsQuantity', '')} pièces"),
                url=f"https://www.bienici.com/annonce/location/brest-29200/{ad_id}",
                city=ad.get("city", "Brest"),
                district=ad.get("district", {}).get("name") if isinstance(ad.get("district"), dict) else ad.get("district"),
                property_type="Appartement",
                rooms=ad.get("roomsQuantity"),
                bedrooms=ad.get("bedroomsQuantity"),
                surface=ad.get("surfaceArea"),
                price=ad.get("price"),
                charges_included=ad.get("chargesIncluded"),
                dpe=ad.get("energyClassification"),
                parking=ad.get("hasParking", False) or ad.get("hasGarage", False),
                furnished=ad.get("isFurnished"),
                image_url=ad.get("photos", [{}])[0].get("url") if ad.get("photos") else None
            )
        except Exception as e:
            print(f"[bienici] erreur parsing: {e}")
            return None