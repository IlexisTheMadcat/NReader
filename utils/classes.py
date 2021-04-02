# IMPORTS
from os import getcwd
from sys import exc_info
from typing import List
from copy import deepcopy
from textwrap import shorten
from asyncio import sleep
from asyncio.exceptions import TimeoutError
from contextlib import suppress

from expiringdict import ExpiringDict
from discord import Message, Embed as DiscordEmbed, Forbidden, TextChannel
from discord.ext.commands.context import Context
from discord.ext.commands.bot import Bot as DiscordBot
from discord.utils import get
from NHentai import NHentai

from utils.errorlog import ErrorLog
from utils.utils import language_to_flag, is_int, is_float


# Override default color for bot fanciness
class Embed(DiscordEmbed):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.color = 0xEC2854
        self.colour = self.color


class Paginator:
    def __init__(
            self,
            page_limit: int = 1000,
            trunc_limit: int = 2000,
            headers: List[str] = None,
            header_extender: str = u'\u200b'
    ):
        self.page_limit = page_limit
        self.trunc_limit = trunc_limit
        self._pages = None
        self._headers = None
        self._header_extender = header_extender
        self.set_headers(headers)

    @property
    def pages(self):
        if self._headers:
            self._extend_headers(len(self._pages))
            headers, self._headers = self._headers, None
            return [
                (headers[i], self._pages[i]) for i in range(len(self._pages))
            ]
        else:
            return self._pages

    def set_headers(self, headers: List[str] = None):
        self._headers = headers

    def set_header_extender(self, header_extender: str = u'\u200b'):
        self._header_extender = header_extender

    def _extend_headers(self, length: int):
        while len(self._headers) < length:
            self._headers.append(self._header_extender)

    def set_trunc_limit(self, limit: int = 2000):
        self.trunc_limit = limit

    def set_page_limit(self, limit: int = 1000):
        self.page_limit = limit

    def paginate(self, value):
        """
        To paginate a string into a list of strings under
        `self.page_limit` characters. Total len of strings
        will not exceed `self.trunc_limit`.
        :param value: string to paginate
        :return list: list of strings under 'page_limit' chars
        """
        spl = str(value).split('\n')
        ret = []
        page = ''
        total = 0
        for i in spl:
            if total + len(page) < self.trunc_limit:
                if (len(page) + len(i)) < self.page_limit:
                    page += '\n{}'.format(i)
                else:
                    if page:
                        total += len(page)
                        ret.append(page)
                    if len(i) > (self.page_limit - 1):
                        tmp = i
                        while len(tmp) > (self.page_limit - 1):
                            if total + len(tmp) < self.trunc_limit:
                                total += len(tmp[:self.page_limit])
                                ret.append(tmp[:self.page_limit])
                                tmp = tmp[self.page_limit:]
                            else:
                                ret.append(tmp[:self.trunc_limit - total])
                                break
                        else:
                            page = tmp
                    else:
                        page = i
            else:
                ret.append(page[:self.trunc_limit - total])
                break
        else:
            ret.append(page)
        self._pages = ret
        return self.pages


