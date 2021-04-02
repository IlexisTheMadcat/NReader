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

    @command(name="help", aliases=["h"])
    @bot_has_permissions(send_messages=True, embed_links=True)
    async def bhelp(self, ctx):
        emb = Embed(
            title="<:info:818664266390700074> Help",
            description="""
**Search, overview, and read doujins in Discord.**
**Support server: [MechHub/DJ4wdsRYy2](https://discord.gg/DJ4wdsRYy2)**
These commands can only be used in NSFW-marked channels!
Aliases are separated by slashes [/].

__`doujin_info/code [code]`__
*Open the details of a doujin. Leave blank for a random one. Discover!*
ー *ProTip: You can use a doujin ID as a command to run this. Ex: "n!177013"*

__`download_doujin/dl <code>`__
*Download all pages of a certain doujin.*

__`search_doujins/search [query]`__ 
*Search doujins. Only the first result page is shown.*
ー While `query` is optional, it is required if you do not have an appendage set up.
ーー See the `search_appendage` command in this message.

__`favorites/fav [add|remove] <code>`__
*Add/Remove a doujin to/from your favorites list. Run with no arguments to view your list.*

__`bookmarks/bm`__
*Review your bookmarks and the doujins they belong to.*
ー *This list is updated when you click the 🔖/❌ icon while reading a doujin.*

🆕__`search_appendage/appendage [text|"clear_appendage"]`__
*Add a string of text to all of your searches. Use this as a way to blacklist tags.*
ー *`text` can be anything (spaces allowed), not just a list of tags. It is fed into nHentai's search bar like normal.*
ー *To clear your appendage, replace `text` with "clear_appendage". Both operations will ask to confirm your change.*
ー *If you get unexpected search results, check back over this command.*

🆕__`custom_random/crand [query]`__
ー Similar to `search_doujins`, except it pulls a random one instead of having to dig through the search.
ー Again, while `query` is optional, it is required if you do not have an appendage set up.

__`history [toggle|clear]`__
*Toggle the recording of or clear your viewing history.*
ー *Your history can only be seen when **you** run the command.*
ー *No one can see your history, you can't see theirs unless in a public channel.*
ー *Your history is updated when you run `doujin_info` or `📖Read` a result from `search_doujins`.*
"""
        ).add_field(
            inline=False,
            name="Misc Commands",
            value="""
__`help`__
*Shows this message.*

__`icons`__
*Show a list of the icons that **this** bot uses and what they mean.*

__`privacy/pcpl/terms/tos/legal`__
*Shows the Privacy Policy and Terms of Service for Mechhub Bot Factory.*

__`invite`__
*Sends this bot's invite url with all permissions listed under Required Permissions.*
"""
        ).add_field(
            inline=False,
            name="Required Permissions",
            value="""
\- Send Messages 
\- Embed Lings
\- Add Reactions
\- *Manage Reactions
\- *Manage Roles 
\- *Manage Channels
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
**Interface**
<a:nreader_loading:810936543401213953> = The bot is loading results.
⬛ A result in a search interactive or favorites list.
🟥 The currently selected result of a search interactive.
*️⃣ A result in a search interactive is a favorite to the caller.

**Warnings/Errors**
❌ Something caused an error and caused the process to stop. Often used as a reaction.
🔎❌ A certain doujin could not be found.
⚠️🚫 A doujin you tried to pull up contains lolicon/shotacon content and cannot be shown in that server.
🟨 An entry in your favorites that contains lolicon/shotacon content and is only shown in DMs or whitelisted servers.

**Languages**
**Note**: There is a small chance that a result displays the wrong language.
🇯🇵 The doujin is in Japanese.
🇺🇸 The doujin is in English.*
🇨🇳 The doujin is in Chinese.
💬 The doujin is written in its original language.
🔄 The doujin was translated from its original language.
💬❌ The doujin has no words or "speechless".
🏳️❔ The language wasn't found yet or not provided.

**Controls**
🔼 Move up in a search interactive.
🔽 Move down in a search interactive.
⏭️ Go to the next page of a doujin.
⏮️ Go to the previous page of a doujin.
🔢 Input a result number in a search or page number in a doujin.
⏹️ Stop an interactive or a doujin **[Auto-invoked when left inactive]**.
📖 Start reading the selected result in a search or a doujin overview.
🔍 Toggle thumbnail/image view of doujin covers in a search or doujin overview.
🔖 Create/replace bookmark.
❌ (In a doujin) Remove bookmark.
""").set_footer(
        text="* English uses the US flag since the UK flag is not yet a valid emoji."
    ).set_author(
        name=self.bot.user.name,
        icon_url=self.bot.user.avatar_url
    ))

def setup(bot):
    bot.add_cog(MiscCommands(bot))
