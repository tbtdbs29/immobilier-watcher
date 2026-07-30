from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Property(BaseModel):
    """
    Modèle commun représentant une annonce immobilière.
    Tous les scrapers doivent retourner cet objet.
    """

    # Source de l'annonce
    source: str = Field(
        description="Site d'origine : leboncoin, bienici, seloger..."
    )

    # Identifiant unique fourni par le site
    external_id: str

    # Informations générales
    title: str

    url: str

    city: str

    district: Optional[str] = None

    address: Optional[str] = None


    # Caractéristiques logement

    property_type: str = "Appartement"

    rooms: Optional[int] = None

    bedrooms: Optional[int] = None

    surface: Optional[float] = None


    # Prix

    price: Optional[int] = None

    charges_included: Optional[bool] = None


    # Energie

    dpe: Optional[str] = None


    # Options

    parking: bool = False

    furnished: Optional[bool] = None


    # Métadonnées

    image_url: Optional[str] = None

    published_at: Optional[datetime] = None

    detected_at: datetime = Field(
        default_factory=datetime.now
    )


    class Config:
        json_schema_extra = {
            "example": {

                "source": "leboncoin",

                "external_id": "123456789",

                "title": "T2 Brest Liberté 38m²",

                "url": "https://www.leboncoin.fr/..."

                ,

                "city": "Brest",

                "district": "Liberté",

                "property_type": "Appartement",

                "rooms": 2,

                "bedrooms": 1,

                "surface": 38,

                "price": 495,

                "dpe": "B",

                "parking": True

            }
        }