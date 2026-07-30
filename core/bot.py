import os
import asyncio

import discord
from dotenv import load_dotenv

load_dotenv()

EMOJI_LIKE = "\U0001f44d"     # 👍
EMOJI_DISLIKE = "\U0001f44e"  # 👎


class ImmobilierBot(discord.Client):
    """
    Bot Discord pour l'immobilier watcher.
    - Envoie les annonces avec réactions 👍/👎
    - 👍 = copie l'annonce dans le salon favoris
    - 👎 = supprime l'annonce
    """

    def __init__(self):
        intents = discord.Intents.default()
        intents.reactions = True
        intents.message_content = False
        super().__init__(intents=intents)

        self._channel_id = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
        self._liked_channel_id = int(os.getenv("DISCORD_LIKED_CHANNEL_ID", "0"))
        self._ready_event = asyncio.Event()

    async def on_ready(self):
        print(f"🤖 Bot Discord connecté : {self.user}")
        self._ready_event.set()

    async def wait_until_ready_custom(self):
        """Attendre que le bot soit connecté."""
        await self._ready_event.wait()

    async def send_listing(self, prop):
        """Envoie une annonce dans le salon principal avec réactions."""
        await self.wait_until_ready_custom()

        channel = self.get_channel(self._channel_id)
        if not channel:
            print(f"   ⚠️  Salon {self._channel_id} introuvable")
            return

        embed = self._build_embed(prop)
        try:
            msg = await channel.send(embed=embed)
            await msg.add_reaction(EMOJI_LIKE)
            await msg.add_reaction(EMOJI_DISLIKE)
        except Exception as e:
            print(f"   ⚠️  Discord erreur: {e}")

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Gérer les réactions sur les messages."""
        # Ignorer les réactions du bot lui-même
        if payload.user_id == self.user.id:
            return

        emoji = str(payload.emoji)

        # 👎 dans le salon favoris = supprimer le favori
        if payload.channel_id == self._liked_channel_id and emoji == EMOJI_DISLIKE:
            channel = self.get_channel(payload.channel_id)
            if not channel:
                return
            try:
                message = await channel.fetch_message(payload.message_id)
                if message.author.id == self.user.id:
                    await self._handle_dislike(message)
            except discord.NotFound:
                pass
            return

        # Vérifier que c'est dans le salon principal
        if payload.channel_id != self._channel_id:
            return

        channel = self.get_channel(payload.channel_id)
        if not channel:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        # Vérifier que c'est un message du bot avec un embed
        if message.author.id != self.user.id or not message.embeds:
            return

        if emoji == EMOJI_LIKE:
            await self._handle_like(message)
        elif emoji == EMOJI_DISLIKE:
            await self._handle_dislike(message)

    async def _handle_like(self, message: discord.Message):
        """Copier l'annonce dans le salon favoris."""
        if not self._liked_channel_id:
            return

        liked_channel = self.get_channel(self._liked_channel_id)
        if not liked_channel:
            print(f"   ⚠️  Salon favoris {self._liked_channel_id} introuvable")
            return

        embed = message.embeds[0]

        # Modifier la couleur pour indiquer un favori
        liked_embed = discord.Embed(
            title=f"⭐ {embed.title}",
            url=embed.url,
            description=embed.description,
            color=0xFFD700  # Or
        )

        if embed.footer:
            liked_embed.set_footer(text=embed.footer.text)
        if embed.thumbnail:
            liked_embed.set_thumbnail(url=embed.thumbnail.url)

        try:
            msg = await liked_channel.send(embed=liked_embed)
            await msg.add_reaction(EMOJI_DISLIKE)
            # Retirer les réactions et marquer comme liké
            await message.clear_reactions()
            await message.add_reaction("\u2b50")  # ⭐
        except Exception as e:
            print(f"   ⚠️  Erreur like: {e}")

    async def _handle_dislike(self, message: discord.Message):
        """Supprimer l'annonce."""
        try:
            await message.delete()
        except Exception as e:
            print(f"   ⚠️  Erreur delete: {e}")

    def _build_embed(self, prop):
        """Construire l'embed Discord pour une annonce."""
        details = []
        if prop.price:
            details.append(f"\U0001f4b0 **{prop.price} \u20ac/mois**")
        if prop.surface:
            details.append(f"\U0001f4d0 {prop.surface} m\u00b2")
        if prop.rooms:
            details.append(f"\U0001f6aa {prop.rooms} pi\u00e8ces")
        if prop.bedrooms:
            details.append(f"\U0001f6cf\ufe0f {prop.bedrooms} chambre(s)")
        if prop.district:
            details.append(f"\U0001f4cd {prop.district}")
        if prop.dpe:
            details.append(f"\u26a1 DPE: {prop.dpe}")
        if prop.parking:
            details.append("\U0001f17f\ufe0f Parking")
        if prop.furnished:
            details.append("\U0001fa91 Meubl\u00e9")

        description = "\n".join(details)

        embed = discord.Embed(
            title=prop.title[:256],
            url=prop.url,
            description=description,
            color=0x2ECC71  # Vert
        )

        embed.set_footer(text=f"Source: {prop.source} \u2022 {prop.city}")

        if prop.image_url:
            embed.set_thumbnail(url=prop.image_url)

        return embed


# Singleton global
_bot_instance: ImmobilierBot | None = None


def get_bot() -> ImmobilierBot:
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = ImmobilierBot()
    return _bot_instance


async def start_bot():
    """Démarrer le bot Discord en tâche de fond."""
    bot = get_bot()
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("⚠️  DISCORD_BOT_TOKEN non configuré dans .env")
        print("   Le bot Discord ne démarrera pas.")
        print("   Les annonces seront envoyées via webhook classique.")
        return
    await bot.start(token)
