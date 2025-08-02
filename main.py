import discord
import os
import json
from discord.ext import tasks

DATA_FILE = "data.json"

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)
        
        

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Connecté en tant que {client.user}')

@tasks.loop(minutes=5)
async def keep_alive():
    guild = client.guilds[0]  # Le serveur sur lequel ton bot est (ou adapte pour plusieurs serveurs)
    channel = discord.utils.get(guild.text_channels, name="commandebot")
    if channel:
        await channel.send("+list crew")

@client.event
async def on_ready():
    print(f'Connecté en tant que {client.user}')
    keep_alive.start()  # Démarrer la tâche répétée
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')

    elif message.content.startswith('$xp'):
        user_id = str(message.author.id)
        data = load_data()

        if user_id not in data:
            data[user_id] = {"xp": 0, "niveau": 1}

        data[user_id]["xp"] += 10

        # Système de niveau simple : 100 XP = level up
        if data[user_id]["xp"] >= 100:
            data[user_id]["xp"] = 0
            data[user_id]["niveau"] += 1
            await message.channel.send(f"🎉 {message.author.mention} est monté niveau {data[user_id]['niveau']} !")
        else:
            await message.channel.send(f"🔹 {message.author.name}, tu as {data[user_id]['xp']} XP.")

        save_data(data)

    elif message.content.startswith('$profil'):
        user_id = str(message.author.id)
        data = load_data()

        if user_id not in data:
            await message.channel.send("Aucune donnée trouvée. Utilise `$xp` pour commencer !")
        else:
            xp = data[user_id]["xp"]
            niveau = data[user_id]["niveau"]
            await message.channel.send(f"🧾 {message.author.name} | Niveau : {niveau} | XP : {xp}")

    elif message.content.startswith('+crew'):
        parts = message.content.split(" ", 1)
        if len(parts) < 2:
            await message.channel.send("❌ Utilise : `+crew NomÉquipage`")
            return

        crew_name = parts[1].strip()
        user_id = str(message.author.id)
        data = load_data()

        # Créer ou mettre à jour l'utilisateur
        if user_id not in data:
            data[user_id] = {"xp": 0, "niveau": 1}

        # Supprimer les anciennes infos d’équipage
        data[user_id]["crew"] = crew_name
        data[user_id]["isCaptain"] = True
        data[user_id]["invites"] = data[user_id].get("invites", [])
        save_data(data)

        # Ajouter le rôle Pirate
        guild = message.guild
        role_name = "Pirate"
        pirate_role = discord.utils.get(guild.roles, name=role_name)

        if not pirate_role:
            pirate_role = await guild.create_role(name=role_name)

        if pirate_role not in message.author.roles:
            await message.author.add_roles(pirate_role)

        await message.channel.send(f"🏴‍☠️ Tu es désormais le capitaine de **{crew_name}**, {message.author.mention} !")


    elif message.content.startswith('+list crew'):
        data = load_data()
        embed = discord.Embed(title="📜 Liste des Équipages", color=discord.Color.gold())
        found = False

        for user_id, infos in data.items():
            if "crew" in infos:
                user = await client.fetch_user(int(user_id))
                embed.add_field(name=infos["crew"], value=f"Capitaine : {user.name}", inline=False)
                found = True

        if not found:
            await message.channel.send("⚠️ Aucun équipage n'a encore été créé.")
            return

        await message.channel.send(embed=embed)

    elif message.content.startswith('+choice job'):
        jobs = ["Cuisinier", "Médecin", "Navigateur", "Charpentier", "Archéologue"]
        parts = message.content.split(" ", 2)
        if len(parts) < 3:
            await message.channel.send("❌ Utilise : `+métier choice NomDuMétier`")
            return

        chosen_job = parts[2].capitalize()
        if chosen_job not in jobs:
            await message.channel.send(f"❌ Métier invalide. Choisis parmi : {', '.join(jobs)}")
            return

        data = load_data()
        user_id = str(message.author.id)

        if user_id not in data:
            data[user_id] = {"xp": 0, "niveau": 1}

        if "job" in data[user_id]:
            await message.channel.send("⚠️ Tu as déjà choisi un métier !")
            return

        data[user_id]["job"] = chosen_job
        save_data(data)
        await message.channel.send(f"🛠️ Tu es maintenant un **{chosen_job}**, {message.author.mention} !")

    elif message.content.startswith('+inv crew'):
        if not message.mentions:
            await message.channel.send("❌ Mentionne la personne que tu veux inviter. Exemple : `+inv crew @Luffy`")
            return

        target = message.mentions[0]
        inviter_id = str(message.author.id)
        target_id = str(target.id)
        data = load_data()

        if inviter_id not in data or "crew" not in data[inviter_id] or not data[inviter_id].get("isCaptain", False):
            await message.channel.send("❌ Tu dois être capitaine d’un équipage pour inviter quelqu’un.")
            return

        if target_id not in data:
            data[target_id] = {"xp": 0, "niveau": 1}

        if "invites" not in data[target_id]:
            data[target_id]["invites"] = []

        crew_name = data[inviter_id]["crew"]
        if crew_name in data[target_id]["invites"]:
            await message.channel.send("⚠️ Cette personne a déjà une invitation pour cet équipage.")
            return

        data[target_id]["invites"].append(crew_name)
        save_data(data)

        await message.channel.send(f"📨 {target.mention}, tu as été invité à rejoindre l’équipage **{crew_name}** ! Utilise `+join crew {crew_name}` pour accepter.")


    elif message.content.startswith('+join crew'):
        parts = message.content.split(" ", 2)
        if len(parts) < 3:
            await message.channel.send("❌ Utilise : `+join crew NomÉquipage`")
            return

        crew_name = parts[2].strip()
        user_id = str(message.author.id)
        data = load_data()

        if user_id not in data:
            data[user_id] = {"xp": 0, "niveau": 1}

        if "crew" in data[user_id]:
            await message.channel.send("❌ Tu fais déjà partie d’un équipage.")
            return

        if crew_name not in data[user_id].get("invites", []):
            await message.channel.send("🚫 Tu n’as pas d’invitation pour cet équipage.")
            return

        data[user_id]["crew"] = crew_name
        data[user_id]["isCaptain"] = False
        data[user_id]["invites"].remove(crew_name)
        save_data(data)

        await message.channel.send(f"✅ Tu as rejoint l’équipage **{crew_name}**, bienvenue à bord, {message.author.mention} !")

    elif message.content.startswith('+info crew'):
     parts = message.content.split(" ", 2)
     if len(parts) < 3:
        await message.channel.send("❌ Utilise : `+info crew NomÉquipage`")
        return

     crew_name = parts[2].strip()
     data = load_data()
     members = []
     total_prime = 0

     for uid, infos in data.items():
        if infos.get("crew", "").lower() == crew_name.lower():
            try:
                user = await client.fetch_user(int(uid))
            except:
                continue  # au cas où l'utilisateur n'existe plus
            job = infos.get("job", "Aucun métier")
            is_captain = infos.get("isCaptain", False)
            prime = infos.get("prime", 0)
            total_prime += prime

            member_info = f"👤 {user.name} — {job}" + (" (Capitaine)" if is_captain else "")
            member_info += f" — 💰 {prime} Berries"
            members.append(member_info)

     if not members:
        await message.channel.send("❌ Aucun membre trouvé pour cet équipage.")
        return

     embed = discord.Embed(title=f"📋    Infos sur l’équipage : {crew_name}",   color=discord.Color.blue())
     embed.description = "\n".join(members)
     embed.set_footer(text=f"💵 Prime totale de l’équipage : {total_prime} Berries")
     await     message.channel.send(embed=embed)
    elif message.content.startswith('+add prime'):
     if not any(role.name.lower() == "admin" for role in message.author.roles):
        await message.channel.send("🚫 Seuls les Admins peuvent utiliser cette commande.")
        return

    parts = message.content.split()
    if len(parts) < 3 or not parts[2].isdigit() or not message.mentions:
        await message.channel.send(" `")
        return

    montant = int(parts[2])
    cible = message.mentions[0]
    cible_id = str(cible.id)

    data = load_data()
    if cible_id not in data:
        data[cible_id] = {"xp": 0, "niveau": 1}

    data[cible_id]["prime"] = data[cible_id].get("prime", 0) + montant
    save_data(data)

    await message.channel.send(f"✅ {cible.mention} a reçu **{montant} berries** de prime ! Prime totale : **{data[cible_id]['prime']} berries**.")
    

token = os.getenv("TOKEN")
if token:
    client.run(token)
else:
    print("Token manquant ! Ajoute-le dans les secrets.")
