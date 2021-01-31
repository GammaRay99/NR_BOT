import discord
from discord.ext import commands, tasks
import random
import nacl
import time
import os
# LOCALS
from keep_alive import keep_alive
import fcts


# CONSTANTS
PREFIX = '.'
# All constants under this will later be stored in a database.
WELCOME_CHANNEL = 669593578112024596
RULES_MESSAGE = 669595153836670986
MEMBER_ROLE = 669248212174897176
NR_EMOJI = "<:NRgang:795870184564719648>"

# SETUP
client = commands.Bot(command_prefix=PREFIX, intents=discord.Intents.all())
client.remove_command('help')


@tasks.loop(seconds=120)
async def update_status():
    # status are loaded here in order to refresh them, so we don't need to restart the bot after adding new status
    listen_status = fcts.get_status("listen_status") 
    game_status = fcts.get_status("play_status")

    activity_listen = discord.Activity(type=discord.ActivityType.listening, name=random.choice(listen_status))
    activity_play = discord.Game(name=random.choice(game_status))
    current_status = random.choice((activity_listen, activity_play))

    # everything has been randomised
    await client.change_presence(activity=current_status)


@client.event
async def on_ready():
    print(f'Logged as {client.user}')
    update_status.start()


@client.event
async def on_member_join(member):
    await member.guild.get_channel(WELCOME_CHANNEL).send(f"Hey {member.mention}, bienvenue sur le serveur NR ! Nous sommes maintenant **{member.guild.member_count}**")
    await member.guild.get_channel(WELCOME_CHANNEL).send(NR_EMOJI)


# REACTION ADD AND DELETE GESTION
@client.event
async def on_raw_reaction_add(payload):
    # message reacted check
    if not payload.message_id == RULES_MESSAGE:
        return
    
    # he dont have the role ? role add action, ignore
    if not payload.member.guild.get_role(MEMBER_ROLE) in payload.member.roles:
        await payload.member.add_roles(payload.member.guild.get_role(MEMBER_ROLE))

@client.event
async def on_raw_reaction_remove(payload):
    # Since payload.member is not available on reaction_remove event, we have to get through user_id
    guild = client.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)

    # message reacted check
    if not payload.message_id == RULES_MESSAGE:
        return

    # does he have the role ? role remove action, ignore
    if guild.get_role(MEMBER_ROLE) in member.roles:
        await member.remove_roles(guild.get_role(MEMBER_ROLE))

# NATIVE COMMANDS GESTION
@client.command(name='ping')
async def latency(context):
    await context.send(f"**{round(client.latency * 1000)}ms** !")


@client.command(name='choix')
async def choix(context):
    # fcts.get_content(ctx) simply return the content of the message in a list, without the command
    content = fcts.get_content(context)
    if not content:
        return await context.send(random.choice(["Oui", "Non"]))
    
    await context.send(random.choice(content))

    # VOICE COMMANDS GESTION
@client.command(name='join')
async def join(context, from_discord=True):
    # member in channel check
    channel = context.message.author.voice.channel
    if not channel:
        return await context.send("Vous n'êtes pas connecté à un salon vocal") if from_discord else None

    # connection / move to channel
    if context.voice_client:
        await context.voice_client.move_to(channel)
    else:
        await channel.connect()

@client.command(name='leave')
async def leave(context):
    # disconnect action
    if not context.voice_client:
        await context.send("Je ne suis pas dans un channel vocal. 👀")
    else:
        await context.voice_client.disconnect()    
    

