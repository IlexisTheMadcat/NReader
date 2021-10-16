from asyncio import sleep, TimeoutError

from discord import AppInfo, Permissions, NotFound
from discord.ext.commands.cog import Cog
from discord.ext.commands.context import Context
from discord.ext.commands.core import bot_has_permissions, command
from discord.utils import oauth_url
from discord_components import Button, Select, SelectOption

from utils.classes import (
    Embed, BotInteractionCooldown)
from cogs.localization import *


class MiscCommands(Cog):
    def __init__(self, bot):
        self.bot = bot

    # ------------------------------------------------------------------------------------------------------------------
    @command(
        name="invite",
        aliases=[
            "インヴァイト",  # JP alias
            "邀請"  # CN alias
        ])
    @bot_has_permissions(send_messages=True, embed_links=True)
    async def invite(self, ctx: Context):
        user_language = self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["Language"]
        if ctx.command.qualified_name not in localization[user_language]:
            conf = await ctx.send(
                embed=Embed(description=localization[user_language]["language_not_available"]["description"]).set_footer(text=localization[user_language]["language_not_available"]["footer"]),
                components=[Button(label=localization[user_language]["language_not_available"]["button"], style=2, emoji="▶️", id="continue")])

            while True:
                try:
                    interaction = await self.bot.wait_for("button_click", timeout=15, bypass_cooldown=True,
                        check=lambda i: i.message.id==conf.id and i.user.id==ctx.author.id)
                except TimeoutError:
                    await conf.edit(
                        embed=Embed(description=localization[user_language]["language_not_available"]["description"]).set_footer(text=localization[user_language]["language_not_available"]["footer"]),
                        components=[Button(label=localization[user_language]["language_not_available"]["button"], style=1, emoji="▶️", id="continue", disabled=True)])
                
                    return
            
                else:
                    try: await interaction.respond(type=6)
                    except NotFound: continue

                    if interaction.component.id == "continue":
                        user_language = "eng"
                        await conf.delete()
                        break

        app_info: AppInfo = await self.bot.application_info()
        permissions = Permissions()
        permissions.update(
            send_messages=True,
            embed_links=True,
            add_reactions=True,
            manage_messages=True,
            manage_roles=True,
            manage_channels=True)

        emb = Embed(
            title=localization[user_language]["invite"]["title"],
            description=localization[user_language]["invite"]["description"].format(url=oauth_url(app_info.id, permissions)),
        ).set_author(
            name=self.bot.user.name,
            icon_url=self.bot.user.avatar_url
        ).set_footer(text=localization[user_language]["invite"]["footer"])
        
        await ctx.send(embed=emb)

    @command(
        name="help",
        aliases=[
            "ヘルプ",  # JP alias
            "信息"  # CN alias
        ])
    @bot_has_permissions(send_messages=True, embed_links=True)
    async def bhelp(self, ctx):
        user_language = self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["Language"]
        if ctx.command.qualified_name not in localization[user_language]:
            conf = await ctx.send(
                embed=Embed(description=localization[user_language]["language_not_available"]["description"]).set_footer(text=localization[user_language]["language_not_available"]["footer"]),
                components=[Button(label=localization[user_language]["language_not_available"]["button"], style=2, emoji="▶️", id="continue")])

            while True:
                try:
                    interaction = await self.bot.wait_for("button_click", timeout=15, bypass_cooldown=True,
                        check=lambda i: i.message.id==conf.id and i.user.id==ctx.author.id)
                except TimeoutError:
                    await conf.edit(
                        embed=Embed(description=localization[user_language]["language_not_available"]["description"]).set_footer(text=localization[user_language]["language_not_available"]["footer"]),
                        components=[Button(label=localization[user_language]["language_not_available"]["button"], style=2, emoji="▶️", id="continue", disabled=True)])
                
                    return
            
                else:
                    try: await interaction.respond(type=6)
                    except NotFound: continue

                    if interaction.component.id == "continue":
                        user_language = "eng"
                        await conf.delete()
                        break

        emb = Embed(
            title=localization[user_language]["help"]["title"],
            description=localization[user_language]["help"]["description"]
        ).set_author(
            name=self.bot.user.name,
            icon_url=self.bot.user.avatar_url
        ).set_footer(text=localization[user_language]["help"]["footer"])
        
        edit = await ctx.send(
            embed=emb,
            components=[
                Select(id="languages", placeholder="🌐💬 Language / 言語 / 语", options=[
                   SelectOption(label=f"{localization[user_language]['language_options']['english']}/English", emoji="🇬🇧", value="eng", description="NReader is written in American English and is the default."),
                   SelectOption(label=f"{localization[user_language]['language_options']['japanese']}/日本語", emoji="🇯🇵", value="jp", description="❌これはまだ準備ができていません。"),  # GT - "This is not ready yet."
                   SelectOption(label=f"{localization[user_language]['language_options']['chinese']}/中國人", emoji="🇨🇳", value="cn", description="❌這還沒有準備好。")  # GT - "This is not ready yet."
                ])])

        while True:
            try:
                interaction = await self.bot.wait_for("select_option", timeout=30,
                    check=lambda i: i.message.id==edit.id and i.user.id==ctx.author.id)
            
            except TimeoutError:
                await edit.edit(components=[])
                return

            except BotInteractionCooldown:
                continue

            else:
                try: await interaction.respond(type=6)
                except NotFound: continue
                
                self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["Language"] = interaction.values[0]
                for notification in self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["NotificationsDue"]:
                    self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["NotificationsDue"][notification] = False

                user_language = self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["Language"]

                emb = Embed(
                    title=localization[user_language]["help"]["title"],
                    description=localization[user_language]["help"]["description"]
                ).set_author(
                    name=self.bot.user.name,
                    icon_url=self.bot.user.avatar_url
                ).set_footer(text=localization[user_language]["help"]["footer"])
        
                await edit.edit(
                    embed=emb,
                    components=[
                        Select(id="languages", placeholder="🌐💬 Language / 言語 / 语", options=[
                           SelectOption(label=f"{localization[user_language]['language_options']['english']}/English", emoji="🇬🇧", value="eng", description="NReader is written in American English and is the default."),
                           SelectOption(label=f"{localization[user_language]['language_options']['japanese']}/日本語", emoji="🇯🇵", value="jp", description="❌これはまだ準備ができていません。"),  # GT - "This is not ready yet."
                           SelectOption(label=f"{localization[user_language]['language_options']['chinese']}/中文", emoji="🇨🇳", value="cn", description="❌這還沒有準備好。")  # GT - "This is not ready yet."
                        ])])
    
    @command(
        name="privacy", 
        aliases=[
            "pcpl", "terms", "tos", "legal",
            "リーガル",  # JP alias
            "合法的"  # CN alias
        ])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    async def legal(self, ctx):
        user_language = self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["Language"]
        if ctx.command.qualified_name[1:len(ctx.command.qualified_name)] not in localization[user_language]:
            conf = await ctx.send(
                embed=Embed(description=localization[user_language]["language_not_available"]["description"]).set_footer(text=localization[user_language]["language_not_available"]["footer"]),
                components=[Button(label=localization[user_language]["language_not_available"]["button"], style=2, emoji="▶️", id="continue")])

            while True:
                try:
                    interaction = await self.bot.wait_for("button_click", timeout=15, bypass_cooldown=True,
                        check=lambda i: i.message.id==conf.id and i.user.id==ctx.author.id)
                except TimeoutError:
                    await conf.edit(
                        embed=Embed(description=localization[user_language]["language_not_available"]["description"]).set_footer(text=localization[user_language]["language_not_available"]["footer"]),
                        components=[Button(label=localization[user_language]["language_not_available"]["button"], style=2, emoji="▶️", id="continue", disabled=True)])
                
                    return
            
                else:
                    try: await interaction.respond(type=6)
                    except NotFound: continue

                    if interaction.component.id == "continue":
                        user_language = "eng"
                        await conf.delete()
                        break

        # Fetch document from one location
        channel = await self.bot.fetch_channel(815473015394926602)
        message = await channel.fetch_message(815473545307881522)
        await ctx.send(embed=Embed(
            title="<:info:818664266390700074> Legal Notice",
            description=message.content
        ).set_author(
            name=self.bot.user.name,
            icon_url=self.bot.user.avatar_url
        ).set_footer(
            text="Provided by MechHub"
        ))


def setup(bot):
    bot.add_cog(MiscCommands(bot))
