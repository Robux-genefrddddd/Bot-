import discord
import openai
import asyncio
from datetime import datetime, timedelta
from langdetect import detect, LangDetectException
from typing import Dict, List, Optional

# Clés API (remplace avec les vraies sans les exposer publiquement)
DISCORD_BOT_TOKEN = "MTM0NjgzOTg1Njc1NTY0MjM5OA.GKl92m.kMc5MfIH6d40F1F1VNMjbaoTxCIk92vmLVeO_c"
OPENROUTER_API_KEY = "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"

# Configuration OpenAI (OpenRouter)
openai.api_base = "https://openrouter.ai/api/v1"
openai.api_key = OPENROUTER_API_KEY

# Intents pour lire les messages
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)

# Mémoire utilisateur (historique des discussions)
memory: Dict[str, List[str]] = {}

# Maintenance
maintenance_end_time: Optional[datetime] = None
maintenance_channel: Optional[discord.TextChannel] = None


def is_french(text: str) -> bool:
    """Vérifie si le texte est principalement en français."""
    try:
        lang = detect(text)
        return lang == "fr"
    except LangDetectException:
        return False


@client.event
async def on_ready():
    print(f"✅ Connecté en tant que {client.user}")


@client.event
async def on_message(message: discord.Message):
    global maintenance_end_time, maintenance_channel, memory

    if message.author.bot:
        return  # Ignore les messages des bots

    user_input: str = message.content
    user_id: str = str(message.author.id)

    # Gestion de la maintenance
    if maintenance_end_time:
        remaining_time: timedelta = maintenance_end_time - datetime.now()
        if remaining_time > timedelta(0):
            await message.channel.send(
                f"⏳ @{message.author.mention} L'IA est en maintenance pour encore {str(remaining_time)}."
            )
            return
        else:
            maintenance_end_time = None
            await message.channel.send(f"✅ @{message.author.mention} L'IA est de retour en ligne !")

    # Commande !maintenance (réservée à "dianlo47")
    if message.content.startswith("!maintenance"):
        if message.author.name == "dianlo47":
            try:
                time_input = user_input.split(" ")[1]
                if "h" in time_input:
                    hours = int(time_input.replace("h", ""))
                    maintenance_end_time = datetime.now() + timedelta(hours=hours)
                elif "m" in time_input:
                    minutes = int(time_input.replace("m", ""))
                    maintenance_end_time = datetime.now() + timedelta(minutes=minutes)
                else:
                    raise ValueError("Format invalide")

                maintenance_channel = message.channel
                await message.channel.send(f"🔧 Maintenance activée pour {time_input}.")
                await asyncio.sleep((maintenance_end_time - datetime.now()).total_seconds())
                await maintenance_channel.send("✅ L'IA est de retour en ligne !")
                maintenance_end_time = None
            except Exception:
                await message.channel.send("❌ Erreur: Utilisation correcte: `!maintenance <durée>` (ex: 1h, 30m).")
        else:
            await message.channel.send("❌ Seul `dianlo47` peut exécuter cette commande.")
        return

    # Commande !clear pour effacer la mémoire utilisateur
    if message.content.startswith("!clear"):
        if message.author.name == "dianlo47":
            memory[user_id] = []
            await message.channel.send(f"🧹 @{message.author.mention} Mémoire effacée avec succès.")
        else:
            await message.channel.send("❌ Seul `dianlo47` peut utiliser cette commande.")
        return

    # Vérification de la langue française (avec tolérance pour les erreurs)
    if not is_french(user_input):
        await message.channel.send(f"⚠️ @{message.author.mention} Merci d'écrire en français pour que je puisse te répondre correctement !")
        return

    # Stockage de la mémoire utilisateur
    user_memory = memory.get(user_id, [])
    user_memory.append(user_input)
    memory[user_id] = user_memory

    # Message temporaire pour indiquer que l'IA répond
    thinking_message = await message.channel.send(f"💭 @{message.author.mention} L'IA est en train de réfléchir...")

    # Création du prompt pour OpenAI
    prompt = f"""Tu es une IA professionnelle et attentionnée, qui se souvient des conversations précédentes.
    Voici l'historique de {message.author.name} :
    {"".join(f"- {msg}\n" for msg in user_memory)}
    Maintenant, réponds de manière claire et précise : {user_input}"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Réponds uniquement en français et de manière professionnelle."},
                {"role": "user", "content": prompt},
            ]
        )
        chat_response = response["choices"][0]["message"]["content"]
    except Exception as e:
        chat_response = f"🚨 Erreur avec OpenRouter : {str(e)}"

    # Modifier le message pour afficher la réponse finale
    await thinking_message.edit(content=f"🤖 @{message.author.mention} {chat_response}")


# Lancer le bot
client.run(DISCORD_BOT_TOKEN)
