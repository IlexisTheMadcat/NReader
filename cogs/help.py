from discord import AppInfo, Permissions
from discord.ext.commands.cog import Cog
from discord.ext.commands.context import Context
from discord.ext.commands.core import bot_has_permissions, command
from discord.utils import oauth_url

from utils.classes import Embed

class MiscCommands(Cog):
    def __init__(self, bot):
        self.bot = bot

    # ------------------------------------------------------------------------------------------------------------------
    @command()
    @bot_has_permissions(send_messages=True, embed_links=True)
    async def invite(self, ctx: Context):
        """Sends an OAuth bot invite URL"""

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
            description=f'[Click Here]({oauth_url(app_info.id, permissions)}) '
                        f'to invite this bot to your server.\n'
        ).set_author(
            name=f"Invite {self.bot.user.name}",
            icon_url=self.bot.user.avatar_url
        ).set_footer(
            text="Provided by MechHub Bot Factory")
        
        await ctx.send(embed=emb)

    @command(name="help")
    @bot_has_permissions(send_messages=True, embed_links=True)
    async def bhelp(self, ctx):
        emb = Embed(
            title="<:info:818664266390700074> Help",
            description="""
**Search, overview, and read doujins in Discord.**
**Support server: [MechHub/DJ4wdsRYy2](https://discord.gg/DJ4wdsRYy2)**

For the full information sheet, visit [this Google Docs page](https://docs.google.com/document/d/e/2PACX-1vQAJRI5B8x0CP3ZCHjK9iZ8KQq3AGHEMwiBQL72Mwf1Zu6N2THedbAi1ThuB9iiuzcBv8ipt5_XfQf4/pub).
Don't worry, it supports dark-mode enforcements :)
"""
        ).add_field(
            inline=False,
            name="Credits",
            value="""
**NHentai-API** and its services are provided by Alexandre Ramos @ PyPI.
"""
        ).set_author(
                name=self.bot.user.name,
                icon_url=self.bot.user.avatar_url
        ).set_footer(
            text="Provided by MechHub Bot Factory")
        
        await ctx.send(embed=emb)
    
    @command(name="privacy", aliases=["pcpl", "terms", "tos", "legal"])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    async def legal(self, ctx):
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
            text="Provided by MechHub Bot Factory"
        ))
    
    @command(aliases=["symbols"])
    @bot_has_permissions(
        send_messages=True, 
        embed_links=True)
    async def icons(self, ctx):
        await ctx.send(embed=Embed(
            title="<:info:818664266390700074> Bot Icons and What They Mean",
            description="""
__**Interface**__
<a:nreader_loading:810936543401213953> = The bot is loading results.
🔎 Bring the thumbnail image to the main image window, and back again.
⬛ A result in a search interactive or favorites list.
🟥 The currently selected result of a search interactive.
`*️⃣` A result in a search interactive is a favorite to the caller.

__**Warnings/Errors/Confirmations**__
✔ Something succeeded in execution.
❌ Something caused an error and caused the process to stop. Often used as a reaction.
🔎❌ A certain doujin could not be found.️️️️
⚠️ A warning mentioned by a command.
⚠️🚫 A doujin you tried to pull up contains lolicon/shotacon content and cannot be shown in that server.
🟨 An entry in your favorites that contains lolicon/shotacon content and is only shown in DMs or whitelisted servers.
⌛ A command or action timed out waiting for user input.

__**Languages**__
**Note**: There is a small chance that a result displays the wrong language.
🇯🇵 The doujin is in Japanese.
🇬🇧 The doujin is in English.
🇨🇳 The doujin is in Chinese.
💬 The doujin is written in its original language.
🔄 The doujin was translated from its original language.
💬❌ The doujin has no words or "speechless".
🏳️❔ The language wasn't yet found or not provided.
💬🧹 The doujin has all its "text cleaned".

__**Controls**__
⌨ Start interacting with a search.
🔼 Move up in a search interactive.
🔽 Move down in a search interactive.
⏭️ Go to the next page of a doujin.
⏮️ Go to the previous page of a doujin.
🔢 Input a result number in a search or page number in a doujin.
⏹️ Stop an interactive or a doujin **[Auto-invoked when left inactive]**.
📖 Start reading the selected result in a search or a doujin overview.
🔍 Toggle thumbnail/image view of doujin covers in a search or doujin overview.
🔖 Create/replace/remove bookmark.
""").set_author(
        name=self.bot.user.name,
        icon_url=self.bot.user.avatar_url
    ))

def setup(bot):
    bot.add_cog(MiscCommands(bot))
