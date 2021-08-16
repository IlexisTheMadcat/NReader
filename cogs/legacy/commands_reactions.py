import os
from re import search
from asyncio import sleep, TimeoutError
from zipfile import ZipFile, ZIP_DEFLATED
from textwrap import shorten
from copy import deepcopy
from contextlib import suppress
from urllib.request import urlretrieve as udownload

from discord import Forbidden
from discord.ext.commands import (
    Cog, bot_has_permissions, 
    bot_has_guild_permissions, command)
from NHentai.nhentai_async import NHentaiAsync as NHentai, Doujin

from utils.classes import (
    Embed, BotInteractionCooldown)
from cogs.classes import (
    ImagePageReader,
    SearchResultsBrowser)
from utils.utils import language_to_flag


class Commands(Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @command(name="test")
    @bot_has_permissions(send_messages=True, embed_links=True)
    async def test(self, ctx):
        try:
            await ctx.send("Done (1/2).")
        except Exception:
            await ctx.author.send("(1/2) I can't send messages there.")
        
        try:
            await ctx.send(embed=Embed(description="Done (2/2)."))
        except Exception:
            await ctx.send("(2/2) I can't send embeds in here.")
        
        print(f"{ctx.author} ({ctx.author.id}) tested.")
    
    @command(aliases=["code"])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    @bot_has_guild_permissions(
        manage_messages=True, 
        manage_channels=True, 
        manage_roles=True)
    async def doujin_info(self, ctx, code="random", interface="new"):
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
        edit = await ctx.send(embed=Embed(
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
            
            if ("lolicon" in doujin.tags or "shotacon" in doujin.tags) and ctx.guild and not lolicon_allowed:
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
                if ("lolicon" in doujin.tags or "shotacon" in doujin.tags) and ctx.guild and not lolicon_allowed:
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

        await edit.edit(content="", embed=emb)
        
        await edit.add_reaction("📖")
        await edit.add_reaction("🔍")

        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=60, 
                    check=lambda r,u: r.message.id==edit.id and \
                        u.id==ctx.author.id and \
                        str(r.emoji) in ["📖", "🔍"])
            
            except TimeoutError:
                emb.set_footer(text="Provided by NHentai-API")
                emb.set_thumbnail(
                    url=doujin.images[0])
                emb.set_image(
                    url=Embed.Empty)
                await edit.edit(embed=emb)
                
                with suppress(Forbidden):
                    await edit.clear_reactions()
                
                return
            
            except BotInteractionCooldown:
                continue
            
            else:
                if str(reaction.emoji) == "📖":
                    with suppress(Forbidden):
                        await edit.clear_reactions()
                    
                    emb.set_footer(text="Provided by NHentai-API")
                    emb.set_thumbnail(
                        url=doujin.images[0])
                    emb.set_image(
                        url=Embed.Empty)
                    await edit.edit(embed=emb, components=[])

                    session = ImagePageReader(self.bot, ctx, doujin.images, f"{doujin.id} [*n*] {doujin.title}")
                    response = await session.setup()
                    if response:
                        print(f"[] {ctx.author} ({ctx.author.id}) started reading `{doujin.id}`.")
                        await session.start()
                    
                    else:
                        emb.set_footer(text=Embed.Empty)
                        await edit.edit(embed=emb)
                    
                    return
                
                elif str(reaction.emoji) == "🔍":
                    if not emb.image:
                        emb.set_image(url=emb.thumbnail.url)
                        emb.set_thumbnail(url=Embed.Empty)
                        # word = "Hide"

                    elif not emb.thumbnail:
                        emb.set_thumbnail(url=emb.image.url)
                        emb.set_image(url=Embed.Empty)
                        # word = "Minimize"
                    
                    await edit.remove_reaction("🔍", ctx.author)
                    await edit.edit(content="", embed=emb)

                    continue
    
    @command(aliases=["search"])
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
            if ctx.guild.id in self.bot.user_data["UserData"][str(ctx.guild.owner_id)]["Settings"]["UnrestrictedServers"]:
                lolicon_allowed = True
        except KeyError:
            pass
        
        if ctx.guild and not ctx.channel.is_nsfw():
            await ctx.send(":x: This command cannot be used in a non-NSFW channel.")
            return
        
        conf = await ctx.send(embed=Embed(
            description="<a:nreader_loading:810936543401213953>"))
    
        nhentai_api = NHentai()

        if str(ctx.author.id) in self.bot.user_data["UserData"] and \
            "Settings" in self.bot.user_data["UserData"][str(ctx.author.id)] and \
            "SearchAppendage" in self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]:
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
        for ind, dj in enumerate(results.doujins):
            message_part.append(
                f"__`{str(results.doujins[ind].id).ljust(7)}`__ | "
                f"{language_to_flag(results.doujins[ind].lang)} | "
                f"{shorten(results.doujins[ind].title, width=50, placeholder='...')}")

        emb = Embed(
            description=f"Showing page {page}/{results.total_pages}"
                        f"{'; illegal results are hidden:' if ctx.guild and not lolicon_allowed else ':'}"
                        f"\n"+('\n'.join(message_part)))
        emb.set_author(
            name="NHentai Search Results",
            url="https://nhentai.net/",
            icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
        emb.set_footer(
            text=f"Press the reload button to load more detailed results.")
        await conf.edit(content='', embed=emb)
        print(f"[] {ctx.author} ({ctx.author.id}) searched for [{query if query else ''}{' || ' if query and appendage else ''}{appendage if appendage else ''}].")

        await conf.add_reaction("🔄")

        try:
            await self.bot.wait_for("reaction_add", timeout=20, bypass_cooldown=True, 
                check=lambda r,u: r.message.id==conf.id and \
                u.id==ctx.author.id and \
                str(r.emoji)=="🔄")
        
        except TimeoutError:
            with suppress(Forbidden):
                await conf.clear_reactions()

            emb.set_footer(text="Provided by NHentai-API")
            await conf.edit(content='', embed=emb)
            return
        
        else:
            with suppress(Forbidden):
                await conf.clear_reactions()
        
        emb.set_author(
            name="NHentai Search Results",
            url="https://nhentai.net/",
            icon_url="https://cdn.discordapp.com/emojis/810936543401213953.gif?v=1")
        emb.set_footer(
            text=f"Loading... [{' '*len(results.doujins)}]")
        await conf.edit(content='', embed=emb)
    
        # Request each doujin to simplify results
        # Edits message every 5 retrievals to show progress
        message_part = []
        for ind, dj in enumerate(results.doujins):
            if dj.id not in self.bot.doujin_cache:
                doujin = await nhentai_api.get_doujin(dj.id)
                self.bot.doujin_cache[dj.id] = doujin
            else:
                doujin = self.bot.doujin_cache[dj.id]
            
            if ind%5 == 0 and ind!=0:
                await sleep(1)
                
                message_part2 = []
                for ind2, dj2 in enumerate(results.doujins):
                    message_part2.append(
                        f"__`{str(dj2.id).ljust(7)}`__ | "
                        f"{language_to_flag(dj2.languages) if isinstance(dj2, Doujin) else language_to_flag(dj2.lang)} | "
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
            
            # Overwrite result with true result attributes
            results.doujins[ind] = doujin

            message_part.append(
                f"__`{str(doujin.id).ljust(7)}`__ | "
                f"{language_to_flag(doujin.languages)} | "
                f"{shorten(doujin.title, width=50, placeholder='...')}")
        
        emb = Embed(
            description=f"Showing page {page}/{results.total_pages}"
                        f"{'; illegal results are hidden:' if ctx.guild and not lolicon_allowed else ':'}"
                        f"\n"+('\n'.join(message_part)))
        emb.set_author(
            name="NHentai Search Results",
            url="https://nhentai.net/",
            icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
        emb.set_footer(
            text=f"Enter INTERACTIVE mode? [{'|'*len(results.doujins)}]")
        await conf.edit(content='', embed=emb)
        await conf.add_reaction("⌨")
        
        try:
            await self.bot.wait_for('reaction_add', timeout=20, bypass_cooldown=True,
                check=lambda r,u: r.message.id==conf.id and \
                    u.id==ctx.author.id and \
                    str(r.emoji)=="⌨")
        except TimeoutError:
            with suppress(Forbidden):
                await conf.clear_reactions()
                
            emb.set_footer(text=f"Provided by NHentai-API [{'|'*len(results.doujins)}]")
            await conf.edit(content='', embed=emb)
            return

        else:
            await conf.clear_reactions()
                
            interactive = SearchResultsBrowser(self.bot, ctx, results, page, msg=conf, lolicon_allowed=lolicon_allowed)
            await interactive.start(ctx)
    
    @command(aliases=["pop"])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    @bot_has_guild_permissions(
        manage_messages=True, 
        manage_channels=True, 
        manage_roles=True)
    async def popular(self, ctx):
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
        for ind, dj in enumerate(results.doujins):
            if dj.id not in self.bot.doujin_cache:
                doujin = await nhentai_api.get_doujin(dj.id)
                self.bot.doujin_cache[dj.id] = doujin
            else:
                doujin = self.bot.doujin_cache[dj.id]
            
            results.doujins[ind] = doujin
            
            if ("lolicon" in doujin.tags or "shotacon" in doujin.tags) and ctx.guild and not lolicon_allowed:
                message_part.append("__`       `__ | ⚠🚫 | Not available in this server.")
            else:
                message_part.append(
                    f"__`{str(results.doujins[ind].id).ljust(7)}`__ | "
                    f"{language_to_flag(results.doujins[ind].languages)} | "
                    f"{shorten(results.doujins[ind].title, width=50, placeholder='...')}")

        emb = Embed(
            description=f"🔥 Popular Now 🔥"
                        f"\n"+('\n'.join(message_part)))
        emb.set_author(
            name="NHentai Search Results",
            url="https://nhentai.net/",
            icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
        emb.set_footer(
            text=f"Enter INTERACTIVE mode? [{'|'*len(results.doujins)}]")
        await conf.edit(content='', embed=emb)
        await conf.add_reaction("⌨")
        
        try:
            await self.bot.wait_for('reaction_add', timeout=20, bypass_cooldown=True,
                check=lambda r,u: r.message.id==conf.id and \
                    u.id==ctx.author.id and \
                    str(r.emoji)=="⌨")
        except TimeoutError:
            with suppress(Forbidden):
                await conf.clear_reactions()
                
            emb.set_footer(text=f"Provided by NHentai-API [{'|'*len(results.doujins)}]")
            await conf.edit(content='', embed=emb)
            return

        else:
            await conf.clear_reactions()
                
            interactive = SearchResultsBrowser(self.bot, ctx, results, page=0, msg=conf, lolicon_allowed=lolicon_allowed)
            await interactive.start(ctx)
    
    @command(aliases=["dl"])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    async def download_doujin(self, ctx, code):
        return await ctx.send("Due to recent shutdowns, this command has been disabled prematurely. It will be removed in the future.")
        
        lolicon_allowed = False
        try:
            if not ctx.guild or ctx.guild.id in self.bot.user_data["UserData"][str(ctx.guild.owner_id)]["Settings"]["UnrestrictedServers"]:
                lolicon_allowed = True
        except KeyError:
            pass
        
        if ctx.guild and not ctx.channel.is_nsfw():
            await ctx.send(":x: This command cannot be used in a non-NSFW channel.")
            return
        
        try:
            code = int(code)
        except ValueError:
            await ctx.send(":x: You didn't type a proper ID. Hint: It has to be a number!")
            return
        
        nhentai_api = NHentai()
        conf = await ctx.send("<a:nreader_loading:810936543401213953>")

        if code not in self.bot.doujin_cache:
            doujin = await nhentai_api.get_doujin(code)
        else:
            doujin = self.bot.doujin_cache[code]

        if not doujin:
            await conf.edit(content="🔎❌ I did not find a doujin with that ID.")
            return
        
        self.bot.doujin_cache[code] = doujin
        
        if ("lolicon" in doujin.tags or "shotacon" in doujin.tags) and ctx.guild:
            try:
                if ctx.guild.id in self.bot.user_data["UserData"][str(ctx.guild.owner_id)]["Settings"]["UnrestrictedServers"]:
                    lolicon_allowed = True
            except KeyError:
                pass

        if ("lolicon" in doujin.tags or "shotacon" in doujin.tags) and ctx.guild and not lolicon_allowed:
            await conf.edit(content=":warning::no_entry_sign: This doujin contains lolicon/shotacon content and cannot be shown publically.")
            return

        emb = Embed(
            description="You are attempting to download a doujin. Press the arrow to continue."
        )
        emb.set_author(
                name=f"{language_to_flag(doujin.languages)} {doujin.title}",
                url=f"https://nhentai.net/g/{doujin.id}/",
                icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
        emb.set_thumbnail(
            url=doujin.images[0]
        )
        
        await conf.edit(content='', embed=emb)
        await conf.add_reaction("⬇")

        try:
            await self.bot.wait_for("reaction_add", timeout=30, bypass_cooldown=True,
                check=lambda r,u: r.message.id==conf.id and \
                    u.id==ctx.message.author.id and \
                    str(r.emoji)=="⬇")
        except TimeoutError:
            await conf.remove_reaction("⬇", self.bot.user)
            emb.description = "You timed out."
            await conf.edit(embed=emb)
            return
        else:
            emb.description = "Downloading...\nYou will be notified when completed."
            emb.set_author(
                name=f"[{language_to_flag(doujin.languages)}] {doujin.title}",
                url=f"https://nhentai.net/g/{doujin.id}/",
                icon_url="https://cdn.discordapp.com/emojis/810936543401213953.gif?v=1")
        
            emb.set_footer(text=f"[{' '*len(doujin.images)}]")
            await conf.edit(embed=emb)
        
        print(f"[] {ctx.author} ({ctx.author.id}) started downloading {doujin.id} ({len(doujin.images)} pages).")
        
        files = list()
        for ind, page_url in enumerate(doujin.images, 1):
            udownload(page_url, f"Workspace/{ctx.message.id}_{doujin.id}_page{ind}.png")
            files.append(f"Workspace/{ctx.message.id}_{doujin.id}_page{ind}.png")
            if ind%5 == 0:
                emb.set_footer(text=f"[{'|'*ind}{' '*(len(doujin.images)-ind)}]")
                await conf.edit(embed=emb)
            
            await sleep(0.5)
        

        emb.set_footer(text=f"Processing zip file... [{'|'*len(doujin.images)}]")
        await conf.edit(embed=emb)
        with ZipFile(f"Workspace/{ctx.message.id}.zip", "w") as send_zip:
            for ind, file_p in enumerate(files, 1):
                send_zip.write(file_p, f"page_{ind}.png", compress_type=ZIP_DEFLATED)
                os.remove(file_p)

        os.rename(f"Workspace/{ctx.message.id}.zip", f"Storage/{ctx.message.id}")
        new_filelink = f"https://nreader.supermechm500.repl.co/download?" \
                       f"id={ctx.message.id}"

        await conf.delete()
        await ctx.send(
            content=f"{ctx.author.mention}, your download has completed. ⬇", 
            embed=Embed(
                color=0x32d17f,
                description=f"Here is a zipped file of your downloaded doujin. [Download]({new_filelink})\n"
                            f'Remember to rename the file from "download" to "**something.zip**".\n'
                            f"Expires in **5 minutes** or until bot is forced to reboot."
            ).set_author(
                    name=f"{language_to_flag(doujin.languages)} {doujin.title}",
                    url=f"https://nhentai.net/g/{doujin.id}/",
                    icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1"
            ).set_footer(
                text=f"[{'|'*len(doujin.images)}]"
            ))

        await sleep(5*60)
        with suppress(FileNotFoundError):
            os.remove(f"Storage/{ctx.message.id}")

    @command(aliases=["fav"])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    async def favorites(self, ctx, mode:str=None, code=None):
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
            emb = Embed(
                color=0xEC2854)
            emb.set_author(
                name="NHentai Favorites",
                url=f"https://nhentai.net/",
                icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")

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

            favorites_list = list()
            remove_queue = list()  # It is very rare that a doujin would get deleted from NHentai

            is_loading = False
            for code in self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Doujins']:
                if code not in self.bot.doujin_cache:
                    is_loading = True
                    break
            
            for ind, code in enumerate(self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Doujins']):
                if code not in self.bot.doujin_cache:
                    doujin = await nhentai_api.get_doujin(code)
                else:
                    doujin = self.bot.doujin_cache[code]
                
                if not doujin:
                    remove_queue.append(code)
                    continue
                else:
                    self.bot.doujin_cache[code] = doujin

                    if ("lolicon" in doujin.tags or "shotacon" in doujin.tags): is_lolicon = True
                    else: is_lolicon = False
                    
                    if is_lolicon and not lolicon_allowed:
                        pass
                    else:
                        favorites_list.append(
                            f"`{'🟨' if is_lolicon else '⬛'}` " \
                            f"__`{str(doujin.id).ljust(7)}`__ | "
                            f"{language_to_flag(doujin.languages)} | "
                            f"{shorten(doujin.title, width=50, placeholder='...')}")
                        
                    if ind%5 == 0 and is_loading:
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
            
            linebreak = "\n"
            if self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Doujins']:
                emb.description = f"**__Added__**\n" \
                                  f"{linebreak.join(favorites_list)}\n"
                emb.set_footer(
                    text=f"[{'|'*len(self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Doujins'])}]")
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

                    if ("lolicon" in doujin.tags or "shotacon" in doujin.tags) and ctx.guild and not lolicon_allowed:
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

    @command(aliases=["bm"])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    async def bookmarks(self, ctx):
        lolicon_allowed = False
        try:
            if not ctx.guild or ctx.guild.id in self.bot.user_data["UserData"][str(ctx.guild.owner_id)]["Settings"]["UnrestrictedServers"]:
                lolicon_allowed = True
        except KeyError:
            pass
        
        if ctx.guild and not ctx.channel.is_nsfw():
            await ctx.send(":x: This command cannot be used in a non-NSFW channel.")
            return

        emb = Embed(
            color=0xEC2854)
        emb.set_author(
            name="NHentai Bookmarks",
            url=f"https://nhentai.net/",
            icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")

        nhentai_api = NHentai()
        edit = await ctx.send("<a:nreader_loading:810936543401213953>")
        
        bookmarks_list = list()
        remove_queue = list()  # It is very rare that a doujin would get deleted from NHentai
        
        for code, page in self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Bookmarks'].items():
            if code not in self.bot.doujin_cache:
                doujin = await nhentai_api.get_doujin(code)
            else:
                doujin = self.bot.doujin_cache[code]

            if not doujin:
                remove_queue.append(code)
                continue
            else:
                self.bot.doujin_cache[code] = doujin

                if ("lolicon" in doujin.tags or "shotacon" in doujin.tags): is_lolicon = True
                else: is_lolicon = False

                if is_lolicon and not lolicon_allowed:
                    continue
                
                else:
                    bookmarks_list.append(
                        f"`{'🟨' if is_lolicon else '⬛'} " \
                        f"{str(code).ljust(7)}` | " \
                        f"{language_to_flag(doujin.languages)} | " \
                        f"{page+1}/{len(doujin.images)} ー " \
                        f"{shorten(doujin.title, width=50, placeholder='...')} ")

        [self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Bookmarks'].pop(code) for code in remove_queue]

        linebreak = "\n"
        if self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Bookmarks']:
            emb.description = f"**__Bookmarks__**\n" \
                              f"{linebreak.join(bookmarks_list)}"
        else:
            emb.description = "You have no bookmarks."
        
        await edit.edit(content="", embed=emb)
    
    @command()
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    async def whitelist(self, ctx, mode=None):
        if ctx.guild and ctx.author.id != ctx.guild.owner_id:
            await ctx.send("❌ You must be the owner of the server to use this command.")
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
                await ctx.send("❌ You have no whitelisted servers.")
                return
                    
        elif mode.lower() in ["add", "a", "+"]:
            if ctx.guild.id not in self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["UnrestrictedServers"]:
                self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["UnrestrictedServers"].append(ctx.guild.id)
            await ctx.send("✔ This server can now access doujins that contain underage characters.")
    
        elif mode.lower() in ["remove", "r", "-"]:
            if ctx.guild.id in self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["UnrestrictedServers"]:
                self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["UnrestrictedServers"].remove(ctx.guild.id)
            await ctx.send("✔ This server can no longer access doujins that contain underage characters.")
        
        else:
            await ctx.send("You didn't specify a mode. Valid modes are `add/a/+` and `remove/r/-`.")

    @command()
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    async def history(self, ctx, switch="view"): # view (default), toggle, clear
        lolicon_allowed = False
        try:
            if not ctx.guild or ctx.guild.id in self.bot.user_data["UserData"][str(ctx.guild.owner_id)]["Settings"]["UnrestrictedServers"]:
                lolicon_allowed = True
        except KeyError:
            pass
    
        if switch.lower() == "view":
            emb = Embed(
                color=0xEC2854)
            emb.set_author(
                name="NHentai History (BOT)",
                url="https://nhentai.net/",
                icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")

            nhentai_api = NHentai()
            edit = await ctx.send(embed=Embed(
                description="<a:nreader_loading:810936543401213953>"))
            
            history = list()
            for number, code in enumerate(self.bot.user_data['UserData'][str(ctx.author.id)]['History'][1]):
                if code not in self.bot.doujin_cache:
                    doujin = await nhentai_api.get_doujin(code)
                else:
                    doujin = self.bot.doujin_cache[code]

                if not doujin:
                    self.bot.user_data['UserData'][str(ctx.author.id)]['History'][1].remove(code)
                    continue
                else:
                    self.bot.doujin_cache[code] = doujin

                    if ("lolicon" in doujin.tags or "shotacon" in doujin.tags): is_lolicon = True
                    else: is_lolicon = False
                    
                    if is_lolicon and not lolicon_allowed:
                        continue
                    else:
                        history.append(
                            f"`{'🟨' if is_lolicon else '⬛'}` "
                            f"__`#{str(number+1).ljust(2)}`__ | "
                            f"__`{str(doujin.id).ljust(7)}`__ | "
                            f"{language_to_flag(doujin.languages)} | "
                            f"{shorten(doujin.title, width=50, placeholder='...')}")
            
            emb.description = ("\n".join(history)) if history and 'placeholder' not in history else "You don't have a history yet."
            await edit.edit(content="", embed=emb)
        
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

    @command(aliases=["append"])
    @bot_has_permissions(
        send_messages=True,
        embed_links=True)
    async def search_appendage(self, ctx, *, appendage=""):
        if appendage and appendage != "clear_appendage":
            conf = await ctx.send(embed=Embed(
                title = "Confirm Search Appendage Update",
                description = f"🔄 You are attempting to update your search appendage;\n"
                              f"```diff\n"
                              f"- [{self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['SearchAppendage']}]\n"
                              f"=====\n"
                              f"+ [{appendage}]"
                              f"```\n"
                              f"Brackets not included. Press ✔ to confirm."
            ).set_footer(text="Please note that this will be appended to searches in all cases, so if you have unexpected results, check back on this command."))
            
            await conf.add_reaction("✔")

            try:
                await self.bot.wait_for("reaction_add", timeout=10, bypass_cooldown=True,
                    check=lambda r,u: r.message.id==conf.id and \
                        u.id==ctx.author.id)
            except TimeoutError:
                await conf.edit(embed=Embed(
                    title="⌛❌ Timed out.",
                    description="If you want to update your search appendage, please confirm within 10 seconds next time."))

                await conf.remove_reaction("✔", self.bot.user)
            
            else:
                self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["SearchAppendage"] = appendage
                
                await conf.edit(embed=Embed(
                    title = "Search Appendage Updated",
                    description = f"✅ The following string will now be appended to all of your searches:\n"
                                  f"```{self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['SearchAppendage']}```\n"
                ).set_footer(text="Please note that this will be appended to searches in all cases, so if you have unexpected results, check back on this command."))
        
        elif appendage == "clear_appendage":
            conf = await ctx.send(embed=Embed(
                title = "Confirm Search Appendage Erase",
                description = f"⚠ You are attempting to erase your search appendage;\n"
                              f"```diff\n"
                              f"- [{self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['SearchAppendage']}]\n"
                              f"```\n"
                              f"Brackets not included. Press ✔ to confirm."
            ).set_footer(text="Please note that this will be appended to searches in all cases, so if you have unexpected results, check back on this command."))
            
            await conf.add_reaction("✔")

            try:
                await self.bot.wait_for("reaction_add", timeout=10, bypass_cooldown=True,
                    check=lambda r,u: r.message.id==conf.id and \
                        u.id==ctx.author.id)
            except TimeoutError:
                await conf.edit(content="⌛❌ If you want to erase your search appendage, please confirm within 10 seconds next time.", embed=None)
                await conf.remove_reaction("✔", self.bot.user)
            
            else:
                self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["SearchAppendage"] = ""
                
                await conf.edit(embed=Embed(
                    title = "Search Appendage Erase",
                    description = "✅ Nothing will be added to your searches."
                ).set_footer(text="Please note that this will be appended to searches in all cases, so if you have unexpected results, check back on this command."))
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

    @favorites.before_invoke
    @bookmarks.before_invoke
    @whitelist.before_invoke
    @history.before_invoke
    @search_appendage.before_invoke
    async def placeholder_remove(self, ctx):
        if ctx.command.name == "favorites":
            if 0 in self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Doujins']:
                self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Doujins'].remove(0)
                return
        
        if ctx.command.name == "bookmarks":
            if "0" in self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Bookmarks']:
                self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Bookmarks'].pop("placeholder")
                return
        
        if ctx.command.name == "whitelist":
            if 0 in self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['UnrestrictedServers']:
                self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['UnrestrictedServers'].remove(0)

        if ctx.command.name == "history":
            if 0 in self.bot.user_data['UserData'][str(ctx.author.id)]['History'][1]:
                self.bot.user_data['UserData'][str(ctx.author.id)]['History'][1].remove(0)
                return
        
        if ctx.command.name == "search_appendage":
            if self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['SearchAppendage'] == " ":
                self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['SearchAppendage']
                return
        
    @favorites.after_invoke
    @bookmarks.after_invoke
    @whitelist.after_invoke
    @history.after_invoke
    @search_appendage.after_invoke
    async def placeholder_add(self, ctx):
        if ctx.command.name == "favorites":
            if 0 not in self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Doujins']:
                self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Doujins'].append(0)
                return
        
        if ctx.command.name == "bookmarks":
            if "0" not in self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Bookmarks']:
                self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Bookmarks'].update({"placeholder": 1})
                return
        
        if ctx.command.name == "whitelist":
            if 0 not in self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['UnrestrictedServers']:
                self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['UnrestrictedServers'].append(0)
        
        if ctx.command.name == "history":
            if 0 not in self.bot.user_data['UserData'][str(ctx.author.id)]['History'][1]:
                self.bot.user_data['UserData'][str(ctx.author.id)]['History'][1].append(0)
                return
        
        if ctx.command.name == "search_appendage":
            if not self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['SearchAppendage']:
                self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['SearchAppendage'] = " "
                return
    
    

def setup(bot):
    bot.add_cog(Commands(bot))
