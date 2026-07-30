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

    print(
        "🚀 Démarrage immobilier watcher"
    )


    config = load_config()


    providers=[

        LeboncoinProvider(config),

        BieniciProvider(config),

        SelogerProvider(config),

        OuestFranceProvider(config)

    ]


    properties=[]



    for provider in providers:


        print(
            "🔎 Recherche",
            provider.name
        )


        try:

            result = await provider.fetch()


            print(
                len(result),
                "annonces trouvées"
            )


            properties.extend(
                result
            )


        except Exception as e:

            print(
                "Erreur",
                provider.name,
                ":",
                e
            )



    print(
        "Total brut:",
        len(properties)
    )


    properties = remove_duplicates(
        properties
    )


    print(
        "Après doublons:",
        len(properties)
    )



    for prop in properties:


        if not filter_property(
            prop,
            config
        ):

            continue



        uid = (
            prop.source
            +
            "_"
            +
            prop.external_id
        )


        if exists(uid):

            continue



        send_discord(
            prop
        )


        save(
            prop
        )



if __name__=="__main__":

    asyncio.run(
        main()
    )