@client.command(name='play')
async def play(context):
    # TODO : add music queue

    # content check
    content = fcts.get_content(context)
    if not content:
        return await context.send("Veuillez entrer une musique à jouer !")

    # already playing (will change)
    voice = discord.utils.get(client.voice_clients, guild=context.guild)
    if voice:
        if voice.is_playing():
            return await context.send(f"Une musique est déjà en cours, ``{PREFIX}stop`` pour l'arrêter. (File de musique en cours de dev)")
    
    # remove old song (will change)
    is_song = os.path.isfile("song.mp3")
    if is_song:
        os.remove("song.mp3")

    # download music action
    async with context.channel.typing():
        if ".com" in content[0]:
            video = content[0]
            await context.send(f"Now playing : {content[0]}")
            
        else:
            await context.send(f'Recherche de : {" ".join(content)}')
            video = fcts.get_url(content)
            await context.send(f"Now playing : {video}")
    
        fcts.download_song(video)

    # rename the downloaded song as "song.mp3" (will change)
    for file in os.listdir('./'):
        if file.endswith(('.webm', '.m4a', '.mp3')):  # since i had troubles with extension, i put more than only mp3, just in case
            os.rename(file, "song.mp3")
    
    # play "song.mp3"
    await join(context, from_discord=False)
    client.voice_clients[0].play(discord.FFmpegPCMAudio("song.mp3"))
    

@client.command(name='stop')
async def stop(context):
    # if he doesnt play anything, he'll leave, otherwise he'll stop
    voice = discord.utils.get(client.voice_clients, guild=context.guild)
    if not voice:
        return await leave(context)
    if not voice.is_playing():
        return await leave(context)

    if voice.is_playing():
        voice.stop()


@client.command(name="pause")
async def pause_music(context): 
    # playing check
    voice = discord.utils.get(client.voice_clients, guild=context.guild)
    if not voice:
        return await context.send("Je ne joue aucune musique !")

    # is paused check
    if not voice.is_playing():
        if voice.is_paused():
            voice.resume()
            return await context.send("Musique lancée !")

    # pause action
    voice.pause()
    await context.send(f"Musique en pause, ``{PREFIX}resume`` pour remettre en route !")


@client.command(name="resume")
async def resume(context):
    # pause and resume do the same thing
    # you can resume to pause, and pause to play if you want to
    await pause_music(context)


# MODS COMMANDS GESTION
@client.command(name='say')
async def say(context):
    # perm check
    if not fcts.is_mod(context.author):
        return await context.message.add_reaction("👀")

    # content check
    content = fcts.get_content(context)
    if not content:
        return await context.message.add_reaction("👀")
    
    # say action
    await context.message.delete()
    await context.send(" ".join(content))


@client.command(name='clear')
async def clear(context):
    # perm check
    if not fcts.is_mod(context.author):
        return await context.send("Vous n'avez pas les droits pour faire ça !")
    
    # content check
    content = fcts.get_content(context)
    if not content:
        await context.send("Vous devez spécifier combien de messages il faut supprimer.")
    
    # valid content check
    try:
        length = int(content[0])
    except ValueError:
        await context.send(f'"{content[0]}"" n\'est pas un nombre valide.')

    # clear action
    await context.channel.purge(limit=length + 1)
    delete_this = await context.send(f"{length} messages supprimés !")
    time.sleep(2)
    await delete_this.delete()


@client.command(name='kick')
async def kick(context):
    # perm check
    if not fcts.is_mod(context.author):
        return await context.send("Vous n'avez pas les droits pour faire ça !")
    
    # content check
    content = fcts.get_content(context)
    if not content:
        return await context.send("Vous devez spécifier un utilisateur à exclure.")
    
    # valid contetn check
    mention = context.message.mentions
    if not mention:
        return await context.send(f"{content[0]} n'est pas un utilisateur valide.")
    
    # incorrect user check
    if mention[0].bot or mention[0].name == "natroch85":
        return await context.send("Impossible d'exclure un bot.")
        # collabs  check
    if mention[0].name in ["GammaRay99", "Paemay", "Sneazz"]:
        return await context.send("Impossible d'exclure cette magnifique personne.")
        # moderator check
    if fcts.is_mod(mention[0]):
        return await context.send("Impossible d'exclure un modérateur")
    
    # kick action
    await mention[0].kick()
    await context.send(f'"{mention[0].name}" was an impostor.')


keep_alive()
client.run(os.getenv("TOKEN"))
