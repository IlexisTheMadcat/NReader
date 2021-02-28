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
from discord import Message, Embed, Forbidden, TextChannel
from discord.ext.commands.context import Context
from discord.ext.commands.bot import Bot as DiscordBot
from NHentai import NHentai

from utils.errorlog import ErrorLog
from utils.utils import language_to_flag

# Paginator created by SirThane @ GitHub
class Paginator:
    def __init__(
            self,
            page_limit: int = 1000,
            trunc_limit: int = 2000,
    ):
        self.page_limit = page_limit
        self.trunc_limit = trunc_limit
        self._pages = None

    @property
    def pages(self):
        return self._pages

    def set_trunc_limit(self, limit: int = 2000):
        self.trunc_limit = limit

    def set_page_limit(self, limit: int = 1000):
        self.page_limit = limit

    def paginate(self, value: str) -> List[str]:
        """
        To paginate a string into a list of strings under
        `self.page_limit` characters. Total len of strings
        will not exceed `self.trunc_limit`.
        :param value: string to paginate
        :return list: list of strings under 'page_limit' chars
        """
        spl = str(value).split('\n')
        ret = list()
        page = ''
        total = 0

        for i in spl:
            if total + len(page) >= self.trunc_limit:
                ret.append(page[:self.trunc_limit - total])
                break

            if (len(page) + len(i)) < self.page_limit:
                page += f'\n{i}'
                continue

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
            ret.append(page)

        self._pages = ret
        return self.pages


class Bot(DiscordBot):

    def __init__(self, *args, **kwargs):

        # Namespace variables, not saved to files
        self.inactive = 0  # Timer to track minutes since responded to a command
        self.waiting: List[int] = list()  # Users waiting for a response from developer
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


# Override default color for bot fanciness
class ModdedEmbed(Embed):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.color = 0xEC2854
        self.colour = self.color


def is_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

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
        "{int()} || {str()}", where int would be an object id and str for title.
        """
        self.bot = bot
        self.current_page: int = 0
        self.images: list = images
        self.name: str = name
        self.code: str = self.name.split('[-n-]')[0].strip(" ")
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
                        "▶ Play"
            )
        self.am_embed.set_author(
            name=self.name,
            icon_url="https://cdn.discordapp.com/attachments/742481946030112779/759591081758949410/emote.png")
        self.am_embed.set_footer(
            text=f"Page [0/{len(self.images)}]: Press PLAY to start reading.")
        
        channel = None
        try:
            channel = await self.ctx.guild.create_text_channel(name=f"📖nreader-{self.ctx.message.id}", nsfw=True)
        except Forbidden:
            return False

        try:
            await channel.set_permissions(self.ctx.guild.me, read_messages=True)
            await channel.set_permissions(self.ctx.guild.default_role, read_messages=False)
            await channel.set_permissions(self.ctx.author, read_messages=True)
        except Forbidden:
            if channel:
                await channel.delete()
                return False
        else:
            conf = await channel.send(content=self.ctx.author.mention, embed=self.am_embed)
    
        await edit.delete()
        await self.ctx.send(embed=Embed(color=0x000000, description=f"[Click/tap here]({conf.jump_url}) to jump to your reader."), delete_after=10)
        
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
                        f"{self.language_to_flag(self.results[ind].languages)} | "
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
