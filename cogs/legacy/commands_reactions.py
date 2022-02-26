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
from cogs.legacy.classes_reactions import ImagePageReader
from utils.misc import language_to_flag
from cogs.localization import *


class RCommands(Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @command(name="old_test")
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
                        await ctx.author.send(localization["eng"]["notifications_due"]["lolicon_viewing_tip"])
                    
                    self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["NotificationsDue"]["LoliconViewingTip"] = True

                return

        else:
            while True:
                doujin = await nhentai_api.get_random()
                self.bot.doujin_cache[doujin.id] = doujin
                if ("lolicon" in doujin.tags or "shotacon" in doujin.tags) and ctx.guild and not lolicon_allowed:
                    await sleep(0.5)
                    continue

                else:
                    break

        # Doujin count for tags
        tags_list = []
        for tag in [tag for tag in doujin.tags if tag.type == "tag"]:
            count = tag.count
            parse_count = list(str(count))
            if len(parse_count) < 4:
                tags_list.append(f"{tag.name}[{count}]")
            elif len(parse_count) >= 4 and len(parse_count) <= 6:
                count = count/1000
                tags_list.append(f"{tag.name}[{round(count, 1)}k]")
            elif len(parse_count) > 7:
                count = count/1000000
                tags_list.append(f"{tag.name}[{round(count, 2)}m]")

        
        if interface == "old":
            emb = Embed(
                description=f"Doujin ID: __`{doujin.id}`__\n"
                            f"Languages: {language_to_flag(doujin.languages)} `{', '.join([tag.name for tag in doujin.languages]) if doujin.languages else 'Not provided'}`\n"
                            f"Pages: `{len(doujin.images)}`\n"
                            f"Artist(s): `{', '.join([tag.name for tag in doujin.artists]) if doujin.artists else 'Not provided'}`\n"
                            f"Character(s): `{', '.join([tag.name for tag in doujin.characters]) if doujin.characters else 'Original'}`\n"
                            f"Parody of: `{', '.join([tag.name for tag in doujin.parodies]) if doujin.parodies else 'Original'}`\n"
                            f"Tags: ```{', '.join(tags_list) if doujin.tags else 'None provided'}```")
        else:
            emb = Embed()
            emb.add_field(
                inline=False,
                name="Title",
                value=f"`{shorten(doujin.title.pretty, width=256, placeholder='...') if doujin.title.pretty else 'Not provided'}`"
            ).add_field(
                inline=False,
                name="ID ー Pages",
                value=f"`{doujin.id} ー {len(doujin.images)}`"
            ).add_field(
                inline=False,
                name="Language(s)",
                value=f"{language_to_flag(doujin.languages)} `{', '.join([tag.name for tag in doujin.languages]) if doujin.languages else 'Not provided'}`"
            ).add_field(
                inline=False,
                name="Artist(s)",
                value=f"`{', '.join([tag.name for tag in doujin.artists]) if doujin.artists else 'Not provided'}`"
            ).add_field(
                inline=False,
                name="Character(s)",
                value=f"`{', '.join([tag.name for tag in doujin.characters]) if doujin.characters else 'Original'}`"
            ).add_field(
                inline=False,
                name="Parody Of",
                value=f"`{', '.join([tag.name for tag in doujin.parodies]) if doujin.parodies else 'Original'}`"
            ).add_field(
                inline=False,
                name="Tags",
                value=f"```{', '.join(tags_list) if doujin.tags else 'None provided'}```"
            )

        emb.set_author(
            name=f"{shorten(doujin.title.pretty, width=120, placeholder='...') if doujin.title.pretty else 'Not provided'}",
            url=f"https://nhentai.net/g/{doujin.id}/",
            icon_url="https://cdn.discordapp.com/emojis/845298862184726538.png?v=1")
        emb.set_thumbnail(
            url=doujin.images[0].src)
        
        print(f"[HRB] {ctx.author} ({ctx.author.id}) looked up `{doujin.id}`.")

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
                    url=doujin.images[0].src)
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
                        url=doujin.images[0].src)
                    emb.set_image(
                        url=Embed.Empty)
                    await edit.edit(embed=emb)

                    session = ImagePageReader(self.bot, ctx, doujin.images, f"{doujin.id} [*n*] {doujin.title.pretty if doujin.title.pretty else 'Not provided'}")
                    response = await session.setup()
                    if response:
                        print(f"[HRB] {ctx.author} ({ctx.author.id}) started reading `{doujin.id}`.")
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
        
        print(f"[HRB] {ctx.author} ({ctx.author.id}) started downloading {doujin.id} ({len(doujin.images)} pages).")
        
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


def setup(bot):
    bot.add_cog(RCommands(bot))
