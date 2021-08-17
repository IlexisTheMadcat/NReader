# IMPORTS
from sys import exc_info
from copy import deepcopy
from textwrap import shorten
from asyncio import sleep
from asyncio.exceptions import TimeoutError
from contextlib import suppress
from typing import List

from discord import (
    Message, TextChannel,
    Forbidden, NotFound)
from discord.utils import get
from discord.ext.commands import Context
from discord.ext.commands.cog import Cog
from discord_components import Button
from NHentai.nhentai_async import NHentaiAsync as NHentai, Doujin

from utils.classes import Embed, Bot, BotInteractionCooldown
from utils.utils import (
    language_to_flag, 
    is_int, is_float)

newline = "\n"

class Classes(Cog):
    def __init__(self, bot):
        self.bot = bot


class SelectionContext:
    """Return a class with information on the current selection in the dictionary."""
    def __init__(
        self,
        index_path,  # Path to current value
        selected_key_value:tuple=(None, None),  # Currently selected key/value pair.
        dir_index_max=float("inf"),
        has_children=False,
        has_parent=False
    ):
        self.path = index_path
        self.selected_key_value = selected_key_value
        self.dir_index_max = dir_index_max
        self.has_children = has_children
        self.has_parent = has_parent


# NEW PEOJECT WORK IN PROGRESS
class SettingsEditor:
    """
    Discord interface for editing values in a dictionary.
    Only simple values such as strings, bools, and numbers are shown and editable.
    New keys cannot be added while editing.

    Parameters:
    `bot` - The Discord Bot class associated with your bot.
    `context` - A `discord.Context` object typically provided by a command or `Bot.get_context(message)`.
    `settings_dict` - The dict that will be modified. Can be any dict in any location, it will be deepcopied.
    `title` - The title of the settings configurator embed.
    `base_color` - The base color of the embed. It can change depending on the value selected.

    Returns the final dict after all changes have been made. 
    Use this to update the dict that was being edited, or for your desire.
    """
    def __init__(self, 
        bot: Bot, 
        ctx:Context, 
        settings_dict:dict, 
        title:str="Settings Editor", 
        base_color:int=0x000000
    ):
        if len(str(settings_dict)) > 2000:
            raise ValueError("This dictionary is too large to show on Discord. "
                             "Max string character limit is 2048 for embed descriptions, but is limited to 2000 in this constructor "
                             "for markdown and GUI characters.")

        self.bot = bot
        self.ctx = ctx
        self.title = title
        self.base_color = base_color

        self.active_message: Message = None
        self.am_embed = None

        # Copy the dict so it isn't updated live until the user clicks the "Save and Quit" button.
        self.settings_dict = deepcopy(settings_dict)

        # The path of indexes in which to iterate through a dict to find a nested value.
        self.selected_path = [0]

    # Create a user-friendly visual of the information in a dictionary.
    def create_description(self, dictionary, depth=0, message_lines=list(), path=[0], reset=True):
        if reset:
            message_lines = list()
        
        for index, (k, v) in enumerate(dictionary.items()):
            path[-1] = index
            is_selected: bool = self.selected_path == path

            print("CD", path)  # TRACK PATH

            if isinstance(v, int) or isinstance(v, float):
                message_lines.append(
                    f"{'ー　'*depth}{k}: **`{v}`** {'🟦◀' if is_selected else ''}")
            
            elif isinstance(v, str):
                message_lines.append(
                    f"{'　ー'*depth}{k}: `{v}` {'🟦◀' if is_selected else ''}")
            
            elif isinstance(v, bool):
                message_lines.append(
                    f"{'　ー'*depth}{k}: `{'🟩 True' if v else '🟥 False'}` {'🟦◀' if is_selected else ''}")
            
            elif isinstance(v, dict):
                message_lines.append(
                    f"{'　ー'*depth}**{k} [** {'🟦🔽' if is_selected else ''}")
                
                path.append(index)
                self.create_description(dictionary[k], depth+1, message_lines, path, reset=False)
            
            else:
                message_lines.append(
                    f"{'　ー'*depth} ~~{k}~~; [❓] {'◀🟦' if is_selected else ''}")
        
        return "\n".join(message_lines)
    
    # Get a SelectionContext object for the selected item in a dictionary.
    # Instead of following a path, iterate through the whole thing for better context.
    def get_selection_context(self, dictionary, depth=0, path=[0]):
        for index, (k, v) in enumerate(dictionary.items()):
            path[-1] = index

            print("GSC", path)  # TRACK PATH

            if self.selected_path == path:
                return SelectionContext(
                    path, 
                    (k,v), 
                    len(dictionary.items()), 
                    len(path) > 0, 
                    isinstance(v, dict)
                )
            
            elif isinstance(v, dict):
                path.append(index)
                self.get_selection_context(dictionary[k], depth+1, path)

    async def setup(self):
        self.am_embed = Embed(
            color=self.base_color, 
            description=self.create_description(self.settings_dict)
        ).set_footer(
            text="🔼🔽◀▶🔢💾 |Up|Down|Parent|Children|Input|Save|")
        
        editor = await self.ctx.send(embed=self.am_embed)

        self.active_message = editor
        await self.active_message.add_reaction("🔼")
        await self.active_message.add_reaction("🔽")
        await self.active_message.add_reaction("◀")
        await self.active_message.add_reaction("▶")
        await self.active_message.add_reaction("🔢")
        await self.active_message.add_reaction("💾")
    
    async def start(self):
        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=300,
                    check=lambda r, u: r.message.channel.id==self.ctx.channel.id and \
                        u.id==self.ctx.author.id and str(r.emoji) in ["🔼", "🔽", "◀", "▶", "🔢", "💾"])
            except TimeoutError:
                self.selected_path = [-1]

                self.am_embed = Embed(
                    color=self.base_color, 
                    description=self.create_description(self.settings_dict)
                ).set_footer(text=Embed.Empty)
                
                await self.active_message.edit(embed=self.am_embed)
                return

            except BotInteractionCooldown:
                continue

            else:
                with suppress(Forbidden):
                    await self.active_message.remove_reaction(str(reaction.emoji), user)

                if str(reaction.emoji) == "🔼":
                    context = self.get_selection_context(self.settings_dict)
                    if self.selected_path[-1] == 0:
                        self.selected_path[-1] = context.dir_index_max-1
                    else:
                        self.selected_path[-1] = self.selected_path[-1] - 1
                    
                    print("UP", self.selected_path)  # TRACK PATH
                    
                    self.am_embed.description = self.create_description(self.settings_dict)
                    self.am_embed.set_footer(
                        text="🔼🔽◀▶🔢💾 |Up|Down|Parent|Children|Input|Save|")

                    await self.active_message.edit(embed=self.am_embed)
                
                elif str(reaction.emoji) == "🔽":
                    context = self.get_selection_context(self.settings_dict)
                    if self.selected_path[-1] == context.dir_index_max-1:
                        self.selected_path[-1] = 0
                    else:
                        self.selected_path[-1] = self.selected_path[-1] + 1
                    
                    print("DOWN", self.selected_path)  # TRACK PATH
                    
                    self.am_embed.description = self.create_description(self.settings_dict)
                    self.am_embed.set_footer(
                        text="🔼🔽◀▶🔢💾 |Up|Down|Parent|Children|Input|Save|")
                    
                    await self.active_message.edit(embed=self.am_embed)
                
                elif str(reaction.emoji) == "◀":
                    context = self.get_selection_context(self.settings_dict)
                    if context.has_parent:
                        self.selected_path.pop()

                        self.am_embed.description = self.create_description(self.settings_dict)
                        self.am_embed.set_footer(
                        text="🔼🔽◀▶🔢💾 |Up|Down|Parent|Children|Input|Save|")

                        await self.active_message.edit(embed=self.am_embed)

                elif str(reaction.emoji) == "▶":
                    context = self.get_selection_context(self.settings_dict)
                    if context.has_children:
                        self.selected_path.append(0)

                        self.am_embed.description = self.create_description(self.settings_dict)
                        self.am_embed.set_footer(
                            text="🔼🔽◀▶🔢💾 |Up|Down|Parent|Children|Input|Save|")

                        await self.active_message.edit(embed=self.am_embed)
                
                elif str(reaction.emoji) == "🔢":
                    context = self.get_selection_context(self.settings_dict)
                    def change_item(dictionary, depth=0, path=[0], new=0):
                        for index, (k, v) in enumerate(dictionary.items()):
                            if self.selected_path == path:
                                if not isinstance(new, type(context.selected_key_value[1])):
                                    return False
                                else:
                                    dictionary[k] = new
                                    return
                            
                            elif isinstance(v, dict):
                                self.get_item(dictionary, depth+1, path.append(index))
                    
                    def python_to_english():
                        item_type = type(context.selected_key_value[1])
                        if item_type == int:
                            return 'a *whole* number.'
                        if item_type == float:
                            return 'a number. Can be a decimal.'
                        elif item_type == bool:
                            return '`True` or `False`.'
                        elif item_type == str:
                            return 'a string.'
                        else:
                            return None

                    if type(context.selected_key_value[1]) not in [int, float, bool, str]:
                        await self.ctx.send(f"⛔ This value of type `{type(context.selected_key_value[1])}` cannot be changed.", delete_after=3)
                        continue
                    
                    self.am_embed.set_footer(text=f"❔ Type the new value for this setting. It must be {python_to_english()}")
                    await self.active_message.edit(embed=self.am_embed)

                    try:
                        message = await self.bot.wait_for("message", timeout=10,
                            check=lambda m: m.author.id == self.ctx.author.id and \
                                m.channel.id == self.ctx.author.id)
                    except TimeoutError:
                        self.am_embed.set_footer(text=f"🔼🔽◀▶🔢💾 |Up|Down|Parent|Children|Input|Save|")
                        await self.active_message.edit(embed=self.am_embed)
                        continue

                    except BotInteractionCooldown:
                        continue

                    else:
                        if message.content == "True":
                            new = True
                        elif message.content == "False":
                            new = False
                        elif is_int(message.content):
                            new = int(message.content)
                        elif is_float(message.content):
                            new = float(message.content)
                        else:  # Assume it is a string as no other types are recognized.
                            new = message.content
                        
                        change_item(self.settings_dict, new=new)
                        if not change_item:
                            await self.ctx.send("❌ Not a valid value. Try again.", delete_after=3)
                            self.am_embed.set_footer(
                                text=f"🔼🔽◀▶🔢💾 |Up|Down|Parent|Children|Input|Save|")
                        else:
                            await self.ctx.send("✔ Value Changed.", delete_after=3)
                            self.am_embed.set_footer(
                                text=f"🔼🔽◀▶🔢💾 |Up|Down|Parent|Children|Input|Save|")

                        self.am_embed.description = self.create_description(self.settings_dict)
                        await self.active_message.edit(embed=self.am_embed)

                elif str(reaction.emoji) == "💾":
                    self.am_embed.set_footer(
                        text="✔ Settings confirmed.")

                    self.am_embed.description = self.create_description(self.settings_dict)
                    await self.active_message.edit(embed=self.am_embed)

                    return self.settings_dict


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

    async def setup(self):
        edit = await self.ctx.send(embed=Embed(
            description="<a:nreader_loading:810936543401213953>"))

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
            description=f"Waiting.")
        self.am_embed.set_author(
            name=self.name,
            icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
        self.am_embed.set_footer(
            text=f"Page [0/{len(self.images)}]: Press ▶ Start to start reading.")
        
        # Reader message
        conf = await self.bot.comp_ext.send_component_msg(channel, 
            content=self.ctx.author.mention, embed=self.am_embed,
            components=[Button(label="Start", style=1, emoji=self.bot.get_emoji(853674277416206387), id="button1")])

        # Portal
        await edit.edit(
            content=conf.channel.mention, 
            embed=Embed(
                description="Click/Tap the mention above to jump to your reader."
                ).set_author(
                    name=self.bot.user.name,
                    icon_url=self.bot.user.avatar_url),
            delete_after=10)
        
        # `delete_after` doesn't work currently with the DC wrapper
        await edit.delete(delay=10)
        
        while True:
            try:
                interaction = await self.bot.wait_for("button_click", timeout=30, bypass_cooldown=True,
                    check=lambda i: 
                        i.message.id == conf.id and \
                        i.user.id == self.ctx.author.id)
        
            except TimeoutError:
                await conf.edit(content="<a:nreader_loading:810936543401213953> Closing...")
            
                await sleep(1)
                await conf.channel.delete()
                return False
        
            else:
                try: await interaction.respond(type=6)
                except NotFound: continue
            
                self.active_message = conf
                self.am_channel = conf.channel
            
                self.am_embed.description = f"<:nprev:853668227124953159>{'<:nfini:853670159310913576>' if self.current_page == (len(self.images)-1) else '<:nnext:853668227207790602>'} Previous|{'__**Finish**__' if self.current_page == (len(self.images)-1) else 'Next'}\n" \
                                            f"<:nsele:853668227212902410><:nstop:853668227175546952> Select|Stop\n" \
                                            f"<:npaus:853668227234529300><:nbook:853668227205038090> Pause|{'Bookmark' if not self.on_bookmarked_page else 'Unbookmark'}"
                self.am_embed.set_image(url=self.images[self.current_page])
                self.am_embed.set_footer(text=f"Page [{self.current_page+1}/{len(self.images)}]")
                self.am_embed.set_thumbnail(url=self.images[self.current_page+1] if (self.current_page+1) in range(0, len(self.images)) else Embed.Empty)
                await self.bot.comp_ext.edit_component_msg(self.active_message, embed=self.am_embed,
                    components=[
                        [Button(emoji=self.bot.get_emoji(853668227124953159), style=2, id="prev", disabled=self.current_page==0),
                        Button(emoji=self.bot.get_emoji(853670159310913576) if self.current_page+1==len(self.images) else self.bot.get_emoji(853668227207790602), style=2, id="next"),
                        Button(emoji=self.bot.get_emoji(853668227212902410), style=2, id="sele"),
                        Button(emoji=self.bot.get_emoji(853668227175546952), style=2, id="stop"),
                        Button(emoji=self.bot.get_emoji(853668227234529300), style=2, id="paus")],
                        [Button(emoji=self.bot.get_emoji(853668227205038090), style=2, id="book"),
                        Button(emoji="⭐", style=2, id="fav"),
                        Button(label="Support Server", style=5, url="https://discord.gg/DJ4wdsRYy2")]])

                await sleep(0.2)
                with suppress(NotFound):
                    await edit.delete()

                return True

    async def start(self):
        if self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["History|*n*|his"]["enabled"]:
            self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["History|*n*|his"]["list"].insert(0, self.code)
            
            if "placeholer" in self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["History|*n*|his"]["list"]:
                self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["History|*n*|his"]["list"].remove("placeholder")
            
            if len(self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["History|*n*|his"]["list"]) >= 2 and \
                self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["History|*n*|his"]["list"][1] == self.code:
                
                self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["History|*n*|his"]["list"].pop(0)
            
            while len(self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["History|*n*|his"]["list"]) > 25:
                self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["History|*n*|his"]["list"].pop()

            while self.code in self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["History|*n*|his"]["list"]:
                self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["History|*n*|his"]["list"].remove(self.code)

            for i in self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["History|*n*|his"]["list"]:
                if isinstance(i, int):
                    self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["History|*n*|his"]["list"].remove(i)
        
        while True:
            try:
                interaction = await self.bot.wait_for("button_click", timeout=60*5,
                    check=lambda i: i.message.id==self.active_message.id and i.user.id==self.ctx.author.id)

            except TimeoutError:
                with suppress(NotFound):
                    self.am_embed.description = ""
                    self.am_embed.set_footer(text=f"You timed out on page [{self.current_page+1}/{len(self.images)}].\n")

                    self.am_embed.set_image(url=Embed.Empty)
                    self.am_embed.set_thumbnail(url=Embed.Empty)
                    await self.active_message.edit(embed=self.am_embed)
                    temp = await self.am_channel.send(content=f"{self.ctx.author.mention}, you timed out in your doujin. Forgot to press pause?", delete_after=1)
                    await temp.delete(delay=1)
        
                    await sleep(10)
                    await self.active_message.edit(content="<a:nreader_loading:810936543401213953> Closing...", embed=None)

                    await sleep(1)
                    await self.am_channel.delete()

                    break
            
            except BotInteractionCooldown:
                continue
            
            else:
                try:
                    if isinstance(interaction.component, list):
                        delay = await self.am_channel.send("Returned unexpected datatype. Please try again. If that fails, let the doujin time out and try again later.")
                        await delay.delete(delay=5)

                    self.bot.inactive = 0
                    if interaction.component.id == "next":  # Next page
                        self.current_page = self.current_page + 1
                        if self.current_page > (len(self.images)-1):  # Finish the doujin if at last page
                            self.am_embed.set_image(url=Embed.Empty)
                            self.am_embed.set_thumbnail(url=Embed.Empty)
                            self.am_embed.description = Embed.Empty
                            self.am_embed.set_footer(text="You finished this doujin.")
                            await self.active_message.edit(embed=self.am_embed)
                            if self.code in self.bot.user_data['UserData'][str(self.ctx.author.id)]['Lists']['Built-in']['Read Later|*n*|rl']:
                                self.bot.user_data['UserData'][str(self.ctx.author.id)]['Lists']['Built-in']['Read Later|*n*|rl'].remove(self.code)
                            
                            await sleep(2)
                            await self.active_message.edit(content="<a:nreader_loading:810936543401213953> Closing...", embed=None)

                            await sleep(1)
                            await self.am_channel.delete()
                            
                            break
                        else:
                            pass
                        
                        if self.code in self.bot.user_data['UserData'][str(self.ctx.author.id)]['Lists']['Built-in']['Bookmarks|*n*|bm'] and \
                            self.current_page == self.bot.user_data['UserData'][str(self.ctx.author.id)]['Lists']['Built-in']['Bookmarks|*n*|bm'][self.code]:
                            self.on_bookmarked_page = True
                        else:
                            self.on_bookmarked_page = False
                        
                        self.am_embed.set_footer(text=f"Page [{self.current_page+1}/{len(self.images)}] {'🔖' if self.on_bookmarked_page else ''}")
                        self.am_embed.set_image(url=self.images[self.current_page])
                        self.am_embed.set_thumbnail(url=self.images[self.current_page+1] if (self.current_page+1) in range(0, len(self.images)) else Embed.Empty)
                        
                        self.am_embed.description = f"<:nprev:853668227124953159>{'<:nfini:853670159310913576>' if self.current_page == (len(self.images)-1) else '<:nnext:853668227207790602>'} Previous|{'__**Finish**__' if self.current_page == (len(self.images)-1) else 'Next'}\n" \
                                                    f"<:nsele:853668227212902410><:nstop:853668227175546952> Select|Stop\n" \
                                                    f"<:npaus:853668227234529300><:nbook:853668227205038090> Pause|{'Bookmark' if not self.on_bookmarked_page else 'Unbookmark'}"

                        await self.bot.comp_ext.edit_component_msg(self.active_message, embed=self.am_embed,
                            components=[
                                [Button(emoji=self.bot.get_emoji(853668227124953159), style=2, id="prev", disabled=self.current_page==0),
                                Button(emoji=self.bot.get_emoji(853670159310913576) if self.current_page+1==len(self.images) else self.bot.get_emoji(853668227207790602), style=2, id="next"),
                                Button(emoji=self.bot.get_emoji(853668227212902410), style=2, id="sele"),
                                Button(emoji=self.bot.get_emoji(853668227175546952), style=2, id="stop"),
                                Button(emoji=self.bot.get_emoji(853668227234529300), style=2, id="paus")],
                                [Button(emoji=self.bot.get_emoji(853668227205038090), style=2, id="book"),
                                Button(emoji="⭐", style=2, id="fav"),
                                Button(label="Support Server", style=5, url="https://discord.gg/DJ4wdsRYy2")]])

                    elif interaction.component.id == "prev":  # Previous page
                        if self.current_page == 0:  # Not allowed to go behind zero
                            continue
                        
                        else:
                            self.current_page = self.current_page - 1
                        
                        if self.code in self.bot.user_data['UserData'][str(self.ctx.author.id)]['Lists']['Built-in']['Bookmarks|*n*|bm'] and \
                            self.current_page == self.bot.user_data['UserData'][str(self.ctx.author.id)]['Lists']['Built-in']['Bookmarks|*n*|bm'][self.code]:
                            self.on_bookmarked_page = True
                        else:
                            self.on_bookmarked_page = False
                        
                        self.am_embed.set_footer(text=f"Page [{self.current_page+1}/{len(self.images)}] {'🔖' if self.on_bookmarked_page else ''}")
                        self.am_embed.set_image(url=self.images[self.current_page])
                        self.am_embed.set_thumbnail(url=self.images[self.current_page+1] if (self.current_page+1) in range(0, len(self.images)) else Embed.Empty)
                        
                        self.am_embed.description = f"<:nprev:853668227124953159>{'<:nfini:853670159310913576>' if self.current_page == (len(self.images)-1) else '<:nnext:853668227207790602>'} Previous|{'__**Finish**__' if self.current_page == (len(self.images)-1) else 'Next'}\n" \
                                                    f"<:nsele:853668227212902410><:nstop:853668227175546952> Select|Stop\n" \
                                                    f"<:npaus:853668227234529300><:nbook:853668227205038090> Pause|{'Bookmark' if not self.on_bookmarked_page else 'Unbookmark'}"
                        
                        await self.bot.comp_ext.edit_component_msg(self.active_message, embed=self.am_embed,
                            components=[
                                [Button(emoji=self.bot.get_emoji(853668227124953159), style=2, id="prev", disabled=self.current_page==0),
                                Button(emoji=self.bot.get_emoji(853670159310913576) if self.current_page+1==len(self.images) else self.bot.get_emoji(853668227207790602), style=2, id="next"),
                                Button(emoji=self.bot.get_emoji(853668227212902410), style=2, id="sele"),
                                Button(emoji=self.bot.get_emoji(853668227175546952), style=2, id="stop"),
                                Button(emoji=self.bot.get_emoji(853668227234529300), style=2, id="paus")],
                                [Button(emoji=self.bot.get_emoji(853668227205038090), style=2, id="book"),
                                Button(emoji="⭐", style=2, id="fav"),
                                Button(label="Support Server", style=5, url="https://discord.gg/DJ4wdsRYy2")]])
                    
                    elif interaction.component.id == "sele":  # Select page
                        await interaction.respond(type=6)
                        bm_page = None
                        if self.code in self.bot.user_data['UserData'][str(self.ctx.author.id)]['Lists']['Built-in']['Bookmarks|*n*|bm']:
                            bm_page = self.bot.user_data['UserData'][str(self.ctx.author.id)]['Lists']['Built-in']['Bookmarks|*n*|bm'][self.code]
                        
                        conf = await self.am_channel.send(embed=Embed(
                            description=f"Enter a page number within 15 seconds, or type `n-cancel` to cancel."
                                        f"{newline+'Bookmarked page: '+str(bm_page) if bm_page else ''}"))

                        while True:
                            try:
                                m = await self.bot.wait_for("message", timeout=15, bypass_cooldown=True,
                                    check=lambda m: m.author.id == self.ctx.author.id and m.channel.id == self.am_channel.id)
                            
                            except TimeoutError:
                                await conf.delete()
                                break

                            else:
                                await m.delete()
                                if m.content == "n-cancel":
                                    await conf.delete()
                                    break
                                
                                if is_int(m.content) and (int(m.content)-1) in range(0, len(self.images)):
                                    await conf.delete()
                                    self.current_page = int(m.content)-1
                                    
                                    if self.code in self.bot.user_data['UserData'][str(self.ctx.author.id)]['Lists']['Built-in']['Bookmarks|*n*|bm'] and \
                                        self.current_page == self.bot.user_data['UserData'][str(self.ctx.author.id)]['Lists']['Built-in']['Bookmarks|*n*|bm'][self.code]:
                                        self.on_bookmarked_page = True
                                    else:
                                        self.on_bookmarked_page = False

                                    self.am_embed.set_footer(text=f"Page [{self.current_page+1}/{len(self.images)}] {'🔖' if self.on_bookmarked_page else ''}")
                                    self.am_embed.set_image(url=self.images[self.current_page])
                                    self.am_embed.set_thumbnail(url=self.images[self.current_page+1] if (self.current_page+1) in range(0, len(self.images)) else Embed.Empty)
                                    
                                    self.am_embed.description = f"<:nprev:853668227124953159>{'<:nfini:853670159310913576>' if self.current_page == (len(self.images)-1) else '<:nnext:853668227207790602>'} Previous|{'__**Finish**__' if self.current_page == (len(self.images)-1) else 'Next'}\n" \
                                                                f"<:nsele:853668227212902410><:nstop:853668227175546952> Select|Stop\n" \
                                                                f"<:npaus:853668227234529300><:nbook:853668227205038090> Pause|{'Bookmark' if not self.on_bookmarked_page else 'Unbookmark'}"

                                    await self.bot.comp_ext.edit_component_msg(self.active_message, embed=self.am_embed,
                                        components=[
                                            [Button(emoji=self.bot.get_emoji(853668227124953159), style=2, id="prev", disabled=self.current_page==0),
                                            Button(emoji=self.bot.get_emoji(853670159310913576) if self.current_page+1==len(self.images) else self.bot.get_emoji(853668227207790602), style=2, id="next"),
                                            Button(emoji=self.bot.get_emoji(853668227212902410), style=2, id="sele"),
                                            Button(emoji=self.bot.get_emoji(853668227175546952), style=2, id="stop"),
                                            Button(emoji=self.bot.get_emoji(853668227234529300), style=2, id="paus")],
                                            [Button(emoji=self.bot.get_emoji(853668227205038090), style=2, id="book"),
                                            Button(emoji="⭐", style=2, id="fav"),
                                            Button(label="Support Server", style=5, url="https://discord.gg/DJ4wdsRYy2")]])
                                    
                                    break
                                
                                else:
                                    continue
                    
                    elif interaction.component.id == "paus":  # Pause and send to recall
                        self.am_embed.set_image(url=Embed.Empty)
                        self.am_embed.set_thumbnail(url=Embed.Empty)
                        self.am_embed.description = Embed.Empty
                        self.am_embed.set_footer(text=f"You paused this doujin on page [{self.current_page+1}/{len(self.images)}].")
                        await self.active_message.edit(embed=self.am_embed)
                        
                        try: await interaction.respond(type=6)
                        except NotFound: continue

                        await sleep(2)
                        await self.active_message.edit(content="<a:nreader_loading:810936543401213953> Closing...", embed=None)
                        
                        await sleep(1)
                        await self.am_channel.delete()
                        
                        await sleep(1)
                        self.bot.user_data["UserData"][str(self.ctx.author.id)]["Recall"] = f"{self.code}*n*{self.current_page}"
                        await self.ctx.author.send(embed=Embed(
                            title="Recall saved.",
                            description=f"Doujin `{self.code}` saved to recall to page [{self.current_page+1}/{len(self.images)}].\n"
                                        f"To get back to this page, run the `n!recall` command to instantly open a new reader starting on that page."))

                        break

                    elif interaction.component.id == "stop":  # Stop entirely
                        self.am_embed.set_image(url=Embed.Empty)
                        self.am_embed.set_thumbnail(url=Embed.Empty)
                        self.am_embed.description = Embed.Empty
                        self.am_embed.set_footer(text=f"You stopped this doujin on page [{self.current_page+1}/{len(self.images)}].")
                        await self.active_message.edit(embed=self.am_embed)

                        try: await interaction.respond(type=6)
                        except NotFound: continue
                        
                        await sleep(2)
                        await self.active_message.edit(content="<a:nreader_loading:810936543401213953> Closing...", embed=None)
                        
                        await sleep(1)
                        await self.am_channel.delete()
                        
                        break
                    
                    elif interaction.component.id == "book":  # Set/Remove bookmark
                        if not self.on_bookmarked_page:
                            if self.current_page == 0:
                                await interaction.respond(embed=Embed(
                                    color=0xFF0000,
                                    description="You cannot bookmark the first page. Use favorites instead!"
                                ).set_footer(text="You may dismiss this message."))
                                continue

                            self.bot.user_data['UserData'][str(self.ctx.author.id)]['Lists']['Built-in']['Bookmarks|*n*|bm'][self.code] = self.current_page
                            self.on_bookmarked_page = True
                        
                        else:
                            if self.code in self.bot.user_data['UserData'][str(self.ctx.author.id)]['Lists']['Built-in']['Bookmarks|*n*|bm']:
                                self.bot.user_data['UserData'][str(self.ctx.author.id)]['Lists']['Built-in']['Bookmarks|*n*|bm'].pop(self.code)
                                self.on_bookmarked_page = False
                        
                        self.am_embed.description = f"<:nprev:853668227124953159>{'<:nfini:853670159310913576>' if self.current_page == (len(self.images)-1) else '<:nnext:853668227207790602>'} Previous|{'__**Finish**__' if self.current_page == (len(self.images)-1) else 'Next'}\n" \
                                                    f"<:nsele:853668227212902410><:nstop:853668227175546952> Select|Stop\n" \
                                                    f"<:npaus:853668227234529300><:nbook:853668227205038090> Pause|{'Bookmark' if not self.on_bookmarked_page else 'Unbookmark'}"
                        self.am_embed.set_footer(text=f"Page [{self.current_page+1}/{len(self.images)}] {'🔖' if self.on_bookmarked_page else ''}")
                        
                        await self.active_message.edit(embed=self.am_embed)

                    elif interaction.component.id == "fav":  # Add to favorites
                        if self.code not in self.bot.user_data['UserData'][str(self.ctx.author.id)]['Lists']['Built-in']['Favorites|*n*|fav']:
                            self.bot.user_data['UserData'][str(self.ctx.author.id)]['Lists']['Built-in']['Favorites|*n*|fav'].append(self.code)

                            await interaction.respond(embed=Embed(
                                description=f"✅ Added `{self.code}` to your favorites."
                            ).set_footer(text="You may dismiss this message."))
                        else:
                            self.bot.user_data['UserData'][str(self.ctx.author.id)]['Lists']['Built-in']['Favorites|*n*|fav'].remove(self.code)

                            await interaction.respond(embed=Embed(
                                description=f"✅ Removed `{self.code}` from your favorites."
                            ).set_footer(text="You may dismiss this message."))

                    # Respond if not already
                    try: await interaction.respond(type=6)
                    except NotFound: continue

                except Exception:
                    error = exc_info()
                    temp = await self.am_channel.send(embed=Embed(
                        color=0xFF0000,
                        description="An unhandled error occured; Please try again.\n"
                                    "If the issue persists, please try reopening the doujin.\n"
                                    "If reopening doesn't work, click the `Support Server` button."
                        ).set_footer(text="This message will disappear in 10 seconds."),
                        delete_after=10)
                    
                    await temp.delete(delay=10)
                        
                    await self.bot.errorlog.send(error, ctx=self.ctx, event="ImagePageReader")
                    
                    continue

        return

class SearchResultsBrowser:
    def __init__(self, bot: Bot, ctx: Context, results: List[Doujin], **kwargs):
        """Class to create and run a browser from NHentai-API

        `results` - obtained from nhentai_api.search(query); Modified `SearchPage` to contain real Doujins, not DoujinThumbnails.
        `msg` - optional message that the bot owns to edit, otherwise created 
        """
        self.bot = bot
        self.ctx = ctx
        self.doujins = results
        self.index = 0
        self.active_message: Message = kwargs.pop("msg", None)
        self.lolicon_allowed = kwargs.pop("lolicon_allowed", None)
        self.name = kwargs.pop("name", "Search Results")

        self.am_embed: Embed = None
    
    async def update_browser(self, ctx):
        message_part = []
        for ind, dj in enumerate(self.doujins):
            try: 
                if ind == self.index and int(dj.id) in self.bot.user_data['UserData'][str(self.ctx.author.id)]['nFavorites']['Doujins']: symbol = '🟩'
                elif ind == self.index: symbol='🟥'
                elif int(dj.id) in self.bot.user_data['UserData'][str(self.ctx.author.id)]['nFavorites']['Doujins']: symbol = '🟦'
                else: symbol='⬛'
            except KeyError: 
                symbol='⬛'
            
            if ("lolicon" in dj.tags or "shotacon" in dj.tags) and self.ctx.guild and not self.lolicon_allowed:
                message_part.append(f"`{symbol} {str(ind+1).ljust(2)}` | __`       `__ | ⚠🚫 | Not available in this server.")
            else:
                message_part.append(
                    f"{'**' if ind == self.index else ''}"
                    f"`{symbol} {str(ind+1).ljust(2)}` | "
                    f"__`{str(self.doujins[ind].id).ljust(7)}`__ | "
                    f"{language_to_flag(self.doujins[ind].languages)} | "
                    f"{shorten(self.doujins[ind].title, width=40, placeholder='...')}{'**' if ind == self.index else ''}")

        self.am_embed = Embed(
            title=self.name,
            description=f"\n"+('\n'.join(message_part))+"\n\n▌█████████████████▓▓▒▒░░")
            
        self.am_embed.set_author(
            name="NHentai",
            url=f"https://nhentai.net/",
            icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")

        nhentai_api = NHentai()
        if self.doujins[self.index].id not in self.bot.doujin_cache:
            doujin = await nhentai_api.get_doujin(self.doujins[self.index].id)
            self.bot.doujin_cache[self.doujins[self.index].id] = doujin
        else:
            doujin = self.bot.doujin_cache[self.doujins[self.index].id]
        
        if ("lolicon" in doujin.tags or "shotacon" in doujin.tags) and self.ctx.guild and not self.lolicon_allowed:
            self.am_embed.add_field(
                name="Main Title",
                inline=False,
                value="No information available.\n"
                      "This doujin cannot be viewed here.")
            
            doujin.images[0] = str(self.bot.user.avatar_url)
        
        else:
            self.am_embed.add_field(
                name=f"Main Title",
                inline=False,
                value=f"{doujin.title}"
            ).add_field(
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
            
        previous_emb = deepcopy(self.active_message.embeds[0])
        if previous_emb.image:
            self.am_embed.set_image(url=doujin.images[0])
            self.am_embed.set_thumbnail(url=Embed.Empty)
        elif previous_emb.thumbnail:
            self.am_embed.set_thumbnail(url=doujin.images[0])
            self.am_embed.set_image(url=Embed.Empty)
        else:  # Image wasn't set yet
            self.am_embed.set_thumbnail(url=doujin.images[0])

        if self.active_message:
            await self.bot.comp_ext.edit_component_msg(self.active_message, embed=self.am_embed,
                components=[
                    [Button(emoji=self.bot.get_emoji(853800909108936754), style=2, id="up"),
                    Button(emoji=self.bot.get_emoji(853800909276315678), style=2, id="down"),
                    Button(emoji=self.bot.get_emoji(853668227212902410), style=2, id="select"),
                    Button(emoji=self.bot.get_emoji(853668227175546952), style=2, id="stop"),
                    Button(emoji=self.bot.get_emoji(853684136379416616), style=2, id="read")],
                    [Button(emoji=self.bot.get_emoji(853684136433942560), style=2, id="zoom"),
                    Button(emoji=self.bot.get_emoji(853668227205038090), style=2, id="readlater"),
                    Button(label="Support Server", style=5, url="https://discord.gg/DJ4wdsRYy2")]]),
        else:
            self.active_message = await self.bot.comp_ext.send_component_msg(self.ctx, embed=self.am_embed,
                components=[
                    [Button(emoji=self.bot.get_emoji(853800909108936754), style=2, id="up"),
                    Button(emoji=self.bot.get_emoji(853800909276315678), style=2, id="down"),
                    Button(emoji=self.bot.get_emoji(853668227212902410), style=2, id="select"),
                    Button(emoji=self.bot.get_emoji(853668227175546952), style=2, id="stop"),
                    Button(emoji=self.bot.get_emoji(853684136379416616), style=2, id="read")],
                    [Button(emoji=self.bot.get_emoji(853684136433942560), style=2, id="zoom"),
                    Button(emoji=self.bot.get_emoji(853668227205038090), style=2, id="readlater"),
                    Button(label="Support Server", style=5, url="https://discord.gg/DJ4wdsRYy2")]]),
            
            await sleep(0.5)
    
    async def start(self, ctx):
        """Initial start of the result browser."""

        await self.update_browser(self.ctx)

        while True:
            try:
                interaction = await self.bot.wait_for("button_click", timeout=300, 
                    check=lambda i: \
                        i.message.id == self.active_message.id and \
                        i.user.id == self.ctx.author.id)
            except TimeoutError:
                message_part = []
                for ind, dj in enumerate(self.doujins):
                    message_part.append(
                        f"{'**' if ind == self.index else ''}__`{str(self.doujins[ind].id).ljust(7)}`__{'**' if ind == self.index else ''} | "
                        f"{language_to_flag(self.doujins[ind].languages)} | "
                        f"{shorten(self.doujins[ind].title, width=50, placeholder='...')}")
                
                self.am_embed = Embed(
                    title=self.name,
                    description=f"\n"+('\n'.join(message_part)))
                self.am_embed.set_author(
                    name="NHentai",
                    url=f"https://nhentai.net/",
                    icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
                

                self.am_embed.set_thumbnail(url=Embed.Empty)
                self.am_embed.set_image(url=Embed.Empty)

                await self.bot.comp_ext.edit_component_msg(self.active_message, embed=self.am_embed, components=[])
                
                return

            except BotInteractionCooldown:
                continue
            
            else:
                try:
                    self.bot.inactive = 0
                    
                    if interaction.component.id == "up":
                        if self.index > 0:
                            self.index -= 1
                            await self.update_browser(self.ctx)
                        elif self.index == 0:
                            self.index = len(self.doujins)-1
                            await self.update_browser(self.ctx)

                    elif interaction.component.id == "down":
                        if self.index < len(self.doujins)-1:
                            self.index += 1
                            await self.update_browser(self.ctx)
                        elif self.index == len(self.doujins)-1:
                            self.index = 0
                            await self.update_browser(self.ctx)
                    
                    elif interaction.component.id == "select":
                        await interaction.respond(
                            embed=Embed(
                                description="Enter a result number within 15 seconds, or type `n-cancel` to cancel.\n"
                                            "Your message will be deleted to keep clean."
                            ).set_footer(text="You may dismiss this message, but the controls won't work until you respond or time out."))

                        while True:
                            try:
                                m = await self.bot.wait_for("message", timeout=15, bypass_cooldown=True,
                                    check=lambda m: m.author.id == self.ctx.author.id and m.channel.id == self.ctx.channel.id)
                            
                            except TimeoutError:
                                break

                            else:
                                await m.delete()
                                if m.content == "n-cancel":
                                    break
                                
                                if is_int(m.content) and (int(m.content)-1) in range(0, len(self.doujins)):
                                    self.index = int(m.content)-1
                                    await self.update_browser(self.ctx)
                                    break

                                else:
                                    continue
                    
                    elif interaction.component.id == "stop":
                        message_part = []
                        for ind, dj in enumerate(self.doujins):                        
                            if ("lolicon" in dj.tags or "shotacon" in dj.tags) and self.ctx.guild and not self.lolicon_allowed:
                                message_part.append("__`       `__ | ⚠🚫 | Not available in this server.")
                            else:
                                message_part.append(
                                    f"__`{str(dj.id).ljust(7)}`__ | "
                                    f"{language_to_flag(dj.languages)} | "
                                    f"{shorten(dj.title, width=50, placeholder='...')}")
                        
                        self.am_embed = Embed(
                            title=self.name,
                            description=f"\n"+('\n'.join(message_part)))

                        self.am_embed.set_author(
                            name="NHentai",
                            url=f"https://nhentai.net/",
                            icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
                        
                        self.am_embed.set_thumbnail(url=Embed.Empty)
                        self.am_embed.set_image(url=Embed.Empty)
                        await self.bot.comp_ext.edit_component_msg(self.active_message, embed=self.am_embed, components=[])
                        
                        return
                    
                    elif interaction.component.id == "read":
                        if ("lolicon" in self.doujins[self.index].tags or "shotacon" in self.doujins[self.index].tags) and self.ctx.guild and not self.lolicon_allowed:
                            continue
                        
                        await self.active_message.clear_reactions()

                        message_part = []
                        for ind, dj in enumerate(self.doujins):                        
                            if ("lolicon" in dj.tags or "shotacon" in dj.tags) and self.ctx.guild and not self.lolicon_allowed:
                                message_part.append("__`       `__ | ⚠🚫 | Not available in this server.")
                            else:
                                message_part.append(
                                f"{'**' if ind == self.index else ''}"
                                f"__`{str(self.doujins[ind].id).ljust(7)}`__ | "
                                f"{language_to_flag(self.doujins[ind].languages)} | "
                                f"{shorten(self.doujins[ind].title, width=40, placeholder='...')}{'**' if ind == self.index else ''}")

                        self.am_embed = Embed(
                            title=self.name,
                            description=f"\n"+('\n'.join(message_part)))
                        self.am_embed.set_author(
                            name="NHentai",
                            url=f"https://nhentai.net/",
                            icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
                        
                        self.am_embed.set_thumbnail(url=Embed.Empty)
                        self.am_embed.set_image(url=Embed.Empty)

                        await self.active_message.edit(content='', embed=self.am_embed)
                        await interaction.respond(type=6)  # Respond now since this option returns.

                        doujin = self.doujins[self.index]
                        session = ImagePageReader(self.bot, ctx, doujin.images, f"{doujin.id} [*n*] {doujin.title}", str(doujin.id))
                        response = await session.setup()
                        if response:
                            await session.start()
                        else:
                            await self.active_message.edit(embed=self.am_embed)

                        return
                    
                    elif interaction.component.id == "zoom":
                        emb = deepcopy(self.am_embed)
                        if not emb.image:
                            self.am_embed.set_image(url=emb.thumbnail.url)
                            self.am_embed.set_thumbnail(url=Embed.Empty)
                        elif not emb.thumbnail:
                            self.am_embed.set_thumbnail(url=emb.image.url)
                            self.am_embed.set_image(url=Embed.Empty)
                        
                        await self.active_message.edit(embed=self.am_embed)

                    elif interaction.component.id == "readlater":
                        if self.doujins[self.index].id not in self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["Read Later|*n*|rl"]:
                            self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["Read Later|*n*|rl"].append(str(self.doujins[self.index].id))
                            await interaction.respond(
                                mention_author=False,
                                embed=Embed(
                                    description=f"✅ Added `{self.doujins[self.index].id}` to your To Read list."
                                ).set_footer(text="You may dismiss this message."))
                        else:
                            self.bot.user_data["UserData"][str(self.ctx.author.id)]["Lists"]["Built-in"]["Read Later|*n*|rl"].remove(str(self.doujins[self.index].id))
                            await interaction.respond(
                                mention_author=False,
                                embed=Embed(
                                    description=f"✅ Removed `{self.doujins[self.index].id}` from your To Read list."
                                ).set_footer(text="You may dismiss this message."))
                    
                    # Respond if not already
                    try: await interaction.respond(type=6)
                    except NotFound: continue
            
                except Exception:
                    error = exc_info()
                    temp = await self.ctx.send(embed=Embed(
                        color=0xFF0000,
                        description="An unhandled error occured; Please try again.\n"
                                    "If the issue persists, please try searching again.\n"
                                    "If searching again doesn't work, click the `Support Server` button."
                        ).set_footer(text="This message will disappear in 10 seconds."),
                        delete_after=10)
                    
                    await temp.delete(delay=10)
                        
                    await self.bot.errorlog.send(error, ctx=self.ctx, event="ImagePageReader")
                    
                    continue

def setup(bot):
    bot.add_cog(Classes(bot))
