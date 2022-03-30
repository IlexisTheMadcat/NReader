from asyncio import sleep, TimeoutError, iscoroutinefunction
from asyncio.transports import ReadTransport

from discord import ui, SelectOption, ButtonStyle, ActionRow, AppInfo, Permissions, NotFound
from discord.ext.commands.cog import Cog
from discord.ext.commands.context import Context
from discord.ext.commands.core import bot_has_permissions, command
from discord.utils import oauth_url

from utils.classes import Embed, BotInteractionCooldown, ViewConstructor
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
    async def invite(self, ctx):
        # This tells the user that the command they are trying to use isn't translated yet.
        user_language = {"lang": self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["Language"]}
        if ctx.command.qualified_name not in localization[user_language["lang"]]:
            class Continue(ui.View):
                def __init__(self):
                    super().__init__(timeout=15)
                    self.value = None
                
                @ui.button(label=localization[user_language["lang"]]["language_not_available"]["button"], style=ButtonStyle.primary, emoji="▶️", custom_id="continue")
                async def continue_button(self, button, interaction):
                    if interaction.user.id == ctx.author.id:
                        user_language["lang"] = "eng"
                        await self.message.delete()
                        self.value = True
                        self.stop()

                async def on_timeout():
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

        app_info: AppInfo = await self.bot.application_info()
        permissions = Permissions()
        permissions.update(
            send_messages=True,
            embed_links=True,
            add_reactions=True,
            manage_messages=True,
            manage_roles=True,
            manage_channels=True,
            use_slash_commands=True)

        emb = Embed(
            title=localization[user_language]["invite"]["title"],
            description=localization[user_language]["invite"]["description"].format(url=oauth_url(app_info.id, permissions=permissions)),
        ).set_author(
            name=self.bot.user.name,
            icon_url=self.bot.user.avatar.url
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
        # This tells the user that the command they are trying to use isn't translated yet.
        user_language = {"lang": self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["Language"]}
        if ctx.command.qualified_name not in localization[user_language["lang"]]:
            class Continue(ui.View):
                def __init__(self):
                    super().__init__(timeout=15)
                    self.value = None
                
                @ui.button(label=localization[user_language["lang"]]["language_not_available"]["button"], style=ButtonStyle.primary, emoji="▶️", custom_id="continue")
                async def continue_button(self, button, interaction):
                    user_language["lang"] = "eng"
                    await conf.delete()
                    self.value = True
                    self.stop()

                async def on_timeout(self):
                    await conf.delete()
                    self.stop()

            emb = Embed(
                description=localization[user_language["lang"]]["language_not_available"]["description"]
            ).set_footer(text=localization[user_language["lang"]]["language_not_available"]["footer"])
            view = Continue()
            conf = await ctx.send(embed=emb, view=view)
            await view.wait()
            if not view.value:
                return
        user_language = user_language["lang"]

        class SelectMenuView(ui.View):
            def __init__(self, bot):
                super().__init__(timeout=10)
                self.add_item(self.Dropdown(bot))

            class Dropdown(ui.Select):
                def __init__(self, bot):
                    options=[
                        SelectOption(label=f"{localization[user_language]['language_options']['english']}/English", emoji="🇬🇧", value="eng", description="NReader is written in American English and is the default."),
                        SelectOption(label=f"{localization[user_language]['language_options']['japanese']}/日本語", emoji="🇯🇵", value="jp", description="部分的な機能。"),  # GT - "Partial functionality."
                        SelectOption(label=f"{localization[user_language]['language_options']['chinese']}/中文", emoji="🇨🇳", value="cn", description="功能有限。")  # GT - "Limited functionality."
                    ]
                    super().__init__(placeholder="🌐💬 Language / 言語 / 语", min_values=1, max_values=1, options=options)
                    self.bot = bot

                async def callback(self, interaction):
                    self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["Language"] = self.values[0]
                    for notification in self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["NotificationsDue"]:
                        self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["NotificationsDue"][notification] = False

                    user_language = self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["Language"]
                    emb = Embed(
                        title=localization[user_language]["help"]["title"],
                        description=localization[user_language]["help"]["description"]
                    ).set_author(
                        name=self.bot.user.name,
                        icon_url=self.bot.user.avatar.url
                    ).set_footer(text=localization[user_language]["help"]["footer"])

                    await interaction.response.edit_message(embed=emb)

            async def on_timeout(self):
                await help_message.edit(embed=emb, view=None)
                self.stop()
        
        emb = Embed(
            title=localization[user_language]["help"]["title"],
            description=localization[user_language]["help"]["description"]
        ).set_author(
            name=self.bot.user.name,
            icon_url=self.bot.user.avatar.url
        ).set_footer(text=localization[user_language]["help"]["footer"])

        help_message = await ctx.send(embed=emb, view=SelectMenuView(self.bot))

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
        # This tells the user that the command they are trying to use isn't translated yet.
        user_language = {"lang": self.bot.user_data["UserData"][str(ctx.author.id)]["Settings"]["Language"]}
        if ctx.command.qualified_name not in localization[user_language["lang"]]:
            class Continue(ui.View):
                def __init__(self):
                    super().__init__(timeout=15)
                    self.value = None
                
                @ui.button(label=localization[user_language["lang"]]["language_not_available"]["button"], style=ButtonStyle.primary, emoji="▶️", custom_id="continue")
                async def continue_button(self, button, interaction):
                    user_language["lang"] = "eng"
                    await conf.delete()
                    self.value = True
                    self.stop()

                async def on_timeout(self):
                    await conf.delete()
                    self.stop()

            emb = Embed(
                description=localization[user_language["lang"]]["language_not_available"]["description"]
            ).set_footer(text=localization[user_language["lang"]]["language_not_available"]["footer"])
            view = Continue()
            conf = await ctx.send(embed=emb, view=view)
            await view.wait()
            if not view.value:
                return

        user_language = user_language["lang"]

        # Fetch document from one location
        channel = await self.bot.fetch_channel(815473015394926602)
        message = await channel.fetch_message(815473545307881522)
        await ctx.send(embed=Embed(
            title="<:info:818664266390700074> Legal Notice",
            description=message.content
        ).set_author(
            name=self.bot.user.name,
            icon_url=self.bot.user.avatar.url
        ).set_footer(
            text="Provided by MechHub"
        ))


async def setup(bot):
    await bot.add_cog(MiscCommands(bot))
