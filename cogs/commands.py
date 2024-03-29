from sys import exc_info
from re import search, findall
from asyncio import sleep, TimeoutError
from textwrap import shorten
from copy import deepcopy
from contextlib import suppress

from udpy import AsyncUrbanClient
from discord import ui, ButtonStyle, Forbidden
from discord.ext.commands import (
    Cog, bot_has_permissions, 
    bot_has_guild_permissions, 
    command, cooldown, max_concurrency)
from discord.ext.commands.core import is_owner
from discord.ext.commands.cooldowns import BucketType
from discord.ext.commands.errors import ExtensionNotLoaded
# from NHentai.nhentai_async import NHentaiAsync as NHentai, Doujin
from utils.NHentai_API.NHentai.nhentai_async import NHentaiAsync as NHentai, Doujin

from utils.classes import Embed
from cogs.classes import (
    ImagePageReader,
    SearchResultsBrowser)
from utils.misc import language_to_flag, restricted_tags
from cogs.localization import *

"""
# Experimental to Stable todo:

from cogs.Tclasses -> from cogs.classes
from cogs.Tlocalization -> from cogs.localization

experimental_prefix = "T" -> experimental_prefix = ""

class TCommands(Cog) -> class Commands(Cog)

bot.add_cog(TCommands(bot)) -> bot.add_cog(Commands(bot))
"""

newline = "\n"
experimental_prefix = ""  # One character only

