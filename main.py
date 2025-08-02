import discord
import os
import json
from discord.ext import tasks
from flask import Flask
from threading import Thread


intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

client = discord.Client(intents=intents)

DATA_FILE = "data.json"

def load_db():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_db(db):
    with open(DATA_FILE, "w") as f:
        json.dump(db, f)

@tasks.loop(minutes=5)
async def keep_alive():
    for guild in client.guilds:
        channel = discord.utils.get(guild.text_channels, name="commandebot")
        if channel:
            await channel.send("+list crew")

@client.event
async def on_ready():
    print(f'✅ Connecté en tant que {client.user}')
    keep_alive.start()

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    db = load_db()
    user_id = str(message.author.id)

    if user_id not in db:
        db[user_id] = {"xp": 0, "niveau": 1}
        save_db(db)

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')

    elif message.content.startswith('$xp'):
        data = db[user_id]
        data["xp"] += 10

        if data["xp"] >= 100:
            data["xp"] = 0
            data["niveau"] += 1
            await message.channel.send(f"🎉 {message.author.mention} est monté niveau {data['niveau']} !")
        else:
            await message.channel.send(f"🔹 {message.author.name}, tu as {data['xp']} XP.")

        db[user_id] = data
        save_db(db)

    elif message.content.startswith('$profil'):
        data = db[user_id]
        xp = data.get("xp", 0)
        niveau = data.get("niveau", 1)
        await message.channel.send(f"🧾 {message.author.name} | Niveau : {niveau} | XP : {xp}")

    elif message.content.startswith('+crew'):
        parts = message.content.split(" ", 1)
        if len(parts) < 2:
            await message.channel.send("❌ Utilise : `+crew NomÉquipage`")
            return

        crew_name = parts[1].strip()
        data = db[user_id]
        data["crew"] = crew_name
        data["isCaptain"] = True
        data.setdefault("invites", [])
        db[user_id] = data
        save_db(db)

        guild = message.guild
        role_name = "Pirate"
        pirate_role = discord.utils.get(guild.roles, name=role_name)

        if not pirate_role:
            pirate_role = await guild.create_role(name=role_name)

        if pirate_role not in message.author.roles:
            await message.author.add_roles(pirate_role)

        await message.channel.send(f"🏴‍☠️ Tu es désormais le capitaine de **{crew_name}**, {message.author.mention} !")

    elif message.content.startswith('+list crew'):
        embed = discord.Embed(title="📜 Liste des Équipages", color=discord.Color.gold())
        found = False

        for uid, infos in db.items():
            if "crew" in infos and infos.get("isCaptain"):
                try:
                    user = await client.fetch_user(int(uid))
                    embed.add_field(name=infos["crew"], value=f"Capitaine : {user.name}", inline=False)
                    found = True
                except:
                    continue

        if not found:
            await message.channel.send("⚠️ Aucun équipage n'a encore été créé.")
            return

        await message.channel.send(embed=embed)

    elif message.content.startswith('+choice job'):
        jobs = ["Cuisinier", "Médecin", "Navigateur", "Charpentier", "Archéologue"]
        parts = message.content.split(" ", 2)
        if len(parts) < 3:
            await message.channel.send("❌ Utilise : `+choice job NomDuMétier`")
            return

        chosen_job = parts[2].capitalize()
        if chosen_job not in jobs:
            await message.channel.send(f"❌ Métier invalide. Choisis parmi : {', '.join(jobs)}")
            return

        data = db[user_id]
        if "job" in data:
            await message.channel.send("⚠️ Tu as déjà choisi un métier !")
            return

        data["job"] = chosen_job
        db[user_id] = data
        save_db(db)
        await message.channel.send(f"🛠️ Tu es maintenant un **{chosen_job}**, {message.author.mention} !")

    elif message.content.startswith('+inv crew'):
        if not message.mentions:
            await message.channel.send("❌ Mentionne la personne à inviter. Exemple : `+inv crew @Nom`")
            return

        target = message.mentions[0]
        inviter_data = db[user_id]

        if "crew" not in inviter_data or not inviter_data.get("isCaptain", False):
            await message.channel.send("❌ Tu dois être capitaine d’un équipage pour inviter quelqu’un.")
            return

        target_id = str(target.id)
        if target_id not in db:
            db[target_id] = {"xp": 0, "niveau": 1}

        target_data = db[target_id]
        target_data.setdefault("invites", [])

        crew_name = inviter_data["crew"]
        if crew_name in target_data["invites"]:
            await message.channel.send("⚠️ Cette personne a déjà une invitation pour cet équipage.")
            return

        target_data["invites"].append(crew_name)
        db[target_id] = target_data
        save_db(db)

        await message.channel.send(f"📨 {target.mention}, tu as été invité à rejoindre **{crew_name}** ! Utilise `+join crew {crew_name}`.")

    elif message.content.startswith('+join crew'):
        parts = message.content.split(" ", 2)
        if len(parts) < 3:
            await message.channel.send("❌ Utilise : `+join crew NomÉquipage`")
            return

        crew_name = parts[2].strip()
        data = db[user_id]

        if "crew" in data:
            await message.channel.send("❌ Tu fais déjà partie d’un équipage.")
            return

        if crew_name not in data.get("invites", []):
            await message.channel.send("🚫 Tu n’as pas d’invitation pour cet équipage.")
            return

        data["crew"] = crew_name
        data["isCaptain"] = False
        data["invites"].remove(crew_name)
        db[user_id] = data
        save_db(db)

        await message.channel.send(f"✅ Tu as rejoint l’équipage **{crew_name}**, bienvenue à bord, {message.author.mention} !")

    elif message.content.startswith('+info crew'):
        parts = message.content.split(" ", 2)
        if len(parts) < 3:
            await message.channel.send("❌ Utilise : `+info crew NomÉquipage`")
            return

        crew_name = parts[2].strip()
        members = []
        total_prime = 0

        for uid, infos in db.items():
            if infos.get("crew", "").lower() == crew_name.lower():
                try:
                    user = await client.fetch_user(int(uid))
                except:
                    continue

                job = infos.get("job", "Aucun métier")
                is_captain = infos.get("isCaptain", False)
                prime = infos.get("prime", 0)
                total_prime += prime

                member = f"👤 {user.name} — {job}"
                if is_captain:
                    member += " (Capitaine)"
                member += f" — 💰 {prime} Berries"
                members.append(member)

        if not members:
            await message.channel.send("❌ Aucun membre trouvé pour cet équipage.")
            return

        embed = discord.Embed(title=f"📋 Infos : {crew_name}", color=discord.Color.blue())
        embed.description = "\n".join(members)
        embed.set_footer(text=f"💵 Prime totale : {total_prime} Berries")
        await message.channel.send(embed=embed)

    elif message.content.startswith('+add prime'):
        if not any(role.name.lower() == "admin" for role in message.author.roles):
            await message.channel.send("🚫 Seuls les Admins peuvent ajouter une prime.")
            return

        parts = message.content.split()
        if len(parts) < 3 or not parts[2].isdigit() or not message.mentions:
            await message.channel.send("❌ Utilise : `+add prime @utilisateur montant`")
            return

        montant = int(parts[2])
        cible = message.mentions[0]
        cible_id = str(cible.id)

        if cible_id not in db:
            db[cible_id] = {"xp": 0, "niveau": 1}

        data = db[cible_id]
        data["prime"] = data.get("prime", 0) + montant
        db[cible_id] = data
        save_db(db)

        await message.channel.send(f"✅ {cible.mention} a reçu **{montant} berries** ! Prime totale : **{data['prime']} berries**.")

app = Flask('')

@app.route('/')
def home():
    return "Le bot est vivant !"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive_web():
    t = Thread(target=run)
    t.start()

keep_alive_web()


# Lancement du bot
token = os.getenv("TOKEN")
if token:
    client.run(token)
else:
    print("❌ Token manquant. Ajoute-le dans les secrets ou variables d'environnement.")
