import os
from sys import exc_info
from copy import deepcopy
from textwrap import shorten
from asyncio import sleep
from contextlib import suppress
from typing import List, Union

from discord import (
    interactions, ui, ButtonStyle, Message, 
    TextChannel, Forbidden, NotFound)
from discord.components import Button
from discord.ui import view
from discord.utils import get
from discord.ext.commands import Context
from discord.ext.commands.cog import Cog
# from NHentai.nhentai_async import NHentaiAsync as NHentai, Doujin
from utils.NHentai_API.NHentai.nhentai_async import NHentaiAsync as NHentai, Doujin

from utils.classes import Embed, Bot, BotInteractionCooldown
from utils.misc import (
    language_to_flag,
    is_int, is_float,
    restricted_tags)
from cogs.Tlocalization import *

"""
# Experimental to Stable todo:

from cogs.Tlocalization -> from cogs.localization

class TClasses(Cog) -> class Classes(Cog)

bot.add_cog(TClasses(bot)) -> bot.add_cog(Classes(bot))
"""

newline = "\n"


class TClasses(Cog):
    def __init__(self, bot):
        self.bot = bot


class ImagePageReader:
    def __init__(self, bot: Bot, ctx: Context, images:list, name:str, code:str, **kwargs):
        """Create and run a reader based on pages from a Doujin. 
        To work for any purpose, this class needs a few changes.
        
        `bot` - The Bot class created on initialization
        `ctx` - Context used
        `images` The list of image urls to use
        `name` - Title of the reader
        `code` - Book/Item ID

        `**kwargs` - Further keyword arguments if need be
        -- `current_page` - The starting page as an integer. Defaults to `0`

        """
        self.bot = bot
        self.ctx: Context = ctx
        self.images: list = images
        self.name: str = name
        self.code: str = code

        self.current_page: int = kwargs.pop("starting_page", 0)
        self.active_message: Message = None

        self.am_embed: Embed = None
        self.am_channel: TextChannel = None
        self.is_paused: bool = False
        self.on_bookmarked_page: bool = False

        self.language = kwargs.pop("user_language", "eng")

    async def update(self, ctx):
        if self.code in self.bot.user_data['UserData'][str(ctx.author.id)]['Lists']['Built-in']['Bookmarks|*n*|bm'] and \
            self.current_page == self.bot.user_data['UserData'][str(ctx.author.id)]['Lists']['Built-in']['Bookmarks|*n*|bm'][self.code]:
            self.on_bookmarked_page = True
        else:
            self.on_bookmarked_page = False

        self.am_embed.description = f"<:nprev:853668227124953159>{'<:nfini:853670159310913576>' if self.current_page == (len(self.images)-1) else '<:nnext:853668227207790602>'} {localization[self.language]['page_reader']['description']['previous']} | {localization[self.language]['page_reader']['description']['finish'] if self.current_page == (len(self.images)-1) else localization[self.language]['page_reader']['description']['next']}\n" \
                                    f"<:nsele:853668227212902410><:nstop:853668227175546952> {localization[self.language]['page_reader']['description']['select']} | {localization[self.language]['page_reader']['description']['stop']}\n" \
                                    f"<:npaus:853668227234529300><:nbook:853668227205038090> {localization[self.language]['page_reader']['description']['pause']} | {localization[self.language]['page_reader']['description']['bookmark'] if not self.on_bookmarked_page else localization[self.language]['page_reader']['description']['unbookmark']}\n" 

        self.am_embed.set_image(url=self.images[self.current_page].src)
        self.am_embed.set_footer(text=localization[self.language]['page_reader']['footer'].format(current=self.current_page+1, total=len(self.images), bookmark='🔖' if self.on_bookmarked_page else ''))

        if self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["ThumbnailPreference"] == 0:
            self.am_embed.set_thumbnail(url=self.images[self.current_page+1].src if (self.current_page+1) in range(0, len(self.images)) else None)                
        if self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["ThumbnailPreference"] == 1:
            self.am_embed.set_thumbnail(url=self.images[self.current_page-1].src if (self.current_page-1) in range(0, len(self.images)) else None) 
        if self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["ThumbnailPreference"] == 2:
            self.am_embed.set_thumbnail(url=None)

        thumbnail_buttons = {
            0: self.bot.get_emoji(903121521571168276),
            1: self.bot.get_emoji(903122915619373106),
            2: self.bot.get_emoji(903121521621491732)
        }

        class IPRControls(ui.View):
            def __init__(self, bot, ctx, parent):
                super().__init__(timeout=600)
                self.value = 0
                self.bot = bot
                self.ctx = ctx
                self.parent = parent
            
            @ui.button(emoji=self.bot.get_emoji(853668227124953159), style=ButtonStyle.secondary, custom_id="previous", disabled=self.current_page==0)
            async def previous_button(self, interaction, button):
                if interaction.user.id == self.ctx.author.id:
                    await interaction.response.defer()

                    if self.parent.current_page == 0:  # Not allowed to go behind zero
                        return self.stop()
                    else:
                        self.parent.current_page = self.parent.current_page - 1

                    self.stop()

            @ui.button(emoji=self.bot.get_emoji(853670159310913576) if self.current_page+1==len(self.images) else self.bot.get_emoji(853668227207790602), style=ButtonStyle.secondary, custom_id="next")
            async def next_button(self, interaction, button):
                if interaction.user.id == self.ctx.author.id:
                    await interaction.response.defer()

                    self.parent.current_page = self.parent.current_page + 1
                    if self.parent.current_page > (len(self.parent.images)-1):  # Finish the doujin if at last page
                        self.parent.am_embed.set_image(url=None)
                        self.parent.am_embed.set_thumbnail(url=None)
                        self.parent.am_embed.description=localization[self.parent.language]['page_reader']['finished']

                        await self.parent.active_message.edit(embed=self.parent.am_embed, view=None)
                        if self.parent.code in self.bot.user_data['UserData'][str(self.ctx.author.id)]['Lists']['Built-in']['Read Later|*n*|rl']:
                            self.bot.user_data['UserData'][str(self.ctx.author.id)]['Lists']['Built-in']['Read Later|*n*|rl'].remove(self.parent.code)
                        
                        await sleep(2)
                        await self.parent.active_message.edit(content=f"{self.parent.bot.get_emoji(810936543401213953)} {localization[self.parent.language]['page_reader']['closing']}", embed=None)

                        await sleep(1)
                        await self.parent.am_channel.delete()

                        self.value = 1
                        self.stop()
                    
                    else:
                        self.stop()

            @ui.button(emoji=self.bot.get_emoji(853668227212902410), style=ButtonStyle.secondary, custom_id="select")
            async def select_button(self, interaction, button):
                if interaction.user.id == self.ctx.author.id:
                    bm_page = None
                    if self.parent.code in self.bot.user_data['UserData'][str(self.ctx.author.id)]['Lists']['Built-in']['Bookmarks|*n*|bm']:
                        bm_page = self.bot.user_data['UserData'][str(self.ctx.author.id)]['Lists']['Built-in']['Bookmarks|*n*|bm'][self.parent.code]

                    class NumberSubmit(ui.Modal, title="🖼 Page Selection"):
                        page = ui.TextInput(
                            label=localization[self.parent.language]['page_reader']['select_inquiry']['modal_label'], 
                            placeholder=localization[self.parent.language]['page_reader']['select_inquiry']['modal_placeholder'].format(pages=len(self.parent.images), bookmark=bm_page+1 if bm_page else "N/A"),
                            max_length=2, required=True)
                        controller = self

                        async def on_submit(self, interaction):
                            await interaction.response.defer()
                            page = str(self.page)
                            if is_int(page) and (int(page)-1) in range(0, len(self.controller.parent.images)):
                                self.controller.parent.current_page = int(page)-1
                            self.stop()

                    modal = NumberSubmit()
                    await interaction.response.send_modal(modal)
                    await modal.wait()
                    
                    self.stop()
                
            @ui.button(emoji=self.bot.get_emoji(853668227175546952), style=ButtonStyle.secondary, custom_id="stop")
            async def stop_button(self, interaction, button):
                if interaction.user.id == self.ctx.author.id:
                    await interaction.response.defer()

                    self.parent.am_embed.set_image(url=None)
                    self.parent.am_embed.set_thumbnail(url=None)
                    self.parent.am_embed.description=localization[self.parent.language]['page_reader']['stopped']
                    
                    await self.parent.active_message.edit(embed=self.parent.am_embed, view=None)

                    await sleep(2)
                    await self.parent.active_message.edit(content=f"{self.bot.get_emoji(810936543401213953)} {localization[self.parent.language]['page_reader']['closing']}", embed=None)
                    
                    await sleep(1)
                    await self.parent.am_channel.delete()
                    
                    self.value = 1
                    self.stop()

            @ui.button(emoji=self.bot.get_emoji(853668227234529300), style=ButtonStyle.secondary, custom_id="pause")
            async def pause_button(self, interaction, button):
                if interaction.user.id == self.ctx.author.id:
                    await interaction.response.defer()

                    self.parent.am_embed.set_image(url=None)
                    self.parent.am_embed.set_thumbnail(url=None)
                    self.parent.am_embed.description=localization[self.parent.language]['page_reader']['paused']
                    
                    await self.parent.active_message.edit(embed=self.parent.am_embed, view=None)

                    await sleep(2)
                    await self.parent.active_message.edit(content=f"{self.bot.get_emoji(810936543401213953)} {localization[self.parent.language]['page_reader']['closing']}", embed=None)
                    
                    await sleep(1)
                    await self.parent.am_channel.delete()
                    
                    await sleep(1)
                    self.bot.user_data["UserData"][str(self.ctx.author.id)]["Recall"] = f"{self.parent.code}*n*{self.parent.current_page}"
                    await self.ctx.author.send(embed=Embed(
                        title=localization[self.parent.language]['page_reader']['recall_saved']['title'],
                        description=localization[self.parent.language]['page_reader']['recall_saved']['description'].format(code=self.parent.code, current=self.parent.current_page+1, total=len(self.parent.images))))

                    self.value = 1
                    self.stop()

            @ui.button(emoji=self.bot.get_emoji(853668227205038090), style=ButtonStyle.secondary, custom_id="bookmark")
            async def bookmark_button(self, interaction, button):
                if interaction.user.id == self.ctx.author.id:
                    await interaction.response.defer()

                    if not self.parent.on_bookmarked_page:
                        if self.parent.current_page == 0:
                            await self.parent.am_channel.send(
                                embed=Embed(
                                    color=0xFF0000,
                                    description=localization[self.parent.language]['page_reader']['cannot_bookmark_first_page']
                                ),
                                delete_after=5)
                            
                            return self.stop()

                        if len(self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["Bookmarks|*n*|bm"]) >= 25: 
                            await self.parent.am_channel.send(
                                color=0xff0000, 
                                embed=Embed(
                                    description=localization[self.parent.language]['page_reader']['bookmarks_full']
                                ),
                                delete_after=5)

                            return self.stop()

                        self.bot.user_data['UserData'][str(self.ctx.author.id)]['Lists']['Built-in']['Bookmarks|*n*|bm'][self.parent.code] = self.parent.current_page
                        self.parent.on_bookmarked_page = True
                    
                    else:
                        if self.parent.code in self.bot.user_data['UserData'][str(self.ctx.author.id)]['Lists']['Built-in']['Bookmarks|*n*|bm']:
                            self.bot.user_data['UserData'][str(self.ctx.author.id)]['Lists']['Built-in']['Bookmarks|*n*|bm'].pop(self.parent.code)
                            self.parent.on_bookmarked_page = False

                    self.stop()

            @ui.button(emoji="⭐", style=ButtonStyle.secondary, custom_id="favorite")
            async def favorite_button(self, interaction, button):
                if interaction.user.id == self.ctx.author.id:
                    await interaction.response.defer()

                    if self.parent.code not in self.bot.user_data['UserData'][str(self.ctx.author.id)]['Lists']['Built-in']['Favorites|*n*|fav']:
                        if len(self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["Favorites|*n*|fav"]) >= 25: 
                            await self.parent.am_channel.send(
                                embed=Embed(
                                    color=0xff0000,
                                    description=localization[self.parent.language]['page_reader']['favorites_full']
                                ), delete_after=5)

                            return self.stop()

                        self.bot.user_data['UserData'][str(self.ctx.author.id)]['Lists']['Built-in']['Favorites|*n*|fav'].append(self.parent.code)

                        await self.parent.am_channel.send(
                            embed=Embed(
                                description=localization[self.parent.language]['page_reader']['added_to_favorites'].format(code=self.parent.code)
                            ),
                            delete_after=5)

                    else:
                        self.bot.user_data['UserData'][str(self.ctx.author.id)]['Lists']['Built-in']['Favorites|*n*|fav'].remove(self.parent.code)

                        await self.parent.am_channel.send(
                            embed=Embed(
                                description=localization[self.parent.language]['page_reader']['removed_from_favorites'].format(code=self.parent.code)
                            ),
                            delete_after=5)

                    self.stop()

            @ui.button(emoji=thumbnail_buttons[self.bot.user_data["UserData"][str(self.ctx.author.id)]["Settings"]["ThumbnailPreference"]], style=ButtonStyle.secondary, custom_id="thumbnail")
            async def thumbnail_button(self, interaction, button):
                if interaction.user.id == self.ctx.author.id:
                    await interaction.response.defer()

                    if self.bot.user_data["UserData"][str(self.ctx.author.id)]["Settings"]["ThumbnailPreference"] == 2:
                        self.bot.user_data["UserData"][str(self.ctx.author.id)]["Settings"]["ThumbnailPreference"] = 0
                    else:
                        self.bot.user_data["UserData"][str(self.ctx.author.id)]["Settings"]["ThumbnailPreference"] += 1

                    self.stop()

            @ui.button(emoji="👥", style=ButtonStyle.secondary, custom_id="add_user")
            async def add_user(self, interaction, button):
                if interaction.user.id == self.ctx.author.id:
                    class UserSubmit(ui.Modal, title="👥 Add User"):
                        user_id = ui.TextInput(
                            label=localization[self.parent.language]['page_reader']['add_user']['prompt'], 
                            placeholder="000000000000000000",
                            max_length=18, required=True)
                        controller = self

                        async def on_submit(self, interaction):
                            await interaction.response.defer()
                            user_id = str(self.user_id)
                            if not is_int(user_id):
                                await self.controller.parent.am_channel.send("error")
                                try:
                                    await interaction.followup.send(localization[self.parent.language]['page_reader']['add_user']['not_a_number'], ephemeral=True)
                                except Exception as e:
                                    await interaction.followup.send("localization error", ephemeral=True)
                                return self.stop()
                            
                            try:
                                member = await self.controller.parent.ctx.guild.fetch_member(int(user_id))
                            except NotFound:
                                await interaction.followup.send(localization[self.parent.language]['page_reader']['add_user']['not_found'], ephemeral=True)
                                return self.stop()
            
                            await self.controller.parent.am_channel.set_permissions(member, read_messages=True, send_messages=True)
                            await interaction.followup.send(f"{self.controller.parent.ctx.author.mention} has added {member.mention}.")
                                
                            self.stop()

                    modal = UserSubmit()
                    await interaction.response.send_modal(modal)
                    await modal.wait()
                    
                    self.stop()

            async def on_timeout(self):
                with suppress(NotFound):
                    self.parent.am_embed.set_image(url=None)
                    self.parent.am_embed.set_thumbnail(url=None)
                    self.parent.am_embed.description=localization[self.parent.language]['page_reader']['timeout'].format(current=self.parent.current_page+1, total=len(self.parent.images))

                    await self.parent.active_message.edit(embed=self.parent.am_embed, view=None)
                    temp = await self.parent.am_channel.send(content=localization[self.parent.language]['page_reader']['timeout_notification'].format(mention=self.ctx.author.mention), delete_after=1)
        
                    await sleep(10)

                    with suppress(NotFound):
                        await self.parent.active_message.edit(content=f"{self.bot.get_emoji(810936543401213953)} {localization[self.parent.language]['page_reader']['closing']}", embed=None)

                    await sleep(1)
                    await self.parent.am_channel.delete()

                self.value = 1
                self.stop()

        self.view = IPRControls(self.bot, self.ctx, self)
        with suppress(NotFound):
            await self.active_message.edit(embed=self.am_embed, view=self.view)
        await self.view.wait()
        return self.view.value

    async def setup(self):
        edit = await self.ctx.send(embed=Embed(
            description=f"{self.bot.get_emoji(810936543401213953)}"))

        # Fetch existing category for readers, otherwise create new
        cat = get(self.ctx.guild.categories, name="📖NReader")
        if not cat:
            cat = await self.ctx.guild.create_category_channel(name="📖NReader")
        elif not cat.permissions_for(self.ctx.guild.me).manage_roles:
            with suppress(Forbidden):
                await cat.delete()
            
            cat = await self.ctx.guild.create_category_channel(name="📖NReader")

        # Create reader channel under category
        channel = await cat.create_text_channel(name=f"📖nreader-{self.ctx.message.id}", nsfw=True)

        # Set channel permissions
        await channel.set_permissions(self.ctx.guild.me, read_messages=True)
        await channel.set_permissions(self.ctx.guild.default_role, read_messages=False)
        await channel.set_permissions(self.ctx.author, read_messages=True)

        self.am_embed = Embed(
            description=localization[self.language]['page_reader']['init']['description'])
        self.am_embed.set_author(
            name=f"{self.code} [*n*] {self.name}",
            icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
        self.am_embed.set_footer(
            text=localization[self.language]['page_reader']['init']['footer'].format(total=len(self.images)))
        
        class Start(ui.View):
            def __init__(self, bot, ctx, parent):
                super().__init__(timeout=30)
                self.value = None
                self.bot = bot
                self.ctx = ctx
                self.parent = parent
            
            @ui.button(label=localization[self.language]["page_reader"]["init"]["button"], style=ButtonStyle.primary, emoji=self.bot.get_emoji(853674277416206387), custom_id="button1")
            async def start_button(self, interaction, button):
                if interaction.user.id == self.ctx.author.id:
                    await interaction.response.defer()

                    self.active_message = view.message

                    self.value = True
                    self.stop()

            async def on_timeout(self):
                with suppress(NotFound):
                    await view.message.edit(content=f"{self.bot.get_emoji(810936543401213953)} {localization[self.parent.language]['page_reader']['closing']}", embed=None)
            
                await sleep(1)
                
                with suppress(NotFound):
                    await view.message.channel.delete()
                
                self.value = 1
                self.stop()

        # Reader message
        view = Start(self.bot, self.ctx, self)
        self.am_channel = channel
        self.active_message = view.message = await self.am_channel.send(embed=self.am_embed, view=view)

        # Portal
        await edit.edit(
            content=self.am_channel.mention, 
            embed=Embed(
                description=localization[self.language]['page_reader']['portal'].format(code=self.code, name=self.name)
                ).set_author(
                    name=self.bot.user.name,
                    icon_url=self.bot.user.avatar.url),
            delete_after=10)

        await view.wait()
        if view.value:
            print(f"[HRB] {self.ctx.author} ({self.ctx.author.id}) started reading `{self.code}`.")
            await self.update(self.ctx)

        return view.value

    async def start(self):
        if self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["History|*n*|his"]["enabled"]:
            while self.code in self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["History|*n*|his"]["list"]:
                self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["History|*n*|his"]["list"].remove(self.code)

            self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["History|*n*|his"]["list"].insert(0, self.code)

            if "0" in self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["History|*n*|his"]["list"]:
                self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["History|*n*|his"]["list"].remove("0")
            
            if len(self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["History|*n*|his"]["list"]) >= 2 and \
                self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["History|*n*|his"]["list"][1] == self.code:
                self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["History|*n*|his"]["list"].pop(0)
            
            while len(self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["History|*n*|his"]["list"]) > 25:
                self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["History|*n*|his"]["list"].pop()

            if "0" not in self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["History|*n*|his"]["list"]:
                self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["History|*n*|his"]["list"].append("0")
        
        while True:
            view_exit_code = await self.update(self.ctx)
            if view_exit_code != 0:
                return

class SearchResultsBrowser:
    def __init__(self, bot: Bot, ctx: Context, results: List[Doujin], **kwargs):
        """Class to create and run a browser from NHentai-API

        `results` - obtained from nhentai_api.search(query)
        `msg` - optional message that the bot owns to edit, otherwise created 
        """
        self.bot = bot
        self.ctx = ctx
        self.doujins = results
        self.index = 0
        self.lolicon_allowed = kwargs.pop("lolicon_allowed", False)
        self.minimal_details = kwargs.pop("minimal_details", True)
        self.name = kwargs.pop("name", "Search Results")

        self.active_message: Message = kwargs.pop("msg", None)
        self.am_embed: Embed = Embed()

        self.language = kwargs.pop("user_language", "eng")
    
    async def update_browser(self, ctx):
        message_part = []
        for ind, dj in enumerate(self.doujins):
            try: 
                if ind == self.index and int(dj.id) in self.bot.user_data['UserData'][str(ctx.author.id)]['Lists']['Built-in']["Favorites|*n*|fav"]: symbol = '🟩'
                elif ind == self.index: symbol='🟥'
                elif int(dj.id) in self.bot.user_data['UserData'][str(ctx.author.id)]['Lists']['Built-in']["Favorites|*n*|fav"]: symbol = '🟦'
                else: symbol='⬛'
            except KeyError: 
                symbol='⬛'
            
            tags = [tag.name for tag in dj.tags if tag.type == "tag"]
            if any([tag in restricted_tags for tag in tags]) and ctx.guild and not self.lolicon_allowed:
                message_part.append(
                    f"{'**' if ind == self.index else ''}"
                    f"`{symbol} {str(ind+1).ljust(2)}` | {localization[self.language]['search_doujins']['search_results']['contains_restricted_tags']}"
                    f"{'**' if ind == self.index else ''}")
            else:
                message_part.append(
                    f"{'**' if ind == self.index else ''}"
                    f"`{symbol} {str(ind+1).ljust(2)}` | "
                    f"__`{str(dj.id).ljust(7)}`__ | "
                    f"{language_to_flag(dj.languages)} | "
                    f"{shorten(dj.title.pretty, width=40, placeholder='...')}"
                    f"{'**' if ind == self.index else ''}")

        doujin = self.doujins[self.index]
        previous_emb = deepcopy(self.am_embed)
        #self.active_message.embeds[0] = self.am_embed

        self.am_embed = Embed(
            title=self.name,
            description=f"\n"+('\n'.join(message_part))+"\n\n▌█████████████████▓▓▒▒░░")
        self.am_embed.set_thumbnail(url=doujin.cover.src)

        if not self.minimal_details:
            if previous_emb.image.url != None:
                self.am_embed.set_image(url=doujin.cover.src)
                self.am_embed.set_thumbnail(url=None)
            elif previous_emb.thumbnail.url != None:
                self.am_embed.set_thumbnail(url=doujin.cover.src)
                self.am_embed.set_image(url=None)        

        nhentai = NHentai()
        tags = [tag.name for tag in doujin.tags if tag.type == "tag"]
        if any([tag in restricted_tags for tag in tags]) and ctx.guild and not self.lolicon_allowed:
            self.am_embed.add_field(
                name=localization[self.language]['results_browser']['forbidden']['title'],
                inline=False,
                value=localization[self.language]['results_browser']['forbidden']['description']
            ).set_footer(
                text=f"⭐ N/A"
            )
            
            doujin.cover.src = str(self.bot.user.avatar.url)
        
        else:
            if self.minimal_details:
                self.am_embed.add_field(
                    name=localization[self.language]['results_browser']['minimal_details'],
                    inline=False,
                    value=
                        f"ID: `{doujin.id}`\n"
                        f"{localization[self.language]['doujin_info']['fields']['title']}: {language_to_flag(doujin.languages)} `{shorten(doujin.title.pretty, width=256, placeholder='...')}`\n"
                        f"{localization[self.language]['doujin_info']['fields']['artists']}: `{', '.join([tag.name for tag in doujin.artists]) if doujin.artists else localization[self.language]['doujin_info']['fields']['not_provided']}`\n"
                        f"{localization[self.language]['doujin_info']['fields']['characters']}: `{', '.join([tag.name for tag in doujin.characters]) if doujin.characters else localization[self.language]['doujin_info']['fields']['original']}`\n"
                        f"{localization[self.language]['doujin_info']['fields']['parodies']}: `{', '.join([tag.name for tag in doujin.parodies]) if doujin.parodies else localization[self.language]['doujin_info']['fields']['original']}`\n"
                        f"{localization[self.language]['doujin_info']['fields']['tags']}:\n||`{shorten(str(', '.join([tag.name for tag in doujin.tags if tag.type == 'tag']) if [tag.name for tag in doujin.tags if tag.type == 'tag'] else localization[self.language]['doujin_info']['fields']['not_provided']), width=950, placeholder='...')}`||"
                ).set_footer(
                    text=f"{localization[self.language]['doujin_info']['sfw']}")

                self.am_embed.set_author(
                    name=f"NHentai",
                    icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")

            else:
                self.am_embed.add_field(
                    name=localization[self.language]['doujin_info']['fields']['title'],
                    inline=False,
                    value=f"`{shorten(doujin.title.pretty, width=256, placeholder='...')}`"
                ).add_field(
                    inline=False,
                    name=localization[self.language]['doujin_info']['fields']['id/pages'],
                    value=f"`{doujin.id}` - `{doujin.total_pages}`"
                ).add_field(
                    inline=False,
                    name=localization[self.language]['doujin_info']['fields']['date_uploaded'],
                    value=f"<t:{int(doujin.upload_at.timestamp())}>"
                ).add_field(
                    inline=False,
                    name=localization[self.language]['doujin_info']['fields']['languages'],
                    value=f"{language_to_flag(doujin.languages)} `{', '.join([localization[self.language]['doujin_info']['fields']['language_names'][tag.name] for tag in doujin.languages]) if doujin.languages else localization[self.language]['doujin_info']['fields']['not_provided']}`"
                ).add_field(
                    inline=False,
                    name=localization[self.language]['doujin_info']['fields']['artists'],
                    value=f"`{', '.join([tag.name for tag in doujin.artists]) if doujin.artists else localization[self.language]['doujin_info']['fields']['not_provided']}`"
                ).add_field(
                    inline=False,
                    name=localization[self.language]['doujin_info']['fields']['characters'],
                    value=f"`{', '.join([tag.name for tag in doujin.characters]) if doujin.characters else localization[self.language]['doujin_info']['fields']['original']}`"
                ).add_field(
                    inline=False,
                    name=localization[self.language]['doujin_info']['fields']['parodies'],
                    value=f"`{', '.join([tag.name for tag in doujin.parodies]) if doujin.parodies else localization[self.language]['doujin_info']['fields']['original']}`"
                ).set_footer(
                    text=f"⭐ {doujin.total_favorites}"
                )

                # Doujin count for tags
                tags_list = []
                for tag in [tag for tag in doujin.tags if tag.type == "tag"]:
                    count = tag.count
                    parse_count = list(str(count))
                    if len(parse_count) < 4:
                        tags_list.append(f"{localization[self.language]['fields']['tag_names'][tag.name] if tag.name in localization[self.language]['doujin_info']['fields']['tag_names'] else tag.name}[{count}]")
                    elif len(parse_count) >= 4 and len(parse_count) <= 6:
                        count = count/1000
                        tags_list.append(f"{localization[self.language]['fields']['tag_names'][tag.name] if tag.name in localization[self.language]['doujin_info']['fields']['tag_names'] else tag.name}[{round(count, 1)}k]")
                    elif len(parse_count) > 7:
                        count = count/1000000
                        tags_list.append(f"{localization[self.language]['fields']['tag_names'][tag.name] if tag.name in localization[self.language]['doujin_info']['fields']['tag_names'] else tag.name}[{round(count, 2)}m]")

                self.am_embed.add_field(
                    inline=False,
                    name=localization[self.language]["doujin_info"]["fields"]["tags"],
                    value=f"```{shorten(str(', '.join(tags_list) if tags_list else localization[self.language]['doujin_info']['fields']['not_provided']), width=1018, placeholder='...')}```"
                )

                self.am_embed.set_author(
                    name=f"NHentai",
                    url=f"https://nhentai.net/g/{doujin.id}/",
                    icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")


        if not self.active_message:
            self.active_message = await ctx.send("...")

        class SRBControls(ui.View):
            def __init__(self, bot, ctx, parent):
                super().__init__(timeout=60)
                self.value = 0
                self.bot = bot
                self.ctx = ctx
                self.parent = parent
            
            @ui.button(emoji=self.bot.get_emoji(853800909108936754), style=ButtonStyle.secondary, custom_id="up")
            async def up_button(self, interaction, button):
                if interaction.user.id == self.ctx.author.id:
                    await interaction.response.defer()

                    if self.parent.index > 0:
                        self.parent.index -= 1
                    elif self.parent.index == 0:
                        self.parent.index = len(self.parent.doujins)-1

                    self.stop()

            @ui.button(emoji=self.bot.get_emoji(853800909276315678), style=ButtonStyle.secondary, custom_id="down")
            async def down_button(self, interaction, button):
                if interaction.user.id == self.ctx.author.id:
                    await interaction.response.defer()

                    if self.parent.index < len(self.parent.doujins)-1:
                        self.parent.index += 1
                    elif self.parent.index == len(self.parent.doujins)-1:
                        self.parent.index = 0

                    self.stop()

            @ui.button(emoji=self.bot.get_emoji(853668227212902410), style=ButtonStyle.secondary, custom_id="select")
            async def select_button(self, interaction, button):
                if interaction.user.id == self.ctx.author.id:
                    # await interaction.response.defer()

                    class NumberSubmit(ui.Modal, title="🟥 Result Selection"):
                        result = ui.TextInput(
                            label=localization[self.parent.language]['results_browser']['select_inquiry']['modal_label'], 
                            placeholder=localization[self.parent.language]['results_browser']['select_inquiry']['modal_placeholder'].format(results=len(self.parent.doujins)),
                            max_length=2, required=True)
                        controller = self

                        async def on_submit(self, interaction):
                            await interaction.response.defer()
                            result = str(self.result)
                            if is_int(result) and (int(result)-1) in range(0, len(self.controller.parent.doujins)):
                                self.controller.parent.index = int(result)-1
                            self.stop()

                    modal = NumberSubmit()
                    await interaction.response.send_modal(modal)
                    await modal.wait()
                    self.stop()

            @ui.button(emoji=self.bot.get_emoji(853668227175546952), style=ButtonStyle.secondary, custom_id="stop")
            async def stop_button(self, interaction, button):
                if interaction.user.id == self.ctx.author.id:
                    await interaction.response.defer()

                    message_part = []
                    for ind, dj in enumerate(self.parent.doujins):
                        tags = [tag.name for tag in dj.tags if tag.type == "tag"]
                        if any([tag in restricted_tags for tag in tags]) and self.ctx.guild and not self.parent.lolicon_allowed:
                            message_part.append(localization[self.parent.language]['search_doujins']['search_results']['contains_restricted_tags'])
                        else:
                            message_part.append(
                                f"__`{str(dj.id).ljust(7)}`__ | "
                                f"{language_to_flag(dj.languages)} | "
                                f"{shorten(dj.title.pretty, width=50, placeholder='...')}")
                    
                    self.parent.am_embed = Embed(
                        title=self.parent.name,
                        description=f"\n"+('\n'.join(message_part)))

                    self.parent.am_embed.set_author(
                        name="NHentai",
                        url=f"https://nhentai.net/",
                        icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
                    
                    self.parent.am_embed.set_thumbnail(url=None)
                    self.parent.am_embed.set_image(url=None)
                    await self.parent.active_message.edit(embed=self.parent.am_embed, view=None)

                    self.value = 1
                    self.stop()

            if not self.ctx.guild or (self.ctx.guild and not all([
                self.ctx.guild.me.guild_permissions.manage_channels, 
                self.ctx.guild.me.guild_permissions.manage_roles, 
                self.ctx.guild.me.guild_permissions.manage_messages])):

                @ui.button(emoji=self.bot.get_emoji(853684136379416616), style=ButtonStyle.secondary, custom_id="read", disabled=True)
                async def read_button(self, interaction, button):
                    return

            else:
                @ui.button(emoji=self.bot.get_emoji(853684136379416616), style=ButtonStyle.secondary, custom_id="read", disabled=self.minimal_details)
                async def read_button(self, interaction, button):
                    if interaction.user.id == self.ctx.author.id:
                        await interaction.response.defer()

                        tags = [tag.name for tag in self.parent.doujins[self.parent.index].tags if tag.type == "tag"]
                        if any([tag in restricted_tags for tag in tags]) and self.ctx.guild and not self.parent.lolicon_allowed:
                            self.stop()
                            return
                        
                        message_part = []
                        for ind, dj in enumerate(self.parent.doujins):
                            tags = [tag.name for tag in dj.tags if tag.type == "tag"]
                            if any([tag in restricted_tags for tag in tags]) and self.ctx.guild and not self.parent.lolicon_allowed:
                                message_part.append(localization[self.parent.language]['search_doujins']['search_results']['contains_restricted_tags'])
                            else:
                                message_part.append(
                                    f"{'**' if ind == self.parent.index else ''}"
                                    f"__`{str(dj.id).ljust(7)}`__ | "
                                    f"{language_to_flag(dj.languages)} | "
                                    f"{shorten(dj.title.pretty, width=50, placeholder='...')}"
                                    f"{'**' if ind == self.parent.index else ''}")

                        self.parent.am_embed = Embed(
                            title=self.parent.name,
                            description=f"\n"+('\n'.join(message_part)))
                        self.parent.am_embed.set_author(
                            name="NHentai",
                            url=f"https://nhentai.net/",
                            icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
                        
                        self.parent.am_embed.set_thumbnail(url=None)
                        self.parent.am_embed.set_image(url=None)

                        await self.parent.active_message.edit(embed=self.parent.am_embed, view=None)

                        self.value = 1
                        self.stop()

                        doujin = self.parent.doujins[self.parent.index]
                        if str(doujin.id) in self.bot.user_data['UserData'][str(self.ctx.author.id)]['Lists']['Built-in']["Bookmarks|*n*|bm"]:
                            page = self.bot.user_data['UserData'][str(self.ctx.author.id)]['Lists']['Built-in']["Bookmarks|*n*|bm"][str(doujin.id)]
                        else:
                            page = 0

                        session = ImagePageReader(self.bot, self.ctx, doujin.images, doujin.title.pretty, str(doujin.id), starting_page=page)
                        response = await session.setup()
                        if response:
                            await session.start()
                        else:
                            await self.parent.active_message.edit(embed=self.parent.am_embed)

                        

            @ui.button(emoji=self.bot.get_emoji(853684136433942560), style=ButtonStyle.secondary, custom_id="zoom", disabled=self.minimal_details)
            async def zoom_button(self, interaction, button):
                if interaction.user.id == self.ctx.author.id:
                    await interaction.response.defer()

                    doujin = self.parent.doujins[self.parent.index]
                    if self.parent.am_embed.image.url == None:
                        self.parent.am_embed.set_image(url=doujin.cover.src)
                        self.parent.am_embed.set_thumbnail(url=None)
                    elif self.parent.am_embed.thumbnail.url == None:
                        self.parent.am_embed.set_thumbnail(url=doujin.cover.src)
                        self.parent.am_embed.set_image(url=None)
                    
                    await self.parent.active_message.edit(embed=self.parent.am_embed)
                    
                    self.stop()

            @ui.button(emoji=self.bot.get_emoji(853668227205038090), style=ButtonStyle.secondary, custom_id="readlater")
            async def readlater_button(self, interaction, button):
                if interaction.user.id == self.ctx.author.id:
                    await interaction.response.defer()

                    if len(self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["Read Later|*n*|rl"]) >= 25: 
                        await self.ctx.send(
                            embed=Embed(
                                color=0xff0000, 
                                description=localization[self.parent.language]['results_browser']['buttons']['read_later_full']
                            ),
                            delete_after=5)
                        
                        self.stop()
                        return

                    if str(self.parent.doujins[self.parent.index].id) not in self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["Read Later|*n*|rl"]:
                        self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["Read Later|*n*|rl"].append(str(self.parent.doujins[self.parent.index].id))
                        await self.ctx.send(
                            embed=Embed(
                                description=localization[self.parent.language]['results_browser']['buttons']['add_to_read_later'].format(code=self.parent.doujins[self.parent.index].id)
                            ),
                            delete_after=5)
                    else:
                        self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["Read Later|*n*|rl"].remove(str(self.parent.doujins[self.parent.index].id))
                        await self.ctx.send(
                            embed=Embed(
                                description=localization[self.parent.language]['results_browser']['buttons']['remove_from_read_later'].format(code=self.parent.doujins[self.parent.index].id)
                            ),
                            delete_after=5)
            
                    self.stop()

            async def on_timeout(self):
                message_part = []
                for ind, dj in enumerate(self.parent.doujins):
                    tags = [tag.name for tag in dj.tags if tag.type == "tag"]
                    if any([tag in restricted_tags for tag in tags]) and self.ctx.guild and not self.parent.lolicon_allowed:
                        message_part.append(localization[self.parent.language]['search_doujins']['search_results']['contains_restricted_tags'])
                    else:
                        message_part.append(
                            f"__`{str(dj.id).ljust(7)}`__ | "
                            f"{language_to_flag(dj.languages)} | "
                            f"{shorten(dj.title.pretty, width=50, placeholder='...')}")
                
                self.parent.am_embed = Embed(
                    title=self.parent.name,
                    description=f"\n"+('\n'.join(message_part)))
                self.parent.am_embed.set_author(
                    name="NHentai",
                    url=f"https://nhentai.net/",
                    icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
                

                self.parent.am_embed.set_thumbnail(url=None)
                self.parent.am_embed.set_image(url=None)

                await self.parent.active_message.edit(embed=self.parent.am_embed, view=None)
                
                self.value = 1
                self.stop()

        view = SRBControls(self.bot, self.ctx, self)
        await self.active_message.edit(embed=self.am_embed, view=view)
        await view.wait()
        return view.value

    async def start(self, ctx):
        """Initial start of the result browser."""

        while True:
            view_exit_code = await self.update_browser(self.ctx)
            if view_exit_code != 0:
                return

async def setup(bot):
    await bot.add_cog(TClasses(bot))