class Commands(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.nhentai_api = NHentai(cloudflare_cookies=self.bot.auth["NHENTAI_CF_CLEARANCE"])
    
    @command(name=f"{experimental_prefix}test")
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    async def test(self, ctx):
        try:
            await ctx.send("Done (1/3).")
        except Exception:
            await ctx.author.send("(1/3) I can't send messages there.")
        
        try:
            await ctx.send(embed=Embed(description="Done (2/3)."))
        except Exception:
            await ctx.send("(2/3) I can't send embeds in here.")

        class TestButton(ui.View):
            def __init__(self):
                super().__init__(timeout=5)
                self.value = None
            
            @ui.button(label="Click to test.", style=ButtonStyle.primary, emoji="🔘", custom_id="test")
            async def continue_button(self, interaction, button):
                if interaction.user.id == ctx.author.id:
                    button.disabled = True
                    button.label = "Success!"
                    button.emoji = "✅"
                    await interaction.response.edit_message(embed=Embed(description="Button complete. (3/3)"), view=self)
                    self.value = True
                    self.stop()

            async def on_timeout(self):
                self.children[0].disabled = True
                self.children[0].label = "Timeout!"
                self.children[0].emoji = "❌"
                await self.message.edit(embed=Embed(description="Button timed out. (3/3)"), view=self)
                self.stop()
        
        view = TestButton()
        view.message = await ctx.send(embed=Embed(description="Waiting for button... (3/3)"), view=view)
        await view.wait()

        print(f"{ctx.author} ({ctx.author.id}) tested.")
       
    @command(
        name=f"{experimental_prefix}doujin_info", 
        aliases=[
            f"{experimental_prefix}code",
            f"{experimental_prefix}コード",  # JP alias
            f"{experimental_prefix}代碼"  # CN alias
        ])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    async def doujin_info(self, ctx, code="random"):
        # This tells the user that the command they are trying to use isn't translated yet.
        user_language = {"lang": self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["Language"]}
        if ctx.command.qualified_name not in localization[user_language["lang"]]:
            class Continue(ui.View):
                def __init__(self):
                    super().__init__(timeout=15)
                    self.value = None
                
                @ui.button(label=localization[user_language["lang"]]["language_not_available"]["button"], style=ButtonStyle.primary, emoji="▶️", custom_id="continue")
                async def continue_button(self, interaction, button):
                    if interaction.user.id == ctx.author.id:
                        await interaction.response.defer()
                        user_language["lang"] = "eng"
                        await self.message.delete()
                        self.value = True
                        self.stop()

                async def on_timeout(self):
                    await self.message.delete()
                    self.stop()

            emb = Embed(
                description=localization[user_language["lang"]]["language_not_available"]["description"]
            ).set_footer(text=localization[user_language["lang"]]["language_not_available"]["footer"])
            view = Continue()
            view.message = await ctx.send(embed=emb, view=view)
            await view.wait()
            if not view.value:
                return
        user_language = user_language["lang"]

        lolicon_allowed = False
        try:
            if not ctx.guild or ctx.guild.id in self.bot.user_data["UserData"][str(ctx.guild.owner_id)]["Settings"]["UnrestrictedServers"]:
                lolicon_allowed = True
        except KeyError:
            pass
        
        # Verify that `code` is a number
        try:
            if code.lower() not in ["random", "r"]:
                code = int(code)
                code = str(code)
        except ValueError:
            await ctx.send(embed=Embed(description=localization[user_language]["doujin_info"]["not_a_valid_id"]))
            return
        
        
        edit = await ctx.send(embed=Embed(description=f"{self.bot.get_emoji(810936543401213953)}"))

        if code.lower() not in ["random", "r"]:
            # Lookup
            try:
                doujin = await self.nhentai_api.get_doujin(code)
            except Exception as e:
                await edit.edit(embed=Embed(description=localization[user_language]["doujin_info"]["unexpected_error"]))
                error = exc_info()
                await self.bot.errorlog.send(error, ctx=ctx, event="Doujin Lookup")
                return

            if not doujin:
                return await edit.edit(embed=Embed(description=localization[user_language]["doujin_info"]["doujin_not_found"]))

            # Stop if it is a sensitive doujin and notify user of workaround
            if not lolicon_allowed and any([tag.name in restricted_tags for tag in doujin.tags]):
                await edit.edit(embed=Embed(description=localization[user_language]["doujin_info"]["is_lolicon"]))

                if not self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["NotificationsDue"]["LoliconViewingTip"]:
                    with suppress(Forbidden):
                        await ctx.author.send(localization[user_language]["notifications_due"]["lolicon_viewing_tip"])
                    
                    self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["NotificationsDue"]["LoliconViewingTip"] = True

                return

        else:
            # Get a random doujin
            while True:
                try:
                    doujin = await self.nhentai_api.get_random()
                except Exception as e:
                    await edit.edit(embed=Embed(description=localization[user_language]["doujin_info"]["unexpected_error"]))
                    error = exc_info()
                    await self.bot.errorlog.send(error, ctx=ctx, event="Doujin Lookup")
                    return

                if not lolicon_allowed and any([tag.name in restricted_tags for tag in doujin.tags]):
                    await sleep(1)
                    continue

                else:
                    break

        minimal_details = False 
        if ctx.guild and not ctx.channel.is_nsfw(): 
            minimal_details = True
        
        if minimal_details:
            emb = Embed(
                description=
                    f"ID: `{doujin.id}`\n"
                    f"{localization[user_language]['doujin_info']['fields']['title']}: {language_to_flag(doujin.languages)} `{shorten(doujin.title.pretty, width=256, placeholder='...')}`\n"
                    f"{localization[user_language]['doujin_info']['fields']['artists']}: `{', '.join([tag.name for tag in doujin.artists]) if doujin.artists else localization[user_language]['doujin_info']['fields']['not_provided']}`\n"
                    f"{localization[user_language]['doujin_info']['fields']['characters']}: `{', '.join([tag.name for tag in doujin.characters]) if doujin.characters else localization[user_language]['doujin_info']['fields']['original']}`\n"
                    f"{localization[user_language]['doujin_info']['fields']['parodies']}: `{', '.join([tag.name for tag in doujin.parodies]) if doujin.parodies else localization[user_language]['doujin_info']['fields']['original']}`\n"
                    f"{localization[user_language]['doujin_info']['fields']['tags']}:\n||`{shorten(str(', '.join([tag.name for tag in doujin.tags if tag.type == 'tag']) if [tag.name for tag in doujin.tags if tag.type == 'tag'] else localization[user_language]['doujin_info']['fields']['not_provided']), width=950, placeholder='...')}`||"
            ).set_footer(
                text=f"{localization[user_language]['doujin_info']['sfw']}"
            )

            emb.set_author(
                name=f"NHentai",
                icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")

            await edit.edit(content="", embed=emb)

            return

        emb = Embed()
        emb.add_field(
            name=localization[user_language]['doujin_info']['fields']['title'],
            inline=False,
            value=f"`{shorten(doujin.title.pretty, width=256, placeholder='...')}`"
        ).add_field(
            inline=False,
            name=localization[user_language]['doujin_info']['fields']['id/pages'],
            value=f"`{doujin.id}` - `{doujin.total_pages}`"
        ).add_field(
            inline=False,
            name=localization[user_language]['doujin_info']['fields']['date_uploaded'],
            value=f"<t:{int(doujin.upload_at.timestamp())}>"
        ).add_field(
            inline=False,
            name=localization[user_language]['doujin_info']['fields']['languages'],
            value=f"{language_to_flag(doujin.languages)} `{', '.join([localization[user_language]['doujin_info']['fields']['language_names'][tag.name] for tag in doujin.languages]) if doujin.languages else localization[user_language]['doujin_info']['fields']['not_provided']}`"
        ).add_field(
            inline=False,
            name=localization[user_language]['doujin_info']['fields']['artists'],
            value=f"`{', '.join([tag.name for tag in doujin.artists]) if doujin.artists else localization[user_language]['doujin_info']['fields']['not_provided']}`"
        ).add_field(
            inline=False,
            name=localization[user_language]['doujin_info']['fields']['characters'],
            value=f"`{', '.join([tag.name for tag in doujin.characters]) if doujin.characters else localization[user_language]['doujin_info']['fields']['original']}`"
        ).add_field(
            inline=False,
            name=localization[user_language]['doujin_info']['fields']['parodies'],
            value=f"`{', '.join([tag.name for tag in doujin.parodies]) if doujin.parodies else localization[user_language]['doujin_info']['fields']['original']}`"
        ).set_footer(
            text=f"⭐ {doujin.total_favorites}"
        )

        # Doujin count for tags
        tags_list = []
        for tag in [tag for tag in doujin.tags if tag.type == "tag"]:
            count = tag.count
            parse_count = list(str(count))
            if len(parse_count) < 4:
                tags_list.append(f"{localization[user_language]['fields']['tag_names'][tag.name] if tag.name in localization[user_language]['doujin_info']['fields']['tag_names'] else tag.name}[{count}]")
            elif len(parse_count) >= 4 and len(parse_count) <= 6:
                count = count/1000
                tags_list.append(f"{localization[user_language]['fields']['tag_names'][tag.name] if tag.name in localization[user_language]['doujin_info']['fields']['tag_names'] else tag.name}[{round(count, 1)}k]")
            elif len(parse_count) > 7:
                count = count/1000000
                tags_list.append(f"{localization[user_language]['fields']['tag_names'][tag.name] if tag.name in localization[user_language]['doujin_info']['fields']['tag_names'] else tag.name}[{round(count, 2)}m]")

        emb.add_field(
            inline=False,
            name=localization[user_language]["doujin_info"]["fields"]["tags"],
            value=f"```{shorten(str(', '.join(tags_list) if tags_list else localization[user_language]['doujin_info']['fields']['not_provided']), width=1018, placeholder='...')}```"
        )

        emb.set_author(
            name=f"NHentai",
            url=f"https://nhentai.net/g/{doujin.id}/",
            icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
        emb.set_thumbnail(url=doujin.images[0].src)

        print(f"[HRB] {ctx.author} ({ctx.author.id}) looked up `{doujin.id}`.")
        
        class DoujinInfoControl(ui.View):
            def __init__(self, bot):
                super().__init__(timeout=30)
                self.value = None
                self.bot = bot
            
            if not ctx.guild or (ctx.guild and not all([
            ctx.guild.me.guild_permissions.manage_channels, 
            ctx.guild.me.guild_permissions.manage_roles, 
            ctx.guild.me.guild_permissions.manage_messages])):
                @ui.button(label=localization[user_language]["doujin_info"]["need_permissions"], style=ButtonStyle.primary, emoji=self.bot.get_emoji(853684136379416616), custom_id="button1", disabled=True)
                async def read_button(self, interaction, button):
                    return

            else:
                @ui.button(label=localization[user_language]["doujin_info"]["read"], style=ButtonStyle.primary, emoji=self.bot.get_emoji(853684136379416616), custom_id="button1")
                async def read_button(self, interaction, button):
                    if interaction.user.id == ctx.author.id:
                        await interaction.response.defer()
                        
                        if not ctx.guild or (ctx.guild and not all([
                            ctx.guild.me.guild_permissions.manage_channels, 
                            ctx.guild.me.guild_permissions.manage_roles, 
                            ctx.guild.me.guild_permissions.manage_messages])):
                            
                            button.disabled = True
                            button.label = localization[user_language]["doujin_info"]["need_permissions"]
                            await view.message.edit(embed=emb, view=self)

                        else:
                            emb.set_thumbnail(
                                url=doujin.images[0].src)
                            emb.set_image(url=None)
                            button.disabled = True
                            button.label = localization[user_language]["doujin_info"]["opened"]
                            self.expand_thumbnail.disabled = True
                            await view.message.edit(embed=emb, view=self)

                            self.stop()

                            session = ImagePageReader(self.bot, ctx, doujin.images, doujin.title.pretty, str(doujin.id), user_language=user_language)
                            response = await session.setup()
                            if response:
                                await session.start()

            @ui.button(label=localization[user_language]["doujin_info"]["expand_thumbnail"], style=ButtonStyle.secondary, emoji=self.bot.get_emoji(853684136433942560), custom_id="button2")
            async def expand_thumbnail(self, interaction, button):
                if interaction.user.id == ctx.author.id:
                    if not emb.image:
                        emb.set_image(url=emb.thumbnail.url)
                        emb.set_thumbnail(url=None)
                        thumbnail_size = localization[user_language]["doujin_info"]["minimize_thumbnail"]

                    elif not emb.thumbnail:
                        emb.set_thumbnail(url=emb.image.url)
                        emb.set_image(url=None)
                        thumbnail_size = localization[user_language]["doujin_info"]["expand_thumbnail"]

                    button.label = thumbnail_size
                    await interaction.response.edit_message(embed=emb, view=self)

            async def on_timeout(self):
                for component in self.children:
                    component.disabled = True
                emb.set_thumbnail(url=doujin.images[0].src)
                emb.set_image(url=None)
                await view.message.edit(embed=emb, view=self)
                self.stop()
        
        view = DoujinInfoControl(self.bot)
        view.message = await edit.edit(embed=emb, view=view)
        await view.wait()
    

    @command(
        name=f"{experimental_prefix}search_doujins",
        aliases=[
            f"{experimental_prefix}search",
            f"{experimental_prefix}サーチ",  # JP alias
            f"{experimental_prefix}搜索",  # CN alias
        ])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    async def search_doujins(self, ctx, *, query: str = ""):
        # This tells the user that the command they are trying to use isn't translated yet.
        user_language = {"lang": self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["Language"]}
        if ctx.command.qualified_name not in localization[user_language["lang"]]:
            class Continue(ui.View):
                def __init__(self):
                    super().__init__(timeout=15)
                    self.value = None
                
                @ui.button(label=localization[user_language["lang"]]["language_not_available"]["button"], style=ButtonStyle.primary, emoji="▶️", custom_id="continue")
                async def continue_button(self, interaction, button):
                    if interaction.user.id == ctx.author.id:
                        await interaction.response.defer()

                        user_language["lang"] = "eng"
                        await self.message.delete()
                        self.value = True
                        self.stop()

                async def on_timeout(self):
                    await self.message.delete()
                    self.stop()

            emb = Embed(
                description=localization[user_language["lang"]]["language_not_available"]["description"]
            ).set_footer(text=localization[user_language["lang"]]["language_not_available"]["footer"])
            view = Continue()
            view.message = await ctx.send(embed=emb, view=view)
            await view.wait()
            if not view.value:
                return
        user_language = user_language["lang"]

        lolicon_allowed = False
        try:
            if not ctx.guild or ctx.guild.id in self.bot.user_data["UserData"][str(ctx.guild.owner_id)]["Settings"]["UnrestrictedServers"]:
                lolicon_allowed = True
        except KeyError:
            pass
        
        
        if "--noappend" in query:
            query = query.replace("--noappend", "")
            appendage = ""
        elif self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["SearchAppendage"] != " ":
            appendage = self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["SearchAppendage"]
        else:
            appendage = ""
        
        if "--showrestricted" in query or lolicon_allowed:
            query = query.replace("--showrestricted", "")
            restricted_appendage = ""
        else:
            restricted_appendage = " ".join([f"-\"{tag}\"" for tag in restricted_tags])

        conf = await ctx.send(embed=Embed(
            description=localization[user_language]['search_doujins']['searching'].format(query=query, appendage=appendage+" "+restricted_appendage)))

        page_raw = search(r"\-\-page=[0-9]+", query)
        if page_raw: 
            page = int(page_raw.group().split("=")[1])
            if not page:
                return await conf.edit(content="", embed=Embed(
                    title=localization[user_language]['search_doujins']['invalid_page']['title'],
                    description=localization[user_language]['search_doujins']['invalid_page']['description']))
            else:
                query = query.replace(page_raw.group(), '').strip(' ')
        else: 
            page = 1
            
        sort_raw = search(r"\-\-sort=(?:(today)|(week)|(month)|(popular)|(recent))", query)
        if sort_raw: 
            value = str(sort_raw.group().split("=")[1])
            if value not in ['today', 'week', 'month', 'popular', 'recent']:
                return await conf.edit(content="", embed=Embed(
                    title=localization[user_language]['search_doujins']['invalid_sort']['title'],
                    description=localization[user_language]['search_doujins']['invalid_sort']['description']))
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
                title=localization[user_language]['search_doujins']['too_broad']['title'],
                description=localization[user_language]['search_doujins']['too_broad']['description']))
            
            return

        try:
            results = await self.nhentai_api.search(query=f"{query} {appendage} {restricted_appendage}", sort=sort, page=page)
        except Exception:
            await conf.edit(embed=Embed(description=localization[user_language]['search_doujins']['unexpected_error']))
            error = exc_info()
            await self.bot.errorlog.send(error, ctx=ctx, event="Doujin Search")
            return

        minimal_details = False 
        if ctx.guild and not ctx.channel.is_nsfw(): 
            minimal_details = True

        if isinstance(results, Doujin):
            await conf.delete()
            ctx.message.content = f"n!code {results.id}"
            await self.bot.process_commands(ctx.message)
            return
        
        if not results.doujins:
            newline = "\n"
            await conf.edit(content='', embed=Embed(
                title = localization[user_language]['search_doujins']['no_results']['title'],
                description = f"{newline+localization[user_language]['search_doujins']['no_results']['description']['appendage'] if appendage else ''}"
                              f"{newline+localization[user_language]['search_doujins']['no_results']['description']['page'] if page_raw else ''}"
                              f"{newline+localization[user_language]['search_doujins']['no_results']['description']['restricted_tags'] if any([tag in query for tag in restricted_tags]) and not lolicon_allowed else ''}"))
            return
        
        message_part = []
        doujins = []
        thumbnail_url = self.bot.user.avatar.url
        for ind, dj in enumerate(results.doujins):
            if not lolicon_allowed and any([tag.name in restricted_tags for tag in dj.tags]):
                message_part.append(localization[user_language]['search_doujins']['contains_restricted_tags'])
            else:
                message_part.append(
                    f"__`{str(dj.id).ljust(7)}`__ | "
                    f"{language_to_flag(dj.languages)} | "
                    f"{shorten(dj.title.pretty, width=50, placeholder='...')}")
                if thumbnail_url == self.bot.user.avatar.url:
                    thumbnail_url = dj.cover.src
            
        emb = Embed(
            title=localization[user_language]['search_doujins']['search_results']['title'],
            description=localization[user_language]['search_doujins']['search_results']['description'].format(
                page=page, pages=results.total_pages if results.total_pages else 1, approximate=results.total_results, results='\n'.join(message_part))
        ).set_author(
            name="NHentai",
            url="https://nhentai.net/",
            icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1"
        ).set_thumbnail(url=thumbnail_url if not minimal_details else None)
        
        print(f"[HRB] {ctx.author} ({ctx.author.id}) searched for [{query if query else ''}{' ' if query and appendage else ''}{appendage if appendage else ''}].")
        
        class Interactive(ui.View):
            def __init__(self, bot):
                super().__init__(timeout=15)
                self.bot = bot
                self.value = None
            
            @ui.button(label=localization[user_language]['search_doujins']['start_interactive'], style=ButtonStyle.primary, emoji=self.bot.get_emoji(853674277416206387), custom_id="button1")
            async def interactive_mode(self, interaction, button):
                if interaction.user.id == ctx.author.id:
                    await interaction.response.defer()
                    self.stop()

                    interactive = SearchResultsBrowser(self.bot, ctx, results.doujins, msg=conf, lolicon_allowed=lolicon_allowed, minimal_details=minimal_details, user_language=user_language)
                    await interactive.start(ctx)

            async def on_timeout(self):
                self.children[0].disabled = True
                await view.message.edit(embed=emb, view=self)
                self.stop()

        view = Interactive(self.bot)
        view.message = await conf.edit(embed=emb, view=view)
        await view.wait()


    @command(
        name=f"{experimental_prefix}popular",
        aliases=[
            f"{experimental_prefix}pop",
            f"{experimental_prefix}ポップ",  # JP alias
            f"{experimental_prefix}人氣",  # CN alias
        ])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    async def popular(self, ctx):
        # This tells the user that the command they are trying to use isn't translated yet.
        user_language = {"lang": self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["Language"]}
        if ctx.command.qualified_name not in localization[user_language["lang"]]:
            class Continue(ui.View):
                def __init__(self):
                    super().__init__(timeout=15)
                    self.value = None
                
                @ui.button(label=localization[user_language["lang"]]["language_not_available"]["button"], style=ButtonStyle.primary, emoji="▶️", custom_id="continue")
                async def continue_button(self, interaction, button):
                    if interaction.user.id == ctx.author.id:
                        await interaction.response.defer()

                        user_language["lang"] = "eng"
                        await self.message.delete()
                        self.value = True
                        self.stop()

                async def on_timeout(self):
                    await self.message.delete()
                    self.stop()

            emb = Embed(
                description=localization[user_language["lang"]]["language_not_available"]["description"]
            ).set_footer(text=localization[user_language["lang"]]["language_not_available"]["footer"])
            view = Continue()
            view.message = await ctx.send(embed=emb, view=view)
            await view.wait()
            if not view.value:
                return
        user_language = user_language["lang"]

        if ctx.guild and not ctx.channel.is_nsfw():
            await ctx.send(embed=Embed(
                description="❌ This command cannot be used in a non-NSFW channel."))

            return

        lolicon_allowed = False
        try:
            if not ctx.guild or ctx.guild.id in self.bot.user_data["UserData"][str(ctx.guild.owner_id)]["Settings"]["UnrestrictedServers"]:
                lolicon_allowed = True
        except KeyError:
            pass
        
        conf = await ctx.send(embed=Embed(
            description=f"{self.bot.get_emoji(810936543401213953)} Loading..."
        ).set_footer(text="This should take no more than 5 seconds."))

        
        results = await self.nhentai_api.get_popular_now()

        message_part = []
        doujins = []
        for ind, dj in enumerate(results.doujins):
            dj = await self.nhentai_api.get_doujin(dj.id)            
            doujins.append(dj)
            
            tags = [tag.name for tag in dj.tags if tag.type == "tag"]
            if not lolicon_allowed and any([tag in restricted_tags for tag in tags]):
                message_part.append("__`       `__ | ⚠🚫 | Contains restricted tags.")
            else:
                message_part.append(
                    f"__`{str(dj.id).ljust(7)}`__ | "
                    f"{language_to_flag(dj.languages)} | "
                    f"{shorten(dj.title.pretty, width=50, placeholder='...')}")

        minimal_details = False 
        if ctx.guild and not ctx.channel.is_nsfw(): 
            minimal_details = True

        emb = Embed(
            title=f"<:npopular:853883174455214102> **Popular Now**",
            description=f"\n"+('\n'.join(message_part)))
        emb.set_author(
            name="NHentai",
            url="https://nhentai.net/",
            icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")

        class Interactive(ui.View):
            def __init__(self, bot):
                super().__init__(timeout=15)
                self.bot = bot
                self.value = None
            
            @ui.button(label=localization[user_language]['search_doujins']['start_interactive'], style=ButtonStyle.primary, emoji=self.bot.get_emoji(853674277416206387), custom_id="button1")
            async def interactive_mode(self, interaction, button):
                if interaction.user.id == ctx.author.id:
                    await interaction.response.defer()
                    self.stop()
                    
                    interactive = SearchResultsBrowser(self.bot, ctx, results.doujins, msg=conf, lolicon_allowed=lolicon_allowed, minimal_details=minimal_details, user_language=user_language)
                    await interactive.start(ctx)

            async def on_timeout(self):
                self.children[0].disabled = True
                await view.message.edit(embed=emb, view=self)
                self.stop()

        # class Interactive(ui.View):
        #     def __init__(self, bot):
        #         super().__init__()
        #         self.bot = bot
        #         self.add_item(ui.Button(label="Start Interactive (out of order)", style=ButtonStyle.danger, emoji=self.bot.get_emoji(853674277416206387), custom_id="button1", disabled=True))

        view = Interactive(self.bot)
        # out of order
        view.message = await conf.edit(embed=emb, view=Interactive(self.bot))
        await view.wait()
        
    @command(
        name=f"{experimental_prefix}whitelist",
        aliases=[
            f"{experimental_prefix}whl",
            f"{experimental_prefix}ホワイトリスト",  # JP alias
            f"{experimental_prefix}白名單"  # CN alias
        ])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    async def whitelist(self, ctx, mode=None):
        # This tells the user that the command they are trying to use isn't translated yet.
        user_language = {"lang": self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["Language"]}
        if ctx.command.qualified_name not in localization[user_language["lang"]]:
            class Continue(ui.View):
                def __init__(self):
                    super().__init__(timeout=15)
                    self.value = None
                
                @ui.button(label=localization[user_language["lang"]]["language_not_available"]["button"], style=ButtonStyle.primary, emoji="▶️", custom_id="continue")
                async def continue_button(self, interaction, button):
                    if interaction.user.id == ctx.author.id:
                        await interaction.response.defer()

                        user_language["lang"] = "eng"
                        await self.message.delete()
                        self.value = True
                        self.stop()

                async def on_timeout(self):
                    await self.message.delete()
                    self.stop()

            emb = Embed(
                description=localization[user_language["lang"]]["language_not_available"]["description"]
            ).set_footer(text=localization[user_language["lang"]]["language_not_available"]["footer"])
            view = Continue()
            view.message = await ctx.send(embed=emb, view=view)
            await view.wait()
            if not view.value:
                return
        user_language = user_language["lang"]

        if not ctx.guild:
            await ctx.send(embed=Embed(
                description=":x: This command must be run in a server. Consider making a private one."))

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

            class Agree(ui.View):
                def __init__(self, bot):
                    super().__init__(timeout=15)
                    self.value = None
                    self.bot = bot
                
                @ui.button(label="Accept", style=ButtonStyle.secondary, emoji="✅", custom_id="button1")
                async def accept_button(self, interaction, button):
                    if interaction.user.id == ctx.author.id:
                        self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["UnrestrictedServers"].append(ctx.guild.id)

                        emb.description="✅ This server can now access doujins that contain underage characters."
                        emb.set_footer(text=None)
                        button.label = "Accepted"
                        for component in self.children:
                            component.disabled = True
                        await interaction.response.edit_message(embed=emb, view=self)
                        self.stop()

                @ui.button(label="Decline", style=ButtonStyle.primary, emoji="❌", custom_id="button2")
                async def decline_button(self, interaction, button):
                    if interaction.user.id == ctx.author.id:
                        emb.description="❌ Operation cancelled."
                        emb.set_footer(text=None)
                        button.label = "Declined"
                        for component in self.children:
                            component.disabled = True
                        await interaction.response.edit_message(embed=emb, view=self)
                        self.stop()

                async def on_timeout(self):
                    for component in self.children:
                        component.disabled = True
                    await view.message.edit(embed=emb, view=self)
                    self.stop()

            view = Agree(self.bot)
            view.message = await ctx.send(embed=emb, view=view)
            await view.wait()

        elif mode.lower() in ["remove", "r", "-"]:
            if ctx.guild.id in self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["UnrestrictedServers"]:
                self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["UnrestrictedServers"].remove(ctx.guild.id)
                await ctx.send(embed=Embed(
                    title="Server Whitelisting",
                    description="✅ This server can no longer access doujins that contain underage characters."))
            else:
                await ctx.send(embed=Embed(
                    title="Server Whitelisting",
                    description="❌ This server is not in the whitelist."))
        
        else:
            await ctx.send(embed=Embed(
                color=0xFF0000,
                description="You didn't specify a mode. Valid modes are `add/a/+` and `remove/r/-`."))

    @command(
        name=f"{experimental_prefix}lists",
        aliases=[
            f"{experimental_prefix}list",
            f"{experimental_prefix}library",
            f"{experimental_prefix}lib", 
            f"{experimental_prefix}l",
            f"{experimental_prefix}リスト"  # JP alias
            f"{experimental_prefix}列表"  # CN alias
        ])
    @bot_has_permissions(
        send_messages=True,
        embed_links=True)
    async def lists(self, ctx, name=None, mode=None, code=None):
        # This tells the user that the command they are trying to use isn't translated yet.
        user_language = {"lang": self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["Language"]}
        if ctx.command.qualified_name not in localization[user_language["lang"]]:
            class Continue(ui.View):
                def __init__(self):
                    super().__init__(timeout=15)
                    self.value = None
                
                @ui.button(label=localization[user_language["lang"]]["language_not_available"]["button"], style=ButtonStyle.primary, emoji="▶️", custom_id="continue")
                async def continue_button(self, interaction, button):
                    if interaction.user.id == ctx.author.id:
                        await interaction.response.defer()

                        user_language["lang"] = "eng"
                        await self.message.delete()
                        self.value = True
                        self.stop()

                async def on_timeout(self):
                    await self.message.delete()
                    self.stop()

            emb = Embed(
                description=localization[user_language["lang"]]["language_not_available"]["description"]
            ).set_footer(text=localization[user_language["lang"]]["language_not_available"]["footer"])
            view = Continue()
            view.message = await ctx.send(embed=emb, view=view)
            await view.wait()
            if not view.value:
                return
        user_language = user_language["lang"]

        minimal_details = False 
        if ctx.guild and not ctx.channel.is_nsfw(): 
            minimal_details = True

        lolicon_allowed = False
        try:
            if not ctx.guild or ctx.guild.id in self.bot.user_data["UserData"][str(ctx.guild.owner_id)]["Settings"]["UnrestrictedServers"]:
                lolicon_allowed = True
        except KeyError:
            pass

        async def load_list(list_items):
            if "0" not in list_items:
                if isinstance(list_items, list):
                    list_items.append("0")
                elif isinstance(list_items, dict):
                    list_items.update({"placeholder":"1"})

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
            
            doujins = []
            passed_placeholder = False
            for ind, code in enumerate(list_items):
                if passed_placeholder:
                    ind -= 1

                bookmark_page = None
                if isinstance(list_items, dict):  # Is the Bookmarks list
                    bookmark_page = list_items[code]

                if code == "placeholder" or code == 0 or code == "0":
                    passed_placeholder = True
                    continue

                doujin = await self.nhentai_api.get_doujin(code)
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

            class Interactive(ui.View):
                def __init__(self, bot):
                    super().__init__(timeout=15)
                    self.bot = bot
                    self.value = None
                
                @ui.button(label=localization[user_language]['search_doujins']['start_interactive'], style=ButtonStyle.primary, emoji=self.bot.get_emoji(853674277416206387), custom_id="button1")
                async def interactive_mode(self, interaction, button):
                    if interaction.user.id == ctx.author.id:
                        await interaction.response.defer()
                        self.stop()

                        interactive = SearchResultsBrowser(self.bot, ctx, doujins, msg=self.message, lolicon_allowed=lolicon_allowed, minimal_details=minimal_details, user_language=user_language)
                        await interactive.start(ctx)

                async def on_timeout(self):
                    self.children[0].disabled = True
                    await view.message.edit(embed=emb, view=self)
                    self.stop()

            view = Interactive(self.bot)
            view.message = await edit.edit(embed=emb, view=view)
            await view.wait()
            return

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
            for _sys_category, _lists in deepcopy(self.bot.user_data["UserData"][str(ctx.author.id)]["Lists"]).items():
                for _list_full_name in deepcopy(_lists).keys():
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

                if not code:
                    await ctx.send(embed=Embed(description="❌ Provide a code, damnit!"))
                    return

                try:
                    code = int(code)
                    code = str(code)
                except ValueError:
                    await ctx.send(embed=Embed(description="❌ You didn't type a proper ID. Come on, numbers!"))
                    return

                
                doujin = await self.nhentai_api.get_doujin(code)

                if not doujin:
                    await ctx.send(embed=Embed(description="🔎❌ I did not find a doujin with that ID."))
                    return

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
                    title="Clearing Favorites",
                    description=f"Are you sure you want to clear this list?\n"
                                f"\n"
                                f"**Name**: {list_name}\n"
                                f"{'**Alias**: '+alias_name+newline if alias_name else ''}"
                                f"**Number of doujins inside**: `{len(target_list)}`")

                class Confirm(ui.View):
                    def __init__(self, bot):
                        super().__init__(timeout=15)
                        self.bot = bot
                        self.value = None
                    
                    @ui.button(label="Continue", style=ButtonStyle.danger, custom_id="button1")
                    async def confirm_button(self, interaction, button):
                        if interaction.user.id == ctx.author.id:
                            self.bot.user_data["UserData"][str(ctx.author.id)]["Lists"][sys_category][full_name] = ["0"]
                            emb = Embed(description=f"✅ Cleared/reset **`{list_name}`** (removed **`{len(target_list)}`** doujins).")
                            await interaction.response.edit_message(embed=emb, view=None)
                            self.stop()

                    @ui.button(label="Cancel", style=ButtonStyle.secondary, custom_id="button2")
                    async def cancel_button(self, interaction, button):
                        if interaction.user.id == ctx.author.id:
                            emb = Embed(description=f"❌ Operation cancelled.")
                            await interaction.response.edit_message(embed=emb, view=None)
                            self.stop()

                    async def on_timeout(self):
                        for component in self.children:
                            component.disabled = True
                        await self.message.edit(embed=emb, view=self)
                        self.stop()

                view = Confirm(self.bot)
                view.message = await ctx.send(embed=emb, view=view)
                await view.wait()
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

                if not code:
                    await ctx.send(embed=Embed(description="❌ Provide a code, damnit!"))
                    return

                try:
                    code = int(code)
                    code = str(code)
                except ValueError:
                    await ctx.send(embed=Embed(description="❌ You didn't type a proper ID. Come on, numbers!"))
                    return

                
                doujin = await self.nhentai_api.get_doujin(code)

                if not doujin:
                    await ctx.send(embed=Embed(description="🔎❌ I did not find a doujin with that ID."))
                    return

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
                    title="Clearing Read Later",
                    description=f"Are you sure you want to clear this list?\n"
                                f"\n"
                                f"**Name**: {list_name}\n"
                                f"{'**Alias**: '+alias_name+newline if alias_name else ''}"
                                f"**Number of doujins inside**: `{len(target_list)}`")
                                
                class Confirm(ui.View):
                    def __init__(self, bot):
                        super().__init__(timeout=15)
                        self.bot = bot
                        self.value = None
                    
                    @ui.button(label="Continue", style=ButtonStyle.danger, custom_id="button1")
                    async def confirm_button(self, interaction, button):
                        if interaction.user.id == ctx.author.id:
                            self.bot.user_data["UserData"][str(ctx.author.id)]["Lists"][sys_category][full_name] = ["0"]
                            emb = Embed(description=f"✅ Cleared/reset **`{list_name}`** (removed **`{len(target_list)}`** doujins).")
                            await interaction.response.edit_message(embed=emb, view=None)
                            self.stop()

                    @ui.button(label="Cancel", style=ButtonStyle.secondary, custom_id="button2")
                    async def cancel_button(self, interaction, button):
                        if interaction.user.id == ctx.author.id:
                            emb = Embed(description=f"❌ Operation cancelled.")
                            await interaction.response.edit_message(embed=emb, view=None)
                            self.stop()

                    async def on_timeout(self):
                        for component in self.children:
                            component.disabled = True
                        await self.message.edit(embed=emb, view=self)
                        self.stop()

                view = Confirm(self.bot)
                view.message = await ctx.send(embed=emb, view=view)
                await view.wait()
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
                        description="❌ That doujin is not in that list."))
                    return

                target_list.pop(code)
                await ctx.send(embed=Embed(description=f"✅ Removed `{code}` from `{list_name}`."))
                return

            elif mode in ["clear", "c"]:
                emb = Embed(
                    title="Clearing Bookmarks",
                    description=f"Are you sure you want to clear this list?\n"
                                f"\n"
                                f"**Name**: {list_name}\n"
                                f"{'**Alias**: '+alias_name+newline if alias_name else ''}"
                                f"**Number of doujins inside**: `{len(target_list)}`")

                class Confirm(ui.View):
                    def __init__(self, bot):
                        super().__init__(timeout=15)
                        self.bot = bot
                        self.value = None
                    
                    @ui.button(label="Continue", style=ButtonStyle.danger, custom_id="button1")
                    async def confirm_button(self, interaction, button):
                        if interaction.user.id == ctx.author.id:
                            self.bot.user_data["UserData"][str(ctx.author.id)]["Lists"][sys_category][full_name] = {"placeholder": 1}
                            emb = Embed(description=f"✅ Cleared/reset **`{list_name}`** (removed **`{len(target_list)}`** doujins).")
                            await interaction.response.edit_message(embed=emb, view=None)
                            self.stop()

                    @ui.button(label="Cancel", style=ButtonStyle.secondary, custom_id="button2")
                    async def cancel_button(self, interaction, button):
                        if interaction.user.id == ctx.author.id:
                            emb = Embed(description=f"❌ Operation cancelled.")
                            await interaction.response.edit_message(embed=emb, view=None)
                            self.stop()

                    async def on_timeout(self):
                        for component in self.children:
                            component.disabled = True
                        await self.message.edit(embed=emb, view=self)
                        self.stop()

                view = Confirm(self.bot)
                view.message = await ctx.send(embed=emb, view=view)
                await view.wait()
                return

        elif name in ["History", "his"]:
            if mode and mode not in ["remove", "r", "-", "clear", "c", "toggle", "t"]:
                await ctx.send(embed=Embed(description="❌ Invalid mode passed. Valid modes are `remove/r/-`, `clear/c`, and `toggle/t`."))
                return
            
            if not mode:
                await load_list(target_list['list'])
                return

            elif mode in ["remove", "r", "-"]:
                if code not in target_list["list"]:
                    await ctx.send(embed=Embed(
                        description="❌ That doujin is not in that list."))
                    return

                target_list["list"].remove(code)
                await ctx.send(embed=Embed(description=f"✅ Removed `{code}` from `{list_name}`."))
                return

            elif mode in ["clear", "c"]:
                emb = Embed(
                    title="Clearing History",
                    description=f"Are you sure you want to clear this list?\n"
                                f"\n"
                                f"**Name**: {list_name}\n"
                                f"{'**Alias**: '+alias_name+newline if alias_name else ''}"
                                f"**Number of doujins inside**: `{len(target_list)}`")
                                
                class Confirm(ui.View):
                    def __init__(self, bot):
                        super().__init__(timeout=15)
                        self.bot = bot
                        self.value = None
                    
                    @ui.button(label="Continue", style=ButtonStyle.danger, custom_id="button1")
                    async def confirm_button(self, interaction, button):
                        if interaction.user.id == ctx.author.id:
                            self.bot.user_data["UserData"][str(ctx.author.id)]["Lists"][sys_category][full_name] = ["0"]
                            emb = Embed(description=f"✅ Cleared/reset **`{list_name}`** (removed **`{len(target_list)}`** doujins).")
                            await interaction.response.edit_message(embed=emb, view=None)
                            self.stop()

                    @ui.button(label="Cancel", style=ButtonStyle.secondary, custom_id="button2")
                    async def cancel_button(self, interaction, button):
                        if interaction.user.id == ctx.author.id:
                            emb = Embed(description=f"❌ Operation cancelled.")
                            await interaction.response.edit_message(embed=emb, view=None)
                            self.stop()

                    async def on_timeout(self):
                        for component in self.children:
                            component.disabled = True
                        await self.message.edit(embed=emb, view=self)
                        self.stop()

                view = Confirm(self.bot)
                view.message = await ctx.send(embed=emb, view=view)
                await view.wait()
                return
        
            elif mode in ["toggle", "t"]:
                target_list["enabled"] = not target_list["enabled"]
                await ctx.send(embed=Embed(description=f"✅ History is now {'`On`' if target_list['enabled'] else '`Off`'}."))
                return

        else:  # Queried list is custom
            if mode in [
                "create", "cr", "!", 
                "rename", "rn", ">", 
                "delete", "del", 
                "add", "a", "+", 
                "remove", "r", "-", 
                "clear", "c", 
                None
            ]:
                if mode in ["create", "cr", "!"]:
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
                    for _lists in deepcopy(self.bot.user_data["UserData"][str(ctx.author.id)]["Lists"]).values():
                        for _list_full_name in deepcopy(_lists).keys():
                            if "|*n*|" in _list_full_name:
                                parts = _list_full_name.split("|*n*|")
                                _list_name = parts[0]
                                _alias = parts[1]
                            else:
                                _list_name = _list_full_name
                                _alias = None

                            if input_aliases[0] in [_list_name, _alias]:
                                await ctx.send(embed=Embed(description=f"❌ A list with the name or alias **`{input_aliases[0]}`** already exists."))
                                return
                            elif len(input_aliases) == 2 and input_aliases[1] in [_list_name, _alias]:
                                await ctx.send(embed=Embed(description=f"❌ A list with the name or alias **`{input_aliases[1]}`** already exists."))
                                return

                    sys_name = "|*n*|".join(input_aliases)

                    self.bot.user_data["UserData"][str(ctx.author.id)]["Lists"]["Custom"][sys_name] = ["0"]
                    await ctx.send(embed=Embed(description=f"✅ Created a new list named **`{input_aliases[0]}`**{' with the alias **`'+input_aliases[1]+'`**' if len(input_aliases)==2 else ''}."))
                
                    if code:
                        try:
                            code = int(code)
                            code = str(code)
                        except ValueError:
                            await ctx.send(embed=Embed(description="❌ You didn't type a proper ID. Come on, numbers!"))
                            return

                        
                        doujin = await self.nhentai_api.get_doujin(code)

                        if not doujin:
                            await ctx.send(embed=Embed(description="🔎❌ I did not find a doujin with that ID."))
                            return

                        if not lolicon_allowed and any([tag in restricted_tags for tag in doujin.tags]):
                            await ctx.send(content="⚠❌ This doujin contains lolicon/shotacon content and cannot be shown publically.")
                            return

                        self.bot.user_data["UserData"][str(ctx.author.id)]["Lists"]["Custom"][sys_name].append(code)
                        await ctx.send(embed=Embed(description=f"✅ Added **`{code}`** to **`{input_aliases[0]}`**."))
                
                    return

                elif mode in ["rename", "rn", ">"]:
                    saved_list = deepcopy(target_list)

                    input_aliases = code.split("//")
                    if len(input_aliases[0]) > 25 or \
                        (len(input_aliases)==2 and len(input_aliases[1]) > 25):
                        await ctx.send(embed=Embed(description="❌ Your list name or alias cannot exceed 25 characters long."))
                        return

                    if len(input_aliases) > 2:
                        await ctx.send(embed=Embed(description="❌ You can only give your list one alias."))
                        return

                    # Check for existing lists and aliases
                    for _lists in deepcopy(self.bot.user_data["UserData"][str(ctx.author.id)]["Lists"]).values():
                        for _list_full_name in deepcopy(_lists).keys():
                            if "|*n*|" in _list_full_name:
                                parts = _list_full_name.split("|*n*|")
                                _list_name = parts[0]
                                _alias = parts[1]
                            else:
                                _list_name = _list_full_name
                                _alias = None

                            if input_aliases[0] in [_list_name, _alias] and _list_full_name != full_name:
                                await ctx.send(embed=Embed(description=f"❌ A list with the name or alias **`{input_aliases[0]}`** already exists."))
                                return
                            elif len(input_aliases) == 2 and input_aliases[1] in [_list_name, _alias] and _list_full_name != full_name:
                                await ctx.send(embed=Embed(description=f"❌ A list with the name or alias **`{input_aliases[1]}`** already exists."))
                                return

                    sys_name = "|*n*|".join(input_aliases)
                    self.bot.user_data["UserData"][str(ctx.author.id)]["Lists"]["Custom"].pop(full_name)
                    self.bot.user_data["UserData"][str(ctx.author.id)]["Lists"]["Custom"][sys_name] = saved_list
                    await ctx.send(embed=Embed(description=f"✅ Renamed list **`{list_name}`** to **`{input_aliases[0]}`**{' with the alias **`'+input_aliases[1]+'`**' if len(input_aliases)==2 else ''}."))
                
                    return

                elif mode in ["delete", "del"]:
                    if not len(target_list):
                        self.bot.user_data["UserData"][str(ctx.author.id)]["Lists"]["Custom"].pop(full_name)
                        await ctx.send(embed=Embed(description=f"✅ Deleted list **`{list_name}`** (empty list)."))
                        return

                    else:
                        emb = Embed(
                            title="Deleting An Occupied List",
                            description=f"Are you sure you want to delete this list?\n"
                                        f"\n"
                                        f"**Name**: **`{list_name}`**\n"
                                        f"{'**Alias**: '+alias_name+newline if alias_name else ''}"
                                        f"**Number of doujins inside**: **`{len(target_list)}`**")

                        class Confirm(ui.View):
                            def __init__(self, bot):
                                super().__init__(timeout=15)
                                self.bot = bot
                                self.value = None
                            
                            @ui.button(label="Continue", style=ButtonStyle.danger, custom_id="button1")
                            async def confirm_button(self, interaction, button):
                                if interaction.user.id == ctx.author.id:
                                    self.bot.user_data["UserData"][str(ctx.author.id)]["Lists"][sys_category].pop(full_name)
                                    emb = Embed(description=f"✅ Deleted **`{list_name}`** (disbanded **`{len(target_list)}`** doujins).")
                                    await interaction.response.edit_message(embed=emb, view=None)
                                    self.stop()

                            @ui.button(label="Cancel", style=ButtonStyle.secondary, custom_id="button2")
                            async def cancel_button(self, interaction, button):
                                if interaction.user.id == ctx.author.id:
                                    emb = Embed(description=f"❌ Operation cancelled.")
                                    await interaction.response.edit_message(embed=emb, view=None)
                                    self.stop()

                            async def on_timeout(self):
                                for component in self.children:
                                    component.disabled = True
                                await self.message.edit(embed=emb, view=self)
                                self.stop()

                        view = Confirm(self.bot)
                        view.message = await ctx.send(embed=emb, view=view)
                        await view.wait()
                        return

                elif mode in ["add", "a", "+"]:
                    if code in target_list:
                        await ctx.send(embed=Embed(description="❌ That doujin is already in that list."))
                        return

                    if len(target_list) >= 25: 
                        await ctx.send(embed=Embed(description="❌ You cannot add more than 25 doujins to a list."))
                        return

                    if not code:
                        await ctx.send(embed=Embed(description="❌ Provide a code, damnit!"))
                        return

                    try:
                        code = int(code)
                        code = str(code)
                    except ValueError:
                        await ctx.send(embed=Embed(description="❌ You didn't type a proper ID. Come on, numbers!"))
                        return

                    edit = await ctx.send(embed=Embed(description="<a:nreader_loading:810936543401213953>"))
                    
                    doujin = await self.nhentai_api.get_doujin(code)

                    if not doujin:
                        await edit.edit(embed=Embed(description="🔎❌ I did not find a doujin with that ID."))
                        return

                    if not lolicon_allowed and any([tag in restricted_tags for tag in doujin.tags]):
                        await edit.edit(content="⚠❌ This doujin contains lolicon/shotacon content and cannot be shown publically.")
                        return

                    target_list.append(code)
                    await edit.edit(embed=Embed(description=f"✅ Added **`{code}`** to **`{list_name}`**."))
                    return

                elif mode in ["remove", "r", "-"]:
                    if code not in target_list:
                        await ctx.send(embed=Embed(description="❌ That doujin is not in that list."))
                        return

                    target_list.remove(code)
                    await ctx.send(embed=Embed(description=f"✅ Removed **`{code}`** from **`{list_name}`**."))
                    return

                elif mode in ["clear", "c"]:
                    emb = Embed(
                        title="Clearing An Occupied List",
                        description=f"Are you sure you want to clear this list?\n"
                                    f"\n"
                                    f"**Name**: **{list_name}**\n"
                                    f"{'**Alias**: '+alias_name+newline if alias_name else ''}"
                                    f"**Number of doujins inside**: **`{len(target_list)}`**")
                                    
                    class Confirm(ui.View):
                        def __init__(self, bot):
                            super().__init__(timeout=15)
                            self.bot = bot
                            self.value = None
                        
                        @ui.button(label="Continue", style=ButtonStyle.danger, custom_id="button1")
                        async def confirm_button(self, interaction, button):
                            if interaction.user.id == ctx.author.id:
                                self.bot.user_data["UserData"][str(ctx.author.id)]["Lists"][sys_category][full_name] = ["0"]
                                emb = Embed(description=f"✅ Cleared/reset **`{list_name}`** (removed **`{len(target_list)}`** doujins).")
                                await interaction.response.edit_message(embed=emb, view=None)
                                self.stop()

                        @ui.button(label="Cancel", style=ButtonStyle.secondary, custom_id="button2")
                        async def cancel_button(self, interaction, button):
                            if interaction.user.id == ctx.author.id:
                                emb = Embed(description=f"❌ Operation cancelled.")
                                await interaction.response.edit_message(embed=emb, view=None)
                                self.stop()

                        async def on_timeout(self):
                            for component in self.children:
                                component.disabled = True
                            await self.message.edit(embed=emb, view=self)
                            self.stop()

                    view = Confirm(self.bot)
                    view.message = await ctx.send(embed=emb, view=view)
                    await view.wait()
                    return

                elif not mode:
                    await load_list(target_list)
                    return

            else:
                await ctx.send(embed=Embed(description="❌ Invalid mode passed. Valid modes are `add/a/+`, `remove/r/-`, `clear/c`, and `delete/del`."))
                return

    @command(
        name=f"{experimental_prefix}recommend",
        aliases=[
            f"{experimental_prefix}rec",
        ])
    @bot_has_permissions(
        send_messages=True,
        embed_links=True)
    async def recommended(self, ctx, query: str = ''):
        # This tells the user that the command they are trying to use isn't translated yet.
        user_language = {"lang": self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["Language"]}
        if ctx.command.qualified_name not in localization[user_language["lang"]]:
            class Continue(ui.View):
                def __init__(self):
                    super().__init__(timeout=15)
                    self.value = None
                
                @ui.button(label=localization[user_language["lang"]]["language_not_available"]["button"], style=ButtonStyle.primary, emoji="▶️", custom_id="continue")
                async def continue_button(self, interaction, button):
                    if interaction.user.id == ctx.author.id:
                        await interaction.response.defer()

                        user_language["lang"] = "eng"
                        await self.message.delete()
                        self.value = True
                        self.stop()

                async def on_timeout(self):
                    await self.message.delete()
                    self.stop()

            emb = Embed(
                description=localization[user_language["lang"]]["language_not_available"]["description"]
            ).set_footer(text=localization[user_language["lang"]]["language_not_available"]["footer"])
            view = Continue()
            view.message = await ctx.send(embed=emb, view=view)
            await view.wait()
            if not view.value:
                return
        user_language = user_language["lang"]

        lolicon_allowed = False
        try:
            if not ctx.guild or ctx.guild.id in self.bot.user_data["UserData"][str(ctx.guild.owner_id)]["Settings"]["UnrestrictedServers"]:
                lolicon_allowed = True
        except KeyError:
            pass

        if not self.bot.user_data["UserData"][str(ctx.author.id)]["Lists"]["Built-in"]["History|*n*|his"]["enabled"] or \
            len(self.bot.user_data["UserData"][str(ctx.author.id)]["Lists"]["Built-in"]["History|*n*|his"]["list"]) == 1:  # includes placeholder
            emb = Embed(
                title=f"History",
                description="❌ You either do not have anything in your history, or you have it disabled. To toggle it, type and enter `n!l History toggle`."
            ).set_author(
                name="NHentai",
                url="https://nhentai.net/",
                icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
            
            await ctx.send(embed=emb)
            return

        list_items = self.bot.user_data["UserData"][str(ctx.author.id)]["Lists"]["Built-in"]["History|*n*|his"]["list"]
        if "0" not in list_items:
            if isinstance(list_items, list):
                list_items.append("0")

        
        conf = await ctx.send(
            embed=Embed(
                description=f"Loading history... (1/2)"
            ).set_author(
                name="NHentai",
                url=f"https://nhentai.net/",
                icon_url="https://cdn.discordapp.com/emojis/810936543401213953.gif?v=1"
            ).set_footer(
                text=f"This part should take no more than 10 seconds."))

        await sleep(1)

        message_part = list()
        remove_queue = list()  # It is very rare that a doujin would get deleted from NHentai
            
        doujins = list()
        tally_tags = dict()
        exclude_titles = list()
        passed_placeholder = False
        for ind, code in enumerate(list_items):
            if passed_placeholder:
                ind -= 1

            bookmark_page = None
            if isinstance(list_items, dict):  # Is the Bookmarks list
                bookmark_page = list_items[code]

            if code == "placeholder" or code == 0 or code == "0":
                passed_placeholder = True
                continue

            doujin = await self.nhentai_api.get_doujin(code)
            if not doujin:
                remove_queue.append(code)
                continue

            tags = [tag.name for tag in doujin.tags if tag.type == "tag"]
            if any([tag in restricted_tags for tag in tags]): is_lolicon = True
            else: is_lolicon = False
            
            for tag in tags:
                if tag not in tally_tags: tally_tags.update({f"\"{tag}\"":1})
                else: tally_tags.update({f"\"{tag}\"":tally_tags[tag]+1})

            exclude_titles.append(f"-title:\"{doujin.title.english}\"")

        [list_items.remove(code) for code in remove_queue]

        tally_tags = sorted(tally_tags, key=lambda x: tally_tags[x])

        minimal_details = False 
        if ctx.guild and not ctx.channel.is_nsfw(): 
            minimal_details = True

        
        if "--noappend" in query:
            query = query.replace("--noappend", "")
            appendage = ""
        elif self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["SearchAppendage"] != " ":
            appendage = self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["SearchAppendage"]
        else:
            appendage = ""

        if not lolicon_allowed:
            appendage = appendage + " " + " ".join([f"-\"{tag}\"" for tag in restricted_tags])

        await conf.edit(
            embed=Embed(
                description=f"Loading searches... (2/2)"
            ).set_author(
                name="NHentai",
                url=f"https://nhentai.net/",
                icon_url="https://cdn.discordapp.com/emojis/810936543401213953.gif?v=1"
            ).set_footer(
                text=f"This part should take no more than 10 seconds."))

        successful_search_tries = 0
        doujins = []
        message_part = []
        thumbnail_url = self.bot.user.avatar.url
        for tag_str in tally_tags:
            if successful_search_tries == 5:
                break

            try:
                results = await self.nhentai_api.search(query=f"{tag_str} {appendage} {' '.join(exclude_titles)}")
            except Exception:
                continue

            if not results.doujins:
                continue

            else:
                doujins.append(results.doujins[0])
                successful_search_tries += 1

            dj = results.doujins[0]
            quotemark = '"'
            message_part.append(
                f"**Because of your interest in __{tag_str.strip(quotemark)}__:**\n"
                f"__`{str(dj.id).ljust(7)}`__ | {language_to_flag(dj.languages)} | {shorten(dj.title.pretty, width=50, placeholder='...')}\n")
            if thumbnail_url == self.bot.user.avatar.url:
                thumbnail_url = dj.cover.src

            exclude_titles.append(f"-title:\"{dj.title.english}\"")

            continue
            
        emb = Embed(
            description=f"\n"+('\n'.join(message_part))
        ).set_author(
            name="NHentai",
            url="https://nhentai.net/",
            icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1"
        ).set_thumbnail(url=thumbnail_url)
        
        print(f"[HRB] {ctx.author} ({ctx.author.id}) searched for [{query if query else ''}{' ' if query and appendage else ''}{appendage if appendage else ''}].")
        
        class Interactive(ui.View):
            def __init__(self, bot):
                super().__init__(timeout=15)
                self.bot = bot
                self.value = None
            
            @ui.button(label=localization[user_language]['search_doujins']['start_interactive'], style=ButtonStyle.primary, emoji=self.bot.get_emoji(853674277416206387), custom_id="button1")
            async def interactive_mode(self, interaction, button):
                if interaction.user.id == ctx.author.id:
                    await interaction.response.defer()
                    self.stop()

                    interactive = SearchResultsBrowser(self.bot, ctx, doujins, msg=conf, lolicon_allowed=lolicon_allowed, minimal_details=minimal_details, user_language=user_language)
                    await interactive.start(ctx)

            async def on_timeout(self):
                self.children[0].disabled = True
                await view.message.edit(embed=emb, view=self)
                self.stop()

        view = Interactive(self.bot)
        view.message = await conf.edit(embed=emb, view=view)
        await view.wait()


    @command(
        name=f"{experimental_prefix}search_appendage",
        aliases=[
            f"{experimental_prefix}append",
            f"{experimental_prefix}アッペンド",  # JP alias
            f"{experimental_prefix}附加"  # CN alias
        ])
    @bot_has_permissions(
        send_messages=True,
        embed_links=True)
    async def search_appendage(self, ctx, *, appendage=""):
        # This tells the user that the command they are trying to use isn't translated yet.
        user_language = {"lang": self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["Language"]}
        if ctx.command.qualified_name not in localization[user_language["lang"]]:
            class Continue(ui.View):
                def __init__(self):
                    super().__init__(timeout=15)
                    self.value = None
                
                @ui.button(label=localization[user_language["lang"]]["language_not_available"]["button"], style=ButtonStyle.primary, emoji="▶️", custom_id="continue")
                async def continue_button(self, interaction, button):
                    if interaction.user.id == ctx.author.id:
                        await interaction.response.defer()
                        
                        user_language["lang"] = "eng"
                        await self.message.delete()
                        self.value = True
                        self.stop()

                async def on_timeout(self):
                    await self.message.delete()
                    self.stop()

            emb = Embed(
                description=localization[user_language["lang"]]["language_not_available"]["description"]
            ).set_footer(text=localization[user_language["lang"]]["language_not_available"]["footer"])
            view = Continue()
            view.message = await ctx.send(embed=emb, view=view)
            await view.wait()
            if not view.value:
                return
        user_language = user_language["lang"]

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

            class Confirm(ui.View):
                def __init__(self, bot):
                    super().__init__(timeout=15)
                    self.bot = bot
                    self.value = None
                
                @ui.button(label="Continue", style=ButtonStyle.danger, custom_id="button1")
                async def confirm_button(self, interaction, button):
                    if interaction.user.id == ctx.author.id:
                        self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["SearchAppendage"] = appendage
                
                        emb = Embed(
                            title = "Search Appendage Updated",
                            description = f"✅ The following string will now be appended to all of your searches:\n"
                                          f"```{self.bot.user_data['UserData'][str(ctx.author.id)]['Settings']['SearchAppendage']}```\n"
                        ).set_footer(text="Please note that this will be appended to searches in all cases, so if you have unexpected results, check back on this command.")
                        await interaction.response.edit_message(embed=emb, view=None)
                        self.stop()

                async def on_timeout(self):
                    for component in self.children:
                        component.disabled = True
                    await self.message.edit(embed=emb, view=self)
                    self.stop()

            view = Confirm(self.bot)
            view.message = await ctx.send(embed=emb, view=view)
            await view.wait()
                
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
            
            class Confirm(ui.View):
                def __init__(self, bot):
                    super().__init__(timeout=15)
                    self.bot = bot
                    self.value = None
                
                @ui.button(label="Continue", style=ButtonStyle.danger, custom_id="button1")
                async def confirm_button(self, interaction, button):
                    if interaction.user.id == ctx.author.id:
                        old = deepcopy(self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["SearchAppendage"])
                        self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["SearchAppendage"] = " "
                
                        emb = Embed(
                            title = "Search Appendage Erased",
                            description = f"✅ Nothing will be added to your searches.\n"
                                        f"```diff\n"
                                        f"- [{old}]\n"
                                        f"```\n"
                        ).set_footer(text="Please note that this will be appended to searches in all cases, so if you have unexpected results, check back on this command.")
                        await interaction.response.edit_message(embed=emb, view=None)
                        self.stop()

                async def on_timeout(self):
                    for component in self.children:
                        component.disabled = True
                    await self.message.edit(embed=emb, view=self)
                    self.stop()
        
            view = Confirm(self.bot)
            view.message = await ctx.send(embed=emb, view=view)
            await view.wait()

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
        aliases=[
            f"{experimental_prefix}rc",
            f"{experimental_prefix}リコール",  # JP alias
            f"{experimental_prefix}記起",  # CN alias
        ])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    @bot_has_guild_permissions(
        manage_messages=True, 
        manage_channels=True, 
        manage_roles=True)
    async def recall(self, ctx):
        # This tells the user that the command they are trying to use isn't translated yet.
        user_language = {"lang": self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["Language"]}
        if ctx.command.qualified_name not in localization[user_language["lang"]]:
            class Continue(ui.View):
                def __init__(self):
                    super().__init__(timeout=15)
                    self.value = None
                
                @ui.button(label=localization[user_language["lang"]]["language_not_available"]["button"], style=ButtonStyle.primary, emoji="▶️", custom_id="continue")
                async def continue_button(self, interaction, button):
                    if interaction.user.id == ctx.author.id:
                        await interaction.response.defer()
                        
                        user_language["lang"] = "eng"
                        await self.message.delete()
                        self.value = True
                        self.stop()

                async def on_timeout(self):
                    await self.message.delete()
                    self.stop()

            emb = Embed(
                description=localization[user_language["lang"]]["language_not_available"]["description"]
            ).set_footer(text=localization[user_language["lang"]]["language_not_available"]["footer"])
            view = Continue()
            view.message = await ctx.send(embed=emb, view=view)
            await view.wait()
            if not view.value:
                return
        user_language = user_language["lang"]

        if not ctx.guild:
            await ctx.send(embed=Embed(
                description=":x: This command must be run in a server. Consider making a private one."))

            return

        if not ctx.channel.is_nsfw():
            await ctx.send(embed=Embed(
                description="❌ This command cannot be used in a non-NSFW channel."))

            return

        lolicon_allowed = False
        try:
            if not ctx.guild or ctx.guild.id in self.bot.user_data["UserData"][str(ctx.guild.owner_id)]["Settings"]["UnrestrictedServers"]:
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
        
        edit = await ctx.send(embed=Embed(description=f"{self.bot.get_emoji(810936543401213953)} Recalling..."))

        
        doujin = await self.nhentai_api.get_doujin(code)
        
        if not doujin:
            await ctx.send(embed=Embed(
                description="🔎❌ Unfortunately, the doujin you were reading is no longer available."))
            
            self.bot.user_data["UserData"][str(ctx.author.id)]["Recall"] = "N/A"
            return
        
        if not lolicon_allowed and any([tag in restricted_tags for tag in doujin.tags]):
            await edit.edit(embed=Embed(
                description="⚠️⛔ You can't recall your doujin here. Did you think you could wormhole like that?"))

        session = ImagePageReader(self.bot, ctx, doujin.images, doujin.title.pretty, str(doujin.id), starting_page=int(page))
        await edit.edit(embed=Embed(description="<:nhentai:845298862184726538> Successfully recalled."))
        self.bot.user_data["UserData"][str(ctx.author.id)]["Recall"] = "N/A"
        response = await session.setup()
        if response:
            self.bot.user_data["UserData"][str(ctx.author.id)]["Recall"] = "N/A"
            
            print(f"[HRB] {ctx.author} ({ctx.author.id}) started reading `{doujin.id}`.")
            await session.start()
        
        else:
            self.bot.user_data["UserData"][str(ctx.author.id)]["Recall"] = f"{code}*n*{page}"
            await edit.edit(embed=Embed(description="❌ You didn't answer the recall in time. It has been reapplied to your profile."))
        
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
        # This tells the user that the command they are trying to use isn't translated yet.
        user_language = {"lang": self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["Language"]}
        if ctx.command.qualified_name not in localization[user_language["lang"]]:
            class Continue(ui.View):
                def __init__(self):
                    super().__init__(timeout=15)
                    self.value = None
                
                @ui.button(label=localization[user_language["lang"]]["language_not_available"]["button"], style=ButtonStyle.primary, emoji="▶️", custom_id="continue")
                async def continue_button(self, interaction, button):
                    if interaction.user.id == ctx.author.id:
                        await interaction.response.defer()
                        
                        user_language["lang"] = "eng"
                        await self.message.delete()
                        self.value = True
                        self.stop()

                async def on_timeout(self):
                    await self.message.delete()
                    self.stop()

            emb = Embed(
                description=localization[user_language["lang"]]["language_not_available"]["description"]
            ).set_footer(text=localization[user_language["lang"]]["language_not_available"]["footer"])
            view = Continue()
            view.message = await ctx.send(embed=emb, view=view)
            await view.wait()
            if not view.value:
                return
        user_language = user_language["lang"]

        edit = await ctx.send(embed=Embed(
            color=0x1d2439,
            description=f"{self.bot.get_emoji(813237675553062954)}"))

        udclient = AsyncUrbanClient()
        response = await udclient.get_definition(word)

        if not response:
            await edit.edit(embed=Embed(
                color=0x1d2439,
                description="🔎❌ I did not find anything. Maybe you typed something wrong?"))
            
            return
        else:
            print(f"[HRB] {ctx.author} ({ctx.author.id}) looked up '{word}' using the built-in Urban Dictionary.")

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


        current_def = {"index": 0}
        examples_part = []
        for ind, example in enumerate(response[current_def["index"]].example_lines):
            examples_part.append(f"> *{example}*")

        emb = Embed(
            color=0x1d2439,
            title=response[current_def['index']].word,
            description=f"{response[current_def['index']].definition}\n"
                        f"\n"
                        f"{newline.join(examples_part)}\n"
                        f"{self.bot.get_emoji(274492025678856192)}{response[current_def['index']].upvotes} "
                        f"{self.bot.get_emoji(274492025720537088)}{response[current_def['index']].downvotes}"
        ).set_author(
            name="Urban Dictionary",
            url=f"https://www.urbandictionary.com/define.php?term={response[current_def['index']].word.replace(' ', '%20')}",
            icon_url="https://cdn.discordapp.com/attachments/655456170391109663/867163805535961109/favicons.png"
        ).set_footer(text=f"[ {current_def['index']+1}/{len(response)} ]")

        class UrbanDictionaryView(ui.View):
            def __init__(self, bot):
                super().__init__(timeout=30)
                self.bot = bot
                self.value = None
            
            @ui.button(label="Previous", style=ButtonStyle.primary, emoji="◀️", custom_id="button1", disabled=True if len(response) <=1 else False)
            async def previous_button(self, interaction, button):
                if interaction.user.id == ctx.author.id:
                    if current_def["index"] == 0:
                        current_def["index"] = len(response)-1
                    else:
                        current_def["index"] = current_def["index"] - 1

                    examples_part = []
                    for ind, example in enumerate(response[current_def["index"]].example_lines):
                        examples_part.append(f"> *{example}*")

                    emb = Embed(
                        color=0x1d2439,
                        title=response[current_def['index']].word,
                        description=f"{response[current_def['index']].definition}\n"
                                    f"\n"
                                    f"{newline.join(examples_part)}\n"
                                    f"{self.bot.get_emoji(274492025678856192)}{response[current_def['index']].upvotes} "
                                    f"{self.bot.get_emoji(274492025720537088)}{response[current_def['index']].downvotes}"
                    ).set_author(
                        name="Urban Dictionary",
                        url=f"https://www.urbandictionary.com/define.php?term={response[current_def['index']].word.replace(' ', '%20')}",
                        icon_url="https://cdn.discordapp.com/attachments/655456170391109663/867163805535961109/favicons.png"
                    ).set_footer(text=f"[ {current_def['index']+1}/{len(response)} ]")
                    await interaction.response.edit_message(embed=emb, view=self)

            @ui.button(label=f"[ ----- ]", style=ButtonStyle.secondary, custom_id="button0", disabled=True)
            async def display_button(self, interaction, button):
                return

            @ui.button(label="Next", style=ButtonStyle.primary, emoji="▶️", custom_id="button2", disabled=True if len(response) <=1 else False)
            async def next_button(self, interaction, button):
                if interaction.user.id == ctx.author.id:
                    if current_def["index"] == len(response)-1:
                        current_def["index"] = 0
                    else:
                        current_def["index"] = current_def["index"] + 1

                    examples_part = []
                    for ind, example in enumerate(response[current_def["index"]].example_lines):
                        examples_part.append(f"> *{example}*")

                    emb = Embed(
                        color=0x1d2439,
                        title=response[current_def['index']].word,
                        description=f"{response[current_def['index']].definition}\n"
                                    f"\n"
                                    f"{newline.join(examples_part)}\n"
                                    f"{self.bot.get_emoji(274492025678856192)}{response[current_def['index']].upvotes} "
                                    f"{self.bot.get_emoji(274492025720537088)}{response[current_def['index']].downvotes}"
                    ).set_author(
                        name="Urban Dictionary",
                        url=f"https://www.urbandictionary.com/define.php?term={response[current_def['index']].word.replace(' ', '%20')}",
                        icon_url="https://cdn.discordapp.com/attachments/655456170391109663/867163805535961109/favicons.png"
                    ).set_footer(text=f"[ {current_def['index']+1}/{len(response)} ]")
                    await interaction.response.edit_message(embed=emb, view=self)

            async def on_timeout(self):
                await udclient.session.close()
                await self.message.edit(embed=emb, view=None)
                self.stop()

        view = UrbanDictionaryView(self.bot)
        view.message = await edit.edit(embed=emb, view=view)
        await view.wait()

    @command(
        name=f"{experimental_prefix}reset_my_data",
        aliases=[
            f"{experimental_prefix}reset", 
            f"{experimental_prefix}rs"])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    async def reset_user_data(self, ctx):
        class ConfirmReset(ui.View):
            def __init__(self, bot, ctx):
                super().__init__(timeout=15)
                self.value = None
                self.bot = bot
                self.ctx = ctx
            
            @ui.button(label="Continue", style=ButtonStyle.danger, custom_id="button1")
            async def confirm_button(self, interaction, button):
                if interaction.user.id == self.ctx.author.id:
                    self.bot.user_data["UserData"].pop(str(self.ctx.author.id))
                    print(f"[HRB] {ctx.author} ({ctx.author.id}) popped their data from NReader.")
                    emb = Embed(
                        title="✅ Reset Success",
                        description="Your data has been removed. Thank you for using NReader!"
                    )
                    await interaction.response.edit_message(embed=emb, view=None)
                    self.stop()

            @ui.button(label="Cancel", style=ButtonStyle.secondary, custom_id="button2")
            async def cancel_button(self, interaction, button):
                if interaction.user.id == self.ctx.author.id:
                    emb = Embed(
                        title="<:nhentai:845298862184726538> Reset Cancelled",
                        description="Your data hasn't been touched."
                    )
                    await interaction.response.edit_message(embed=emb, view=None)
                    self.stop()

            async def on_timeout(self):
                for component in self.children:
                    component.disabled = True
                await self.message.edit(embed=emb, view=self)
                self.stop()

        emb = Embed(
            title="⚠️ Resetting User Data",
            description="You've requested to remove all of your data from NReader's database.\n"
                        "If you wish to continue, press Confirm. To leave your data untouched, press Cancel."
        )
        view = ConfirmReset(self.bot, ctx)
        view.message = await ctx.send(embed=emb, view=view)
        await view.wait()
        return

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


async def setup(bot):
    await bot.add_cog(Commands(bot))
