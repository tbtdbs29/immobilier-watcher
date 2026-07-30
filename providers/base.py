from abc import ABC, abstractmethod
from typing import List

from models.property import Property


class BaseProvider(ABC):
    """
    Classe abstraite de base pour tous les scrapers immobiliers.

    Chaque site doit implémenter :
    - fetch()
    - name()
    """

    def __init__(self, config: dict):
        self.config = config


    @abstractmethod
    async def fetch(self) -> List[Property]:
        """
        Récupère les annonces depuis le site.

        Retour attendu :
        [
            Property(...),
            Property(...)
        ]
        """

        pass


    @property
    @abstractmethod
    def name(self) -> str:
        """
        Nom du provider.

        Exemple :
        "leboncoin"
        """

        pass


    def is_enabled(self) -> bool:
        """
        Permet de désactiver un scraper facilement
        depuis la configuration.
        """

        return True