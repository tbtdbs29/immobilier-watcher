"""Test: envoie une fausse annonce pour tester les réactions 👍👎"""
import asyncio
from dotenv import load_dotenv
from models.property import Property
from core.bot import get_bot, start_bot

load_dotenv()

FAKE_LISTINGS = [
    Property(
        source="test",
        external_id="test_001",
        title="[TEST] Superbe T3 lumineux - Centre-ville Brest",
        url="https://example.com/test-annonce-1",
        city="Brest",
        district="Siam",
        property_type="Appartement",
        rooms=3,
        bedrooms=2,
        surface=65.0,
        price=450,
        dpe="C",
        parking=True,
        furnished=False,
    ),
    Property(
        source="test",
        external_id="test_002",
        title="[TEST] Grand T4 avec balcon - Lambézellec",
        url="https://example.com/test-annonce-2",
        city="Brest",
        district="Lambézellec",
        property_type="Appartement",
        rooms=4,
        bedrooms=3,
        surface=85.0,
        price=620,
        dpe="B",
        parking=False,
        furnished=True,
    ),
]


async def main():
    print("🤖 Démarrage du bot Discord...")

    # Lancer le bot en tâche de fond
    bot_task = asyncio.create_task(start_bot())

    bot = get_bot()
    try:
        await asyncio.wait_for(bot.wait_until_ready_custom(), timeout=30)
    except asyncio.TimeoutError:
        print("❌ Bot timeout - vérifie ton DISCORD_BOT_TOKEN")
        return

    print("✅ Bot connecté!")
    print("📨 Envoi de 2 annonces test...")

    for listing in FAKE_LISTINGS:
        await bot.send_listing(listing)

    print("✅ 2 annonces envoyées! Va sur Discord et teste:")
    print("   👍 = copie dans le salon favoris")
    print("   👎 = supprime le message")
    print("\n   Ctrl+C pour arrêter le bot")

    # Garder le bot actif pour écouter les réactions
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Arrêt du bot")
        await bot.close()


asyncio.run(main())
