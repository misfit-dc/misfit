'''
MIT License

Copyright (c) [2023] [MannuVilasara]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''
# IMPORTS
import discord
from constants import token,spam,modappch
from discord.ext import commands
import json
import requests
from utils import *
import youtube_dl
from discord.utils import get
import discord
from discord import Message as DiscordMessage
import logging
from base import Message, Conversation
from constants import (
    BOT_INVITE_URL,
    DISCORD_BOT_TOKEN,
    EXAMPLE_CONVOS,
    ACTIVATE_THREAD_PREFX,
    MAX_THREAD_MESSAGES,
    SECONDS_DELAY_RECEIVING_MSG,
)
import asyncio
from utils import (
    logger,
    # should_block,
    close_thread,
    is_last_message_stale,
    discord_message_to_message,
)
import completion
from completion import generate_completion_response, process_response,gf_response
from moderation import (
    moderate_message,
    send_moderation_blocked_message,
    send_moderation_flagged_message,
)

from discord.ext import commands

import json



logging.basicConfig(
    format="[%(asctime)s] [%(filename)s:%(lineno)d] %(message)s", level=logging.INFO
)


intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.dm_messages = True
intents.presences = True 
intents.members = True 


activity=discord.Activity(type=discord.ActivityType.watching, name="✔ MISFIT") #CHANGE THE ACTIVITY TO YOUR WISH

bot = commands.Bot(command_prefix="m!",intents=intents,status=discord.Status.idle,activity=activity) #CHANGE THE PREFIX

bot.remove_command("help")

@bot.event
async def on_ready():
    logger.info(f"We have logged in as {bot.user}. Invite URL: {BOT_INVITE_URL}")
    completion.MY_BOT_NAME = bot.user.name
    completion.MY_BOT_EXAMPLE_CONVOS = []
    for c in EXAMPLE_CONVOS:
        messages = []
        for m in c.messages:
            if m.user == "Lenard":
                messages.append(Message(user=bot.user.name, text=m.text))
            else:
                messages.append(m)
        completion.MY_BOT_EXAMPLE_CONVOS.append(Conversation(messages=messages))
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")


# ON MESSAGE EVENT
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await bot.process_commands(message)
    data = mongo()
    create_user = data.find_one({"_id":int(message.author.id)})
    if message.author == bot.user:
        return
# ACCEPTING REPSONSES FROM DM AND SENDING THEM IN SPAM CHANNEL
    if isinstance(message.channel, discord.DMChannel): 
        channel_id = int(spam) # Replace with the ID of the channel you want to send the message to
        channel = bot.get_channel(channel_id)
        embed = discord.Embed(title=str(message.author.name),description = str(message.content))
        embed.set_thumbnail(url=message.author.display_avatar)
        if message.author == bot.user:
            return
        if create_user == None:
            print(f'Received a DM from {message.author.name}: {message.content}')
            await message.author.send("https://discord.gg/unusual")
            await message.author.send("Please Send Atleast 1 message in our server")
            await channel.send(embed=embed)
        else:
            print(f'Received a DM from {message.author.name}: {message.content}')
            await channel.send(embed=embed)
    try:
        # block servers not in allow list
        # if should_block(guild=message.guild):
        #     return

        # ignore messages from the bot
        if message.author == bot.user:
            return

        # ignore messages not in a thread
        channel = message.channel
        if not isinstance(channel, discord.Thread):
            return

        # ignore threads not created by the bot
        thread = channel
        if thread.owner_id != bot.user.id:
            return

        # ignore threads that are archived locked or title is not what we want
        if (
            thread.archived
            or thread.locked
            or not thread.name.startswith(ACTIVATE_THREAD_PREFX)
        ):
            # ignore this thread
            return

        if thread.message_count > MAX_THREAD_MESSAGES:
            # too many messages, no longer going to reply
            await close_thread(thread=thread)
            return

        # moderate the message
        
        # wait a bit in case user has more messages
        if SECONDS_DELAY_RECEIVING_MSG > 0:
            await asyncio.sleep(SECONDS_DELAY_RECEIVING_MSG)
            if is_last_message_stale(
                interaction_message=message,
                last_message=thread.last_message,
                bot_id=bot.user.id,
            ):
                # there is another message, so ignore this one
                return

        logger.info(
            f"Thread message to process - {message.author}: {message.content[:50]} - {thread.name} {thread.jump_url}"
        )

        channel_messages = [
            discord_message_to_message(message)
            async for message in thread.history(limit=MAX_THREAD_MESSAGES)
        ]
        channel_messages = [x for x in channel_messages if x is not None]
        channel_messages.reverse()

        # generate the response
        async with thread.typing():
            response_data = await generate_completion_response(
                messages=channel_messages, user=message.author
            )

        if is_last_message_stale(
            interaction_message=message,
            last_message=thread.last_message,
            bot_id=bot.user.id,
        ):
            # there is another message and its not from us, so ignore this response
            return

        # send response
        await process_response(
            user=message.author, thread=thread, response_data=response_data
        )
    except Exception as e:
        logger.exception(e)
# NOT COMPLETED CODE
    # chatbotchannel = 1122217290251911168
    # gptchannel = bot.get_channel(chatbotchannel)
    # if message.channel.id == chatbotchannel:
    #     async with gptchannel.typing():
    #         response = openAI(prompt=message.content)
    #         await gptchannel.send(response)


# ADDING THE USERS TO DB ON MESSAGE
    if message.author == bot.user:
        return
    try:
        if create_user == None:
            user = {
                "_id":int(message.author.id),
                "name":str(message.author.name),
                # "messages":1

            }
            data.insert_one(user)
            print(f"Added {str(message.author.name)} to db")
        # else:
        #     data.delete_one(create_user)
        #     create_user["messages"] = int(create_user["messages"]) + 1
        #     data.insert_one(create_user)
        #     print("Updated messages count for", str(message.author))


    except Exception as e:
        print(e)

# VIEW AVATAR COMMAND
@bot.tree.command(name="chat", description="Create a new thread for conversation")
@discord.app_commands.checks.has_permissions(send_messages=True)
@discord.app_commands.checks.has_permissions(view_channel=True)
@discord.app_commands.checks.bot_has_permissions(send_messages=True)
@discord.app_commands.checks.bot_has_permissions(view_channel=True)
@discord.app_commands.checks.bot_has_permissions(manage_threads=True)
async def chat_command(int: discord.Interaction, message: str):
    try:
        # only support creating thread in text channel
        if not isinstance(int.channel, discord.TextChannel):
            return

        # block servers not in allow list
        # if should_block(guild=int.guild):
            return

        user = int.user
        logger.info(f"Chat command by {user} {message[:20]}")
        try:
            # moderate the message
            flagged_str, blocked_str = moderate_message(message=message, user=user)
            await send_moderation_blocked_message(
                guild=int.guild,
                user=user,
                blocked_str=blocked_str,
                message=message,
            )
            if len(blocked_str) > 0:
                # message was blocked
                await int.response.send_message(
                    f"Your prompt has been blocked by moderation.\n{message}",
                    ephemeral=True,
                )
                return

            embed = discord.Embed(
                description=f"<@{user.id}> wants to chat! 🤖💬",
                color=discord.Color.green(),
            )
            embed.add_field(name=user.name, value=message)


            await int.response.send_message(embed=embed)
            response = await int.original_response()

        except Exception as e:
            logger.exception(e)
            await int.response.send_message(
                f"Failed to start chat {str(e)}", ephemeral=True
            )
            return

        # create the thread
        thread = await response.create_thread(
            name=f"{ACTIVATE_THREAD_PREFX} {user.name[:20]} - {message[:30]}",
            slowmode_delay=1,
            reason="gpt-bot",
            auto_archive_duration=60,
        )
        async with thread.typing():
            # fetch completion
            messages = [Message(user=user.name, text=message)]
            response_data = await generate_completion_response(
                messages=messages, user=user
            )
            # response_data = await gf_response(prompt=messages,chat_history=None)

            # send the result
            await process_response(
                user=user, thread=thread, response_data=response_data
            )
    except Exception as e:
        logger.exception(e)
        await int.response.send_message(
            f"Failed to start chat {str(e)}", ephemeral=True
        )
@bot.command()
async def av(ctx,member:discord.User = None):
    if member == None:
        member = ctx.author
    embed = discord.Embed()
    embed.set_image(url=member.display_avatar)
    await ctx.send(embed = embed)

# PING
@bot.command()
async def ping(ctx):
    ping = bot.latency
    await ctx.send(f"`Pong : {int(ping*100)}`")

# VERIFY (UNDER DEVELOPMENT)
@bot.command()
async def verify(ctx):
    role = discord.utils.get(ctx.guild.roles, name="-.*-member-.*-")
    role2 = discord.utils.get(ctx.guild.roles, name="unverified")
    question = discord.Embed(title = "React With ✅ to verify")
    message = await ctx.send(embed=question)
    await message.add_reaction('✅')


    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ['🔴','✅'] 
    
    while True:
        try:
            reaction, _ = await bot.wait_for('reaction_add', check=check)  
        except TimeoutError:
            await ctx.send('aah Mode')
        else:
            if reaction.emoji == '✅':
                member = ctx.author
                await member.add_roles(role)
                await member.remove_roles(role2)
                await ctx.send(f"{member.display_name} Verified!.")

# MOD APPLICATION
@bot.command()
async def modapp(ctx):
    db = mongo()
    user = db.find_one({"_id":int(ctx.author.id)})
    if 'mod' not in user:
        question = discord.Embed(title = "Are You Sure want to create Mod Application")
        message = await ctx.send(embed=question)
        await message.add_reaction('✔')
        await message.add_reaction('❌')  # Add reaction options


        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ['✔','❌'] 
        try:
            reaction, _ = await bot.wait_for('reaction_add',timeout=60.0, check=check)  
        except TimeoutError:
            await ctx.send('Timed Out')
        else:
            if reaction.emoji == '✔':
                embed = discord.Embed(title = "MOD APPLICATION",description=f"New Application created by {ctx.author.name}")
                await ctx.send(embed=embed)
                await ctx.send(f"<@{ctx.author.id}> `Please check Your DM. If didn't recieved please make sure your dm's are open for this server`")
                await ctx.author.send('Please Reply In Single Line')
                await ctx.author.send('https://media.tenor.com/Vant9OGye9gAAAAC/rainbow-bar-divider.gif')
                questions = [
                    'What is your discord username?',
                    'what is your discord userid?',
                    'How old are you?',
                    'Are You level 15 or above on our server?',
                    'For how many hours you are active in discord?',
                    'What is your timezone?',
                    'Do you have any mod experience before?',
                    'You created a new role how will you check if you had given correct perms or not?',
                    "A person is blackmailing someone in their dm what would you do?",
                    'A person is asking for a mod or admin or any other higher role,what will be your response?',
                    'What is the condition for warn?',
                ]
                answers = {}
                data = ["username","userid","age","level","active","timezone","experience","perms","blackmailing","ignore","warn"]

                for i in range (len(questions)):
                    await ctx.author.send(questions[i])

                    def check(message):
                        return message.author == ctx.author and isinstance(message.channel, discord.DMChannel)

                    try:
                        response = await bot.wait_for('message', timeout=90.0, check=check)
                        answers[data[i]] = response.content
                    except TimeoutError:
                        await ctx.author.send('You did not provide a response in time.')
                        break
                json_data = json.dumps(answers, indent=4)
                channel_id = int(modappch)
                channel = bot.get_channel(channel_id)

                # form data
                username = answers["username"]
                userid = answers["userid"]
                age = answers["age"]
                level = answers["level"]
                active = answers["active"]
                timezone = answers["timezone"]
                experience = answers["experience"]
                perms = answers["perms"]
                blackmailing = answers["blackmailing"]
                ignore = answers["ignore"]
                warn = answers["warn"]

                application = discord.Embed(title="MOD APPLICATION",description=f"Here is Mod Application from {ctx.author.name} \n **__User__** \n\n Name: {username} \n\n UserID: {userid} \n\n Age: {age} \n\n __**Questions**__ \n\n Are You level 15 or above on our server? \n {level} \n\n For how many hours you are active in discord? \n {active} \n\n What is your timezone? \n {timezone} \n\n Do you have any mod experience before? \n {experience} \n\n You created a new role how will you check if you had given correct perms or not? \n {perms} \n\n A person is blackmailing someone in their dm what would you do? \n {blackmailing} \n\n A person is asking for a mod or admin or any other higher role,what will be your response? \n {ignore} \n\n What is the condition for warn? \n {warn}")
                if channel is None:
                    return
                else:
                    await channel.send(f"here's a response from <@{ctx.author.id}>",embed = application)
                    db.delete_one(user)
                    user["mod"] = "True"
                    db.insert_one(user)

                await ctx.author.send("Thank you for answering the questions! Your Response has been recorded. Please don't send multiple applications or we have to remove your name from database")
            elif reaction.emoji == '❌':
                await ctx.send("Application Canceled")
    else:
        await ctx.send("You Can Only submit one application at a time. Please wait for the Admin to read that")

@bot.command()
@commands.has_role("read mod application")
async def read(ctx,member : discord.Member = None):
    if member == None:
        await ctx.send("Please Select the user to mark his application read")
    else:
        db = mongo()
        user = db.find_one({"_id":member.id})
        db.delete_one(user)
        del user["mod"]
        db.insert_one(user)
        await ctx.send(f"Marked <@{member.id}> Application as read")

# @bot.command()
# async def messages(ctx,member :discord.Member = None):
    
#     if member == None:
#         member = ctx.author

#     db = mongo()
#     user = db.find_one({"_id":int(member.id)})
#     messages = user["messages"]
#     embed = discord.Embed(title=f"{member.display_name} sent {messages} messages.",colour=discord.Colour.green())
#     await ctx.send(embed=embed)

@bot.tree.command(name="mannu",description="Mannu")
async def mannu(interaction :discord.Interaction):
    embed = discord.Embed(title="About Mannu",description="Hi There! I Am Mannu.The whole code is written by me so please gimme credit while using this code.\n There is MIT License in the file don't remove it but You can sublicense it. You can contact me on [Telegram](https://t.me/mannu_vilasara).\n Feel free to do changes in the code. Well its still under development. I'll publish the code of the production build as soon as possible. Join the Support server [here](https://discord.gg/unusual).",color=discord.Colour.green())
    embed.set_thumbnail(url="https://images-ext-1.discordapp.net/external/kKLwKGcE5w2SBsOtpFOHt1HuI9MeR3oX6uZNYWWyOEc/%3Fsize%3D1024/https/cdn.discordapp.com/guilds/997483421255340092/users/1035439449070383106/avatars/a_60c8c1e867cbce3d760c6012c1afd7cf.gif")
    embed.set_footer(text=f"Requested by {interaction.user}")
    await interaction.response.send_message(embed=embed)
    

@bot.command()
async def cat(ctx):
    get = getCat()
    url = get[0]["url"]
    embed = discord.Embed()
    embed.set_image(url=url)
    await ctx.send(embed=embed)

@bot.command()
async def dog(ctx):
    url = getDog()
    embed = discord.Embed()
    embed.set_image(url=url)
    await ctx.send(embed=embed)

@bot.command()
async def truth(ctx):
    a = requests.get("https://api.truthordarebot.xyz/v1/truth").json()
    question = a["question"]
    embed = discord.Embed(title=f"{question}")
    embed.set_author(name=ctx.author.display_name,icon_url=ctx.author.display_avatar)
    await ctx.send(embed=embed)

@bot.command()
async def dare(ctx):
    a = requests.get("https://api.truthordarebot.xyz/api/dare").json()
    question = a["question"]
    embed = discord.Embed(title=f"{question}")
    embed.set_author(name=ctx.author.display_name,icon_url=ctx.author.display_avatar)
    await ctx.send(embed=embed)

@bot.command()
async def wyr(ctx):
    a = requests.get("https://api.truthordarebot.xyz/api/wyr").json()
    await ctx.send(a["question"])

@bot.command()
async def nhie(ctx):
    a = requests.get("https://api.truthordarebot.xyz/api/nhie").json()
    await ctx.send(a["question"])

@bot.command()
async def gpt(ctx,*,prompt :str = None):
    async with ctx.typing():
        if prompt == None:
            await ctx.send("Please Type Your question")
        else:
            response = openAI(prompt=prompt)
            await ctx.send(response)
@bot.command()
async def set_timezone(ctx,timezone:str = None):
    if timezone == None:
            await ctx.send("Please enter your timezone")
            return
    a = requests.get(f"https://www.timeapi.io/api/Time/current/zone?timeZone={timezone}").json()
    if "Invalid Timezone" in a:
        await ctx.send("Please Enter A Valid Timezone")
        return
    else:
        db = mongo()
        user = db.find_one({"_id":int(ctx.author.id)})
        if 'timezone' not in user:
            question = discord.Embed(title = f"Are You Sure want to Set {timezone} as your timezone")
            message = await ctx.send(embed=question)
            await message.add_reaction('✔')
            await message.add_reaction('❌')  # Add reaction options


            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ['✔','❌'] 
            try:
                reaction, _ = await bot.wait_for('reaction_add',timeout=60.0, check=check)  
            except TimeoutError:
                await ctx.send('Timed Out')
            else:
                if reaction.emoji == '✔':
                    db.delete_one(user)
                    user["timezone"] = timezone
                    db.insert_one(user)
                    await ctx.send("Success")
                elif reaction.emoji == '❌':
                    await ctx.send("Canceled")
        else:
            db.delete_one(user)
            del user["timezone"]
            user["timezone"] = timezone
            db.insert_one(user)
            await ctx.send(f"`Updated your timezone to {timezone}`")

@bot.command()
async def time(ctx,member:discord.Member = None):
    if member == None:
        member = ctx.author
    db = mongo()
    user = db.find_one({"_id":int(member.id)})
    if 'timezone' in user:
        timezone = user["timezone"]
        a = requests.get(f"https://www.timeapi.io/api/Time/current/zone?timeZone={timezone}").json()
        time = a["time"]
        date = a["date"]
        colour = discord.Colour.green()
        embed = discord.Embed(title=f"Time for {member.display_name}",description=f"Date: {date} \n Time: {time} \n  <a:anime_zerotwohypedfast:1120375721819377715> ",color=colour)
        embed.set_thumbnail(url=member.display_avatar)
        await ctx.send(embed=embed)
        return
    else:
        if ctx.author.id == member.id:
            await ctx.send(f"Please set your timezone")
        else:
            await ctx.send(f"Please ask {member.display_name} to set their timezone")

@bot.command()
async def echo(ctx,*,message:str = "Mannu is good boy."):
    message_id = ctx.message.id
    delete = await ctx.channel.fetch_message(message_id)
    await delete.delete()
    await ctx.send(message)

@bot.command()
async def spotify(ctx, member: discord.Member = None):
    if member == None:
        member = ctx.author
    spotify_activity = None
    for activity in member.activities:
        if isinstance(activity, discord.Spotify):
            spotify_activity = activity
            break

    if spotify_activity is not None:
        song_name = spotify_activity.title
        artist_name = spotify_activity.artist
        album_name = spotify_activity.album
        thumbnail = spotify_activity.album_cover_url
        duration = spotify_activity.duration

        embed = discord.Embed(title="Spotify",description=f"**Song**\n{song_name}\n\n**Artist(s)**\n{artist_name}\n\n**Album**\n{album_name}\n\n**Duration**\n{duration}",color=discord.Colour.green())
        embed.set_thumbnail(url=thumbnail)
        embed.set_footer(text=f"Spotify of {member.display_name}",icon_url=member.display_avatar)
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title="Spotify",description=f"Not Listening",color=discord.Colour.red())
        embed.set_footer(text=f"Spotify of {member.display_name}",icon_url=member.display_avatar)
        await ctx.send(embed=embed)

@bot.command()
async def gh(ctx, username):
    url = f'https://api.github.com/users/{username}'
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        avatar = data.get('avatar_url')
        name = data.get('name')
        bio = data.get('bio')
        followers = data.get('followers')
        following = data.get('following')
        public_repos = data.get('public_repos')
        url = data.get('html_url')

        embed = discord.Embed(title=f"GitHub Profile - {username}", url=url)
        embed.set_thumbnail(url=avatar)
        if name:
            embed.add_field(name="Name", value=name, inline=False)
        if bio:
            embed.add_field(name="Bio", value=bio, inline=False)
        if followers:
            embed.add_field(name="Followers", value=followers, inline=True)
        if following:
            embed.add_field(name="Following", value=following, inline=True)
        if public_repos:
            embed.add_field(name="Public Repositories", value=public_repos, inline=True)

        await ctx.send(embed=embed)
    else:
        await ctx.send("GitHub profile not found.")

@bot.command()
async def sum(ctx,a:int,b:int):
    c = a + b
    await ctx.send(c)

@bot.command()
async def diff(ctx,a:int,b:int):
    c = a - b
    await ctx.send(c)

@bot.command()
async def multiply(ctx,a:int,b:int):
    c = a*b
    await ctx.send(c)

@bot.command()
async def div(ctx,a:int,b:int):
    c = a/b
    await ctx.send(c)
@bot.command()
async def cuddle(ctx,member:discord.Member):
    if member == None:
        await ctx.send("So Lonely.")
        return
    if ctx.author == member:
        await ctx.send("You can't cuddle with yourself.")
    else:
        a = requests.get("https://api.waifu.pics/sfw/cuddle").json()
        url = a["url"]
        embed = discord.Embed(title=f"{ctx.author.display_name} cuddle with {member.display_name}")
        embed.set_image(url=url)
        await ctx.send(embed=embed)
@bot.command()
async def help(ctx):
    description = "**__Official Server Bot of Misfit__** \n\n **Owners**: <@1035439449070383106>,<@790503319889379330>,<@953323321255145514> \n\n**Get A random Cat pic**\n`m!cat`\n\n**Get A random Dog pic**\n`m!dog`\n\n **Mathematical Operations**\n`m!sum(+)`  \n  `m!diff(-)`  \n  `m!muliply(*)`  \n  `m!divide(/)`\n\n**Get Spotify Playing Status**\n`m!spotify`\n\n**Search Github Profile**\n`m!gh`"
    embed = discord.Embed(title="Misfit Help",description=description,color=discord.Colour.green(),url="https://github.com/MannuVilasara/misfit")
    img = ctx.guild.icon
    embed.set_thumbnail(url=img)
    embed.add_field(name="--**Create Mod Application**--",value="`m!modapp`",inline= True)
    embed.add_field(name="--**Get User avatar**--",value="`m!av`",inline= True)
    embed.add_field(name="--**Ask gpt**--",value="`m!gpt`",inline= True)
    await ctx.send(embed=embed)

@bot.command()
async def waifu(ctx):
    a = requests.get("https://api.waifu.pics/sfw/waifu").json()
    url = a["url"]
    embed = discord.Embed(color= discord.Colour.green())
    embed.set_image(url=url)
    await ctx.send(embed=embed)

@bot.tree.command(name="activity",description="Get An activity to not get bored")
async def activity(int:discord.Interaction):
    await int.response.defer()
    a = requests.get("https://www.boredapi.com/api/activity").json()
    response = a["activity"]
    embed = discord.Embed(title=f"{response}")
    embed.set_author(name="Ray<3",icon_url="https://cdn.discordapp.com/avatars/790503319889379330/651f247855d243e538293ff703e1f827.webp?")
    await int.followup.send(embed=embed)

@bot.tree.command(name="set-timezone",description="Set Your Timezone")
async def set_timezone(interaction:discord.Interaction,timezone:str):
    try:
        await interaction.response.defer()
        a = requests.get(f"https://www.timeapi.io/api/Time/current/zone?timeZone={timezone}").json()
        if "Invalid Timezone" in a:
            await interaction.followup.send("Please Enter A Valid Timezone.", ephemeral=True)
            return
        else:
            db = mongo()
            user = db.find_one({"_id":int(interaction.user.id)})
            if 'timezone' not in user:
                question = discord.Embed(title = f"Are You Sure want to Set {timezone} as your timezone")
                message = await interaction.followup.send(embed=question)
                await message.add_reaction('✔')
                await message.add_reaction('❌')  # Add reaction options


                def check(reaction, user):
                    return user == interaction.user and str(reaction.emoji) in ['✔','❌'] 
                try:
                    reaction, _ = await bot.wait_for('reaction_add',timeout=60.0, check=check)  
                except TimeoutError:
                    await interaction.followup.send('Timed Out', ephemeral=True)
                else:
                    if reaction.emoji == '✔':
                        db.delete_one(user)
                        user["timezone"] = timezone
                        db.insert_one(user)
                        await interaction.followup.send("Success.", ephemeral=True)
                    elif reaction.emoji == '❌':
                        await interaction.followup.send("Canceled.", ephemeral=True)
            else:
                db.delete_one(user)
                del user["timezone"]
                user["timezone"] = timezone
                db.insert_one(user)
                await interaction.followup.send(f"`Updated your timezone to {timezone}`")
    except Exception as e:
        print(f"An error occurred: {e}")
@bot.tree.command(name="help",description="View Commands of Misift")
async def help_command(int:discord.Interaction):
    description = "**__Official Server Bot of Misfit__** \n\n **Owners**: <@1035439449070383106>,<@790503319889379330>,<@953323321255145514> \n\n**Get A random Cat pic**\n`m!cat`\n\n**Get A random Dog pic**\n`m!dog`\n\n **Mathematical Operations**\n`m!sum(+)`  \n  `m!diff(-)`  \n  `m!muliply(*)`  \n  `m!divide(/)`\n\n**Get Spotify Playing Status**\n`m!spotify`\n\n**Search Github Profile**\n`m!gh`"
    embed = discord.Embed(title="Misfit Help",description=description,color=discord.Colour.green(),url="https://github.com/MannuVilasara/misfit")
    img = int.guild.icon
    embed.set_thumbnail(url=img)
    embed.add_field(name="--**Create Mod Application**--",value="`m!modapp`",inline= True)
    embed.add_field(name="--**Get User avatar**--",value="`m!av`",inline= True)
    embed.add_field(name="--**Ask gpt**--",value="`m!gpt`",inline= True)
    await int.response.send_message(embed=embed)

@bot.tree.command(name="echo",description="Make the bot send Message")
async def echo_cmd(int:discord.Interaction,message:str):
    await int.response.send_message(message)
bot.run(token)