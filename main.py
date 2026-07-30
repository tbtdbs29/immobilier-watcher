import asyncio

from core.config import load_config
from core.filters import filter_property
from core.deduplicate import remove_duplicates
from core.database import exists, save
from core.notifier import send_discord

from providers.leboncoin import LeboncoinProvider
from providers.bienici import BieniciProvider
from providers.seloger import SelogerProvider
from providers.ouestfrance import OuestFranceProvider



async def main():

    print("🚀 Démarrage immobilier watcher")


    config = load_config()


    providers = [

        LeboncoinProvider(config),

        BieniciProvider(config),

        SelogerProvider(config),

        OuestFranceProvider(config)

    ]


    all_properties = []


    for provider in providers:

        print(
            f"🔎 Recherche {provider.name}"
        )


        try:

            properties = await provider.fetch()


            print(
                f"{len(properties)} annonces trouvées"
            )


            all_properties.extend(
                properties
            )


        except Exception as error:

            print(
                f"Erreur {provider.name} :",
                error
            )



    print(
        f"Total brut : {len(all_properties)}"
    )



    all_properties = remove_duplicates(
        all_properties
    )


    print(
        f"Après doublons : {len(all_properties)}"
    )



    valid_properties = []


    for prop in all_properties:


        if filter_property(
            prop,
            config
        ):

            valid_properties.append(
                prop
            )



    print(
        f"Après filtres : {len(valid_properties)}"
    )



    for prop in valid_properties:


        unique_id = (
            prop.source
            +
            "_"
            +
            prop.external_id
        )


        if exists(unique_id):

            continue



        print(
            "Nouvelle annonce :",
            prop.title
        )


        send_discord(
            prop
        )


        save(
            prop
        )



if __name__ == "__main__":

    asyncio.run(
        main()
    )