import os
import requests
from dotenv import load_dotenv

load_dotenv()


async def send_discord_async(prop):
    """Envoie via le bot Discord (avec réactions 👍👎)."""
    from core.bot import get_bot
    bot = get_bot()
    if bot.is_ready():
        await bot.send_listing(prop)
        return True
    return False


async def send_discord(prop):
    """Envoie une annonce sur Discord. Utilise le bot si dispo, sinon webhook."""
    # Essayer le bot d'abord
    sent = await send_discord_async(prop)
    if sent:
        return

    # Fallback webhook classique (sans réactions)
    _send_webhook(prop)


def _send_webhook(prop):
    """Fallback: envoi via webhook simple (pas de réactions)."""
    webhook = os.getenv("DISCORD_WEBHOOK", "").strip()

    if not webhook:
        print("   ⚠️  DISCORD_WEBHOOK non configuré dans .env")
        return

    if not webhook.startswith("http"):
        print(f"   ⚠️  DISCORD_WEBHOOK invalide (doit commencer par https://)")
        return

    details = []
    if prop.price:
        details.append(f"💰 **{prop.price} €/mois**")
    if prop.surface:
        details.append(f"📐 {prop.surface} m²")
    if prop.rooms:
        details.append(f"🚪 {prop.rooms} pièces")
    if prop.bedrooms:
        details.append(f"🛏️ {prop.bedrooms} chambre(s)")
    if prop.district:
        details.append(f"📍 {prop.district}")
    if prop.dpe:
        details.append(f"⚡ DPE: {prop.dpe}")
    if prop.parking:
        details.append("🅿️ Parking")
    if prop.furnished:
        details.append("🪑 Meublé")

    description = "\n".join(details)

    embed = {
        "title": prop.title[:256],
        "url": prop.url,
        "description": description,
        "color": 3066993,
        "footer": {
            "text": f"Source: {prop.source} • {prop.city}"
        }
    }

    if prop.image_url:
        embed["thumbnail"] = {"url": prop.image_url}

    payload = {
        "embeds": [embed]
    }

    try:
        resp = requests.post(webhook, json=payload, timeout=10)
        if resp.status_code not in (200, 204):
            print(f"   ⚠️  Discord erreur: {resp.status_code}")
    except Exception as e:
        print(f"   ⚠️  Discord erreur: {e}")


def send_summary(new_count: int, total: int):
    """Envoie un résumé du scan sur Discord via webhook."""
    webhook = os.getenv("DISCORD_WEBHOOK", "").strip()
    if not webhook or not webhook.startswith("http"):
        return

    if new_count > 0:
        description = f"🆕 **{new_count}** nouvelle(s) annonce(s) envoyée(s) sur **{total}** analysées."
        color = 3066993  # Vert
    else:
        description = f"Aucune nouvelle annonce trouvée sur **{total}** analysées.\nLes critères n'ont rien donné cette fois, on retente dans 1h !"
        color = 15105570  # Orange

    payload = {
        "embeds": [{
            "title": "📊 Résumé du scan",
            "description": description,
            "color": color,
        }]
    }

    try:
        requests.post(webhook, json=payload, timeout=10)
    except Exception:
        pass