class Bot(DiscordBot):

    def __init__(self, *args, **kwargs):

        # Namespace variables, not saved to files
        self.inactive = 0  # Timer to track minutes since responded to a command
        self.waiting: list = list()  # Users waiting for a response from developer
        self.cwd = getcwd()  # Global bot directory
        self.text_status = f"{kwargs.get('command_prefix')}help"  # Change first half of text status

        # Namespace variable to indicate if a support thread is open or not.
        # If true, the developer cannot accept a support message if another is already active.
        self.thread_active = False

        # Alias for user_data['config']
        self.config = kwargs.pop("config") 

         # Online database
        self.database = kwargs.pop("database")

        # Local copy of the database
        self.user_data = kwargs.pop("user_data")
        print("[] Loaded data.")

        # Attribute for accessing tokens from database
        self.auth = kwargs.pop("auth")

        # A cache of loaded doujins, it will fill as doujins are retrieved by code.
        # It is a DICTIONARY of DICTIONARY. 
        # Values expire in 1 day since addition or resets when bot reloads.
        self.doujin_cache = ExpiringDict(max_len=float('inf'), max_age_seconds=86400)

        # Get the channel ready for errorlog
        # Bot.get_channel method not available until on_ready
        self.errorlog_channel: int = kwargs.pop("errorlog", None)
        self.errorlog: ErrorLog = kwargs.get("errorlog", None)

        # Load bot arguments into __init__
        super().__init__(*args, **kwargs)

    def run(self, *args, **kwargs):
        print("[BOT INIT] Logging in with token...")
        super().run(self.auth["BOT_TOKEN"], *args, **kwargs)
    
    async def on_error(self, event_name, *args, **kwargs):
        '''Error handler for Exceptions raised in events'''
        if self.config["debug_mode"]:  # Hold true the purpose for the debug_mode option
            await super().on_error(event_method=event_name, *args, **kwargs)
            return
        
        # Try to get Exception that was raised
        error = exc_info()  # `from sys import exc_info` at the top of your script

        # If the Exception raised is successfully captured, use ErrorLog
        if error:
            await self.errorlog.send(error, event=event_name)

        # Otherwise, use default handler
        else:
            await super().on_error(event_method=event_name, *args, **kwargs)


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
        pass


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
    def create_description(self, dictionary, depth=0, message_lines=list(), path=[0]):
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
                self.create_description(dictionary[k], depth+1, message_lines, path)
            
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
                    path, (k,v), 
                    len(dictionary.items()), 
                    len(path) > 0, 
                    isinstance(v, dict))
            
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
                            check=lambda m: m.author.id == self.ctx.author.id and m.channel.id == self.ctx.author.id)
                    except TimeoutError:
                        self.am_embed.set_footer(text=f"🔼🔽◀▶🔢💾 |Up|Down|Parent|Children|Input|Save|")
                        await self.active_message.edit(embed=self.am_embed)
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
    def __init__(self, bot: Bot, ctx: Context, images:list, name:str, **kwargs):
        """Create and run a reader based on pages from a Doujin. 
        To work for any purpose, this class needs a few changes.
        
        `bot` - The Bot class created on initialization
        `ctx` - Context used
        `images` The list of image urls to use
        `name` - Title of the reader
        `**kwargs` - Further keyword arguments if need be

        This class in particular requires a certain format for `name`:
        `f"{int()} || {str()}"`, where int would be an object id and str for title.
        """
        self.bot = bot
        self.current_page: int = 0
        self.images: list = images
        self.name: str = name
        self.code: str = self.name.split('[*n*]')[0].strip(" ")
        self.ctx: Context = ctx
        self.active_message: Message = None
        self.am_embed: Embed = None
        self.am_channel: TextChannel = None
        self.is_paused: bool = False
        self.on_bookmarked_page: bool = False

    async def setup(self):
        if str(self.ctx.author.id) not in self.bot.user_data["UserData"]:
            self.bot.user_data["UserData"][str(self.ctx.author.id)] = {}
        if "nFavorites" not in self.bot.user_data["UserData"][str(self.ctx.author.id)]:
            self.bot.user_data["UserData"][str(self.ctx.author.id)]["nFavorites"] = {}
        if "Bookmarks" not in self.bot.user_data["UserData"][str(self.ctx.author.id)]["nFavorites"]:
            self.bot.user_data["UserData"][str(self.ctx.author.id)]["nFavorites"]["Bookmarks"] = {}

        edit = await self.ctx.send("<a:nreader_loading:810936543401213953>")
        self.am_embed: Embed = Embed(
            color=0xEC2854,
            description=f"Active emojis will appear here.\n" \
                        "▶ Play")
        self.am_embed.set_author(
            name=self.name,
            icon_url="https://cdn.discordapp.com/attachments/742481946030112779/759591081758949410/emote.png")
        self.am_embed.set_footer(
            text=f"Page [0/{len(self.images)}]: Press ▶ Play to start reading.")

        # Fetch existing category for readers, otherwise create new
        cat = get(self.ctx.guild.categories, name="📖NReader")
        if not cat:
            cat = await self.ctx.guild.create_category_channel(name="📖NReader")

        # Create reader channel under category
        channel = await cat.create_text_channel(name=f"📖nreader-{self.ctx.message.id}", nsfw=True)

        # Set channel permissions
        await channel.set_permissions(self.ctx.guild.me, read_messages=True)
        await channel.set_permissions(self.ctx.guild.default_role, read_messages=False)
        await channel.set_permissions(self.ctx.author, read_messages=True)

        # Reader message
        conf = await channel.send(content=self.ctx.author.mention, embed=self.am_embed)

        # Portal
        await edit.edit(
            content=conf.channel.mention, 
            embed=Embed(
                description="Click/Tap the mention above to jump to your reader."
                ).set_author(
                    name=self.bot.user.name,
                    icon_url=self.bot.user.avatar_url), 
                delete_after=10)
        
        await conf.add_reaction("▶")
        
        def check(reaction, user):
            return reaction.message.id == conf.id and \
                str(reaction.emoji) == "▶" and str(user.id) == str(self.ctx.author.id)
        
        try:
            await self.bot.wait_for("reaction_add", timeout=30, check=check)
        except TimeoutError:
            await conf.edit(content="<a:nreader_loading:810936543401213953> Closing...")
            
            await sleep(1)
            await conf.channel.delete()
            return False
        else:
            self.active_message = conf
            self.am_channel = conf.channel
            await self.active_message.clear_reactions()
            
            edit = await self.am_channel.send("<a:nreader_loading:810936543401213953>")
            self.am_embed.description = "⏮⏭ Previous|Next\n🔢⏹ Select|Stop\n⏸🔖 Pause|Bookmark"
            self.am_embed.set_image(url=self.images[0])
            self.am_embed.set_footer(text=f"Page [{self.current_page+1}/{len(self.images)}]")
            self.am_embed.set_thumbnail(url=self.images[self.current_page+1] if (self.current_page+1) in range(0, len(self.images)) else Embed.Empty)
            await self.active_message.edit(embed=self.am_embed)

            await self.active_message.add_reaction("⏮")
            await self.active_message.add_reaction("⏭")
            await self.active_message.add_reaction("🔢")
            await self.active_message.add_reaction("⏹")
            await self.active_message.add_reaction("⏸")
            await self.active_message.add_reaction("🔖")
            await sleep(0.2)
            await edit.delete()
            return True

    async def start(self):
        while True:
            def check(reaction, user):
                return reaction.message.id == self.active_message.id and \
                    str(reaction.emoji) in ["⏮", "⏭", "🔢", "⏹", "⏸", "▶", "🔖", "❌"] and \
                    str(user.id) == str(self.ctx.author.id)

            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=60*5, check=check)
            except TimeoutError:
                await self.active_message.clear_reactions()
                
                self.am_embed.description = ""
                self.am_embed.set_footer(text=f"You timed out on page [{self.current_page+1}/{len(self.images)}].\n")

                self.am_embed.set_image(url=Embed.Empty)
                self.am_embed.set_thumbnail(url=Embed.Empty)
                await self.active_message.edit(embed=self.am_embed)
                await self.am_channel.send(content=f"|🔔| {self.ctx.author.mention}, you timed out in your doujin. Forgot to press pause?", delete_after=1)
        
                await sleep(10)
                await self.active_message.edit(content="<a:nreader_loading:810936543401213953> Closing...", embed=None)

                await sleep(1)
                await self.am_channel.delete()

                break
            else:
                if str(reaction.emoji) == "⏭":  # Next page
                    await self.active_message.remove_reaction("⏭", self.ctx.author)

                    self.current_page = self.current_page + 1
                    if self.current_page > (len(self.images)-1):  # Finish the doujin if at last page
                        await self.active_message.clear_reactions()
                        
                        self.am_embed.set_image(url=Embed.Empty)
                        self.am_embed.set_thumbnail(url=Embed.Empty)
                        self.am_embed.description = Embed.Empty
                        self.am_embed.set_footer(text="You finished this doujin.")
                        await self.active_message.edit(embed=self.am_embed)
                        
                        await sleep(2)
                        await self.active_message.edit(content="<a:nreader_loading:810936543401213953> Closing...", embed=None)

                        await sleep(1)
                        await self.am_channel.delete()
                        
                        break
                    else:
                        pass
                    
                    if self.code in self.bot.user_data['UserData'][str(self.ctx.author.id)]['nFavorites']['Bookmarks']:
                        if self.current_page == self.bot.user_data['UserData'][str(self.ctx.author.id)]['nFavorites']['Bookmarks'][self.code]:
                            self.on_bookmarked_page = True
                            await self.active_message.remove_reaction("🔖", self.bot.user)
                            await self.active_message.add_reaction("❌")
                        else:
                            self.on_bookmarked_page = False
                            await self.active_message.remove_reaction("❌", self.bot.user)
                            await self.active_message.add_reaction("🔖")
                    
                    self.am_embed.set_footer(text=f"Page [{self.current_page+1}/{len(self.images)}] {'Bookmarked' if self.on_bookmarked_page else ''}")
                    self.am_embed.set_image(url=self.images[self.current_page])
                    self.am_embed.set_thumbnail(url=self.images[self.current_page+1] if (self.current_page+1) in range(0, len(self.images)) else Embed.Empty)
                    self.am_embed.description = f"⏮⏭ Previous|{'**__Finish__**' if self.current_page == (len(self.images)-1) else 'Next'}\n🔢⏹ Select|Stop\n⏸{'🔖 Pause|Bookmark' if not self.on_bookmarked_page else '❌ Pause|Unbookmark'}"

                    await self.active_message.edit(embed=self.am_embed)
                    
                    continue

                elif str(reaction.emoji) == "⏮":  # Previous page
                    await self.active_message.remove_reaction("⏮", self.ctx.author)

                    if self.current_page == 0:  # Not allowed to go behind zero
                        continue
                    else:
                        self.current_page = self.current_page - 1
                    
                    if self.code in self.bot.user_data['UserData'][str(self.ctx.author.id)]['nFavorites']['Bookmarks']:
                        if self.current_page == self.bot.user_data['UserData'][str(self.ctx.author.id)]['nFavorites']['Bookmarks'][self.code]:
                            self.on_bookmarked_page = True
                            await self.active_message.remove_reaction("🔖", self.bot.user)
                            await self.active_message.add_reaction("❌")
                        else:
                            self.on_bookmarked_page = False
                            await self.active_message.remove_reaction("❌", self.bot.user)
                            await self.active_message.add_reaction("🔖")
                    
                    self.am_embed.set_footer(text=f"Page [{self.current_page+1}/{len(self.images)}] {'Bookmarked' if self.on_bookmarked_page else ''}")
                    self.am_embed.set_image(url=self.images[self.current_page])
                    self.am_embed.set_thumbnail(url=self.images[self.current_page+1] if (self.current_page+1) in range(0, len(self.images)) else Embed.Empty)
                    self.am_embed.description = f"⏮⏭ Previous|Next\n🔢⏹ Select|Stop\n⏸{'🔖 Pause|Bookmark' if not self.on_bookmarked_page else '❌ Pause|Unbookmark'}"

                    await self.active_message.edit(embed=self.am_embed)
                    
                    continue
                
                elif str(reaction.emoji) == "🔢":  # Select page
                    await self.active_message.remove_reaction("🔢", self.ctx.author)
                    
                    self.am_embed.set_footer(text=f"Page [{self.current_page+1}/{len(self.images)}]: Enter the page number you would like to go to...\n"
                                                  f"{'Bookmarked page: '+str(int(self.bot.user_data['UserData'][str(self.ctx.author.id)]['nFavorites']['Bookmarks'][self.code])+1) if self.code in self.bot.user_data['UserData'][str(self.ctx.author.id)]['nFavorites']['Bookmarks'] else ''}")
                    
                    await self.active_message.edit(embed=self.am_embed)

                    def check(m):
                        return m.channel.id == self.active_message.channel.id
                    
                    while True:
                        try:
                            resp = await self.bot.wait_for("message", timeout=10, check=check)
                        except TimeoutError:
                            self.am_embed.set_footer(text=f"Page [{self.current_page+1}/{len(self.images)}]")
                            await self.active_message.edit(embed=self.am_embed)
                            break
                        else:
                            if is_int(resp.content) and (int(resp.content)-1) in range(0, len(self.images)):
                                self.current_page = (int(resp.content)-1)
                                if self.ctx.guild:
                                    await resp.delete()
                                
                                if self.code in self.bot.user_data['UserData'][str(self.ctx.author.id)]['nFavorites']['Bookmarks']:
                                    if self.current_page == self.bot.user_data['UserData'][str(self.ctx.author.id)]['nFavorites']['Bookmarks'][self.code]:
                                        self.on_bookmarked_page = True
                                        await self.active_message.remove_reaction("🔖", self.bot.user)
                                        await self.active_message.add_reaction("❌")
                                    else:
                                        self.on_bookmarked_page = False
                                        await self.active_message.remove_reaction("❌", self.bot.user)
                                        await self.active_message.add_reaction("🔖")

                                self.am_embed.set_footer(text=f"Page [{self.current_page+1}/{len(self.images)}] {'Bookmarked' if self.on_bookmarked_page else ''}")
                                self.am_embed.set_image(url=self.images[self.current_page])
                                self.am_embed.set_thumbnail(url=self.images[self.current_page+1] if (self.current_page+1) in range(0, len(self.images)) else Embed.Empty)
                                self.am_embed.description = f"⏮⏭ Previous|{'**__Finish__**' if self.current_page == (len(self.images)-1) else 'Next'}\n🔢⏹ Select|Stop\n⏸{'🔖 Pause|Bookmark' if not self.on_bookmarked_page else '❌ Pause|Unbookmark'}"

                                await self.active_message.edit(embed=self.am_embed)
                                break
                            else:
                                await resp.delete()
                                await self.am_channel.send("Not a valid number!", delete_after=2)
                                continue
                
                elif str(reaction.emoji) == "⏸":  # Pause for a maximum of one hour
                    await self.active_message.clear_reactions()
                
                    self.am_embed.set_image(url=Embed.Empty)
                    self.am_embed.set_thumbnail(url=self.images[0])
                    self.am_embed.description = "▶ Play"
                    self.am_embed.set_footer(text="You've paused this doujin. Come back within an hour!")
                    
                    await self.active_message.edit(embed=self.am_embed)
                    await self.active_message.add_reaction("▶")

                    try:
                        await self.bot.wait_for("reaction_add", timeout=(60*55), 
                            check=lambda r,u: r.message.id==self.active_message.id and str(r.emoji)=="▶" and u.id==self.ctx.author.id)
                    except TimeoutError:
                        warning = await self.am_channel.send(f"{self.ctx.author.mention}, you're about to time out in 5 minutes. Press play and pause again if you need more time.")
                        try:
                            await self.bot.wait_for("reaction_add", timeout=(60*5), 
                                check=lambda r,u: r.message.id==self.active_message.id and str(r.emoji)=="▶" and u.id==self.ctx.author.id)
                        except TimeoutError:
                            await warning.delete()
                            await self.active_message.delete()
                            conf = await self.am_channel.send(f"|🔔| {self.ctx.author.mention}, you timed out on page [{self.current_page+1}/{len(self.images)}]. This reader will be terminated.")
                            
                            await sleep(10)
                            await conf.edit(content="<a:nreader_loading:810936543401213953> Closing...", embed=None)
                            
                            await sleep(1)
                            await self.am_channel.delete()
                            return
                        else:
                            await warning.delete()
                            pass

                    finally:
                        edit = await self.am_channel.send("<a:nreader_loading:810936543401213953>")
                        await self.active_message.clear_reactions()

                        self.am_embed.set_footer(text=f"Page [{self.current_page+1}/{len(self.images)}]")
                        self.am_embed.set_image(url=self.images[self.current_page])
                        self.am_embed.set_thumbnail(url=self.images[self.current_page+1] if (self.current_page+1) in range(0, len(self.images)) else Embed.Empty)
                        self.am_embed.description = f"⏮⏭ Previous|Next\n🔢⏹ Select|Stop\n⏸{'🔖 Pause|Bookmark' if not self.on_bookmarked_page else '❌ Pause|Unbookmark'}"
                        
                        await self.active_message.edit(embed=self.am_embed)

                        await self.active_message.add_reaction("⏮")
                        await self.active_message.add_reaction("⏭")
                        await self.active_message.add_reaction("🔢")
                        await self.active_message.add_reaction("⏹")
                        await self.active_message.add_reaction("⏸")
                        if self.on_bookmarked_page:
                            await self.active_message.add_reaction("❌")
                        else:
                            await self.active_message.add_reaction("🔖")
                        
                        await edit.delete()

                elif str(reaction.emoji) == "⏹":  # Stop entirely
                    await self.active_message.clear_reactions()
                    
                    self.am_embed.set_image(url=Embed.Empty)
                    self.am_embed.set_thumbnail(url=Embed.Empty)
                    self.am_embed.description = Embed.Empty
                    self.am_embed.set_footer(text=f"You stopped this doujin on page [{self.current_page+1}/{len(self.images)}].")
                    await self.active_message.edit(embed=self.am_embed)
                    
                    await sleep(2)
                    await self.active_message.edit(content="<a:nreader_loading:810936543401213953> Closing...", embed=None)
                    
                    await sleep(1)
                    await self.am_channel.delete()
                    break
                
                elif str(reaction.emoji) == "🔖":
                    await self.active_message.remove_reaction("🔖", self.ctx.author)
                    
                    if self.current_page == 0:
                        await self.am_channel.send("You cannot bookmark the first page!", delete_after=3)
                        continue

                    if self.on_bookmarked_page:
                        await self.am_channel.send("Page already bookmarked!", delete_after=3)
                        continue

                    self.bot.user_data['UserData'][str(self.ctx.author.id)]['nFavorites']['Bookmarks'][self.code] = self.current_page

                    self.on_bookmarked_page = True

                    await self.active_message.remove_reaction("🔖", self.bot.user)
                    await self.active_message.add_reaction("❌")
                    self.am_embed.description = "⏮⏭ Previous|Next\n🔢⏹ Select|Stop\n⏸❌ Pause|Unbookmark"
                    self.am_embed.set_footer(text=f"Page [{self.current_page+1}/{len(self.images)}] Bookmarked")
                    await self.active_message.edit(embed=self.am_embed)
                    continue

                elif str(reaction.emoji) == "❌":
                    await self.active_message.remove_reaction("❌", self.ctx.author)

                    if not self.on_bookmarked_page:
                        self.am_embed.set_footer(text=f"Page [{self.current_page+1}/{len(self.images)}] 🕗 Page is not bookmarked!")
                        await self.active_message.edit(embed=self.am_embed)
                        await sleep(2)
                        self.am_embed.set_footer(text=f"Page [{self.current_page+1}/{len(self.images)}]")
                        await self.active_message.edit(embed=self.am_embed)
                        continue

                    if self.code in self.bot.user_data['UserData'][str(self.ctx.author.id)]['nFavorites']['Bookmarks']:
                        self.bot.user_data['UserData'][str(self.ctx.author.id)]['nFavorites']['Bookmarks'].pop(self.code)

                        self.on_bookmarked_page = False

                        await self.active_message.remove_reaction("❌", self.bot.user)
                        await self.active_message.add_reaction("🔖")
                        self.am_embed.description = f"⏮⏭ Previous|Next\n🔢⏹ Select|Stop\n⏸🔖 Pause|Bookmark"
                        self.am_embed.set_footer(text=f"Page [{self.current_page+1}/{len(self.images)}]")
                        await self.active_message.edit(embed=self.am_embed)
                        continue

        return

