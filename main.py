import discord
from discord.ext import commands, tasks
import json
import os

TOKEN = os.environ.get("DISCORD_TOKEN")
CHANNEL_ID = 123456789012345678  # Remplace par l’ID de ton salon

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="+", intents=intents)

# ---------------- Sauvegarde ------------------

def load_data():
    try:
        with open("data.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(data):
    with open("data.json", "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

# ---------------- Commandes -------------------

@bot.command()
async def list(ctx):
    crew_list = data.get("crews", [])
    if not crew_list:
        await ctx.send("Aucun équipage enregistré.")
    else:
        await ctx.send("Équipages : " + ", ".join(crew_list))

@bot.command()
async def addcrew(ctx, *, crew_name):
    data.setdefault("crews", []).append(crew_name)
    save_data(data)
    await ctx.send(f"Équipage '{crew_name}' ajouté !")

# ---------------- Répondre à soi-même ---------

@bot.event
async def on_message(message):
    await bot.process_commands(message)  # Pas de filtre sur message.author

# ---------------- Ping régulier ----------------

@tasks.loop(minutes=5)
async def auto_list_crew():
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send("+list")

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")
    auto_list_crew.start()

# ---------------- Lancer le bot ----------------

bot.run(TOKEN)
