from __future__ import annotations  # Must be imported first

########################################
# Modular version of a script written by SirThane @ Github 
# Partially rewritten by SUPERMECHM500 @ Repl.it
#
# --- Combatibility ---
# Compatible with Discord.py 1.6.0 and most other rewrite versions.
#
# --- Credit ---
# If used in an open-source project, please provide credit for:
# ー SirThane @ GitHub
# ー SUPERMECHM500 @ Repl.it
########################################

# The following variables must be added in `class Bot(DiscordBot)` __init__
"""
# Get the channel ready for errorlog
# Bot.get_channel method not available until on_ready
self.errorlog_channel: int = kwargs.pop("errorlog", None)
self.errorlog: ErrorLog = kwargs.get("errorlog", None)
"""

# The following function must be added/overwritten in `class Bot(DiscordBot)`
"""
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
"""

# The following check must be added in your `on_ready` event 
# in your driver script (typically "main.py")
"""
# Add the ErrorLog object
bot.errorlog = ErrorLog(bot, <channelID>)
"""

# The following raiser can be added in your `on_command_error` event 
# for functionality with command errors. You should add this at the 
# end of the event, however placement does not entirely matter.
"""
# Raising the exception causes the progam 
# to think about the exception in the wrong way, so we must 
# target the exception indirectly.
try:
    raise error.original  # `error` is provided by on_command_error's second argument.
except Exception:
    error = exc_info()

await bot.errorlog.send(error, event=f"Command: {ctx.command.name}")  # Add self. before bot if you are using cogs
return  # Optional return
"""

from traceback import extract_tb
from asyncio import sleep
from discord.channel import TextChannel
from discord.colour import Colour
from discord.embeds import Embed as DiscordEmbed
from discord.errors import DiscordException
from discord.ext.commands.context import Context
from discord.message import Message
from typing import List, Union, Tuple

# Zero Width Space
ZWSP = u'\u200b'

# Used by ErrorLog
class Embed(DiscordEmbed):

    def copy(self):
        """Returns a shallow copy of the embed.

        Must copy the method from discord.Embed, or it would
        return a copy of the super class."""
        return Embed.from_dict(self.to_dict())

    def strip_head(self):
        self.title = ""
        self.description = ""
        self.set_author(name="", url="", icon_url="")
        self.set_thumbnail(url="")

    def strip_foot(self):
        self.set_image(url="")
        self.set_footer(text="", icon_url="")

    def split(self) -> List[Embed]:
        title = len(self.title) if self.title else 0
        desc = len(self.description) if self.description else 0
        author_name = len(self.author.name) if self.author.name else 0
        author_url = len(self.author.url) if self.author.url else 0
        author_icon_url = len(self.author.icon_url) if self.author.icon_url else 0
        thumbnail = len(self.thumbnail.url) if self.thumbnail.url else 0

        image = len(self.image.url) if self.image.url else 0
        footer_text = len(self.footer.text) if self.footer.text else 0
        footer_icon_url = len(self.footer.icon_url) if self.footer.icon_url else 0

        field_lengths = [len(field.name) + len(field.value) for field in self.fields]

        head = sum((title, desc, author_name, author_url, author_icon_url, thumbnail))
        foot = sum((image, footer_text, footer_icon_url))

        if head + foot + sum(field_lengths) < 6000:
            return [self]

        char_count = head

        pages = list()
        page = self.copy()

        fields = [field.copy() for field in self.to_dict().get("fields", None)]

        page.clear_fields()
        page.strip_foot()

        for i, field in enumerate(fields):

            if char_count + field_lengths[i] < 6000 and len(page.fields) <= 25:
                page.add_field(
                    name=field["name"],
                    value=field["value"],
                    inline=field["inline"]
                )
                char_count += field_lengths[i]

            else:
                pages.append(page)

                page = self.copy()
                page.strip_head()
                page.clear_fields()
                page.strip_foot()

                page.add_field(
                    name=field["name"],
                    value=field["value"],
                    inline=field["inline"]
                )
                char_count = field_lengths[i]

        if char_count + foot < 6000:
            page.set_footer(
                text=self.footer.text,
                icon_url=self.footer.icon_url
            )
            pages.append(page)

        else:
            pages.append(page)

            page = self.copy()
            page.strip_head()
            page.clear_fields()

            pages.append(page)

        return pages


class ErrorLog:
    def __init__(self, bot, channel: Union[int, str, TextChannel]):
        self.bot = bot
        if isinstance(channel, int):
            channel = self.bot.get_channel(channel)
        elif isinstance(channel, str):
            channel = self.bot.get_channel(int(channel))
        if isinstance(channel, TextChannel):
            self.channel = channel
        else:
            self.channel = None

    async def send(self, error: Tuple, ctx: Context = None, event: str = None) -> Message:
        """
        Send formated exception data as an embed to the target
            errorlog channel specified in `channel`.
        
        error: tuple - Retrieved from sys.exc_info() for universal causes.
        ctx: Context - Context of the event. Could be `None`.
        event: str - The event that the error occured in. Appears in the `em_tb` title.
        """

        if not self.channel:
            raise AttributeError("ErrorLog channel not set")
        em = await self.em_tb(error, ctx, event)
        for i, page in enumerate(em.split()):
            if i:
                await sleep(0.1)
            
            msg = await self.channel.send(embed=em)
            self.bot.error_contexts.update({msg.id: ctx})

    @staticmethod
    async def em_tb(error: Tuple, ctx: Context = None, event: str = None) -> Embed:
        """Creates an embed from the given traceback."""

        title = f"Exception ignored in event `{event}`" if event else None
        description = f"**{type(error[1]).__name__}**: {str(error[1])}"

        stack = extract_tb(error[2])  # stack = extract_tb(error.__traceback__)
        tb_fields = [
            {
                "name": f"{ZWSP}\n__{fn}__",
                "value": f"Line `{ln}` in `{func}`:\n```py\n{txt}\n```",
                "inline": False
            } for fn, ln, func, txt in stack
        ]

        em = Embed(color=Colour.red(), title=title, description=f"{description}")

        if hasattr(ctx, "author"):
            em.add_field(
                name="Context",
                inline=False,
                value=f"User: `{ctx.author}` ({ctx.author.id})\n"
                      f"Guild: `{ctx.guild if ctx.guild else 'Unavailable'}` ({ctx.guild.id if ctx.guild else '0'})\n"
                      f"Channel: `{ctx.channel}` ({ctx.channel.id})\n"
                      f"Message: `{ctx.message.content if ctx.message.content else 'No Content'}`\n"
                      f"**Copy this message ID and access `bot.error_contexts[<id>]` for Context.**")
        else:
            em.set_footer(text=f"This event was caused by an element in the source code.")

        for field in tb_fields:
            em.add_field(**field)

        return em
