import os
from asyncio import sleep
from zipfile import ZipFile, ZIP_DEFLATED
from asyncio.exceptions import TimeoutError
from textwrap import shorten
from contextlib import suppress
from urllib.request import urlretrieve as udownload

from discord import Forbidden
from discord.ext.commands.cog import Cog
from discord.ext.commands.core import bot_has_permissions, command
from NHentai import NHentai, Doujin

from utils.classes import ImagePageReader, SearchResultsBrowser, Embed
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
            await ctx.send(embed=Embed(color=0x000000, description="Done (2/2)."))
        except Exception:
            await ctx.send("(2/2) I can't send embeds in here.")
    
    @command(aliases=["code"])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True, 
        manage_messages=True, 
        manage_channels=True, 
        manage_roles=True)
    async def doujin_info(self, ctx, code="random"):
        lolicon_allowed = False
        try:
            if ctx.guild.id in self.bot.user_data["UserData"][str(ctx.guild.owner_id)]["Settings"]["Unrestricted Servers"]:
                lolicon_allowed = True
        except KeyError:
            pass
            
        if not ctx.channel.is_nsfw():
            await ctx.send(":x: This command cannot be used in a non-NSFW channel.")
            return
        
        try:
            if code.lower() not in ["random", "r"]:
                code = int(code)
                code = str(code)
        except ValueError:
            await ctx.send(":x: You didn't type a proper ID. Hint: It has to be a number!")
            return
        
        nhentai_api = NHentai()
        edit = await ctx.send("<a:nreader_loading:810936543401213953>")

        if code.lower() not in ["random", "r"]:
            if code not in self.bot.doujin_cache:
                doujin = nhentai_api._get_doujin(code)
            else:
                doujin = self.bot.doujin_cache[code]

            if not doujin:
                await edit.edit(content=":mag_right::x: I did not find a doujin with that ID.")
                return
            else:
                self.bot.doujin_cache[code] = doujin
            
        
            if ("lolicon" in doujin.tags or "shotacon" in doujin.tags) and ctx.guild and not lolicon_allowed:
                await edit.edit(content=":warning::no_entry_sign: This doujin contains lolicon/shotacon content and cannot be shown publically.")

                with suppress(Forbidden):
                    await ctx.author.send("Tip: To view lolicon/shotacon doujins on Discord, you need to invite me to a server that you "
                                          "own and run the `n!whitelist <'add' or 'remove'>` (Server-owner only) command. \n"
                                          "This will allow all users in your server to open lolicon/shotacon doujins.\n"
                                          "This command is not in the help menu.\n"
                                          "Lolicon/shotacon doujins are __only__ reflected on your history, favorites, or bookmarks __**in whitelisted servers**__.")
                
                print(f"[] ⚠ {ctx.author} ({ctx.author.id}) attempted to read `{doujin.id}` containing underage characters in a restricted server.")
                return
        else:
            while True:
                doujin = nhentai_api.get_random()
                self.bot.doujin_cache[doujin.id] = doujin
                if ("lolicon" in doujin.tags or "shotacon" in doujin.tags) and ctx.guild and not lolicon_allowed:
                    await edit.edit(edit="<a:nreader_loading:810936543401213953> Retrying...")
                    await sleep(0.75)
                    continue
                else:
                    break

        if str(ctx.author.id) not in self.bot.user_data["UserData"]:
            self.bot.user_data["UserData"][str(ctx.author.id)] = {}
        if "History" not in self.bot.user_data["UserData"][str(ctx.author.id)]:
            self.bot.user_data["UserData"][str(ctx.author.id)]["History"] = [True, []]

        if self.bot.user_data["UserData"][str(ctx.author.id)]["History"][0]:
            self.bot.user_data["UserData"][str(ctx.author.id)]["History"][1].insert(0, doujin.id)
            if len(self.bot.user_data["UserData"][str(ctx.author.id)]["History"][1]) >= 2 and \
                self.bot.user_data["UserData"][str(ctx.author.id)]["History"][1][1] == doujin.id:
                self.bot.user_data["UserData"][str(ctx.author.id)]["History"][1].pop(0)
        
        emb = Embed(
            description=f"{'**[Random]**' if code.lower() in ['random', 'r'] else ''}[{'{'}Tap to open{'}'}](https://nhentai.net/g/{doujin.id}/)\n"
                        f"Doujin ID: `{doujin.id}`\n"
                        f"Secondary Title: `{doujin.secondary_title if doujin.secondary_title != '' else 'Not provided'}`\n"
                        f"Pages: `{len(doujin.images)}`\n"
                        f"Artist(s): `{', '.join(doujin.artists) if doujin.artists != [] else 'Not provided'}`\n"
                        f"Language(s): `{', '.join(doujin.languages) if doujin.languages != [] else 'Not provided'}`\n"
                        f"Character(s): `{', '.join(doujin.characters) if doujin.characters != [] else 'Original'}`\n"
                        f"Tags: ```{', '.join(doujin.tags) if doujin.tags != [] else 'None provided'}```\n")
        emb.set_author(
            name=f"[{language_to_flag(doujin.languages)}] {doujin.title}",
            url=f"https://nhentai.net/g/{doujin.id}/",
            icon_url="https://cdn.discordapp.com/attachments/742481946030112779/759591081758949410/emote.png")
        emb.set_footer(
            text="Would you like to read this doujin on Discord?")
        emb.set_thumbnail(
            url=doujin.images[0])
        
        print(f"[] {ctx.author} ({ctx.author.id}) looked up `{code}`"
              f"{' containing underage characters in an unrestricted server.' if ('lolicon' in doujin.tags or 'shotacon' in doujin.tags) and ctx.guild and lolicon_allowed else '.'}")

        await edit.edit(content="", embed=emb)                  
        await edit.add_reaction("📖")
        await edit.add_reaction("🔍")

        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=60, 
                    check=lambda r, u: r.message.id==edit.id and u.id==ctx.author.id and str(r.emoji) in ["📖", "🔍"])
            
            except TimeoutError:
                emb.set_footer(text=Embed.Empty)
                emb.set_thumbnail(
                    url=doujin.images[0])
                emb.set_image(
                    url=Embed.Empty)
                await edit.edit(embed=emb)
                with suppress(Forbidden):
                    await edit.clear_reactions()
                
                return
            else:
                if str(reaction.emoji) == "📖":
                    with suppress(Forbidden):
                        await edit.clear_reactions()
                    
                    emb.set_footer(text="A reader was created for you.")
                    emb.set_thumbnail(
                        url=doujin.images[0])
                    emb.set_image(
                        url=Embed.Empty)
                    await edit.edit(embed=emb)

                    session = ImagePageReader(self.bot, ctx, doujin.images, f"{doujin.id} [*n*] {doujin.title}")
                    response = await session.setup()
                    if response:
                        await session.start()
                    else:
                        emb.set_footer(text=Embed.Empty)
                        await edit.edit(embed=emb)
                    
                    return
                
                elif str(reaction.emoji) == "🔍":
                    if not emb.image:
                        emb.set_image(url=emb.thumbnail.url)
                        emb.set_thumbnail(url=Embed.Empty)
                    elif not emb.thumbnail:
                        emb.set_thumbnail(url=emb.image.url)
                        emb.set_image(url=Embed.Empty)
                    
                    await edit.remove_reaction("🔍", ctx.author)
                    await edit.edit(embed=emb)

                    continue
                    
    @command(aliases=["search"])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True, 
        manage_messages=True, 
        manage_channels=True, 
        manage_roles=True)
    async def search_doujins(self, ctx, *, query: str = ""):
        lolicon_allowed = False
        try:
            if ctx.guild.id in self.bot.user_data["UserData"][str(ctx.guild.owner_id)]["Settings"]["Unrestricted Servers"]:
                lolicon_allowed = True
        except KeyError:
            pass
        
        if ctx.guild and not ctx.channel.is_nsfw():
            await ctx.send(":x: This command cannot be used in a non-NSFW channel.")
            return
        
        conf = await ctx.send("<a:nreader_loading:810936543401213953>")
    
        nhentai_api = NHentai()

        if self.bot.user_data["UserData"] and \
            self.bot.user_data["UserData"][str(ctx.author.id)] and \
            "Settings" in self.bot.user_data["UserData"][str(ctx.author.id)] and \
            "SearchAppendage" in self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]:
            appendage = self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["SearchAppendage"]
        else:
            appendage = ""

        if not query and not appendage:
            await conf.edit(content="You're kidding? You need to tell me what to search, or update your search appendage (See \"search_appendage\" in `n!help`).")
        
        results: dict = nhentai_api.search(query=query+f"{' -lolicon -shotacon' if ctx.guild and not lolicon_allowed else ''} {appendage}", sort='popular', page=1)

        if isinstance(results, Doujin):
            if results.id not in self.bot.doujin_cache:
                self.bot.doujin_cache[results.id] = results
            
            await conf.delete()
            ctx.message.content = f"n!code {results.id}"
            await self.bot.process_commands(ctx.message)
            return
        
        if not results.doujins:
            await conf.edit(content='I did not find anything. Check your keywords!')
            return
        
        message_part = []
        for ind, dj in enumerate(results.doujins):
            message_part.append(
                f"__`{str(results.doujins[ind].id).ljust(7)}`__ | "
                f"🏳❔ | "
                f"{shorten(results.doujins[ind].title, width=50, placeholder='...')}")
        emb = Embed(
            description=f"First page only displayed"
                        f"{'; illegal results are hidden:' if ctx.guild and not lolicon_allowed else ':'}"
                        f"\n"+('\n'.join(message_part)))
        emb.set_author(
            name="NHentai Search Results",
            url="https://nhentai.net/",
            icon_url="https://cdn.discordapp.com/attachments/742481946030112779/759591081758949410/emote.png")
        emb.set_footer(
            text="Loading more details...")
        await conf.edit(content='', embed=emb)
        await conf.add_reaction("<a:nreader_loading:810936543401213953>")

        print(f"[] {ctx.author} ({ctx.author.id}) searched for [{query}].")
    
        # Request each doujin to simplify results
        message_part = []
        for ind, dj in enumerate(results.doujins):
            if dj.id not in self.bot.doujin_cache:
                doujin = nhentai_api._get_doujin(dj.id)
                self.bot.doujin_cache[dj.id] = doujin
            else:
                doujin = self.bot.doujin_cache[dj.id]
            
            # Overwrite result with 'true' result attributes
            results.doujins[ind] = doujin

            message_part.append(
                f"__`{str(doujin.id).ljust(7)}`__ | "
                f"{language_to_flag(doujin.languages)} | "
                f"{shorten(doujin.title, width=50, placeholder='...')}")
        emb = Embed(
            description=f"First page only displayed"
                        f"{'; illegal results are hidden:' if ctx.guild and not lolicon_allowed else ':'}"
                        f"\n"+('\n'.join(message_part)))
        emb.set_author(
            name="NHentai Search Results",
            url="https://nhentai.net/",
            icon_url="https://cdn.discordapp.com/attachments/742481946030112779/759591081758949410/emote.png")
        emb.set_footer(
            text="Enter INTERACTIVE mode?")
        await conf.remove_reaction("<a:nreader_loading:810936543401213953>", self.bot.user)
        await conf.edit(content='', embed=emb)
        await conf.add_reaction("⌨")
        
        try:
            await self.bot.wait_for('reaction_add', timeout=20, 
                check=lambda r, u: r.message.id==conf.id and u.id==ctx.author.id and str(r.emoji)=="⌨")
        except TimeoutError:
            with suppress(Forbidden):
                await conf.clear_reactions()
                
            emb.set_footer(text="Provided by NHentai-API")
            await conf.edit(content='', embed=emb)
        else:
            await conf.clear_reactions()
                
            interactive = SearchResultsBrowser(self.bot, ctx, results, conf, lolicon_allowed=lolicon_allowed)
            await interactive.start(ctx)
    
    # IN CONSTRUCTION, UNFINISHED
    @command(aliases=["crand"])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True, 
        manage_messages=True, 
        manage_channels=True, 
        manage_roles=True)
    async def custom_random(self, ctx, *, query: str = ""):
        lolicon_allowed = False
        try:
            if ctx.guild.id in self.bot.user_data["UserData"][str(ctx.guild.owner_id)]["Settings"]["Unrestricted Servers"]:
                lolicon_allowed = True
        except KeyError:
            pass
        
        if ctx.guild and not ctx.channel.is_nsfw():
            await ctx.send(":x: This command cannot be used in a non-NSFW channel.")
            return
        
        conf = await ctx.send("<a:nreader_loading:810936543401213953>")
    
        nhentai_api = NHentai()

        if self.bot.user_data["UserData"] and \
            self.bot.user_data["UserData"][str(ctx.author.id)] and \
            "Settings" in self.bot.user_data["UserData"][str(ctx.author.id)] and \
            "SearchAppendage" in self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]:
            appendage = self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["SearchAppendage"]
        else:
            appendage = ""
        
        if not query and not appendage:
            await conf.edit(content="You're kidding? You need to tell me what to search, or update your search appendage (See \"search_appendage\" in `n!help`).")
        
        results: dict = nhentai_api.search(query=query+f"{' -lolicon -shotacon' if ctx.guild and not lolicon_allowed else ''} {appendage}", sort='popular', page=1)

        if isinstance(results, Doujin):
            if results.id not in self.bot.doujin_cache:
                self.bot.doujin_cache[results.id] = results
            
            await conf.delete()
            ctx.message.content = f"n!code {results.id}"
            await self.bot.process_commands(ctx.message)
            return
        
        if not results.doujins:
            await conf.edit(content='I did not find anything. Check your keywords!\nThis may also be the cause of your search_appendage. See \"search_appendage\" in `n!help`.')
            return
        
        message_part = []
        for ind, dj in enumerate(results.doujins):
            message_part.append(
                f"__`{str(results.doujins[ind].id).ljust(7)}`__ | "
                f"🏳❔ | "
                f"{shorten(results.doujins[ind].title, width=50, placeholder='...')}")
        emb = Embed(
            description=f"First page only displayed"
                        f"{'; illegal results are hidden:' if ctx.guild and not lolicon_allowed else ':'}"
                        f"\n"+('\n'.join(message_part)))
        emb.set_author(
            name="NHentai Search Results",
            url="https://nhentai.net/",
            icon_url="https://cdn.discordapp.com/attachments/742481946030112779/759591081758949410/emote.png")
        emb.set_footer(
            text="Loading more details...")
        await conf.edit(content='', embed=emb)
        await conf.add_reaction("<a:nreader_loading:810936543401213953>")

        print(f"[] {ctx.author} ({ctx.author.id}) searched for [{query}].")
    
        # Request each doujin to simplify results
        message_part = []
        for ind, dj in enumerate(results.doujins):
            if dj.id not in self.bot.doujin_cache:
                doujin = nhentai_api._get_doujin(dj.id)
                self.bot.doujin_cache[dj.id] = doujin
            else:
                doujin = self.bot.doujin_cache[dj.id]
            
            # Overwrite result with 'true' result attributes
            results.doujins[ind] = doujin

            message_part.append(
                f"__`{str(doujin.id).ljust(7)}`__ | "
                f"{language_to_flag(doujin.languages)} | "
                f"{shorten(doujin.title, width=50, placeholder='...')}")
        emb = Embed(
            description=f"First page only displayed"
                        f"{'; illegal results are hidden:' if ctx.guild and not lolicon_allowed else ':'}"
                        f"\n"+('\n'.join(message_part)))
        emb.set_author(
            name="NHentai Search Results",
            url="https://nhentai.net/",
            icon_url="https://cdn.discordapp.com/attachments/742481946030112779/759591081758949410/emote.png")
        emb.set_footer(
            text="Enter INTERACTIVE mode?")
        await conf.remove_reaction("<a:nreader_loading:810936543401213953>", self.bot.user)
        await conf.edit(content='', embed=emb)
        await conf.add_reaction("⌨")
        
        try:
            await self.bot.wait_for('reaction_add', timeout=20, 
                check=lambda r, u: r.message.id==conf.id and u.id==ctx.author.id and str(r.emoji)=="⌨")
        except TimeoutError:
            with suppress(Forbidden):
                await conf.clear_reactions()
                
            emb.set_footer(text="Provided by NHentai-API")
            await conf.edit(content='', embed=emb)
        else:
            await conf.clear_reactions()
                
            interactive = SearchResultsBrowser(self.bot, ctx, results, conf, lolicon_allowed=lolicon_allowed)
            await interactive.start(ctx)
    
    @command(aliases=["dl"])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    async def download_doujin(self, ctx, code):
        lolicon_allowed = False
        try:
            if not ctx.guild or ctx.guild.id in self.bot.user_data["UserData"][str(ctx.guild.owner_id)]["Settings"]["Unrestricted Servers"]:
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
            doujin = nhentai_api._get_doujin(code)
        else:
            doujin = self.bot.doujin_cache[code]

        if not doujin:
            await conf.edit(content=":mag_right::x: I did not find a doujin with that ID.")
            return
        
        self.bot.doujin_cache[code] = doujin
        
        if ("lolicon" in doujin.tags or "shotacon" in doujin.tags) and ctx.guild:
            try:
                if ctx.guild.id in self.bot.user_data["UserData"][str(ctx.guild.owner_id)]["Settings"]["Unrestricted Servers"]:
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
                icon_url="https://cdn.discordapp.com/attachments/742481946030112779/759591081758949410/emote.png")
        emb.set_thumbnail(
            url=doujin.images[0]
        )
        
        conf = await ctx.edit(content='', embed=emb)
        await conf.add_reaction("⬇")

        try:
            await self.bot.wait_for("reaction_add", timeout=30, check=lambda r, u: r.message.id == conf.id and u.id == ctx.message.author.id and str(r.emoji) == "⬇")
        except TimeoutError:
            await conf.remove_reaction("⬇", self.bot.user)
            emb.description = "You timed out."
            await conf.edit(embed=emb)
            return
        else:
            emb.description = "<a:nreader_loading:810936543401213953> Downloading...\nYou will be notified when completed."
            emb.set_footer(text=f"| --- [0/{len(doujin.images)}] --- |")
            await conf.edit(embed=emb)
        
        print(f"[] {ctx.author} ({ctx.author.id}) started downloading {doujin.id} ({len(doujin.images)} pages).")
        
        files: list = list()
        for ind, page_url in enumerate(doujin.images, 1):
            udownload(page_url, f"Workspace/{ctx.message.id}_{doujin.id}_page{ind}.png")
            files.append(f"Workspace/{ctx.message.id}_{doujin.id}_page{ind}.png")
            if ind%5 == 0:
                emb.set_footer(text=f"| --- [{ind}/{len(doujin.images)}] --- |")
                await conf.edit(embed=emb)
        

        emb.set_footer(text="Processing zip file...")
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
                            f"Expires in 5 minutes."
        ))

        await sleep(5*60)
        with suppress(FileNotFoundError):
            os.remove(f"Storage/{ctx.message.id}")

    @command(aliases=["fav"])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    async def favorites(self, ctx, mode:str=None, code=None):
        if str(ctx.author.id) not in self.bot.user_data["UserData"]:
            self.bot.user_data["UserData"][str(ctx.author.id)] = {}
        if "nFavorites" not in self.bot.user_data["UserData"][str(ctx.author.id)]:
            self.bot.user_data["UserData"][str(ctx.author.id)]["nFavorites"] = {}
        if "Bookmarks" not in self.bot.user_data["UserData"][str(ctx.author.id)]["nFavorites"]:
            self.bot.user_data["UserData"][str(ctx.author.id)]["nFavorites"]["Bookmarks"] = {}
        if "Doujins" not in self.bot.user_data["UserData"][str(ctx.author.id)]["nFavorites"]:
            self.bot.user_data["UserData"][str(ctx.author.id)]["nFavorites"]["Doujins"] = []
        
        lolicon_allowed = False
        try:
            if not ctx.guild or ctx.guild.id in self.bot.user_data["UserData"][str(ctx.guild.owner_id)]["Settings"]["Unrestricted Servers"]:
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
                icon_url="https://cdn.discordapp.com/attachments/742481946030112779/759591081758949410/emote.png")

            nhentai_api = NHentai()
            edit = await ctx.send("<a:nreader_loading:810936543401213953>")
            
            favorites_list = list()
            remove_queue = list()  # It is very rare that a doujin would get deleted from NHentai
            for code in self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Doujins']:
                if code not in self.bot.doujin_cache:
                    doujin = nhentai_api._get_doujin(code)
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
                        favorites_list.append(
                            f"`{'🟨' if is_lolicon else '⬛'}` " \
                            f"__`{str(doujin.id).ljust(7)}`__ | "
                            f"{language_to_flag(doujin.languages)} | "
                            f"{shorten(doujin.title, width=50, placeholder='...')}")
                        
            [self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Doujins'].pop(code) for code in remove_queue]

            linebreak = "\n"
            if self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Doujins']:
                emb.description = f"**__Added__**\n" \
                                  f"{linebreak.join(favorites_list)}\n"
            else:
                emb.description = "You have no favorites."

            await edit.edit(content="", embed=emb)
        
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
                    doujin = nhentai_api._get_doujin(code)
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
                            icon_url="https://cdn.discordapp.com/attachments/742481946030112779/759591081758949410/emote.png")
                        await edit.edit(content="", embed=emb)
                        return

                    
                    if doujin.id not in self.bot.user_data["UserData"][str(ctx.author.id)]["nFavorites"]["Doujins"]:
                        self.bot.user_data["UserData"][str(ctx.author.id)]["nFavorites"]["Doujins"].append(doujin.id)
                        
                        emb = Embed(
                            description=f":white_check_mark: Added `{code}` to your favorites list!"
                            ).set_author(
                            name="NHentai Favorites",
                            url=f"https://nhentai.net/",
                            icon_url="https://cdn.discordapp.com/attachments/742481946030112779/759591081758949410/emote.png")
                        await edit.edit(content="", embed=emb)
                        return
                    
                    else:
                        emb = Embed(
                            description=f":x: `{code}` is already in your favorites list."
                            ).set_author(
                            name="NHentai Favorites",
                            url=f"https://nhentai.net/",
                            icon_url="https://cdn.discordapp.com/attachments/742481946030112779/759591081758949410/emote.png")
                        await edit.edit(content="", embed=emb)
            
            elif mode.lower() in ["remove", "r", "-"]:
                try:
                    code = int(code)
                except ValueError:
                    await ctx.send(":x: You didn't type a proper ID. Hint: It has to be a number!")
                    return
                    
                if code in self.bot.user_data["UserData"][str(ctx.author.id)]["nFavorites"]["Doujins"]:
                    self.bot.user_data["UserData"][str(ctx.author.id)]["nFavorites"]["Doujins"].remove(code)
                    
                    emb = Embed(
                        description=f":white_check_mark: Removed `{code}` from your favorites list!"
                        ).set_author(
                        name="NHentai Favorites",
                        url=f"https://nhentai.net/",
                        icon_url="https://cdn.discordapp.com/attachments/742481946030112779/759591081758949410/emote.png")
                    await ctx.send(embed=emb)
                
                else:
                    emb = Embed(
                        description=f":x: `{code}` is not in your favorites list."
                        ).set_author(
                        name="NHentai Favorites",
                        url=f"https://nhentai.net/",
                        icon_url="https://cdn.discordapp.com/attachments/742481946030112779/759591081758949410/emote.png")
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
            if not ctx.guild or ctx.guild.id in self.bot.user_data["UserData"][str(ctx.guild.owner_id)]["Settings"]["Unrestricted Servers"]:
                lolicon_allowed = True
        except KeyError:
            pass
        
        if ctx.guild and not ctx.channel.is_nsfw():
            await ctx.send(":x: This command cannot be used in a non-NSFW channel.")
            return

        if str(ctx.author.id) not in self.bot.user_data["UserData"]:
            self.bot.user_data["UserData"][str(ctx.author.id)] = {}
        if "nFavorites" not in self.bot.user_data["UserData"][str(ctx.author.id)]:
            self.bot.user_data["UserData"][str(ctx.author.id)]["nFavorites"] = {}
        if "Bookmarks" not in self.bot.user_data["UserData"][str(ctx.author.id)]["nFavorites"]:
            self.bot.user_data["UserData"][str(ctx.author.id)]["nFavorites"]["Bookmarks"] = {}
        if "Doujins" not in self.bot.user_data["UserData"][str(ctx.author.id)]["nFavorites"]:
            self.bot.user_data["UserData"][str(ctx.author.id)]["nFavorites"]["Doujins"] = []
        
        emb = Embed(
            color=0xEC2854)
        emb.set_author(
            name="NHentai Bookmarks",
            url=f"https://nhentai.net/",
            icon_url="https://cdn.discordapp.com/attachments/742481946030112779/759591081758949410/emote.png")

        nhentai_api = NHentai()
        edit = await ctx.send("<a:nreader_loading:810936543401213953>")
        
        bookmarks_list = list()
        remove_queue = list()  # It is very rare that a doujin would get deleted from NHentai
        for code, page in self.bot.user_data['UserData'][str(ctx.author.id)]['nFavorites']['Bookmarks'].items():
            if code not in self.bot.doujin_cache:
                doujin = nhentai_api._get_doujin(code)
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
                    bookmarks_list.append(f"`{'🟨' if is_lolicon else '⬛'} " \
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
        if str(ctx.author.id) not in self.bot.user_data["UserData"]:
            self.bot.user_data["UserData"][str(ctx.author.id)] = {}
        if "Settings" not in self.bot.user_data["UserData"][str(ctx.author.id)]:
            self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"] = {}
        if "Unrestricted Servers" not in self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]:
            self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["Unrestricted Servers"] = []
        
        if ctx.author.id != ctx.guild.owner_id:
            await ctx.send("❌ You must be the owner of the server to use this command.")
            return
        
        if not mode:
            if self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["Unrestricted Servers"]:
                message_part = []
                for i in self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["Unrestricted Servers"]:
                    guild = self.bot.get_guild(i)
                    if guild: message_part.append(f"ID: {i} ー Name: {guild.name}")
                    else: self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["Unrestricted Servers"].remove(i)
                    continue
                
                await ctx.send(embed=Embed(
                    title="Whitelisted Servers",
                    description="```"+"\n".join(message_part)+"```"
                ))
            
            else:
                await ctx.send("❌ You have no whitelisted servers.")
                return
        
        elif mode.lower() in ["add", "a", "+"]:
            if ctx.guild.id not in self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["Unrestricted Servers"]:
                self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["Unrestricted Servers"].append(ctx.guild.id)
            await ctx.send("✔ This server can now access doujins that contain underage characters.")
    
        elif mode.lower() in ["remove", "r", "-"]:
            if ctx.guild.id in self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["Unrestricted Servers"]:
                self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["Unrestricted Servers"].remove(ctx.guild.id)
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
            if not ctx.guild or ctx.guild.id in self.bot.user_data["UserData"][str(ctx.guild.owner_id)]["Settings"]["Unrestricted Servers"]:
                lolicon_allowed = True
        except KeyError:
            pass
    
        if str(ctx.author.id) not in self.bot.user_data["UserData"]:
            self.bot.user_data["UserData"][str(self.ctx.author.id)] = {}
        if "History" not in self.bot.user_data["UserData"][str(ctx.author.id)]:
            self.bot.user_data["UserData"][str(ctx.author.id)]["History"] = [True, []]
        
        if switch.lower() == "view":
            emb = Embed(
                color=0xEC2854)
            emb.set_author(
                name="NHentai History (BOT)",
                url="https://nhentai.net/",
                icon_url="https://cdn.discordapp.com/attachments/742481946030112779/759591081758949410/emote.png")

            nhentai_api = NHentai()
            edit = await ctx.send("<a:nreader_loading:810936543401213953>")
            
            history = list()
            for number, code in enumerate(self.bot.user_data['UserData'][str(ctx.author.id)]['History'][1]):
                if code not in self.bot.doujin_cache:
                    doujin = nhentai_api._get_doujin(code)
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
                        history.append(f"{number+1}: {doujin.id}{' ⚠' if is_lolicon else ''} ー {shorten(doujin.title, width=50, placeholder='...')}")
            
            emb.description = ("\n".join(history)) if history else "You don't have a history yet."
            await edit.edit(content="", embed=emb)
        
        elif switch.lower() == "clear":
            self.bot.user_data["UserData"][str(ctx.author.id)]["History"] = [
                self.bot.user_data["UserData"][str(ctx.author.id)]["History"][0], []]

            emb = Embed(
                color=0xEC2854)
            emb.set_author(
                name="NHentai History (BOT)",
                url=f"https://nhentai.net/",
                icon_url="https://cdn.discordapp.com/attachments/742481946030112779/759591081758949410/emote.png")
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
                icon_url="https://cdn.discordapp.com/attachments/742481946030112779/759591081758949410/emote.png")
            emb.description = f"{'✅' if self.bot.user_data['UserData'][str(ctx.author.id)]['History'][0] else '❎'} History toggled"

            await ctx.send(embed=emb)
    
    @command(aliases=["appendage"])
    @bot_has_permissions(
        send_messages=True,
        embed_links=True)
    async def search_appendage(self, ctx, *, appendage=""):
        if str(ctx.author.id) not in self.bot.user_data["UserData"]:
            self.bot.user_data["UserData"][str(ctx.author.id)] = {}
        if "Settings" not in self.bot.user_data["UserData"][str(ctx.author.id)]:
            self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"] = {}
        if "SearchAppendage" not in self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]:
            self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["SearchAppendage"] = ""
        
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
                await self.bot.wait_for("reaction_add", timeout=10,
                    check=lambda r, u: r.message.id==conf.id and u.id==ctx.author.id)
            except TimeoutError:
                await conf.edit(content="⌛❌ If you want to update your search appendage, please confirm within 10 seconds next time.", embed=None)
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
                await self.bot.wait_for("reaction_add", timeout=10,
                    check=lambda r, u: r.message.id==conf.id and u.id==ctx.author.id)
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

def setup(bot):
    bot.add_cog(Commands(bot))
