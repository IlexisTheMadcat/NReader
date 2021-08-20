from re import search, findall
from asyncio import sleep, TimeoutError
from textwrap import shorten
from copy import deepcopy
from contextlib import suppress

from udpy import AsyncUrbanClient
from discord import Forbidden, NotFound
from discord.ext.commands import (
    Cog, bot_has_permissions, 
    bot_has_guild_permissions, command)
from discord_components import Button
from dev_nhentai.nhentai_async import NHentaiAsync as NHentai, Doujin, DoujinThumbnail

from utils.classes import (
    Embed, BotInteractionCooldown)
from cogs.Tclasses import (
    ImagePageReader,
    SearchResultsBrowser)
from utils.Tmisc import language_to_flag, restricted_tags, render_date

newline = "\n"
experimental_prefix = "T"

class Commands(Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @command(name=f"{experimental_prefix}test")
    @bot_has_permissions(send_messages=True, embed_links=True)
    async def test(self, ctx):
        try:
            await ctx.send("Done (1/3).")
        except Exception:
            await ctx.author.send("(1/3) I can't send messages there.")
        
        try:
            await ctx.send(embed=Embed(description="Done (2/3)."))
        except Exception:
            await ctx.send("(2/3) I can't send embeds in here.")
        
        conf = await self.bot.comp_ext.send_component_msg(ctx, embed=Embed(description="Waiting for button... (3/3)."),
            components=[Button(label="Example.", style=1, emoji="🔘", id="button1")])

        try:
            interaction = await self.bot.wait_for("button_click", timeout=10, bypass_cooldown=True,
                check=lambda i: \
                    i.user.id == ctx.author.id and \
                    i.message.id == conf.id and \
                    i.component.id == "button1")
        
        except TimeoutError:
            await self.bot.comp_ext.edit_component_msg(conf, embed=Embed(description="Button timed out (3/3)."),
                components=[Button(label="Timeout.", style=4, emoji="🕒", id="button1", disabled=True)])

        except Exception:
            await self.bot.comp_ext.edit_component_msg(conf, embed=Embed(description="Button failed (3/3)."),
                components=[Button(label="Failed.", style=4, emoji="⛔", id="button1", disabled=True)])
        
        else:
            await self.bot.comp_ext.edit_component_msg(conf, embed=Embed(description="Button complete. (3/3)."),
                components=[Button(label="Complete.", style=3, emoji="✅", id="button1")])
            
            await interaction.respond(type=6)
            
        
        print(f"{ctx.author} ({ctx.author.id}) tested.")
       
    @command(
        name=f"{experimental_prefix}doujin_info", 
        aliases=[f"{experimental_prefix}code"])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    async def doujin_info(self, ctx, code="random", interface="new"):
        # TODO: Update ImagePageReader

        lolicon_allowed = False
        try:
            if not ctx.guild or ctx.guild.id in self.bot.user_data["UserData"][str(ctx.guild.owner_id)]["Settings"]["UnrestrictedServers"]:
                lolicon_allowed = True
        except KeyError:
            pass
        
        # Must use in an NSFW channel
        if ctx.guild and not ctx.channel.is_nsfw():
            await ctx.send(embed=Embed(
                description="❌ This command cannot be used in a non-NSFW channel."))

            return
        
        # Verify that `code` is a number
        try:
            if code.lower() not in ["random", "r"]:
                code = int(code)
                code = str(code)
        except ValueError:
            await ctx.send(embed=Embed(description="❌ You didn't type a proper ID. Come on, numbers!"))
            return
        
        nhentai_api = NHentai()
        edit = await self.bot.comp_ext.send_component_msg(ctx, embed=Embed(description=f"{self.bot.get_emoji(810936543401213953)}"))

        if code.lower() not in ["random", "r"]:
            # Lookup
            doujin = await nhentai_api.get_doujin(code)
            if not doujin:
                return await edit.edit(embed=Embed(description="🔎❌ I did not find a doujin with that ID."))

            # Stop if it is a sensitive doujin and notify user of workaround
            if not lolicon_allowed and any([tag.name in restricted_tags for tag in doujin.tags]):
                await edit.edit(embed=Embed(description="⚠️⛔ This doujin contains lolicon/shotacon content and cannot be displayed publically."))

                if not self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["NotificationsDue"]["LoliconViewingTip"]:
                    with suppress(Forbidden):
                        await ctx.author.send(self.bot.config["lolicon_viewing_tip"])
                    
                    self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["NotificationsDue"]["LoliconViewingTip"] = True

                return

        else:
            # Get a random doujin
            while True:
                doujin = await nhentai_api.get_random()
                self.bot.doujin_cache[str(doujin.id)] = doujin
                if not lolicon_allowed and any([tag in restricted_tags for tag in doujin.tags]):
                    await edit.edit(embed=Embed(
                        description=f"{self.bot.get_emoji(810936543401213953)} Retrying..."))
                        
                    await sleep(0.5)
                    continue

                else:
                    break
        
        if interface == "old":
            emb = Embed(
                description=f"Doujin ID: __`{doujin.id}`__\n"
                            f"Secondary Title: `{doujin.secondary_title if doujin.secondary_title else 'Not provided'}`\n"
                            f"Language(s): {language_to_flag(doujin.languages)}`{', '.join(doujin.languages) if doujin.languages else 'Not provided'}`\n"
                            f"Pages: `{len(doujin.images)}`\n"
                            f"Artist(s): `{', '.join(doujin.artists) if doujin.artists else 'Not provided'}`\n"
                            f"Character(s): `{', '.join(doujin.characters) if doujin.characters else 'Original'}`\n"
                            f"Parody of: `{', '.join(doujin.parodies) if doujin.parodies else 'Original'}`\n"
                            f"Tags: ```{', '.join(doujin.tags) if doujin.tags != [] else 'None provided'}```\n")
            
            emb.set_author(
                name=f"{doujin.title if doujin.title else '[Untitled]'}",
                url=f"https://nhentai.net/g/{doujin.id}/",
                icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
            emb.set_thumbnail(
                url=doujin.images[0])
        else:
            emb = Embed()
            emb.add_field(
                name=f"Title",
                inline=False,
                value=f"{shorten(doujin.title.pretty, width=256, placeholder='...')}"
            ).add_field(
                inline=False,
                name="ID || Pages",
                value=f"`{doujin.id}` - `{doujin.total_pages}`"
            ).add_field(
                inline=False,
                name="Date Uploaded",
                value=f"`{render_date(doujin.upload_at)}`"
            ).add_field(
                inline=False,
                name="Language(s) in this work",
                value=f"{language_to_flag(doujin.languages)} `{', '.join([tag.name for tag in doujin.languages]) if doujin.languages else 'Not provided'}`"
            ).add_field(
                inline=False,
                name="Featured artist(s)",
                value=f"`{', '.join([tag.name for tag in doujin.artists]) if doujin.artists else 'Not provided'}`"
            ).add_field(
                inline=False,
                name="Character(s) in this work",
                value=f"`{', '.join([tag.name for tag in doujin.characters]) if doujin.characters else 'Original'}`"
            ).add_field(
                inline=False,
                name="A parody of",
                value=f"`{', '.join([tag.name for tag in doujin.parodies]) if doujin.parodies else 'Original'}`"
            ).set_footer(
                text=f"⭐ {doujin.total_favorites}"
            )

            # Doujin count for tags
            tags_list = []
            for tag in doujin.tags:
                if tag.type != "tag": continue
                count = tag.count
                parse_count = list(str(count))
                if len(parse_count) < 4:
                    tags_list.append(f"{tag.name}[{count}]")
                elif len(parse_count) >= 4 and len(parse_count) <= 6:
                    count = count/1000
                    tags_list.append(f"{tag.name}[{round(count, 1)}k]")
                elif len(parse_count) > 7:
                    count = count/1000000
                    tags_list.append(f"{tag.name}[{round(count, 2)}m]")

            emb.add_field(
                inline=False,
                name="Content tags",
                value=f"```{', '.join(tags_list) if doujin.tags else 'None provided'}```"
            )

            emb.set_author(
                name=f"NHentai",
                url=f"https://nhentai.net/g/{doujin.id}/",
                icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
            emb.set_thumbnail(url=doujin.images[0].src)
        
        print(f"[] {ctx.author} ({ctx.author.id}) looked up `{doujin.id}`.")

        if not ctx.guild or (ctx.guild and not all([
            ctx.guild.me.guild_permissions.manage_channels, 
            ctx.guild.me.guild_permissions.manage_roles, 
            ctx.guild.me.guild_permissions.manage_messages])):
            await self.bot.comp_ext.edit_component_msg(edit, content="", embed=emb,
                components=[
                    [Button(label="Need Permissions", style=1, emoji=self.bot.get_emoji(853684136379416616), id="button1", disabled=True),
                    Button(label="Expand Thumbnail", style=2, emoji=self.bot.get_emoji(853684136433942560), id="button2")]
                ])
        else:
            await self.bot.comp_ext.edit_component_msg(edit, content="", embed=emb,
                components=[
                    [Button(label="Read", style=1, emoji=self.bot.get_emoji(853684136379416616), id="button1"),
                    Button(label="Expand Thumbnail", style=2, emoji=self.bot.get_emoji(853684136433942560), id="button2")]
                ])

        while True:
            try:
                interaction = await self.bot.wait_for("button_click", timeout=60, 
                    check=lambda i: i.message.id==edit.id and i.user.id==ctx.author.id)
            
            except TimeoutError:
                emb.set_thumbnail(url=doujin.images[0].src)
                emb.set_image(url=Embed.Empty)
                
                with suppress(NotFound):
                    await self.bot.comp_ext.edit_component_msg(edit, embed=emb, 
                        components=[
                            [Button(label="Read", style=1, emoji=self.bot.get_emoji(853684136379416616), id="button1", disabled=True),
                            Button(label="Expand Thumbnail", style=2, emoji=self.bot.get_emoji(853684136433942560), id="button2", disabled=True)]
                        ])
                
                return
            
            except BotInteractionCooldown:
                continue
            
            else:
                await interaction.respond(type=6)
                if interaction.component.id == "button1":
                    with suppress(Forbidden):
                        await edit.clear_reactions()

                    if not ctx.guild or (ctx.guild and not all([
                        ctx.guild.me.guild_permissions.manage_channels, 
                        ctx.guild.me.guild_permissions.manage_roles, 
                        ctx.guild.me.guild_permissions.manage_messages])):
                        await ctx.send(embed=Embed(description="❌ Unexpected loss of required permissions."), delete_after=5)
                        continue
                    else:
                        emb.set_thumbnail(
                            url=doujin.images[0].src)
                        emb.set_image(url=Embed.Empty)
                        await self.bot.comp_ext.edit_component_msg(edit, content="", embed=emb,
                            components=[
                                [Button(label="Opened", style=1, emoji=self.bot.get_emoji(853684136379416616), id="button1", disabled=True),
                                Button(label="Expand Thumbnail", style=2, emoji=self.bot.get_emoji(853684136433942560), id="button2", disabled=True)]
                            ])

                        session = ImagePageReader(self.bot, ctx, doujin.images, f"{doujin.id} [*n*] {doujin.title.pretty}", str(doujin.id))
                        response = await session.setup()
                        if response:
                            print(f"[] {ctx.author} ({ctx.author.id}) started reading `{doujin.id}`.")
                            await session.start()
                    
                        else:
                            await edit.edit(embed=emb)
                    
                        return
                
                if interaction.component.id == "button2":
                    if not emb.image:
                        emb.set_image(url=emb.thumbnail.url)
                        emb.set_thumbnail(url=Embed.Empty)
                        word = "Minimize"

                    elif not emb.thumbnail:
                        emb.set_thumbnail(url=emb.image.url)
                        emb.set_image(url=Embed.Empty)
                        word = "Expand"
                    
                    if not ctx.guild or (ctx.guild and not all([
                        ctx.guild.me.guild_permissions.manage_channels, 
                        ctx.guild.me.guild_permissions.manage_roles, 
                        ctx.guild.me.guild_permissions.manage_messages])):
                        await self.bot.comp_ext.edit_component_msg(edit, content="", embed=emb,
                            components=[
                                [Button(label="Need Permissions", style=1, emoji=self.bot.get_emoji(853684136379416616), id="button1", disabled=True),
                                Button(label=f"{word} Thumbnail", style=2, emoji=self.bot.get_emoji(853684136433942560), id="button2")]
                            ])
                    else:
                        await self.bot.comp_ext.edit_component_msg(edit, content="", embed=emb,
                            components=[
                                [Button(label="Read", style=1, emoji=self.bot.get_emoji(853684136379416616), id="button1"),
                                Button(label=f"{word} Thumbnail", style=2, emoji=self.bot.get_emoji(853684136433942560), id="button2")]
                            ])

                    continue
    
    @command(
        name=f"{experimental_prefix}search_doujins",
        aliases=[f"{experimental_prefix}search"])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    @bot_has_guild_permissions(
        manage_messages=True, 
        manage_channels=True, 
        manage_roles=True)
    async def search_doujins(self, ctx, *, query: str = ""):
        lolicon_allowed = False
        try:
            if not ctx.guild or ctx.guild.id in self.bot.user_data["UserData"][str(ctx.guild.owner_id)]["Settings"]["UnrestrictedServers"]:
                lolicon_allowed = True
        except KeyError:
            pass
        
        if not ctx.channel.is_nsfw():
            await ctx.send("❌ This command cannot be used in a non-NSFW channel.")
            return
        
        conf = await self.bot.comp_ext.send_component_msg(ctx, embed=Embed(description=f"{self.bot.get_emoji(810936543401213953)}"))
    
        nhentai_api = NHentai()

        if "--noappend" in query:
            query = query.replace("--noappend", "")
            appendage = ""
        elif str(ctx.author.id) in self.bot.user_data["UserData"] and \
            "Settings" in self.bot.user_data["UserData"][str(ctx.author.id)] and \
            "SearchAppendage" in self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"] and \
            self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["SearchAppendage"] != " ":
            appendage = self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["SearchAppendage"]
        else:
            appendage = ""
        
        page_raw = search(r"\-\-page=[0-9]+", query)
        if page_raw: 
            page = int(page_raw.group().split("=")[1])
            if not page:
                return await conf.edit(content="", embed=Embed(
                    title="❌ Invalid page number.",
                    description="`0` (zero) is not a valid page number. Page number must be greater than zero."))
            else:
                query = query.replace(page_raw.group(), '').strip(' ')
        else: 
            page = 1
            
        sort_raw = search(r"\-\-sort=(?:(today)|(week)|(month)|(popular)|(recent))", query)
        if sort_raw: 
            value = str(sort_raw.group().split("=")[1])
            if value not in ['today', 'week', 'month', 'popular', 'recent']:
                return await conf.edit(content="", embed=Embed(
                    title="❌ Invalid sort parameter.",
                    description="That's not a method I can sort by. I can only support by popularity `today`, this `week`, this `month`, all time `popular`, or `recent` (default)."))
            else:
                query = query.replace(sort_raw.group(), '').strip(' ')

                if value == 'today':
                    sort = 'popular-today'
                elif value == 'week':
                    sort = 'popular-week'
                elif value == 'month':
                    sort = 'popular-month'
                elif value == 'popular':
                    sort = 'popular'
                elif value == 'recent':
                    sort = None
        else: 
            sort = 'popular'

        if not query and not appendage:
            await conf.edit(content="", embed=Embed(
                title="❌ Search is too broad. Say something.",
                description="You need to tell me what to search, or update your search appendage (See `search_appendage` in `n!help`)."))
            
            return

        results = await nhentai_api.search(query=query+f"{appendage}", sort=sort, page=page)

        if isinstance(results, Doujin):
            if results.id not in self.bot.doujin_cache:
                self.bot.doujin_cache[results.id] = results
            
            await conf.delete()
            ctx.message.content = f"n!code {results.id}"
            await self.bot.process_commands(ctx.message)
            return
        
        if not results.doujins:
            newline = "\n"
            await conf.edit(content='', embed=Embed(
                title = "🔎❌ I did not find anything. Check your keywords!",
                description = f"{newline+'`*️⃣` This may be the cause of your search appendage. See `search_appendage` in `n!help`, or add `--noappend` to bypass it.' if appendage else ''}"
                              f'{newline+"`*️⃣` You have added a page number to your search (`--page#`). Please check that your page is within the total page count (check by searching without a page)." if page_raw else ""}'))
            return
        
        message_part = []
        doujins = []
        for ind, dj in enumerate(results.doujins):
            if not lolicon_allowed and any([tag.name in restricted_tags for tag in dj.tags]):
                message_part.append("__`       `__ | ⚠🚫 | Contains restricted tags.")
            else:
                message_part.append(
                    f"__`{str(dj.id).ljust(7)}`__ | "
                    f"{language_to_flag(dj.languages)} | "
                    f"{shorten(dj.title.pretty, width=50, placeholder='...')}")

        emb = Embed(
            description=f"Showing page {page}/{results.total_pages if results.total_pages else '1'} ({results.total_results} doujins)"
                        f"{'; illegal results are hidden:' if ctx.guild and not lolicon_allowed else ':'}"
                        f"\n"+('\n'.join(message_part))
        ).set_author(
            name="NHentai",
            url="https://nhentai.net/",
            icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1"
        ).set_thumbnail(url=results.doujins[0].cover.src)
        
        print(f"[] {ctx.author} ({ctx.author.id}) searched for [{query if query else ''}{' ' if query and appendage else ''}{appendage if appendage else ''}].")
        
        await self.bot.comp_ext.edit_component_msg(conf, embed=emb,
            components=[Button(label="Start Interactive", style=1, emoji=self.bot.get_emoji(853674277416206387), id="button1")])
        
        try:
            interaction = await self.bot.wait_for('button_click', timeout=20, bypass_cooldown=True,
                check=lambda i: i.message.id==conf.id and \
                    i.user.id==ctx.author.id and \
                    i.component.id=="button1")
        except TimeoutError:
            await self.bot.comp_ext.edit_component_msg(conf, embed=emb,
                components=[Button(label="Start Interactive", style=1, emoji=self.bot.get_emoji(853674277416206387), id="button1", disabled=True)])
            
            return

        else:
            await interaction.respond(type=6)

            await self.bot.comp_ext.edit_component_msg(conf, embed=emb, components=[])
            
            interactive = SearchResultsBrowser(self.bot, ctx, results.doujins, msg=conf, lolicon_allowed=lolicon_allowed)
            await interactive.start(ctx)
    
    @command(
        name=f"{experimental_prefix}popular",
        aliases=[f"{experimental_prefix}pop"])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    async def popular(self, ctx):
        lolicon_allowed = False
        try:
            if not ctx.guild or ctx.guild.id in self.bot.user_data["UserData"][str(ctx.guild.owner_id)]["Settings"]["UnrestrictedServers"]:
                lolicon_allowed = True
        except KeyError:
            pass
        
        if not ctx.channel.is_nsfw():
            await ctx.send(embed=Embed(
                description="❌ This command cannot be used in a non-NSFW channel."))

            return
        
        conf = await ctx.send(embed=Embed(
            description=f"{self.bot.get_emoji(810936543401213953)} Loading..."
        ).set_footer(text="This should take no more than 5 seconds."))

        nhentai_api = NHentai()
        results = await nhentai_api.get_popular_now()

        message_part = []
        doujins = []
        for ind, dj in enumerate(results.doujins):
            dj = await nhentai_api.get_doujin(dj.id)            
            doujins.append(dj)
            
            tags = [tag.name for tag in dj.tags if tag.type == "tag"]
            if not lolicon_allowed and any([tag in restricted_tags for tag in tags]):
                message_part.append("__`       `__ | ⚠🚫 | Contains restricted tags.")
            else:
                message_part.append(
                    f"__`{str(dj.id).ljust(7)}`__ | "
                    f"{language_to_flag(dj.languages)} | "
                    f"{shorten(dj.title.pretty, width=50, placeholder='...')}")

        emb = Embed(
            title=f"<:npopular:853883174455214102> **Popular Now**",
            description=f"\n"+('\n'.join(message_part)))
        emb.set_author(
            name="NHentai",
            url="https://nhentai.net/",
            icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
        
        await self.bot.comp_ext.edit_component_msg(conf, embed=emb,
            components=[Button(label="Start Interactive", style=1, emoji=self.bot.get_emoji(853674277416206387), id="button1")])
        
        try:
            interaction = await self.bot.wait_for('button_click', timeout=20, bypass_cooldown=True,
                check=lambda i: i.message.id==conf.id and \
                    i.user.id==ctx.author.id and \
                    i.component.id=="button1")
        except TimeoutError:
            await self.bot.comp_ext.edit_component_msg(conf, embed=emb,
                components=[Button(label="Start Interactive", style=2, emoji=self.bot.get_emoji(853674277416206387), id="button1", disabled=True)])
            
            return

        else:
            await interaction.respond(type=6)

            await self.bot.comp_ext.edit_component_msg(conf, embed=emb, components=[])

            interactive = SearchResultsBrowser(self.bot, ctx, doujins, msg=conf, name=f"<:npopular:853883174455214102> **Popular Now**", lolicon_allowed=lolicon_allowed)
            await interactive.start(ctx)
    
    @command(
        name=f"{experimental_prefix}whitelist",
        aliases=[f"{experimental_prefix}whl"])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    async def whitelist(self, ctx, mode=None):
        if not ctx.guild:
            await ctx.send(embed=Embed(
                description=":x: These commands must be run in a server. Consider making a private one."))

            return

        if ctx.guild and ctx.author.id != ctx.guild.owner_id:
            await ctx.send(embed=Embed(
                color=0xFF0000,
                description="❌ You must be the owner of the server to use this command."))
            
            return
        
        if not mode:
            if self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["UnrestrictedServers"]:
                message_part = []
                for i in deepcopy(self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["UnrestrictedServers"]):
                    guild = self.bot.get_guild(i)
                    if guild: message_part.append(f"Name: {guild.name} ({i})")
                    else: self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["UnrestrictedServers"].remove(i)
                    continue
                
                await ctx.send(embed=Embed(
                    title="Whitelisted Servers",
                    description="```"+"\n".join(message_part)+"```"))

            else:
                await ctx.send(embed=Embed(
                    description="❌ You have no whitelisted servers."))

                return
                    
        elif mode.lower() in ["add", "a", "+"]:
            emb = Embed(
                title="Server Whitelisting",
                description="⚠ You're about to enable restricted features for this entire server. "
                            "Using these features around others may have an impact on their judgements on you.\n"
                            "The bot developer is not responsible for loss of friendships in this case, nor shall the developer be accused of distributing this content under their behalf. It is solely on **you**.\n"
                            "Remember, admins can see what you read in your server. If you want to read in private, remove admins or create a new server.")
            
            emb.set_footer(text="If you still want to continue, press the 'I accept' button.")
            
            conf = await self.bot.comp_ext.send_component_msg(ctx, embed=emb,
                components=[
                    [Button(label="Accept", style=2, id="button1"),
                     Button(label="Decline", style=1, id="button2")]])
            
            try:
                interaction = await self.bot.wait_for('button_click', timeout=60,
                    check=lambda i: \
                        i.message.id==conf.id and \
                        i.user.id==ctx.author.id)
            
            except TimeoutError:
                await self.bot.comp_ext.edit_component_msg(conf, embed=emb, bypass_cooldown=True,
                    components=[
                        [Button(label="Accept", style=2, emoji="✅", id="button1", disabled=True),
                         Button(label="Decline", style=1, emoji="❌", id="button2", disabled=True)]])
                
                return

            else:
                await interaction.respond(type=6)
                
                if interaction.component.id == "button1":
                    if ctx.guild.id not in self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["UnrestrictedServers"]:
                        self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["UnrestrictedServers"].append(ctx.guild.id)
                    await self.bot.comp_ext.edit_component_msg(conf, embed=Embed(
                        title="Server whitelisting",
                        description="✔ This server can now access doujins that contain underage characters."),
                        components=[
                            [Button(label="Accepted", style=3, emoji="✅", id="button1", disabled=True),
                             Button(label="Decline", style=1, emoji="❌", id="button2", disabled=True)]])
                
                if interaction.component.id == "button2":
                    await self.bot.comp_ext.edit_component_msg(conf, embed=Embed(
                        color=0xFF0000,
                        title="Server whitelisting",
                        description="❌ Operation cancelled."),
                        components=[
                            [Button(label="Accept", style=2, emoji="✅", id="button1", disabled=True),
                             Button(label="Declined", style=4, emoji="❌", id="button2", disabled=True)]])
    
        elif mode.lower() in ["remove", "r", "-"]:
            if ctx.guild.id in self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["UnrestrictedServers"]:
                self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["UnrestrictedServers"].remove(ctx.guild.id)
            await ctx.send(embed=Embed(
                title="Server whitelisting",
                description="✔ This server can no longer access doujins that contain underage characters."))
        
        else:
            await ctx.send(embed=Embed(
                color=0xFF0000,
                description="You didn't specify a mode. Valid modes are `add/a/+` and `remove/r/-`."))

    @command(
        name=f"{experimental_prefix}lists",
        aliases=[
            f"{experimental_prefix}library",
            f"{experimental_prefix}lib", 
            f"{experimental_prefix}l"])
    @bot_has_permissions(
        send_messages=True,
        embed_links=True)
    async def lists(self, ctx, name=None, mode=None, code=None):
        if not ctx.guild:
            await ctx.send(embed=Embed(
                description="❌ These commands must be run in a server. Consider making a private one."))

            return

        lolicon_allowed = False
        try:
            if not ctx.guild or ctx.guild.id in self.bot.user_data["UserData"][str(ctx.guild.owner_id)]["Settings"]["UnrestrictedServers"]:
                lolicon_allowed = True
        except KeyError:
            pass

        if not ctx.channel.is_nsfw():
            await ctx.send("❌ This command cannot be used in a non-NSFW channel.")
            return

        async def load_list(list_items):
            if not len(list_items)-1:
                emb = Embed(
                    title=f"{list_name}",
                    description="❌ There is nothing in this list."
                ).set_author(
                    name="NHentai",
                    url="https://nhentai.net/",
                    icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
            
                await ctx.send(embed=emb)
                return

            nhentai_api = NHentai()
            edit = await ctx.send(
                embed=Embed(
                    description=f"Loading..."
                ).set_author(
                    name="NHentai",
                    url=f"https://nhentai.net/",
                    icon_url="https://cdn.discordapp.com/emojis/810936543401213953.gif?v=1"
                ).set_footer(
                    text=f"This should take no more than 10 seconds."))

            await sleep(1)

            message_part = list()
            remove_queue = list()  # It is very rare that a doujin would get deleted from NHentai

            is_loading = False
            for code in list_items:
                if code not in self.bot.doujin_cache and code != "0":
                    is_loading = True
                    break
            
            doujins = []
            passed_placeholder = False
            for ind, code in enumerate(list_items):
                if passed_placeholder:
                    ind -= 1

                bookmark_page = None
                if isinstance(list_items, dict):  # Is the Bookmarks list
                    bookmark_page = list_items[item]

                if code == "placeholder":
                    passed_placeholder = True
                    continue

                doujin = await nhentai_api.get_doujin(code)
                if not doujin:
                    remove_queue.append(code)
                    continue

                tags = [tag.name for tag in doujin.tags if tag.type == "tag"]
                if any([tag in restricted_tags for tag in tags]): is_lolicon = True
                else: is_lolicon = False
                    
                if is_lolicon and not lolicon_allowed:
                    pass
                else:
                    if not bookmark_page:
                        message_part.append(
                            f"__`{str(doujin.id).ljust(7)}`__ | "
                            f"{language_to_flag(doujin.languages)} | "
                            f"{shorten(doujin.title.pretty, width=50, placeholder='...')}")
                    elif bookmark_page:
                        message_part.append(
                            f"__`{str(doujin.id).ljust(7)}`__ | "
                            f"{language_to_flag(doujin.languages)} | "
                            f"Page [{bookmark_page}/{len(doujin.images)}] | "
                            f"{shorten(doujin.title.pretty, width=40, placeholder='...')}")
                        
                    doujins.append(doujin)
            
            [list_items.remove(code) for code in remove_queue]
            
            emb = Embed(
                title=f"{list_name}",
                description=f"\n"+('\n'.join(message_part))
            ).set_author(
                name="NHentai",
                url="https://nhentai.net/",
                icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
                
            await self.bot.comp_ext.edit_component_msg(edit, embed=emb,
                components=[Button(label="Start Interactive", style=1, emoji=self.bot.get_emoji(853674277416206387), id="button1")])
                
            try:
                interaction = await self.bot.wait_for('button_click', timeout=20, bypass_cooldown=True,
                    check=lambda i: i.message.id==edit.id and \
                        i.user.id==ctx.author.id and \
                        i.component.id=="button1")
            except TimeoutError:
                await self.bot.comp_ext.edit_component_msg(edit, embed=emb,
                    components=[Button(label="Start Interactive", style=2, emoji=self.bot.get_emoji(853674277416206387), id="button1", disabled=True)])
                    
                return

            else:
                await interaction.respond(type=6)

                await self.bot.comp_ext.edit_component_msg(edit, embed=emb, components=[])

                interactive = SearchResultsBrowser(self.bot, ctx, doujins, msg=edit, name=f"{list_name}", lolicon_allowed=lolicon_allowed)
                await interactive.start(ctx)

                return

            await edit.edit(embed=emb)

        if not name:
            built_in_str = []
            custom_str = []
            for sys_category, lists in self.bot.user_data["UserData"][str(ctx.author.id)]["Lists"].items():
                for ind, (list_full_name, contents) in enumerate(lists.items()):
                    if "|*n*|" in list_full_name:
                        parts = list_full_name.split("|*n*|")
                        list_name = parts[0]
                        alias = parts[1]
                    else:
                        list_name = list_full_name
                        alias = None

                    if sys_category == "Built-in":
                        if list_name == "Favorites": 
                            length = len(contents)
                            list_name = "⭐ Favorites"
                        if list_name == "Read Later": 
                            length = len(contents)
                            list_name = "📑 Read Later"
                        if list_name == "Bookmarks": 
                            length = len(contents)
                            list_name = "🔖 Bookmarks"
                            print(contents)
                        if list_name == "History": 
                            length = len(contents["list"])
                            list_name = "🕑 History"
                        built_in_str.append(f"**{list_name}**{'||/'+alias+'||' if alias else ''} ({length-1})")

                    if sys_category == "Custom" and list_name != "placeholder":
                        custom_str.append(f"**{list_name}**{'||/'+alias+'||' if alias else ''} ({len(contents)-1})")

            emb = Embed(
                title="Your Library",
                description="Here are your lists."
            ).set_author(
                    name="NHentai",
                    url="https://nhentai.net/",
                    icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1"
            ).add_field(
                name="__📌 Built-in__",
                inline=False,
                value=f"{newline.join(built_in_str)}")
            if custom_str: emb.add_field(
                name="__💾 Custom__",
                inline=False,
                value=f"{newline.join(custom_str)}")

            await ctx.send(embed=emb)
            return

        if "|*n*|" in name:
            await ctx.send(embed=Embed(description="❌ `|*n*|` is a reserved string for the bot and you cannot use it."))
            return

        # Get item by alias within string
        list_name = None
        alias_name = None
        full_name = None
        sys_category = None
        target_list = None
        if mode not in ["create", "cr"]:
            for _sys_category, _lists in self.bot.user_data["UserData"][str(ctx.author.id)]["Lists"].items():
                for ind, (_list_full_name, contents) in enumerate(_lists.items()):
                    if "|*n*|" in _list_full_name:
                        parts = _list_full_name.split("|*n*|")
                        _list_name = parts[0]
                        _alias = parts[1]
                    else:
                        _list_name = _list_full_name
                        _alias = None

                    if name in [_list_name, _alias]:
                        list_name = _list_name
                        alias_name = _alias
                        full_name = _list_full_name
                        sys_category = _sys_category
                        target_list = self.bot.user_data["UserData"][str(ctx.author.id)]["Lists"][_sys_category][_list_full_name]
                        break

            if not full_name or list_name == "placeholder":
                await ctx.send(embed=Embed(description="🔎❌ That list doesn't exist in your library."))
                return

        if sys_category == "Built-in" and mode in ["delete", "del"]:
            if list_name == "History":
                await ctx.send(embed=Embed(
                    description="❌ You cannot delete a built-in list.\n"
                                "You can clear any list using the mode `clear` or `c`.\n"
                                "If you want to disable history logging, use the mode `toggle`."))
            else:
                await ctx.send(embed=Embed(
                    description="❌ You cannot delete a built-in list.\n"
                                "You can clear any list using the mode `clear` or `c`."))

            return

        if name in ["Favorites", "fav"]:
            if mode and mode not in ["add", "a", "+", "remove", "r", "-", "clear", "c"]:
                await ctx.send(embed=Embed(description="❌ Invalid mode passed. Valid modes are `add/a/+`, `remove/r/-`, and `clear/c`."))
                return

            if not mode:
                await load_list(target_list)
                return

            elif mode in ["add", "a", "+"]:
                if code in target_list:
                    await ctx.send(embed=Embed(description="❌ That doujin is already in that list."))
                    return

                if len(target_list) >= 25: 
                    await ctx.send(embed=Embed(description="❌ You cannot add more than 25 doujins to a list."))
                    return

                try:
                    code = int(code)
                    code = str(code)
                except ValueError:
                    await ctx.send(embed=Embed(description="❌ You didn't type a proper ID. Come on, numbers!"))
                    return

                nhentai_api = NHentai()
                if code not in self.bot.doujin_cache:
                    doujin = await nhentai_api.get_doujin(code)
                else:
                    doujin = self.bot.doujin_cache[code]

                if not doujin:
                    await ctx.send(embed=Embed(description="🔎❌ I did not find a doujin with that ID."))
                    return

                self.bot.doujin_cache[code] = doujin

                if not lolicon_allowed and any([tag in restricted_tags for tag in doujin.tags]):
                    await ctx.send(content="⚠❌ This doujin contains lolicon/shotacon content and cannot be shown publically.")
                    return

                target_list.append(code)
                await ctx.send(embed=Embed(description=f"✅ Added `{code}` to `{list_name}`."))
                return

            elif mode in ["remove", "r", "-"]:
                if code not in target_list:
                    await ctx.send(embed=Embed(description="❌ That doujin is not in that list."))
                    return

                target_list.remove(code)
                await ctx.send(embed=Embed(description=f"✅ Removed `{code}` from `{list_name}`."))
                return

            elif mode in ["clear", "c"]:
                emb = Embed(
                    title="Clearing An Occupied List",
                    description=f"Are you sure you want to clear this list?\n"
                                f"\n"
                                f"**Name**: {list_name}\n"
                                f"{'**Alias**: '+alias_name+newline if alias_name else ''}"
                                f"**Number of doujins inside**: {len(target_list)-1}")
                conf = await self.bot.comp_ext.send_component_msg(ctx, embed=emb,
                    components=[
                        [Button(label="Continue", style=4, id="button1"),
                        Button(label="Cancel", style=1, id="button2")]])
                try:
                    interaction = await self.bot.wait_for("button_click", timeout=20, bypass_cooldown=True, 
                        check=lambda i: i.message.id==conf.id and i.user.id==ctx.author.id)
        
                except TimeoutError:
                    await self.bot.comp_ext.edit_component_msg(conf, embed=emb,
                        components=[
                            [Button(label="Continue", style=4, id="button1", disabled=True),
                            Button(label="Cancel", style=1, id="button2", disabled=True)]])
                        
                else:
                    await interaction.respond(type=6)
                    if interaction.component.id == "button1":
                        self.bot.user_data["UserData"][str(ctx.author.id)]["Lists"][sys_category][full_name] = ["0"]
                        await self.bot.comp_ext.edit_component_msg(
                            conf, embed=Embed(description=f"✅ Cleared/reset `{list_name}` (removed {len(target_list)-1} doujins)."), components=[])
                    elif interaction.component.id == "button2":
                        await self.bot.comp_ext.edit_component_msg(
                            conf, embed=Embed(description=f"❌ Operation cancelled."), components=[])
                return

        elif name in ["Read Later", "rl"]:
            if mode and mode not in ["add", "a", "+", "remove", "r", "-", "clear", "c"]:
                await ctx.send(embed=Embed(description="❌ Invalid mode passed. Valid modes are `add/a/+`, `remove/r/-`, and `clear/c`."))
                return
            
            if not mode:
                await load_list(target_list)
                return

            elif mode in ["add", "a", "+"]:
                if code in target_list:
                    await ctx.send(embed=Embed(description="❌ That doujin is already in that list."))
                    return

                if len(target_list) >= 25: 
                    await ctx.send(embed=Embed(description="❌ You cannot add more than 25 doujins to a list."))
                    return

                try:
                    code = int(code)
                    code = str(code)
                except ValueError:
                    await ctx.send(embed=Embed(description="❌ You didn't type a proper ID. Come on, numbers!"))
                    return

                nhentai_api = NHentai()
                if code not in self.bot.doujin_cache:
                    doujin = await nhentai_api.get_doujin(code)
                else:
                    doujin = self.bot.doujin_cache[code]

                if not doujin:
                    await ctx.send(embed=Embed(description="🔎❌ I did not find a doujin with that ID."))
                    return

                self.bot.doujin_cache[code] = doujin

                if not lolicon_allowed and any([tag in restricted_tags for tag in doujin.tags]):
                    await ctx.send(content="⚠❌ This doujin contains lolicon/shotacon content and cannot be shown publically.")
                    return

                target_list.append(code)
                await ctx.send(embed=Embed(description=f"✅ Added `{code}` to `{list_name}`."))
                return

            elif mode in ["remove", "r", "-"]:
                if code not in target_list:
                    await ctx.send(embed=Embed(description="❌ That doujin is not in that list."))
                    return

                target_list.remove(code)
                await ctx.send(embed=Embed(description=f"✅ Removed `{code}` from `{list_name}`."))
                return

            elif mode in ["clear", "c"]:
                emb = Embed(
                    title="Clearing An Occupied List",
                    description=f"Are you sure you want to clear this list?\n"
                                f"\n"
                                f"**Name**: {list_name}\n"
                                f"{'**Alias**: '+alias_name+newline if alias_name else ''}"
                                f"**Number of doujins inside**: {len(target_list)-1}")
                conf = await self.bot.comp_ext.send_component_msg(ctx, embed=emb,
                    components=[
                        [Button(label="Continue", style=4, id="button1"),
                        Button(label="Cancel", style=2, id="button2")]])
                try:
                    interaction = await self.bot.wait_for("button_click", timeout=20, bypass_cooldown=True, 
                        check=lambda i: i.message.id==conf.id and i.user.id==ctx.author.id)
        
                except TimeoutError:
                    await self.bot.comp_ext.edit_component_msg(conf, embed=emb,
                        components=[
                            [Button(label="Continue", style=4, id="button1", disabled=True),
                            Button(label="Cancel", style=2, id="button2", disabled=True)]])
                        
                else:
                    await interaction.respond(type=6)
                    if interaction.component.id == "button1":
                        self.bot.user_data["UserData"][str(ctx.author.id)]["Lists"][sys_category][full_name] = ["0"]
                        await self.bot.comp_ext.edit_component_msg(
                            conf, embed=Embed(description=f"✅ Cleared/reset `{list_name}` (removed {len(target_list)-1} doujins)."), components=[])
                    elif interaction.component.id == "button2":
                        await self.bot.comp_ext.edit_component_msg(
                            conf, embed=Embed(description=f"❌ Operation cancelled."), components=[])
                return

        elif name in ["Bookmarks", "bm"]:
            if mode and mode not in ["remove", "r", "-", "clear", "c"]:
                await ctx.send(embed=Embed(description="❌ Invalid mode passed. Valid modes are `remove/r/-` and `clear/c`."))
                return

            if not mode:
                await load_list(target_list)
                return

            elif mode in ["remove", "r", "-"]:
                if code not in target_list:
                    await ctx.send(embed=Embed(
                        description="❌ That doujin is not in that list.\n"
                                    "Note: In the case of bookmarks, use the format `code/-/bookmarked_page` for `code`."))
                    return

                target_list.pop(code)
                await ctx.send(embed=Embed(description=f"✅ Removed `{code}` from `{list_name}`."))
                return

            elif mode in ["clear", "c"]:
                emb = Embed(
                    title="Clearing An Occupied List",
                    description=f"Are you sure you want to clear this list?\n"
                                f"\n"
                                f"**Name**: {list_name}\n"
                                f"{'**Alias**: '+alias_name+newline if alias_name else ''}"
                                f"**Number of doujins inside**: {len(target_list)-1}")
                conf = await self.bot.comp_ext.send_component_msg(ctx, embed=emb,
                    components=[
                        [Button(label="Continue", style=4, id="button1"),
                        Button(label="Cancel", style=2, id="button2")]])
                try:
                    interaction = await self.bot.wait_for("button_click", timeout=20, bypass_cooldown=True, 
                        check=lambda i: i.message.id==conf.id and i.user.id==ctx.author.id)
        
                except TimeoutError:
                    await self.bot.comp_ext.edit_component_msg(conf, embed=emb,
                        components=[
                            [Button(label="Continue", style=4, id="button1", disabled=True),
                            Button(label="Cancel", style=2, id="button2", disabled=True)]])
                        
                else:
                    await interaction.respond(type=6)
                    if interaction.component.id == "button1":
                        self.bot.user_data["UserData"][str(ctx.author.id)]["Lists"][sys_category][full_name] = {"0": 0}
                        await self.bot.comp_ext.edit_component_msg(
                            conf, embed=Embed(description=f"✅ Cleared/reset `{list_name}` (removed {len(target_list)-1} doujins)."), components=[])
                    elif interaction.component.id == "button2":
                        await self.bot.comp_ext.edit_component_msg(
                            conf, embed=Embed(description=f"❌ Operation cancelled."), components=[])
                return

        elif name in ["History", "his"]:
            if mode and mode not in ["remove", "r", "-", "clear", "c", "toggle", "t"]:
                await ctx.send(embed=Embed(description="❌ Invalid mode passed. Valid modes are `remove/r/-`, `clear/c`, and `toggle/t`."))
                return
            
            if not mode:
                await load_list(target_list['list'])
                return

            elif mode in ["remove", "r", "-"]:
                if code not in target_list:
                    await ctx.send(embed=Embed(
                        description="❌ That doujin is not in that list.\n"
                                    "Note: In the case of bookmarks, use the format `code/-/bookmarked_page` for `code`."))
                    return

                target_list.remove(code)
                await ctx.send(embed=Embed(description=f"✅ Removed `{code}` from `{list_name}`."))
                return

            elif mode in ["clear", "c"]:
                emb = Embed(
                    title="Clearing An Occupied List",
                    description=f"Are you sure you want to clear this list?\n"
                                f"\n"
                                f"**Name**: {list_name}\n"
                                f"{'**Alias**: '+alias_name+newline if alias_name else ''}"
                                f"**Number of doujins inside**: {len(target_list)-1}")
                conf = await self.bot.comp_ext.send_component_msg(ctx, embed=emb,
                    components=[
                        [Button(label="Continue", style=4, id="button1"),
                        Button(label="Cancel", style=2, id="button2")]])
                try:
                    interaction = await self.bot.wait_for("button_click", timeout=20, bypass_cooldown=True, 
                        check=lambda i: i.message.id==conf.id and i.user.id==ctx.author.id)
        
                except TimeoutError:
                    await self.bot.comp_ext.edit_component_msg(conf, embed=emb,
                        components=[
                            [Button(label="Continue", style=4, id="button1", disabled=True),
                            Button(label="Cancel", style=2, id="button2", disabled=True)]])
                        
                else:
                    await interaction.respond(type=6)
                    if interaction.component.id == "button1":
                        self.bot.user_data["UserData"][str(ctx.author.id)]["Lists"][sys_category][full_name]["list"] = ["0"]
                        await self.bot.comp_ext.edit_component_msg(
                            conf, embed=Embed(description=f"✅ Cleared/reset `{list_name}` (removed {len(target_list)-1} doujins)."), components=[])
                    elif interaction.component.id == "button2":
                        await self.bot.comp_ext.edit_component_msg(
                            conf, embed=Embed(description=f"❌ Operation cancelled."), components=[])
                return
        
            elif mode in ["toggle", "t"]:
                target_list["enabled"] = not target_list["enabled"]
                await ctx.send(embed=Embed(description=f"✅ History is now {'`On`' if target_list['enabled'] else '`Off`'}."))
                return

        else:  # Queried list is custom
            if mode in ["add", "a", "+", "remove", "r", "-", "clear", "c", "delete", "del", "create", "cr", None]:
                if mode in ["create", "cr"]:
                    if len(self.bot.user_data["UserData"][str(ctx.author.id)]["Lists"]["Custom"]) > 25:
                        await ctx.send(embed=Embed(description="❌ You cannot create more than 25 custom lists."))
                        return
                    
                    input_aliases = name.split("//")
                    if len(input_aliases[0]) > 25 or \
                        (len(input_aliases)==2 and len(input_aliases[1]) > 25):
                        await ctx.send(embed=Embed(description="❌ Your list name or alias cannot exceed 25 characters long."))
                        return

                    if len(input_aliases) > 2:
                        await ctx.send(embed=Embed(description="❌ You can only give your list one alias."))
                        return

                    # Check for existing lists and aliases
                    for _sys_category, _lists in self.bot.user_data["UserData"][str(ctx.author.id)]["Lists"].items():
                        for ind, (_list_full_name, contents) in enumerate(_lists.items()):
                            if "|*n*|" in _list_full_name:
                                parts = _list_full_name.split("|*n*|")
                                _list_name = parts[0]
                                _alias = parts[1]
                            else:
                                _list_name = _list_full_name
                                _alias = None

                            if input_aliases[0] in [_list_name, _alias]:
                                await ctx.send(embed=Embed(description=f"❌ A list with the name or alias `{input_aliases[0]}` already exists."))
                                return
                            elif len(input_aliases) == 2 and input_aliases[1] in [_list_name, _alias]:
                                await ctx.send(embed=Embed(description=f"❌ A list with the name or alias `{input_aliases[1]}` already exists."))
                                return

                    sys_name = "|*n*|".join(input_aliases)

                    self.bot.user_data["UserData"][str(ctx.author.id)]["Lists"]["Custom"][sys_name] = ["0"]
                    await ctx.send(embed=Embed(description=f"✅ Created a new list named `{input_aliases[0]}`{' with the alias `'+input_aliases[1]+'`' if len(input_aliases)==2 else ''}."))
                
                    if code:
                        try:
                            code = int(code)
                            code = str(code)
                        except ValueError:
                            await ctx.send(embed=Embed(description="❌ You didn't type a proper ID. Come on, numbers!"))
                            return

                        nhentai_api = NHentai()
                        if code not in self.bot.doujin_cache:
                            doujin = await nhentai_api.get_doujin(code)
                        else:
                            doujin = self.bot.doujin_cache[code]

                        if not doujin:
                            await ctx.send(embed=Embed(description="🔎❌ I did not find a doujin with that ID."))
                            return

                        self.bot.doujin_cache[code] = doujin

                        if not lolicon_allowed and any([tag in restricted_tags for tag in doujin.tags]):
                            await ctx.send(content="⚠❌ This doujin contains lolicon/shotacon content and cannot be shown publically.")
                            return

                        self.bot.user_data["UserData"][str(ctx.author.id)]["Lists"]["Custom"][sys_name].append(code)
                        await ctx.send(embed=Embed(description=f"✅ Added `{code}` to `{input_aliases[0]}`."))
                
                    return

                elif mode in ["add", "a", "+"]:
                    if code in target_list:
                        await ctx.send(embed=Embed(description="❌ That doujin is already in that list."))
                        return

                    if len(target_list) >= 25: 
                        await ctx.send(embed=Embed(description="❌ You cannot add more than 25 doujins to a list."))
                        return

                    try:
                        code = int(code)
                        code = str(code)
                    except ValueError:
                        await ctx.send(embed=Embed(description="❌ You didn't type a proper ID. Come on, numbers!"))
                        return

                    edit = await ctx.send(embed=Embed(description="<a:nreader_loading:810936543401213953>"))
                    nhentai_api = NHentai()
                    if code not in self.bot.doujin_cache:
                        doujin = await nhentai_api.get_doujin(code)
                    else:
                        doujin = self.bot.doujin_cache[code]

                    if not doujin:
                        await edit.edit(embed=Embed(description="🔎❌ I did not find a doujin with that ID."))
                        return

                    self.bot.doujin_cache[code] = doujin

                    if not lolicon_allowed and any([tag in restricted_tags for tag in doujin.tags]):
                        await edit.edit(content="⚠❌ This doujin contains lolicon/shotacon content and cannot be shown publically.")
                        return

                    target_list.append(code)
                    await edit.edit(embed=Embed(description=f"✅ Added `{code}` to `{list_name}`."))
                    return

                elif mode in ["remove", "r", "-"]:
                    if code not in target_list:
                        await ctx.send(embed=Embed(description="❌ That doujin is not in that list."))
                        return

                    target_list.remove(code)
                    await edit.edit(embed=Embed(description=f"✅ Removed `{code}` from `{list_name}`."))
                    return

                elif mode in ["clear", "c"]:
                    emb = Embed(
                        title="Clearing An Occupied List",
                        description=f"Are you sure you want to clear this list?\n"
                                    f"\n"
                                    f"**Name**: {list_name}\n"
                                    f"{'**Alias**: '+alias_name+newline if alias_name else ''}"
                                    f"**Number of doujins inside**: {len(target_list)-1}")
                    conf = await self.bot.comp_ext.send_component_msg(ctx, embed=emb,
                        components=[
                            [Button(label="Continue", style=4, id="button1"),
                            Button(label="Cancel", style=2, id="button2")]])
                    try:
                        interaction = await self.bot.wait_for("button_click", timeout=20, bypass_cooldown=True, 
                            check=lambda i: i.message.id==conf.id and i.user.id==ctx.author.id)
        
                    except TimeoutError:
                        await self.bot.comp_ext.edit_component_msg(conf, embed=emb,
                            components=[
                                [Button(label="Continue", style=4, id="button1", disabled=True),
                                Button(label="Cancel", style=2, id="button2", disabled=True)]])
                        
                    else:
                        await interaction.respond(type=6)
                        if interaction.component.id == "button1":
                            self.bot.user_data["UserData"][str(ctx.author.id)]["Lists"][sys_category][full_name] = ["0"]
                            await self.bot.comp_ext.edit_component_msg(
                                conf, embed=Embed(description=f"✅ Cleared/reset `{list_name}` (removed {len(target_list)-1} doujins)."), components=[])
                        elif interaction.component.id == "button2":
                            await self.bot.comp_ext.edit_component_msg(
                                conf, embed=Embed(description=f"❌ Operation cancelled."), components=[])
                    return

                elif mode in ["delete", "del"]:
                    if not len(target_list)-1:
                        self.bot.user_data["UserData"][str(ctx.author.id)]["Lists"]["Custom"].pop(full_name)
                        await ctx.send(embed=Embed(description=f"✅ Deleted list `{list_name}` (empty list)."))

                    else:
                        emb = Embed(
                            title="Deleting An Occupied List",
                            description=f"Are you sure you want to delete this list?\n"
                                        f"\n"
                                        f"**Name**: {list_name}\n"
                                        f"{'**Alias**: '+alias_name+newline if alias_name else ''}"
                                        f"**Number of doujins inside**: {len(target_list)-1}")

                        conf = await self.bot.comp_ext.send_component_msg(ctx, embed=emb,
                            components=[
                                [Button(label="Continue", style=4, id="button1"),
                                Button(label="Cancel", style=2, id="button2")]])
        
                        try:
                            interaction = await self.bot.wait_for("button_click", timeout=20, bypass_cooldown=True, 
                                check=lambda i: i.message.id==conf.id and i.user.id==ctx.author.id)
        
                        except TimeoutError:
                            await self.bot.comp_ext.edit_component_msg(conf, embed=emb,
                                components=[
                                    [Button(label="Continue", style=4, id="button1", disabled=True),
                                    Button(label="Cancel", style=2, id="button2", disabled=True)]])
            
                            return
        
                        else:
                            await interaction.respond(type=6)
                            if interaction.component.id == "button1":
                                self.bot.user_data["UserData"][str(ctx.author.id)]["Lists"]["Custom"].pop(full_name)
                                emb.description = f"✅ Deleted list `{list_name}` (disbanded {len(target_list)-1} doujins)."
                                await self.bot.comp_ext.edit_component_msg(conf, embed=emb, components=[])
            
                            
                            elif interaction.component.id == "button2":
                                emb.description = f"❌ Operation cancelled."
                                await self.bot.comp_ext.edit_component_msg(conf, embed=emb, components=[])
                    return

                elif not mode:
                    await load_list(target_list)
                    return

            else:
                await ctx.send(embed=Embed(description="❌ Invalid mode passed. Valid modes are `add/a/+`, `remove/r/-`, `clear/c`, and `delete/del`."))
                return

    @command(
        name=f"{experimental_prefix}search_appendage",
        aliases=[f"{experimental_prefix}append"])
    @bot_has_permissions(
        send_messages=True,
        embed_links=True)
    async def search_appendage(self, ctx, *, appendage=""):
        if appendage and appendage != "clear_appendage":
            emb = embed=Embed(
                title = "Confirm Search Appendage Update",
                description = f"🔄 You are attempting to update your search appendage;\n"
                              f"```diff\n"
                              f"- [{self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['SearchAppendage']}]\n"
                              f"=====\n"
                              f"+ [{appendage}]"
                              f"```\n"
                              f"Brackets not included. Press `Update` to confirm.")
            emb.set_footer(text="Please note that this will be appended to searches in all cases, so if you have unexpected results, check back on this command.")

            conf = await self.bot.comp_ext.send_component_msg(ctx, embed=emb,
                components=[Button(label="Update", style=1, emoji="💾", id="button1")])
                
            try:
                interaction = await self.bot.wait_for('button_click', timeout=20, bypass_cooldown=True,
                    check=lambda i: i.message.id==conf.id and \
                        i.user.id==ctx.author.id and \
                        i.component.id=="button1")

            except TimeoutError:
                await self.bot.comp_ext.edit_component_msg(conf, embed=emb,
                    components=[Button(label="Update", style=1, emoji="💾", id="button1", disabled=True)])
                    
                return

            else:
                await interaction.respond(type=6)

                self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["SearchAppendage"] = appendage
                
                await self.bot.comp_ext.edit_component_msg(conf, embed=Embed(
                    title = "Search Appendage Updated",
                    description = f"✅ The following string will now be appended to all of your searches:\n"
                                  f"```{self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['SearchAppendage']}```\n"
                ).set_footer(text="Please note that this will be appended to searches in all cases, so if you have unexpected results, check back on this command."),
                components=[Button(label="Updated", style=3, emoji="💾", id="button1", disabled=True)])
        
                return

                
        elif appendage == "clear_appendage":
            if not self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["SearchAppendage"]:
                await ctx.send(embed=Embed(
                    title="Confirm Search Appendage Erase",
                    description="You don't have a search appendage set."))
                
                return

            emb = embed=Embed(
                title = "Confirm Search Appendage Erase",
                description = f"⚠ You are attempting to erase your search appendage;\n"
                              f"```diff\n"
                              f"- [{self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['SearchAppendage']}]\n"
                              f"```\n"
                              f"Brackets not included. Press `Update` to confirm.")
            
            emb.set_footer(text="Please note that this will be appended to searches in all cases, so if you have unexpected results, check back on this command.")
            
            conf = await self.bot.comp_ext.send_component_msg(ctx, embed=emb,
                components=[Button(label="Erase", style=4, emoji="💾", id="button1")])
                
            try:
                interaction = await self.bot.wait_for('button_click', timeout=20, bypass_cooldown=True,
                    check=lambda i: i.message.id==conf.id and \
                        i.user.id==ctx.author.id and \
                        i.component.id=="button1")

            except TimeoutError:
                await self.bot.comp_ext.edit_component_msg(conf, embed=emb,
                    components=[Button(label="Erase", style=4, emoji="💾", id="button1", disabled=True)])
                    
                return

            else:
                await interaction.respond(type=6)

                old = deepcopy(self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["SearchAppendage"])
                self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["SearchAppendage"] = ""
                
                await self.bot.comp_ext.edit_component_msg(conf, embed=Embed(
                    title = "Search Appendage Erased",
                    description = f"✅ Nothing will be added to your searches.\n"
                                  f"```diff\n"
                                  f"- [{old}]\n"
                                  f"```\n"
                ).set_footer(text="Please note that this will be appended to searches in all cases, so if you have unexpected results, check back on this command."),
                components=[Button(label="Erased", style=3, emoji="💾", id="button1", disabled=True)])
        

                return

        else:
            if self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["SearchAppendage"]:
                await ctx.send(embed=Embed(
                    title = "Current Search Appendage",
                    description = f"📝 The following string is what you told me to append to all of your searches:\n"
                                  f"```{self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['SearchAppendage']}```\n"
                ).set_footer(text="Please note that this will be appended to searches in all cases, so if you have unexpected results, check back on this command."))
            
            else:
                await ctx.send(embed=Embed(
                    title = "Current Search Appendage",
                    description = "ℹ Nothing is being added to your searches."
                ).set_footer(text="Please note that this will be appended to searches in all cases, so if you have unexpected results, check back on this command."))

    @command(
        name=f"{experimental_prefix}recall",
        aliases=[f"{experimental_prefix}rc"])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    @bot_has_guild_permissions(
        manage_messages=True, 
        manage_channels=True, 
        manage_roles=True)
    async def recall(self, ctx):
        if not ctx.guild:
            await ctx.send(embed=Embed(
                description=":x: These commands must be run in a server. Consider making a private one."))

            return

        lolicon_allowed = False
        try:
            if not ctx.guild or ctx.guild.id in self.bot.user_data["UserData"][str(ctx.guild.owner_id)]["Settings"]["UnrestrictedServers"]:
                lolicon_allowed = True
        except KeyError:
            pass

        if not ctx.channel.is_nsfw():
            await ctx.send("❌ This command cannot be used in a non-NSFW channel.")
            return
        
        recall_id = self.bot.user_data["UserData"][str(ctx.author.id)]["Recall"]
        if recall_id == "N/A":
            await ctx.send(embed=Embed(
                title="Unavailable",
                description="You don't have a doujin to recall."))
            return
            
        code, page = self.bot.user_data["UserData"][str(ctx.author.id)]["Recall"].split("*n*")
        
        edit = await ctx.send(embed=Embed(description=f"{self.bot.get_emoji(810936543401213953)} Recalling..."))

        nhentai_api = NHentai()
        if code not in self.bot.doujin_cache:
            doujin = await nhentai_api.get_doujin(code)
        else:
            doujin = self.bot.doujin_cache[code]
        
        if not doujin:
            await ctx.send(embed=Embed(
                description="🔎❌ Unfortunately, the doujin you were reading is no longer available."))
            
            self.bot.user_data["UserData"][str(ctx.author.id)]["Recall"] = "N/A"
            return

        else:
            self.bot.doujin_cache[code] = doujin
        
        if not lolicon_allowed and any([tag in restricted_tags for tag in doujin.tags]):
            await edit.edit(embed=Embed(
                description="⚠️⛔ You can't recall your doujin here. Did you think you could wormhole like that?"))

        session = ImagePageReader(self.bot, ctx, doujin.images, f"{doujin.id} [*n*] {doujin.title.pretty}", str(doujin.id), starting_page=int(page))
        response = await session.setup()
        if response:
            self.bot.user_data["UserData"][str(ctx.author.id)]["Recall"] = "N/A"
            
            await edit.edit(embed=Embed(description="<:nhentai:845298862184726538> Successfully recalled."))
            print(f"[] {ctx.author} ({ctx.author.id}) started reading `{doujin.id}`.")
            await session.start()
        
        else:
            await edit.edit(embed=Embed(description="❌ You didn't answer the recall in time. Run this command again."))
        
        return

    @command(
        name=f"{experimental_prefix}urban_dictionary",
        aliases=[
            f"{experimental_prefix}urban", 
            f"{experimental_prefix}ud"])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    async def urban_dictionary(self, ctx, *, word):
        edit = await self.bot.comp_ext.send_component_msg(ctx, embed=Embed(
            color=0x1d2439,
            description=f"{self.bot.get_emoji(813237675553062954)}"))

        udclient = AsyncUrbanClient()
        response = await udclient.get_definition(word)

        if not response:
            await self.bot.comp_ext.edit_component_msg(edit, embed=Embed(
                color=0x1d2439,
                description="🔎❌ I did not find anything. Maybe you typed something wrong?"))
            
            return
        else:
            print(f"[] {ctx.author} ({ctx.author.id}) looked up '{word}' using the built-in Urban Dictionary.")

        # Manual cleaning
        for res in response:
            # Remove redundant characters and escape markdown
            res.example = res.example.replace("\r", "") 
            res.example = res.example.strip("\n")
            res.example = res.example.replace("*", "\*")
            res.example = res.example.replace("_", "\_")
            res.example = res.example.replace("`", "\`")

            res.definition = res.definition.replace("\r", "") 
            res.definition = res.definition.strip("\n")
            res.definition = res.definition.replace("*", "\*")
            res.definition = res.definition.replace("_", "\_")
            res.definition = res.definition.replace("`", "\`")

            # Add bot markdown
            defhyperlinks = findall(r"""(\[([A-Za-z0-9_ "']+)\])""", res.definition)
            exahyperlinks = findall(r"""(\[([A-Za-z0-9_ "']+)\])""", res.example)
            for hl, hl_word in defhyperlinks: 
                res.definition = res.definition.replace(hl, f"**[{hl_word}](https://www.urbandictionary.com/define.php?term={hl_word.replace(' ', '%20')})**")
            for hl, hl_word in exahyperlinks: 
                res.example = res.example.replace(hl, f"**[{hl_word}](https://www.urbandictionary.com/define.php?term={hl_word.replace(' ', '%20')})**")
            
            res.example_lines = res.example.split("\n") 
            while "" in res.example_lines: res.example_lines.remove("")
            for ind, ex in enumerate(res.example_lines):
                res.example_lines[ind] = ex.strip(" ")


        current_def = 0
        examples_part = []
        for ind, example in enumerate(response[current_def].example_lines):
            examples_part.append(f"> *{example}*")

        await self.bot.comp_ext.edit_component_msg(edit, 
            embed=Embed(
                color=0x1d2439,
                title=response[current_def].word,
                description=f"{response[current_def].definition}\n"
                            f"\n"
                            f"{newline.join(examples_part)}\n"
                            f"{self.bot.get_emoji(274492025678856192)}{response[current_def].upvotes} "
                            f"{self.bot.get_emoji(274492025720537088)}{response[current_def].downvotes}"
            ).set_author(
                name="Urban Dictionary",
                url=f"https://www.urbandictionary.com/define.php?term={response[current_def].word.replace(' ', '%20')}",
                icon_url="https://cdn.discordapp.com/attachments/655456170391109663/867163805535961109/favicons.png"),
            
            components=[[
                Button(label="Previous", style=2 if current_def<=0 else 1, emoji="◀️", id="button1", disabled=True if len(response) <=1 else False),
                Button(label=f"[ {current_def+1}/{len(response)} ]", style=2, id="button0", disabled=True),
                Button(label="Next", style=2 if current_def>=len(response)-1 else 1, emoji="▶️", id="button2", disabled=True if len(response) <=1 else False)]]
        )

        while len(response) > 1:
            try:
                interaction = await self.bot.wait_for("button_click", timeout=60, 
                    check=lambda i: i.message.id==edit.id and i.user.id==ctx.author.id)

            except TimeoutError:
                examples_part = []
                for example in response[current_def].example_lines:
                    examples_part.append(f"> *{example}*")

                await self.bot.comp_ext.edit_component_msg(edit, 
                    embed=Embed(
                        color=0x1d2439,
                        title=response[current_def].word,
                        description=f"{response[current_def].definition}\n"
                                    f"\n"
                                    f"{newline.join(examples_part)}\n"
                                    f"{self.bot.get_emoji(274492025678856192)}{response[current_def].upvotes} "
                                    f"{self.bot.get_emoji(274492025720537088)}{response[current_def].downvotes}"
                    ).set_author(
                        name="Urban Dictionary",
                        url=f"https://www.urbandictionary.com/define.php?term={response[current_def].word.replace(' ', '%20')}",
                        icon_url="https://cdn.discordapp.com/attachments/655456170391109663/867163805535961109/favicons.png"),
            
                    components=[[
                        Button(label="Timeout", style=2, emoji="◀️", id="button1", disabled=True),
                        Button(label=f"[ {current_def+1}/{len(response)} ]", style=2, id="button0", disabled=True),
                        Button(label="Timeout", style=2, emoji="▶️", id="button2", disabled=True)]]
                )
            else:
                await interaction.respond(type=6)

                if interaction.component.id == "button1":
                    if current_def == 0:
                        current_def = len(response)-1
                    else:
                        current_def = current_def - 1

                elif interaction.component.id == "button2":
                    if current_def == len(response)-1:
                        current_def = 0
                    else:
                        current_def = current_def + 1

                examples_part = []
                for example in response[current_def].example_lines:
                    examples_part.append(f"> *{example}*")

                await self.bot.comp_ext.edit_component_msg(edit, 
                    embed=Embed(
                        color=0x1d2439,
                        title=response[current_def].word,
                        description=f"{response[current_def].definition}\n"
                                    f"\n"
                                    f"{newline.join(examples_part)}\n"
                                    f"{self.bot.get_emoji(274492025678856192)}{response[current_def].upvotes} "
                                    f"{self.bot.get_emoji(274492025720537088)}{response[current_def].downvotes}"
                    ).set_author(
                        name="Urban Dictionary",
                        url=f"https://www.urbandictionary.com/define.php?term={response[current_def].word.replace(' ', '%20')}",
                        icon_url="https://cdn.discordapp.com/attachments/655456170391109663/867163805535961109/favicons.png"),
            
                    components=[[
                        Button(label="Previous", style=2 if current_def<=0 else 1, emoji="◀️", id="button1", disabled=False),
                        Button(label=f"[ {current_def+1}/{len(response)} ]", style=2, id="button0", disabled=True),
                        Button(label="Next", style=2 if current_def>=len(response)-1 else 1, emoji="▶️", id="button2", disabled=False)]]
                )

                continue

    @whitelist.before_invoke
    @search_appendage.before_invoke
    async def placeholder_remove(self, ctx):
        if ctx.command.name == "whitelist":
            if 0 in self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['UnrestrictedServers']:
                self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['UnrestrictedServers'].remove(0)
        
        if ctx.command.name == "search_appendage":
            if self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['SearchAppendage'] == " ":
                self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['SearchAppendage'] = ""
                return

    @whitelist.after_invoke
    @search_appendage.after_invoke
    async def placeholder_add(self, ctx):
        if ctx.command.name == "whitelist":
            if 0 not in self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['UnrestrictedServers']:
                self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['UnrestrictedServers'].append(0)
        
        if ctx.command.name == "search_appendage":
            if not self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['SearchAppendage']:
                self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['SearchAppendage'] = " "
                return


def setup(bot):
    bot.add_cog(Commands(bot))
