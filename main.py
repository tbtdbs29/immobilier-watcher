import asyncio
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from core.config import load_config
from core.filters import filter_property
from core.deduplicate import remove_duplicates
from core.database import exists, save, reset_db
from core.notifier import send_discord, send_summary
from core.bot import get_bot, start_bot

from providers.leboncoin import LeboncoinProvider
from providers.bienici import BieniciProvider
from providers.foncia import FonciaProvider
from providers.laforet import LaforetProvider
from providers.barraine import BarraineProvider
from providers.brestavenir import BrestAvenirProvider
from providers.iad import IadProvider
from providers.finistere_habitat import FinistereHabitatProvider
from providers.ouestfrance import OuestFranceProvider


async def run_scan():
    print(f"\n{'='*50}")
    print(f"🔍 Scan démarré à {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*50}")

    config = load_config()

    providers = [
        BieniciProvider(config),
        LeboncoinProvider(config),
        FonciaProvider(config),
        LaforetProvider(config),
        BarraineProvider(config),
        BrestAvenirProvider(config),
        IadProvider(config),
        FinistereHabitatProvider(config),
        OuestFranceProvider(config),
    ]

    properties = []

    for provider in providers:
        print(f"\n🔎 {provider.name}...")
        try:
            result = await provider.fetch()
            print(f"   ✓ {len(result)} annonces")
            properties.extend(result)
        except Exception as e:
            print(f"   ✗ Erreur {provider.name}: {e}")

    print(f"\n📊 Total brut: {len(properties)}")

    properties = remove_duplicates(properties)
    print(f"📊 Après dédoublonnage: {len(properties)}")

    new_count = 0
    filtered_count = 0
    for prop in properties:
        if not filter_property(prop, config):
            filtered_count += 1
            continue

        uid = f"{prop.source}_{prop.external_id}"

        if exists(uid):
            continue

        # Nouvelle annonce !
        new_count += 1
        print(f"   🆕 {prop.title} - {prop.price}€")

        await send_discord(prop)
        save(prop, uid)

    print(f"\n📊 Filtrées (rejetées): {filtered_count}")
    print(f"✅ Scan terminé: {new_count} nouvelle(s) annonce(s) envoyée(s)")

    # Résumé Discord (toujours envoyé)
    send_summary(new_count, len(properties))

    return new_count


async def main():
    load_dotenv()
    config = load_config()

    ci_mode = "--ci" in sys.argv

    if ci_mode:
        # Mode CI (GitHub Actions) : scan unique avec bot pour réactions
        print("🚀 Immobilier Watcher (mode CI)")

        has_bot_token = bool(os.getenv("DISCORD_BOT_TOKEN"))
        if has_bot_token:
            bot_task = asyncio.create_task(start_bot())
            bot = get_bot()
            try:
                await asyncio.wait_for(bot.wait_until_ready_custom(), timeout=30)
                print("🤖 Bot Discord connecté (réactions 👍👎)")
            except asyncio.TimeoutError:
                print("⚠️  Bot timeout, fallback webhook")

        await run_scan()

        if has_bot_token and get_bot().is_ready():
            await get_bot().close()

        print("🏁 Terminé")
        return

    interval = config.get("scraping", {}).get("interval_minutes", 60)

    print("🚀 Immobilier Watcher démarré")
    print(f"⏰ Scan toutes les {interval} minutes")

    has_bot_token = bool(os.getenv("DISCORD_BOT_TOKEN"))

    if has_bot_token:
        print("🤖 Bot Discord activé (réactions 👍👎)")
        # Lancer le bot en tâche de fond
        bot_task = asyncio.create_task(start_bot())
        # Attendre que le bot soit connecté
        bot = get_bot()
        try:
            await asyncio.wait_for(bot.wait_until_ready_custom(), timeout=30)
        except asyncio.TimeoutError:
            print("⚠️  Bot Discord timeout, on continue sans")
    else:
        print("📨 Mode webhook (pas de réactions)")
        print("   Pour activer le bot: ajouter DISCORD_BOT_TOKEN dans .env")
        bot_task = None

    print("   (Premier scan immédiat)\n")

    # Premier scan immédiat
    await run_scan()

    # Scheduler pour les scans suivants
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_scan, "interval", minutes=interval)
    scheduler.start()

    # Garder le programme en vie (le bot tourne aussi dans la même boucle)
    try:
        while True:
            await asyncio.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 Arrêt du watcher")
        if bot_task:
            bot = get_bot()
            await bot.close()
        scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())