class SearchResultsBrowser:
    def __init__(self, bot: Bot, ctx: Context, results: list, msg:Message=None, msg2:Message=None, lolicon_allowed=False):
        """Class to create and run a browser from NHentai-API

        `results` - obtained from nhentai_api.search(query); Modified `SearchPage` to contain real Doujins, not DoujinThumbnails.
        `msg` - optional message that the bot owns to edit, otherwise created 
        `msg2` - optional second message
        """
        self.bot = bot
        self.ctx = ctx
        self.results = results.doujins
        self.lolicon_allowed = lolicon_allowed
        self.current_result = 0
        self.active_message: Message = msg
        self.active_message2: Message = msg2
        self.am_embed: Embed = None
    
    async def edit_dual_messages(self, embed1, embed2):
        # Local veriable doesn't change when editing, do so manually
        await self.active_message.edit(content='', embed=embed1)
        self.active_message.content = ''
        self.active_message.embeds[0] = embed1

        await self.active_message2.edit(content='', embed=embed2)
        self.active_message.content = ''
        self.active_message.embeds[0] = embed2
    
    async def update_browser(self, ctx):
        message_part = []
        for ind, dj in enumerate(self.results):
            try: 
                if ind == self.current_result and int(dj.id) in self.bot.user_data['UserData'][str(self.ctx.author.id)]['nFavorites']['Doujins']: symbol = "*️⃣"
                elif ind == self.current_result: symbol='🟥'
                elif int(dj.id) in self.bot.user_data['UserData'][str(self.ctx.author.id)]['nFavorites']['Doujins']: symbol = "🟦"
                else: symbol='⬛'
            except KeyError: 
                symbol='⬛'
            
            message_part.append(
                f"`{symbol} {str(ind+1).ljust(2)}` | "
                f"{'**' if ind == self.current_result else ''}__`{str(self.results[ind].id).ljust(7)}`__ | "
                f"{language_to_flag(self.results[ind].languages)} | "
                f"{shorten(self.results[ind].title, width=40, placeholder='...')}{'**' if ind == self.current_result else ''}")

        self.am_embed = Embed(
            color=0xEC2854,
            description=f"First page only displayed"
                        f"{'; illegal results are hidden:' if ctx.guild and not self.lolicon_allowed else ':'}"
                        f"\n"+('\n'.join(message_part)))
        self.am_embed.set_author(
            name="NHentai Search Results [INTERACTIVE]",
            url=f"https://nhentai.net/",
            icon_url="https://cdn.discordapp.com/attachments/742481946030112779/759591081758949410/emote.png")
        self.am_embed.set_footer(
            text="Provided by NHentai-API")

        if self.results[self.current_result].id not in self.bot.doujin_cache:
            nhentai_api = NHentai()
            doujin = nhentai_api._get_doujin(self.results[self.current_result].id)
            self.bot.doujin_cache[self.results[self.current_result].id] = doujin
        else:
            doujin = self.bot.doujin_cache[self.results[self.current_result].id]
        
        emb = Embed(
            color=0xEC2854,
            description=f"[{'{'}Tap to open{'}'}](https://nhentai.net/g/{doujin.id}/)\n"
                        f"Secondary Title: `{doujin.secondary_title if doujin.secondary_title != '' else 'Not provided'}`\n"
                        f"Pages: `{len(doujin.images)}`\n"
                        f"Artist(s): `{', '.join(doujin.artists) if doujin.artists != [] else 'Not provided'}`\n"
                        f"Language(s): `{', '.join(doujin.languages) if doujin.languages != [] else 'Not provided'}`\n"
                        f"Character(s): `{', '.join(doujin.characters) if doujin.characters != [] else 'Original'}`\n"
                        f"Tags:```{', '.join(doujin.tags) if doujin.tags != [] else 'None provided'}```\n")
        emb.set_author(
            name=f"[{language_to_flag(doujin.languages)}] {doujin.title}",
            url=f"https://nhentai.net/g/{doujin.id}/",
            icon_url="https://cdn.discordapp.com/attachments/742481946030112779/759591081758949410/emote.png")

        previous_emb = deepcopy(self.active_message2.embeds[0])
        if previous_emb.image:
            emb.set_image(url=doujin.images[0])
            emb.set_thumbnail(url=Embed.Empty)
            emb.set_footer(text="🔼🔽🔢⏹📖🔍 |Up|Down|Select|Stop|Read|Zoom-|")
        elif previous_emb.thumbnail:
            emb.set_thumbnail(url=doujin.images[0])
            emb.set_image(url=Embed.Empty)
            emb.set_footer(text="🔼🔽🔢⏹📖🔍 |Up|Down|Select|Stop|Read|Zoom+|")
        else:  # Image wasn't set yet
            emb.set_thumbnail(url=doujin.images[0])
            emb.set_footer(text="🔼🔽🔢⏹📖🔍 |Up|Down|Select|Stop|Read|Zoom+|")

        await self.edit_dual_messages(self.am_embed, emb)
    
    async def start(self, ctx):
        """Initial start of the result browser."""

        if not self.active_message:
            self.active_message = await ctx.send("<a:nreader_loading:810936543401213953>")
            await sleep(0.5)
        
        if not self.active_message2:
            self.active_message2 = await ctx.send(
                embed=Embed(description="<a:nreader_loading:810936543401213953> Getting things ready..."))
            await sleep(0.5)
        
        await self.active_message2.add_reaction("🔼")
        await self.active_message2.add_reaction("🔽")
        await self.active_message2.add_reaction("🔢")
        await self.active_message2.add_reaction("⏹")
        await self.active_message2.add_reaction("📖")
        
        await sleep(0.5)
        await self.update_browser(self.ctx)

        await self.active_message2.add_reaction("🔍")

        def check(reaction, user):
            return reaction.message.id == self.active_message2.id and \
                str(reaction.emoji) in ["🔼", "🔽", "🔢", "⏹", "📖", "🔍"] and \
                user.id == self.ctx.author.id

        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=300, check=check)
            except TimeoutError:
                await self.active_message.clear_reactions()

                message_part = []
                for ind, dj in enumerate(self.results):
                    message_part.append(
                        f"{'**' if ind == self.current_result else ''}__`{str(self.results[ind].id).ljust(7)}`__{'**' if ind == self.current_result else ''} | "
                        f"{language_to_flag(self.results[ind].languages)} | "
                        f"{shorten(self.results[ind].title, width=50, placeholder='...')}")
                
                self.am_embed = Embed(
                    color=0xEC2854,
                    description=f"First page only displayed"
                                f"{'; illegal results are hidden:' if ctx.guild and not self.lolicon_allowed else ':'}"
                                f"\n"+('\n'.join(message_part)))
                self.am_embed.set_author(
                    name="NHentai Search Results",
                    url=f"https://nhentai.net/",
                    icon_url="https://cdn.discordapp.com/attachments/742481946030112779/759591081758949410/emote.png")
                self.am_embed.set_footer(
                    text=f"Provided by NHentai-API; ⏲ Controller timed out.")
                self.am_embed.set_image(
                    url=Embed.Empty)

                await self.active_message.edit(content='', embed=self.am_embed)
                await self.active_message2.delete()
                return
            else:
                with suppress(Forbidden):
                    await self.active_message2.remove_reaction(str(reaction.emoji), user)
                
                if str(reaction.emoji) == "🔼":
                    if self.current_result > 0:
                        self.current_result -= 1
                        await self.update_browser(self.ctx)
                    elif self.current_result == 0:
                        self.current_result = len(self.results)-1
                        await self.update_browser(self.ctx)

                elif str(reaction.emoji) == "🔽":
                    if self.current_result < len(self.results)-1:
                        self.current_result += 1
                        await self.update_browser(self.ctx)
                    elif self.current_result == len(self.results)-1:
                        self.current_result = 0
                        await self.update_browser(self.ctx)
                
                elif str(reaction.emoji) == "🔢":
                    self.am_embed.set_footer(text="Enter a result number...")
                    await self.active_message.edit(embed=self.am_embed)

                    while True:
                        try:
                            m = await self.bot.wait_for("message", timeout=10, check=lambda m: m.author.id == self.ctx.author.id and m.channel.id == self.ctx.channel.id)
                        except TimeoutError:
                            self.am_embed.set_footer(text=Embed.Empty)
                            await self.active_message.edit(embed=self.am_embed)
                            break
                        else:
                            await m.delete()
                            
                            if is_int(m.content) and (int(m.content)-1) in range(0, len(self.results)):
                                self.current_result = int(m.content)-1
                                await self.update_browser(self.ctx)
                                break
                            else:
                                await self.am_channel.send("Not a valid number!", delete_after=2)
                                continue
                
                elif str(reaction.emoji) == "⏹":
                    message_part = []
                    for ind, dj in enumerate(self.results):
                        message_part.append(
                            f"__`{str(self.results[ind].id).ljust(7)}`__ | "
                            f"{language_to_flag(self.results[ind].languages)} | "
                            f"{shorten(self.results[ind].title, width=40, placeholder='...')}")
                    self.am_embed = Embed(
                        color=0xEC2854,
                        description=f"First page only displayed"
                                    f"{'; illegal results are hidden:' if ctx.guild else ':'}"
                                    f"\n"+('\n'.join(message_part)))
                    self.am_embed.set_author(
                        name="NHentai Search Results",
                        url=f"https://nhentai.net/",
                        icon_url="https://cdn.discordapp.com/attachments/742481946030112779/759591081758949410/emote.png")
                    self.am_embed.set_footer(
                        text=f"Provided by NHentai-API")
                    self.am_embed.set_thumbnail(
                        url=Embed.Empty)
                    self.am_embed.set_image(
                        url=Embed.Empty)

                    await self.active_message.clear_reactions()
                    await self.active_message.edit(content='', embed=self.am_embed)
                    await self.active_message2.delete()
                    return
                
                elif str(reaction.emoji) == "📖":
                    await self.active_message.clear_reactions()
                    
                    if str(self.ctx.author.id) not in self.bot.user_data["UserData"]:
                        self.bot.user_data["UserData"][str(self.ctx.author.id)] = {}
                    if "History" not in self.bot.user_data["UserData"][str(self.ctx.author.id)]:
                        self.bot.user_data["UserData"][str(self.ctx.author.id)]["History"] = [True, []]
                    
                    if self.bot.user_data["UserData"][str(ctx.author.id)]["History"][0]:
                        self.bot.user_data["UserData"][str(ctx.author.id)]["History"][1].insert(0, 
                        self.bot.doujin_cache[self.results[self.current_result].id].id)
                        if len(self.bot.user_data["UserData"][str(ctx.author.id)]["History"][1]) >= 2 and \
                            self.bot.user_data["UserData"][str(ctx.author.id)]["History"][1][1] == \
                            self.bot.doujin_cache[self.results[self.current_result].id].id:
                            self.bot.user_data["UserData"][str(ctx.author.id)]["History"][1].pop(0)
                        
                        if len(self.bot.user_data["UserData"][str(ctx.author.id)]["History"][1]) >= 25:
                            self.bot.user_data["UserData"][str(ctx.author.id)]["History"][1].pop()

                    message_part = []
                    for ind, dj in enumerate(self.results):
                        message_part.append(
                            f"{'**' if ind == self.current_result else ''}"
                            f"__`{str(self.results[ind].id).ljust(7)}`__ | "
                            f"{language_to_flag(self.results[ind].languages)} | "
                            f"{shorten(self.results[ind].title, width=40, placeholder='...')}{'**' if ind == self.current_result else ''}")
                    self.am_embed = Embed(
                        color=0xEC2854,
                        description=f"First page only displayed"
                                    f"{'; illegal results are hidden:' if ctx.guild else ':'}"
                                    f"\n"+('\n'.join(message_part)))
                    self.am_embed.set_author(
                        name="NHentai Search Results",
                        url=f"https://nhentai.net/",
                        icon_url="https://cdn.discordapp.com/attachments/742481946030112779/759591081758949410/emote.png")
                    self.am_embed.set_footer(
                        text=f"Provided by NHentai-API; Opened doujin {self.results[self.current_result].id}")
                    self.am_embed.set_thumbnail(
                        url=Embed.Empty)
                    self.am_embed.set_image(
                        url=Embed.Empty)

                    await self.active_message.edit(content='', embed=self.am_embed)
                    await self.active_message2.delete()

                    session = ImagePageReader(self.bot, ctx, self.bot.doujin_cache[self.results[self.current_result].id].images, 
                        f"{self.bot.doujin_cache[self.results[self.current_result].id].id} || {self.bot.doujin_cache[self.results[self.current_result].id].title}")
                    response = await session.setup()
                    if response:
                        await session.start()
                    else:
                        self.am_embed.set_footer(text="Provided by NHentai-API; You timed out.")
                        await self.active_message.edit(embed=self.am_embed)

                    return
                
                elif str(reaction.emoji) == "🔍":
                    emb = deepcopy(self.active_message2.embeds[0])
                    if not emb.image:
                        emb.set_image(url=emb.thumbnail.url)
                        emb.set_thumbnail(url=Embed.Empty)
                        emb.set_footer(text="🔼🔽🔢⏹📖🔍 |Up|Down|Select|Stop|Read|Zoom-|")
                    elif not emb.thumbnail:
                        emb.set_thumbnail(url=emb.image.url)
                        emb.set_image(url=Embed.Empty)
                        emb.set_footer(text="🔼🔽🔢⏹📖🔍 |Up|Down|Select|Stop|Read|Zoom+|")
                    
                    await self.active_message2.edit(embed=emb)