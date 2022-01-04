# IMPORTS
from os import getcwd
from sys import exc_info
from typing import List
from copy import deepcopy
from textwrap import shorten
from asyncio import sleep
from asyncio.exceptions import TimeoutError
from contextlib import suppress

from discord import (
    Message, TextChannel,
    Forbidden, NotFound)
from discord.utils import get
from discord.ext.commands import Context
from discord.ext.commands.cog import Cog
from NHentai.nhentai_async import NHentaiAsync as NHentai, SearchPage, PopularPage

from utils.classes import Embed, Bot, BotInteractionCooldown
from utils.misc import (
    language_to_flag, 
    is_int, is_float)


newline = "\n"


class RClasses(Cog):
    def __init__(self, bot):
        self.bot = bot


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
        edit = await self.ctx.send(embed=Embed(
            description="<a:nreader_loading:810936543401213953>"))
        
        self.am_embed: Embed = Embed(
            color=0xEC2854,
            description=f"Active emojis will appear here.\n" \
                        "▶ Play")
        self.am_embed.set_author(
            name=self.name,
            icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
        self.am_embed.set_footer(
            text=f"Page [0/{len(self.images)}]: Press ▶ Play to start reading.")

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

        # Reader message
        conf = await channel.send(content=self.ctx.author.mention, embed=self.am_embed)

        # Portal
        await edit.edit(
            content=conf.channel.mention, 
            embed=Embed(
                description="Click/Tap the mention above to jump to your reader."
                ).set_author(
                    name=self.bot.user.name,
                    icon_url=self.bot.user.avatar.url),
            delete_after=10)
        
        await conf.add_reaction("▶")
        
        try:
            await self.bot.wait_for("reaction_add", timeout=30, bypass_cooldown=True,
                check=lambda r,u: r.message.id == conf.id and \
                    u.id == self.ctx.author.id and \
                    str(r.emoji) == "▶")
        
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
            self.am_embed.description = "⏮⏭ Previous|Next\n🔢⏹ Select|Stop\n⏯ Pause"
            self.am_embed.set_image(url=self.images[0].src)
            self.am_embed.set_footer(text=f"Page [{self.current_page+1}/{len(self.images)}]")
            self.am_embed.set_thumbnail(url=self.images[self.current_page+1].src if (self.current_page+1) in range(0, len(self.images)) else Embed.Empty)
            await self.active_message.edit(embed=self.am_embed)

            await self.active_message.add_reaction("⏮")
            await self.active_message.add_reaction("⏭")
            await self.active_message.add_reaction("🔢")
            await self.active_message.add_reaction("⏹")
            await self.active_message.add_reaction("⏯")
            await sleep(0.2)
            await edit.delete()
            return True

    async def start(self):
        def payload_check(payload):  # Use raw payload to compensate for the longer wait
            return \
                payload.message_id==self.active_message.id and \
                payload.user_id==self.ctx.author.id and \
                str(payload.emoji) in ["⏮", "⏭", "🔢", "⏹", "⏯", "▶", "❌"]

        while True:
            try:
                payload = await self.bot.wait_for("raw_reaction_add", timeout=60*5,
                    check=payload_check)
            
            except BotInteractionCooldown:
                continue

            except TimeoutError:
                with suppress(NotFound):
                    await self.active_message.clear_reactions()
                    
                    self.am_embed.description = ""
                    self.am_embed.set_footer(text=f"You timed out on page [{self.current_page+1}/{len(self.images)}].\n")

                    self.am_embed.set_image(url=Embed.Empty)
                    self.am_embed.set_thumbnail(url=Embed.Empty)
                    await self.active_message.edit(embed=self.am_embed)
                    await self.am_channel.send(content=f"{self.ctx.author.mention}, you timed out in your doujin. Forgot to press pause?", delete_after=1)
            
                    await sleep(10)
                    await self.active_message.edit(content="<a:nreader_loading:810936543401213953> Closing...", embed=None)

                    await sleep(1)
                    await self.am_channel.delete()

                break
            
            except BotInteractionCooldown:
                continue
            
            else:
                self.bot.inactive = 0
                with suppress(Forbidden):
                    user = await self.bot.fetch_user(payload.user_id)
                    await self.active_message.remove_reaction(str(payload.emoji), user)

                if str(payload.emoji) == "⏭":  # Next page
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
                    
                    self.am_embed.set_footer(text=f"Page [{self.current_page+1}/{len(self.images)}]")
                    self.am_embed.set_image(url=self.images[self.current_page].src)
                    self.am_embed.set_thumbnail(url=self.images[self.current_page+1].src if (self.current_page+1) in range(0, len(self.images)) else Embed.Empty)
                    self.am_embed.description = f"⏮⏭ Previous|{'**__Finish__**' if self.current_page == (len(self.images)-1) else 'Next'}\n🔢⏹ Select|Stop\n⏯ Pause"

                    await self.active_message.edit(embed=self.am_embed)
                    
                    continue

                elif str(payload.emoji) == "⏮":  # Previous page
                    if self.current_page == 0:  # Not allowed to go behind zero
                        continue
                    
                    else:
                        self.current_page = self.current_page - 1
                    
                    self.am_embed.set_footer(text=f"Page [{self.current_page+1}/{len(self.images)}]")
                    self.am_embed.set_image(url=self.images[self.current_page].src)
                    self.am_embed.set_thumbnail(url=self.images[self.current_page+1].src if (self.current_page+1) in range(0, len(self.images)) else Embed.Empty)
                    self.am_embed.description = f"⏮⏭ Previous|Next\n🔢⏹ Select|Stop\n⏯ Pause"

                    await self.active_message.edit(embed=self.am_embed)
                    
                    continue
                
                elif str(payload.emoji) == "🔢":  # Select page
                    conf = await self.am_channel.send(embed=Embed(
                        description=f"Enter the page number you would like to go to."))

                    while True:
                        try:
                            resp = await self.bot.wait_for("message", timeout=10, bypass_cooldown=True,
                                check=lambda m: m.channel.id == self.am_channel.id and
                                    m.author.id == self.ctx.author.id)
                        except TimeoutError:
                            await conf.delete()
                            break
                        
                        except BotInteractionCooldown:
                            continue

                        else:
                            if is_int(resp.content) and (int(resp.content)-1) in range(0, len(self.images)):
                                self.current_page = (int(resp.content)-1)
                                await resp.delete()
                                await conf.delete()
                                
                                self.am_embed.set_footer(text=f"Page [{self.current_page+1}/{len(self.images)}]")
                                self.am_embed.set_image(url=self.images[self.current_page].src)
                                self.am_embed.set_thumbnail(url=self.images[self.current_page+1].src if (self.current_page+1) in range(0, len(self.images)) else Embed.Empty)
                                self.am_embed.description = f"⏮⏭ Previous|{'**__Finish__**' if self.current_page == (len(self.images)-1) else 'Next'}\n🔢⏹ Select|Stop\n⏯ Pause"

                                await self.active_message.edit(embed=self.am_embed)
                                break
                            
                            else:
                                await resp.delete()
                                await self.am_channel.send(embed=Embed(
                                    color=0xFF0000,
                                    description="Not a valid number!"), 
                                    delete_after=2)

                                continue
                
                elif str(payload.emoji) == "⏯":  # Pause for a maximum of one hour
                    self.am_embed.set_image(url=Embed.Empty)
                    self.am_embed.set_thumbnail(url=self.images[0].src)
                    self.am_embed.description = "⏯ Play"
                    self.am_embed.set_footer(text="You've paused this doujin. Come back within an hour!")
                    
                    await self.active_message.edit(embed=self.am_embed)
                    
                    def payload_check_pause(payload):  # Use raw payload to compensate for the longer wait
                        return \
                            payload.message_id==self.active_message.id and \
                            payload.user_id==self.ctx.author.id and \
                            str(payload.emoji)=="⏯"
                    
                    try:
                        await self.bot.wait_for("raw_reaction_add", timeout=(60*55), bypass_cooldown=True,
                            check=payload_check_pause)
                    
                    except TimeoutError:
                        warning = await self.am_channel.send(f"{self.ctx.author.mention}, you're about to time out in 5 minutes. Press play and pause again if you need more time.")
                        
                        try:                               
                            await self.bot.wait_for("raw_reaction_add", timeout=(60*5), bypass_cooldown=True,
                                check=payload_check_pause)
                        
                        except TimeoutError:
                            await warning.delete()
                            await self.active_message.delete()
                            conf = await self.am_channel.send(f"{self.ctx.author.mention}, you timed out on page [{self.current_page+1}/{len(self.images)}]. This reader will be terminated.")
                            
                            await sleep(10)
                            await conf.edit(content="<a:nreader_loading:810936543401213953> Closing...", embed=None)
                            
                            await sleep(1)
                            await self.am_channel.delete()
                            return
                        
                        else:
                            await warning.delete()

                            with suppress(Forbidden):
                                await self.active_message.remove_reaction("⏯", self.ctx.author)

                            self.am_embed.set_footer(text=f"Page [{self.current_page+1}/{len(self.images)}]")
                            self.am_embed.set_image(url=self.images[self.current_page].src)
                            self.am_embed.set_thumbnail(url=self.images[self.current_page+1].src if (self.current_page+1) in range(0, len(self.images)) else Embed.Empty)
                            self.am_embed.description = f"⏮⏭ Previous|Next\n🔢⏹ Select|Stop\n⏯ Pause"
                            
                            await self.active_message.edit(embed=self.am_embed)

                    else:
                        with suppress(Forbidden):
                            await self.active_message.remove_reaction("⏯", self.ctx.author)

                        self.am_embed.set_footer(text=f"Page [{self.current_page+1}/{len(self.images)}]")
                        self.am_embed.set_image(url=self.images[self.current_page].src)
                        self.am_embed.set_thumbnail(url=self.images[self.current_page+1].src if (self.current_page+1) in range(0, len(self.images)) else Embed.Empty)
                        self.am_embed.description = f"⏮⏭ Previous|Next\n🔢⏹ Select|Stop\n⏯ Pause"
                        
                        await self.active_message.edit(embed=self.am_embed)

                elif str(payload.emoji) == "⏹":  # Stop entirely
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

        return

    
def setup(bot):
    bot.add_cog(RClasses(bot))
