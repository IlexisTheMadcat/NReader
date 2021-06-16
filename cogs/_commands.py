from re import search
from asyncio import sleep, TimeoutError
from textwrap import shorten
from copy import deepcopy
from contextlib import suppress

from discord import Forbidden, NotFound
from discord.ext.commands import (
    Cog, bot_has_permissions, 
    bot_has_guild_permissions, command)
from discord_components import Button
from NHentai.nhentai_async import NHentaiAsync as NHentai, Doujin, DoujinThumbnail

from utils.classes import (
    Embed, BotInteractionCooldown)
from cogs._classes import (
    ImagePageReader,
    SearchResultsBrowser)
from utils.utils import language_to_flag, restricted_tags


class Commands(Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @command(name="Ttest")
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
            await self.bot.comp_ext.edit_component_msg(conf, embed=Embed(description="Button failed (3/3)."),
                components=[Button(label="Failed.", style=4, emoji="⛔", id="button1", disabled=True)])
        
        else:
            await self.bot.comp_ext.edit_component_msg(conf, embed=Embed(description="Button complete. (3/3)."),
                components=[Button(label="Complete.", style=3, emoji="✅", id="button1")])
            
            await interaction.respond(type=6)
            
        
        print(f"{ctx.author} ({ctx.author.id}) tested.")
       
    @command(aliases=["Tcode"])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    @bot_has_guild_permissions(
        manage_messages=True, 
        manage_channels=True, 
        manage_roles=True)
    async def Tdoujin_info(self, ctx, code="random", interface="new"):
        lolicon_allowed = False
        try:
            if ctx.guild.id in self.bot.user_data["UserData"][str(ctx.guild.owner_id)]["Settings"]["UnrestrictedServers"]:
                lolicon_allowed = True
        except KeyError:
            pass
            
        if not ctx.channel.is_nsfw():
            await ctx.send(embed=Embed(
                description=":x: This command cannot be used in a non-NSFW channel."))

            return
        
        try:
            if code.lower() not in ["random", "r"]:
                code = int(code)
                code = str(code)
        except ValueError:
            await ctx.send(embed=Embed(
                description=":x: You didn't type a proper ID. Hint: It has to be a number!"))

            return
        
        nhentai_api = NHentai()
        edit = await self.bot.comp_ext.send_component_msg(ctx, embed=Embed(
            description="<a:nreader_loading:810936543401213953>"))

        if code.lower() not in ["random", "r"]:
            if code not in self.bot.doujin_cache:
                doujin = await nhentai_api.get_doujin(code)
            else:
                doujin = self.bot.doujin_cache[code]

            if not doujin:
                await edit.edit(embed=Embed(
                    description=":mag_right::x: I did not find a doujin with that ID."))

                return
            
            else:
                self.bot.doujin_cache[code] = doujin
            
            if not lolicon_allowed and any([tag in restricted_tags for tag in doujin.tags]):
                await edit.edit(embed=Embed(
                    description=":warning::no_entry_sign: This doujin contains lolicon/shotacon content and cannot be displayed publically."))

                if not self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["NotificationsDue"]["LoliconViewingTip"]:
                    with suppress(Forbidden):
                        await ctx.author.send(self.bot.config["lolicon_viewing_tip"])
                    
                    self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["NotificationsDue"]["LoliconViewingTip"] = True

                return

        else:
            while True:
                doujin = await nhentai_api.get_random()
                self.bot.doujin_cache[doujin.id] = doujin
                if not lolicon_allowed and any([tag in restricted_tags for tag in doujin.tags]):
                    await edit.edit(embed=Embed(
                        description="<a:nreader_loading:810936543401213953> Retrying..."))
                        
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
        else:
            emb = Embed()
            emb.add_field(
                inline=False,
                name="Secondary Title",
                value=f"`{doujin.secondary_title if doujin.secondary_title else 'Not provided'}`"
            ).add_field(
                inline=False,
                name="Doujin ID ー Pages",
                value=f"`{doujin.id} ー {len(doujin.images)} pages`"
            ).add_field(
                inline=False,
                name="Language(s)",
                value=f"{language_to_flag(doujin.languages)} `{', '.join(doujin.languages) if doujin.languages else 'Not provided'}`"
            ).add_field(
                inline=False,
                name="Artist(s)",
                value=f"`{', '.join(doujin.artists) if doujin.artists else 'Not provided'}`"
            ).add_field(
                inline=False,
                name="Character(s)",
                value=f"`{', '.join(doujin.characters) if doujin.characters else 'Original'}`"
            ).add_field(
                inline=False,
                name="Parody Of",
                value=f"`{', '.join(doujin.parodies) if doujin.parodies else 'Original'}`"
            ).add_field(
                inline=False,
                name="Tags",
                value=f"```{', '.join(doujin.tags) if doujin.tags != [] else 'None provided'}```"
            )

        emb.set_author(
            name=f"{shorten(doujin.title, width=120, placeholder='...')}",
            url=f"https://nhentai.net/g/{doujin.id}/",
            icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
        emb.set_thumbnail(
            url=doujin.images[0])
        emb.set_footer(
            text="Would you like to read this doujin on Discord?")
        
        print(f"[] {ctx.author} ({ctx.author.id}) looked up `{doujin.id}`.")

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
                emb.set_footer(text="Provided by NHentai-API")
                emb.set_thumbnail(
                    url=doujin.images[0])
                emb.set_image(
                    url=Embed.Empty)
                
                with suppress(NotFound):
                    await self.bot.comp_ext.edit_component_msg(edit, embed=emb, 
                        components=[
                            [Button(label="Timeout", style=2, emoji=self.bot.get_emoji(853684136379416616), id="button1", disabled=True),
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
                    
                    emb.set_footer(text="Provided by NHentai-API")
                    emb.set_thumbnail(
                        url=doujin.images[0])
                    emb.set_image(
                        url=Embed.Empty)
                    await self.bot.comp_ext.edit_component_msg(edit, content="", embed=emb,
                        components=[
                            [Button(label="Opened", style=1, emoji=self.bot.get_emoji(853684136379416616), id="button1", disabled=True),
                            Button(label="Expand Thumbnail", style=2, emoji=self.bot.get_emoji(853684136433942560), id="button2", disabled=True)]
                        ])

                    session = ImagePageReader(self.bot, ctx, doujin.images, f"{doujin.id} [*n*] {doujin.title}", str(doujin.id))
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
                    
                    await self.bot.comp_ext.edit_component_msg(edit, content="", embed=emb,
                        components=[
                            [Button(label="Read", style=1, emoji=self.bot.get_emoji(853684136379416616), id="button1"),
                            Button(label=f"{word} Thumbnail", style=2, emoji=self.bot.get_emoji(853684136433942560), id="button2")]
                        ])

                    continue
    
    @command(aliases=["Tsearch"])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    @bot_has_guild_permissions(
        manage_messages=True, 
        manage_channels=True, 
        manage_roles=True)
    async def Tsearch_doujins(self, ctx, *, query: str = ""):
        lolicon_allowed = False
        try:
            if ctx.guild.id in self.bot.user_data["UserData"][str(ctx.guild.owner_id)]["Settings"]["UnrestrictedServers"]:
                lolicon_allowed = True
        except KeyError:
            pass
        
        if ctx.guild and not ctx.channel.is_nsfw():
            await ctx.send(":x: This command cannot be used in a non-NSFW channel.")
            return
        
        conf = await self.bot.comp_ext.send_component_msg(ctx, embed=Embed(
            description="<a:nreader_loading:810936543401213953>"))
    
        nhentai_api = NHentai()

        if str(ctx.author.id) in self.bot.user_data["UserData"] and \
            "Settings" in self.bot.user_data["UserData"][str(ctx.author.id)] and \
            "SearchAppendage" in self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"] and \
            self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["SearchAppendage"] != " ":
            appendage = self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["SearchAppendage"]
        else:
            appendage = ""
        
        page_raw = search(r"#[0-9]+", query)
        if page_raw: 
            page = int(page_raw.group().strip("#"))
            query = query.replace(page_raw.group(), '').strip(' ')
        else: 
            page = 1

        if not query and not appendage:
            await conf.edit(content="", embed=Embed(
                title="❌ Search is too broad. Say something.",
                description="You need to tell me what to search, or update your search appendage (See `search_appendage` in `n!help`)."))
            
            return

        results = await nhentai_api.search(query=query+f"{' -lolicon -shotacon' if ctx.guild and not lolicon_allowed else ''} {appendage}", sort='popular', page=page)

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
                description = f"{newline+'`*️⃣` This may be the cause of your search appendage. See `search_appendage` in `n!help`.' if appendage else ''}"
                              f'{newline+"`*️⃣` You have added a page number to your search. Please check that your page is within the total page count (check by searching without a page)." if page_raw else ""}'))
            return
        
        message_part = []
        doujins = []
        for ind, dj in enumerate(results.doujins):
            if dj.id in self.bot.doujin_cache:
                dj = self.bot.doujin_cache[dj.id]
                dj.lang = dj.languages
            
            doujins.append(dj)
            
            message_part.append(
                f"__`{str(dj.id).ljust(7)}`__ | "
                f"{language_to_flag(dj.lang)} | "
                f"{shorten(dj.title, width=50, placeholder='...')}")

        emb = Embed(
            description=f"Showing page {page}/{results.total_pages}"
                        f"{'; illegal results are hidden:' if ctx.guild and not lolicon_allowed else ':'}"
                        f"\n"+('\n'.join(message_part)))
        emb.set_author(
            name="NHentai Search Results",
            url="https://nhentai.net/",
            icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
        emb.set_footer(text="Provided by NHentai-API")
        
        await self.bot.comp_ext.edit_component_msg(conf, embed=emb,
            components=[Button(label="Load", style=1, emoji="🔄", id="button1")])
        
        print(f"[] {ctx.author} ({ctx.author.id}) searched for [{query if query else ''}{' ' if query and appendage else ''}{appendage if appendage else ''}].")

        try:
            interaction = await self.bot.wait_for("button_click", timeout=20, bypass_cooldown=True, 
                check=lambda i: i.message.id==conf.id and \
                i.user.id==ctx.author.id and \
                i.component.id=="button1")
        
        except TimeoutError:
            with suppress(Forbidden):
                await conf.clear_reactions()

            await self.bot.comp_ext.edit_component_msg(conf, embed=emb,
                components=[Button(label="Timeout", style=2, emoji="🔄", id="button1", disabled=True)])
            
            return
        
        else:
            await interaction.respond(type=6)
        
        # Request each doujin to simplify results
        # Edits message every 5 retrievals to show progress
        if any([isinstance(dj, DoujinThumbnail) for dj in doujins]):
            emb.set_author(
                name="NHentai Search Results",
                url="https://nhentai.net/",
                icon_url="https://cdn.discordapp.com/emojis/810936543401213953.gif?v=1")
            emb.set_footer(
                text=f"Loading... [{' '*len(results.doujins)}]")
            
            await self.bot.comp_ext.edit_component_msg(conf, embed=emb,
                components=[Button(label="Loading...", style=2, emoji=self.bot.get_emoji(810936543401213953), id="button1", disabled=True)])
    
            message_part = []
            doujins2 = []
            for ind, dj in enumerate(doujins):
                if dj.id in self.bot.doujin_cache:
                    dj = self.bot.doujin_cache[dj.id]
                    dj.lang = dj.languages
                else:
                    dj = await nhentai_api.get_doujin(dj.id)
                    self.bot.doujin_cache[dj.id] = dj

                    dj.lang = dj.languages
                    results.doujins[ind] = dj
                
                doujins2.append(dj)
                
                if (ind%5 == 0) and (ind != 0):
                    await sleep(1)

                    message_part2 = []
                    for ind2, dj2 in enumerate(results.doujins):
                        message_part2.append(
                            f"__`{str(dj2.id).ljust(7)}`__ | "
                            f"{language_to_flag(dj2.lang)} | "
                            f"{shorten(dj2.title, width=50, placeholder='...')}")
                        
                    emb2 = Embed(
                        description=f"Showing page {page}/{results.total_pages}"
                                    f"{'; illegal results are hidden:' if ctx.guild and not lolicon_allowed else ':'}"
                                    f"\n"+('\n'.join(message_part2)))
                    emb2.set_author(
                        name="NHentai Search Results",
                        url="https://nhentai.net/",
                        icon_url="https://cdn.discordapp.com/emojis/810936543401213953.gif?v=1")
                    emb2.set_footer(
                        text=f"Loading... [{'|'*ind}{' '*(len(results.doujins)-ind)}]")
                    
                    await conf.edit(embed=emb2)
                
                message_part.append(
                    f"__`{str(dj.id).ljust(7)}`__ | "
                    f"{language_to_flag(dj.lang)} | "
                    f"{shorten(dj.title, width=50, placeholder='...')}")
        
            doujins = doujins2

        emb = Embed(
            description=f"Showing page {page}/{results.total_pages}"
                        f"{'; illegal results are hidden:' if ctx.guild and not lolicon_allowed else ':'}"
                        f"\n"+('\n'.join(message_part)))
        emb.set_author(
            name="NHentai Search Results",
            url="https://nhentai.net/",
            icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
        emb.set_footer(text="Provided by NHentai-API")
        
        await self.bot.comp_ext.edit_component_msg(conf, embed=emb,
            components=[Button(label="Start Interactive", style=1, emoji="⌨", id="button1")])
        
        try:
            interaction = await self.bot.wait_for('button_click', timeout=20, bypass_cooldown=True,
                check=lambda i: i.message.id==conf.id and \
                    i.user.id==ctx.author.id and \
                    i.component.id=="button1")
        except TimeoutError:
            await self.bot.comp_ext.edit_component_msg(conf, embed=emb,
                components=[Button(label="Timeout", style=2, emoji="⌨", id="button1", disabled=True)])
            
            return

        else:
            await interaction.respond(type=6)

            await self.bot.comp_ext.edit_component_msg(conf, embed=emb, components=[])
            
            interactive = SearchResultsBrowser(self.bot, ctx, doujins, msg=conf, lolicon_allowed=lolicon_allowed)
            await interactive.start(ctx)
    
    @command(aliases=["Tpop"])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    @bot_has_guild_permissions(
        manage_messages=True, 
        manage_channels=True, 
        manage_roles=True)
    async def Tpopular(self, ctx):
        lolicon_allowed = False
        try:
            if ctx.guild.id in self.bot.user_data["UserData"][str(ctx.guild.owner_id)]["Settings"]["UnrestrictedServers"]:
                lolicon_allowed = True
        except KeyError:
            pass
        
        if not ctx.channel.is_nsfw():
            await ctx.send(embed=Embed(
                description=":x: This command cannot be used in a non-NSFW channel."))

            return
        
        conf = await ctx.send(embed=Embed(
            description="<a:nreader_loading:810936543401213953> Loading popular results..."))

        nhentai_api = NHentai()
        results = await nhentai_api.get_popular_now()

        message_part = []
        doujins = []
        for ind, dj in enumerate(results.doujins):
            if dj.id not in self.bot.doujin_cache:
                dj = await nhentai_api.get_doujin(dj.id)
                self.bot.doujin_cache[dj.id] = dj
            else:
                dj = self.bot.doujin_cache[dj.id]
            
            doujins.append(dj)
            
            if ("lolicon" in dj.tags or "shotacon" in dj.tags) and ctx.guild and not lolicon_allowed:
                message_part.append("__`       `__ | ⚠🚫 | Not available in this server.")
            else:
                message_part.append(
                    f"__`{str(dj.id).ljust(7)}`__ | "
                    f"{language_to_flag(dj.languages)} | "
                    f"{shorten(dj.title, width=50, placeholder='...')}")

        emb = Embed(
            title=f"<:npopular:853883174455214102> **Popular Now**",
            description=f"\n"+('\n'.join(message_part)))
        emb.set_author(
            name="NHentai Search Results",
            url="https://nhentai.net/",
            icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
        emb.set_footer(text="Provided by NHentai-API")
        
        await self.bot.comp_ext.edit_component_msg(conf, embed=emb,
            components=[Button(label="Start Interactive", style=1, emoji="⌨", id="button1")])
        
        try:
            interaction = await self.bot.wait_for('button_click', timeout=20, bypass_cooldown=True,
                check=lambda i: i.message.id==conf.id and \
                    i.user.id==ctx.author.id and \
                    i.component.id=="button1")
        except TimeoutError:
            await self.bot.comp_ext.edit_component_msg(conf, embed=emb,
                components=[Button(label="Timeout", style=2, emoji="⌨", id="button1", disabled=True)])
            
            return

        else:
            await interaction.respond(type=6)

            await self.bot.comp_ext.edit_component_msg(conf, embed=emb, components=[])

            interactive = SearchResultsBrowser(self.bot, ctx, doujins, msg=conf, name=f"<:npopular:853883174455214102> **Popular Now**", lolicon_allowed=lolicon_allowed)
            await interactive.start(ctx)
    
    @command(aliases=["Tfav"])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    async def Tfavorites(self, ctx, mode:str=None, code=None):
        lolicon_allowed = False
        try:
            if not ctx.guild or ctx.guild.id in self.bot.user_data["UserData"][str(ctx.guild.owner_id)]["Settings"]["UnrestrictedServers"]:
                lolicon_allowed = True
        except KeyError:
            pass
        
        if ctx.guild and not ctx.channel.is_nsfw():
            await ctx.send(":x: This command cannot be used in a non-NSFW channel.")
            return
        
        if not mode:
            nhentai_api = NHentai()
            edit = await ctx.send(embed=Embed(
                description=f"Loading..."
            ).set_author(
                name="NHentai Favorites",
                url=f"https://nhentai.net/",
                icon_url="https://cdn.discordapp.com/emojis/810936543401213953.gif?v=1"
            ).set_footer(
                text=f"[{' '*len(self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Doujins'])}]"
            ))

            message_part = list()
            remove_queue = list()  # It is very rare that a doujin would get deleted from NHentai

            is_loading = False
            for code in self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Doujins']:
                if str(code) not in self.bot.doujin_cache:
                    is_loading = True
                    break
            
            doujins = []
            for ind, code in enumerate(self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Doujins']):
                if str(code) not in self.bot.doujin_cache:
                    doujin = await nhentai_api.get_doujin(code)
                else:
                    doujin = self.bot.doujin_cache[str(code)]
                
                if not doujin:
                    remove_queue.append(code)
                    continue
                else:
                    self.bot.doujin_cache[str(code)] = doujin

                    if any([tag in restricted_tags for tag in doujin.tags]): is_lolicon = True
                    else: is_lolicon = False
                    
                    if is_lolicon and not lolicon_allowed:
                        pass
                    else:
                        message_part.append(
                            f"__`{str(doujin.id).ljust(7)}`__ | "
                            f"{language_to_flag(doujin.languages)} | "
                            f"{shorten(doujin.title, width=50, placeholder='...')}")
                        
                        doujins.append(doujin)
                        
                    if ind%5 == 0 and ind!=0 and is_loading:
                        await edit.edit(embed=Embed(
                            description=f"Loading..."
                        ).set_author(
                            name="NHentai Favorites",
                            url=f"https://nhentai.net/",
                            icon_url="https://cdn.discordapp.com/emojis/810936543401213953.gif?v=1"
                        ).set_footer(
                            text=f"[{'|'*ind}{' '*(len(self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Doujins'])-ind)}]"
                        ))

                        await sleep(0.2)
                    
                    continue
            
            [self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Doujins'].pop(code) for code in remove_queue]
            
            emb = Embed(
                title=f"⭐ Favorites",
                description=f"\n"+('\n'.join(message_part)))
            emb.set_author(
                name="NHentai Search Results",
                url="https://nhentai.net/",
                icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
            emb.set_footer(text="Provided by MechHub")
            
            if self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Doujins']:
                await self.bot.comp_ext.edit_component_msg(edit, embed=emb,
                    components=[Button(label="Start Interactive", style=1, emoji="⌨", id="button1")])
                
                try:
                    interaction = await self.bot.wait_for('button_click', timeout=20, bypass_cooldown=True,
                        check=lambda i: i.message.id==edit.id and \
                            i.user.id==ctx.author.id and \
                            i.component.id=="button1")
                except TimeoutError:
                    await self.bot.comp_ext.edit_component_msg(edit, embed=emb,
                        components=[Button(label="Timeout", style=2, emoji="⌨", id="button1", disabled=True)])
                    
                    return

                else:
                    await interaction.respond(type=6)

                    await self.bot.comp_ext.edit_component_msg(edit, embed=emb, components=[])

                    interactive = SearchResultsBrowser(self.bot, ctx, doujins, msg=edit, name=f"⭐ Favorites", lolicon_allowed=lolicon_allowed)
                    await interactive.start(ctx)

                    return
            
            else:
                emb.description = "You have no favorites."

            await edit.edit(embed=emb)
        
        elif mode:
            if mode.lower() in ["add", "a", "+"]:
                try:
                    code = int(code)
                except ValueError:
                    await ctx.send(":x: You didn't type a proper ID. Hint: It has to be a number!")
                    return

                nhentai_api = NHentai()
                edit = await ctx.send("<a:nreader_loading:810936543401213953>")

                if code not in self.bot.doujin_cache:
                    doujin = await nhentai_api.get_doujin(code)
                else:
                    doujin = self.bot.doujin_cache[code]

                if not doujin:
                    await edit.edit(content=":mag_right::x: I did not find a doujin with that ID.")
                    return
                else:
                    self.bot.doujin_cache[code] = doujin

                    if not lolicon_allowed and any([tag in restricted_tags for tag in doujin.tags]):
                        await edit.edit(content=":warning::no_entry_sign: This doujin contains lolicon/shotacon content and cannot be shown publically.")
                        return
                    
                    if len(self.bot.user_data["UserData"][str(ctx.author.id)]["nFavorites"]["Doujins"]) >= 25:
                        emb = Embed(
                            description=f":x: Your favorites list is full. You can only hold 25."
                        ).set_author(
                            name="NHentai Favorites",
                            url=f"https://nhentai.net/",
                            icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
                        
                        await edit.edit(content="", embed=emb)
                        return
                    
                    if doujin.id not in self.bot.user_data["UserData"][str(ctx.author.id)]["nFavorites"]["Doujins"]:
                        self.bot.user_data["UserData"][str(ctx.author.id)]["nFavorites"]["Doujins"].append(doujin.id)
                        
                        emb = Embed(
                            description=f":white_check_mark: Added `{code}` to your favorites list."
                        ).set_author(
                            name="NHentai Favorites",
                            url=f"https://nhentai.net/",
                            icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
                        await edit.edit(content="", embed=emb)
                        return
                    
                    else:
                        emb = Embed(
                            description=f":x: `{code}` is already in your favorites list."
                        ).set_author(
                            name="NHentai Favorites",
                            url=f"https://nhentai.net/",
                            icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
                        await edit.edit(content="", embed=emb)
            
            elif mode.lower() in ["remove", "r", "-"]:
                try:
                    code = int(code)
                except ValueError:
                    await ctx.send(":x: You didn't type a proper ID. Hint: It has to be a number!")
                    return
                
                self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Doujins'].remove(0)  # Remove placeholder value

                if code in self.bot.user_data["UserData"][str(ctx.author.id)]["nFavorites"]["Doujins"]:
                    self.bot.user_data["UserData"][str(ctx.author.id)]["nFavorites"]["Doujins"].remove(code)
                    
                    emb = Embed(
                        description=f":white_check_mark: Removed `{code}` from your favorites list!"
                        ).set_author(
                        name="NHentai Favorites",
                        url=f"https://nhentai.net/",
                        icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
                    await ctx.send(embed=emb)
                
                else:
                    emb = Embed(
                        description=f":x: `{code}` is not in your favorites list."
                        ).set_author(
                        name="NHentai Favorites",
                        url=f"https://nhentai.net/",
                        icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
                    await ctx.send(embed=emb)
                
            else:
                await ctx.send("You didn't specify a mode. Valid modes are `add/a/+` and `remove/r/-`.")

    @command(aliases=["Tbm"])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    async def Tbookmarks(self, ctx):
        lolicon_allowed = False
        try:
            if not ctx.guild or ctx.guild.id in self.bot.user_data["UserData"][str(ctx.guild.owner_id)]["Settings"]["UnrestrictedServers"]:
                lolicon_allowed = True
        except KeyError:
            pass
        
        if ctx.guild and not ctx.channel.is_nsfw():
            await ctx.send(":x: This command cannot be used in a non-NSFW channel.")
            return

        nhentai_api = NHentai()
        edit = await ctx.send(embed=Embed(
                description=f"Loading..."
            ).set_author(
                name="NHentai Bookmarks",
                url=f"https://nhentai.net/",
                icon_url="https://cdn.discordapp.com/emojis/810936543401213953.gif?v=1"
            ).set_footer(
                text=f"[{' '*len(self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Bookmarks'])}]"
        ))
        
        message_part = list()
        remove_queue = list()  # It is very rare that a doujin would get deleted from NHentai
        
        doujins = []
        for code, page in self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Bookmarks'].items():
            if str(code) not in self.bot.doujin_cache:
                doujin = await nhentai_api.get_doujin(code)
            else:
                doujin = self.bot.doujin_cache[str(code)]

            if not doujin:
                remove_queue.append(code)
                continue
            else:
                self.bot.doujin_cache[str(code)] = doujin

                if any([tag in restricted_tags for tag in doujin.tags]): is_lolicon = True
                else: is_lolicon = False
                
                if is_lolicon and not lolicon_allowed:
                    pass
                else:
                    message_part.append(
                        f"__`{str(code).ljust(7)}`__ | " \
                        f"{language_to_flag(doujin.languages)} | " \
                        f"{page+1}/{len(doujin.images)} ー " \
                        f"{shorten(doujin.title, width=50, placeholder='...')} ")
                    
                    doujins.append(doujin)

        [self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Bookmarks'].pop(code) for code in remove_queue]

        emb = Embed(
            title=f"🔖 Bookmarks")
        emb.set_author(
            name="NHentai Search Results",
            url="https://nhentai.net/",
            icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
        emb.set_footer(text="Provided by MechHub")

        if self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Bookmarks']:
            emb.description = "\n".join(message_part)
            
            await self.bot.comp_ext.edit_component_msg(edit, embed=emb,
                components=[Button(label="Start Interactive", style=1, emoji="⌨", id="button1")])
            
            try:
                interaction = await self.bot.wait_for('button_click', timeout=20, bypass_cooldown=True,
                    check=lambda i: i.message.id==edit.id and \
                        i.user.id==ctx.author.id and \
                        i.component.id=="button1")
            except TimeoutError:
                await self.bot.comp_ext.edit_component_msg(edit, embed=emb,
                    components=[Button(label="Timeout", style=2, emoji="⌨", id="button1", disabled=True)])
                
                return

            else:
                await interaction.respond(type=6)

                await self.bot.comp_ext.edit_component_msg(edit, embed=emb, components=[])

                interactive = SearchResultsBrowser(self.bot, ctx, doujins, msg=edit, name=f"🔖 Bookmarks", lolicon_allowed=lolicon_allowed)
                await interactive.start(ctx)

                return
        else:
            emb.description = "You have no bookmarks."
        
        await edit.edit(content="", embed=emb)
    
    @command()
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    async def Twhitelist(self, ctx, mode=None):
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
                title="Server whitelisting",
                description="⚠ You're about to enable restricted features for this entire server. "
                            "Using these features around others may have an impact on their judgements on you.\n"
                            "The bot developer is not responsible for loss of friendships in this case, nor shall the developer be accused of distributing this content under their behalf. It is solely on **you**.\n"
                            "Remember, admins can see what you read in your server. "
                            "If you want to read in private, remove admins or create a new server.")
            
            emb.set_footer(text="If you still want to continue, press the 'I accept' button.")
            
            conf = await self.bot.comp_ext.send_component_msg(ctx, embed=emb,
                components=[
                    [Button(label="I accept", style=3, id="button1"),
                     Button(label="I decline", style=4, id="button2")]])
            
            try:
                interaction = await self.bot.wait_for('button_click', timeout=20, bypass_cooldown=True,
                    check=lambda i: \
                        i.message.id==conf.id and \
                        i.user.id==ctx.author.id)
            
            except TimeoutError:
                await self.bot.comp_ext.edit_component_msg(conf, embed=emb,
                    components=[
                        [Button(label="Timeout", style=3, id="button1", disabled=True),
                         Button(label="Timeout", style=4, id="button2", disabled=True)]])
                
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
                            [Button(label="Accepted", style=3, id="button1", disabled=True),
                             Button(label="I decline", style=2, id="button2", disabled=True)]])
                
                if interaction.component.id == "button2":
                    await self.bot.comp_ext.edit_component_msg(conf, embed=Embed(
                        color=0xFF0000,
                        title="Server whitelisting",
                        description="Operation cancelled."),
                        components=[
                            [Button(label="I accept", style=2, id="button1", disabled=True),
                             Button(label="Declined", style=4, id="button2", disabled=True)]])
    
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

    @command()
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    async def Thistory(self, ctx, switch="view"): # view (default), toggle, clear
        lolicon_allowed = False
        try:
            if not ctx.guild or ctx.guild.id in self.bot.user_data["UserData"][str(ctx.guild.owner_id)]["Settings"]["UnrestrictedServers"]:
                lolicon_allowed = True
        except KeyError:
            pass
    
        if switch.lower() == "view":
            nhentai_api = NHentai()
            edit = await ctx.send(embed=Embed(
                    description=f"Loading..."
                ).set_author(
                    name="NHentai History (BOT)",
                    url=f"https://nhentai.net/",
                    icon_url="https://cdn.discordapp.com/emojis/810936543401213953.gif?v=1"
                ).set_footer(
                    text=f"[{' '*len(self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Doujins'])}]"
            ))
            
            message_part = list()
            remove_queue = list()

            is_loading = False
            for code in self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['History']:
                if str(code) not in self.bot.doujin_cache:
                    is_loading = True
                    break

            doujins = []
            for ind, code in enumerate(self.bot.user_data['UserData'][str(ctx.author.id)]['History'][1]):
                if str(code) not in self.bot.doujin_cache:
                    doujin = await nhentai_api.get_doujin(code)
                    print(code)

                else:
                    doujin = self.bot.doujin_cache[str(code)]

                if not doujin:
                    remove_queue.append(code)
                    continue
                else:
                    self.bot.doujin_cache[str(code)] = doujin

                    if any([tag in restricted_tags for tag in doujin.tags]): is_lolicon = True
                    else: is_lolicon = False
                    
                    if is_lolicon and not lolicon_allowed:
                        pass
                    else:
                        doujin.title = f"{str(ind+1).ljust(2)} | {doujin.title}"

                        message_part.append(
                            f"__`{str(code).ljust(7)}`__ | " \
                            f"{language_to_flag(doujin.languages)} | " \
                            f"{shorten(doujin.title, width=50, placeholder='...')} ")
                        
                        doujins.append(doujin)
                    
                    if ind%5 == 0 and ind!=0 and is_loading:
                        await edit.edit(embed=Embed(
                            description=f"Loading..."
                        ).set_author(
                            name="NHentai History (BOT)",
                            url=f"https://nhentai.net/",
                            icon_url="https://cdn.discordapp.com/emojis/810936543401213953.gif?v=1"
                        ).set_footer(
                            text=f"[{'|'*ind}{' '*(len(self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Doujins'])-ind)}]"
                        ))

                        await sleep(0.5)
            
            [self.bot.user_data['UserData'][str(ctx.author.id)]['History'][1].pop(code) for code in remove_queue]
            
            emb = Embed(
                title=f"🕖 History (Top=Latest)")
            emb.set_author(
                name="NHentai Search Results",
                url="https://nhentai.net/",
                icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
            emb.set_footer(text="Provided by MechHub")

            if self.bot.user_data['UserData'][str(ctx.author.id)]['History'][1]:
                emb.description = "\n".join(message_part)

                await self.bot.comp_ext.edit_component_msg(edit, embed=emb,
                    components=[Button(label="Start Interactive", style=1, emoji="⌨", id="button1")])
                
                try:
                    interaction = await self.bot.wait_for('button_click', timeout=20, bypass_cooldown=True,
                        check=lambda i: i.message.id==edit.id and \
                            i.user.id==ctx.author.id and \
                            i.component.id=="button1")
                except TimeoutError:
                    await self.bot.comp_ext.edit_component_msg(edit, embed=emb,
                        components=[Button(label="Timeout", style=2, emoji="⌨", id="button1", disabled=True)])
                    
                    return

                else:
                    await interaction.respond(type=6)

                    await self.bot.comp_ext.edit_component_msg(edit, embed=emb, components=[])

                    interactive = SearchResultsBrowser(self.bot, ctx, doujins, msg=edit, name=f"🕖 History (Top=Latest)", lolicon_allowed=lolicon_allowed)
                    await interactive.start(ctx)

                    return
            
            else:
                emb.description = "You don't have a history yet."
            
            await edit.edit(embed=emb)
        
        elif switch.lower() == "clear":
            self.bot.user_data["UserData"][str(ctx.author.id)]["History"] = [
                self.bot.user_data["UserData"][str(ctx.author.id)]["History"][0], ["placeholder"]]

            emb = Embed(
                color=0xEC2854)
            emb.set_author(
                name="NHentai History (BOT)",
                url=f"https://nhentai.net/",
                icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
            emb.description = "💾 History cleared"

            await ctx.send(embed=emb)
        
        elif switch == "toggle":
            self.bot.user_data["UserData"][str(ctx.author.id)]["History"][0] = \
                not self.bot.user_data["UserData"][str(ctx.author.id)]["History"][0]

            emb = Embed(
                color=0xEC2854)
            emb.set_author(
                name="NHentai History (BOT)",
                url="https://nhentai.net/",
                icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
            emb.description = f"{'✅' if self.bot.user_data['UserData'][str(ctx.author.id)]['History'][0] else '❎'} History toggled"

            await ctx.send(embed=emb)

    @command(aliases=["Tappend"])
    @bot_has_permissions(
        send_messages=True,
        embed_links=True)
    async def Tsearch_appendage(self, ctx, *, appendage=""):
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
                await self.bot.comp_ext.edit_component_msg(conf, embed=Embed(
                    title="⌛❌ Timed out.",
                    description="If you want to update your search appendage, please confirm within 10 seconds next time."), 
                    components=[Button(label="Timeout", style=2, emoji="💾", id="button1", disabled=True)])
                    
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
                await self.bot.comp_ext.edit_component_msg(conf, embed=Embed(
                    title="⌛❌ Timed out.",
                    description="If you want to erase your search appendage, please confirm within 10 seconds next time."), 
                    components=[Button(label="Timeout", style=2, emoji="💾", id="button1", disabled=True)])
                    
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

    @command(aliases=["Trc"])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    @bot_has_guild_permissions(
        manage_messages=True, 
        manage_channels=True, 
        manage_roles=True)
    async def Trecall(self, ctx):
        lolicon_allowed = False
        try:
            if ctx.guild.id in self.bot.user_data["UserData"][str(ctx.guild.owner_id)]["Settings"]["UnrestrictedServers"]:
                lolicon_allowed = True
        except KeyError:
            pass
        
        recall_id = self.bot.user_data["UserData"][str(ctx.author.id)]["Recall"]
        if recall_id == "N/A":
            await ctx.send(embed=Embed(
                title="Unavailable",
                description="You don't have a doujin to recall."))
            return
            
        code, page = self.bot.user_data["UserData"][str(ctx.author.id)]["Recall"].split("*n*")
        
        edit = await ctx.send(embed=Embed(description="<a:nreader_loading:810936543401213953> Recalling..."))

        nhentai_api = NHentai()
        doujin = await nhentai_api.get_doujin(code)
        
        if not lolicon_allowed and any([tag in restricted_tags for tag in doujin.tags]):
            await edit.edit(embed=Embed(
                description=":warning::no_entry_sign: You can't recall your doujin here. Did you think you could wormhole like that?"))

        session = ImagePageReader(self.bot, ctx, doujin.images, f"{doujin.id} [*n*] {doujin.title}", str(doujin.id), starting_page=int(page))
        response = await session.setup()
        if response:
            self.bot.user_data["UserData"][str(ctx.author.id)]["Recall"] = "N/A"
            
            await edit.edit(embed=Embed(description="<:nhentai:845298862184726538> Successfully recalled."))
            print(f"[] {ctx.author} ({ctx.author.id}) started reading `{doujin.id}`.")
            await session.start()
        
        else:
            await edit.edit(embed=Embed(description="❌ You didn't answer the recall in time. Run this command again."))
        
        return

    @Tfavorites.before_invoke
    @Tbookmarks.before_invoke
    @Twhitelist.before_invoke
    @Thistory.before_invoke
    @Tsearch_appendage.before_invoke
    async def placeholder_remove(self, ctx):
        if ctx.command.name == "Tfavorites":
            if 0 in self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Doujins']:
                self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Doujins'].remove(0)
                return
        
        if ctx.command.name == "Tbookmarks":
            if "0" in self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Bookmarks']:
                self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Bookmarks'].pop("placeholder")
                return
        
        if ctx.command.name == "Twhitelist":
            if 0 in self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['UnrestrictedServers']:
                self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['UnrestrictedServers'].remove(0)

        if ctx.command.name == "Thistory":
            if 0 in self.bot.user_data['UserData'][str(ctx.author.id)]['History'][1]:
                self.bot.user_data['UserData'][str(ctx.author.id)]['History'][1].remove(0)
                return
        
        if ctx.command.name == "Tsearch_appendage":
            if len(self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['SearchAppendage']) == 1:
                self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['SearchAppendage'] = ""
                return
        
    @Tfavorites.after_invoke
    @Tbookmarks.after_invoke
    @Twhitelist.after_invoke
    @Thistory.after_invoke
    @Tsearch_appendage.after_invoke
    async def placeholder_add(self, ctx):
        if ctx.command.name == "Tfavorites":
            if 0 not in self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Doujins']:
                self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Doujins'].append(0)
                return
        
        if ctx.command.name == "Tbookmarks":
            if "0" not in self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Bookmarks']:
                self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Bookmarks'].update({"placeholder": 1})
                return
        
        if ctx.command.name == "Twhitelist":
            if 0 not in self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['UnrestrictedServers']:
                self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['UnrestrictedServers'].append(0)
        
        if ctx.command.name == "Thistory":
            if 0 not in self.bot.user_data['UserData'][str(ctx.author.id)]['History'][1]:
                self.bot.user_data['UserData'][str(ctx.author.id)]['History'][1].append(0)
                return
        
        if ctx.command.name == "Tsearch_appendage":
            if not self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['SearchAppendage']:
                self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['SearchAppendage'] = " "
                return


def setup(bot):
    bot.add_cog(Commands(bot))
