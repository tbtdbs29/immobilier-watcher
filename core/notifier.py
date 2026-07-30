import os
import requests

from dotenv import load_dotenv

load_dotenv()

def send_discord(property):


    webhook = os.getenv(
        "DISCORD_WEBHOOK"
    )


    if not webhook:
        return



    message = f"""
🏠 Nouvelle annonce

📍 {property.city}

{property.title}

💰 {property.price} €

🔗 {property.url}
"""


    requests.post(
        webhook,
        json={
            "content": message
        }
    )