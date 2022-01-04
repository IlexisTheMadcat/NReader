from os import getcwd
from sys import exc_info
from typing import List
from asyncio import iscoroutinefunction

from discord import ui, Embed as DiscordEmbed
from discord.ext.commands import Bot as DiscordBot
from expiringdict import ExpiringDict


newline = "\n"


# Override default color for bot fanciness
class Embed(DiscordEmbed):
    def __init__(self, *args, **kwargs):
        color = kwargs.pop("color", 0x000000)
        if not color:
            color = 0xEC2854
        
        super().__init__(*args, color=color, **kwargs)

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

class BotInteractionCooldown(Exception):
    pass

class Bot(DiscordBot):
    def __init__(self, *args, **kwargs):
        # Timer to track minutes since responded to a command.
        self.inactive = 0

        # Global bot directory
        self.cwd = getcwd()

        # Tokens
        self.auth = kwargs.pop("auth")

        # Default data. Used to initialize and update data structures.
        self.defaults = kwargs.pop("defaults")
        
        # Database
        self.use_firebase = kwargs.pop("use_firebase")
        self.database = kwargs.pop("database")  # Online
        self.user_data = kwargs.pop("user_data") # Local
        self.config = self.user_data["config"]  # Shortcut for user_data['config']
        print("[HRB] Data and configurations loaded.")

        # Get the channel ready for errorlog
        # Bot.get_channel method not available until on_ready
        self.errorlog_channel: int = kwargs.pop("errorlog", None)

        # Cooldown to be used in all loops and the beginnings of commands.
        # Users whose ID is in here cannot interact with the bot for `max_age_seconds`
        self.global_cooldown = ExpiringDict(max_len=float('inf'), max_age_seconds=1)

        # A cache of loaded doujins, it will fill as doujins are retrieved by code.
        # Values expire in 3 days since addition or resets when bot reloads.
        self.error_contexts = ExpiringDict(max_len=float('inf'), max_age_seconds=259200)

        # A cache of loaded doujins, it will fill as doujins are retrieved by code.
        # Values expire in 1 day since addition or resets when bot reloads.
        self.doujin_cache = ExpiringDict(max_len=float('inf'), max_age_seconds=86400)

        # Load bot arguments into __init__
        super().__init__(*args, **kwargs)
    
    def run(self, *args, **kwargs):
        print("[BOT INIT] Logging in with token...")
        super().run(self.auth["BOT_TOKEN"], *args, **kwargs)
    
    async def on_error(self, event_name, *args, **kwargs):
        '''Error handler for Exceptions raised in events'''
        if self.config["debug_mode"]:  # Hold true the purpose for the debug_mode option
            await super().on_error(*args, **kwargs)
            return
        
        # Try to get Exception that was raised
        error = exc_info()  # `from sys import exc_info` at the top of your script

        # If the Exception raised is successfully captured, use ErrorLog
        if error:
            await self.errorlog.send(error, event=event_name)

        # Otherwise, use default handler
        else:
            await super().on_error(*args, **kwargs)
    
    async def on_message(self, msg):
        """Disable primary Bot.process_commands listener for cogs to call individually."""
        return

    async def wait_for(self, *args, **kwargs):
        """Delay primary Bot.wait_for listener. Raises BotInteractionCooldown if on cooldown."""
        bypass_cooldown: bool = kwargs.pop("bypass_cooldown", False)
        if bypass_cooldown:
            return await super().wait_for(*args, **kwargs)
        
        if "message" in args:
            msg = await super().wait_for(*args, **kwargs)
            if msg.author.id in self.global_cooldown: raise BotInteractionCooldown("Bot interaction on cooldown.")
            else: self.global_cooldown.update({msg.author.id:"placeholder"})
            return msg

        elif "reaction_add" in args:
            reaction, user = await super().wait_for(*args, **kwargs)
            if user.id in self.global_cooldown: raise BotInteractionCooldown("Bot interaction on cooldown.")
            else: self.global_cooldown.update({user.id:"placeholder"})
            return reaction, user
        
        elif "raw_reaction_add" in args:
            payload = await super().wait_for(*args, **kwargs)
            if payload.user_id in self.global_cooldown: raise BotInteractionCooldown("Bot interaction on cooldown.")
            else: self.global_cooldown.update({payload.user_id:"placeholder"})
            return payload

        elif "button_click" in args:
            payload = await super().wait_for(*args, **kwargs)
            if payload.user.id in self.global_cooldown: raise BotInteractionCooldown("Bot interaction on cooldown.")
            else: self.global_cooldown.update({payload.user.id:"placeholder"})
            return payload
        
        else:
            return await super().wait_for(*args, **kwargs)


class ViewConstructor(ui.View):
    def __init__(self, parent_attrs=None, timeout=0, timeout_callback=None, view_classes=[]):
        """
        This constructor is for constructing Select views.
        Must pass parent class `self` to use its features.
        For a looping view, create the message editor as a separate function and call that function in the view_class callback. 
        Pass the callback interaction and view_class's self.values into that function
        """
        self.timeout_callback = timeout_callback

        super().__init__(timeout=timeout)
        if not view_classes:
            raise ValueError("View Items need to be provided.")

        for view_class in view_classes:
            self.add_item(view_class)

    async def on_timeout(self):
        if self.timeout_callback:
            if iscoroutinefunction(self.timeout_callback):
                await self.timeout_callback()
            elif not iscoroutinefunction(self.timeout_callback):
                self.timeout_callback()
