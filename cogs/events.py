# IMPORTS
from copy import deepcopy
from sys import exc_info
from contextlib import suppress

from discord.message import Message
from discord.errors import Forbidden, NotFound, HTTPException
from discord.ext.commands import Cog, Context
from discord.ext.commands.cooldowns import BucketType
from discord.ext.commands.errors import (
    BotMissingPermissions,
    CommandNotFound,
    CommandOnCooldown,
    MaxConcurrencyReached,
    MissingPermissions,
    MissingRequiredArgument,
    NotOwner, BadArgument,
    CheckFailure
)

from utils.classes import Embed
from cogs.localization import *

class Events(Cog):
    def __init__(self, bot):
        self.bot = bot

    # Message events
    # --------------------------------------------------------------------------------------------------------------------------
    @Cog.listener()
    async def on_message(self, msg: Message):
        # Cooldown
        if msg.author.id in self.bot.global_cooldown: return
        else: self.bot.global_cooldown.update({msg.author.id:"placeholder"})

        # If bot listing supports webhooks
        if msg.author.id == 726313554717835284:
            ids = msg.content.split(";")
            voter = int(ids[0])
            voted_for = int(ids[1])

            if voted_for == self.bot.user.id:
                user = await self.bot.get_user(voter)
                if not user: return

                try:
                    await user.send("Voting message")

                except HTTPException or Forbidden:
                    print(f"[❌] {user} ({user.id}) voted for \"{self.bot.user}\". DM Failed.")
                else:
                    print(f"[✅] {user} ({user.id} voted for \"{self.bot.user}\".")

                return
        
        # Don't respond to bots.
        if msg.author.bot:
            return 

        # Checks if the message is any attempted command.
        if msg.content.startswith(self.bot.command_prefix) and not msg.content.startswith(self.bot.command_prefix+" "):
            if str(msg.author.id) not in self.bot.user_data["UserData"]:
                self.bot.user_data["UserData"][str(msg.author.id)] = deepcopy(self.bot.defaults["UserData"]["UID"])

            user_language = self.bot.user_data["UserData"][str(msg.author.id)]["Settings"]["Language"]
            
            if not self.bot.user_data["UserData"][str(msg.author.id)]["Settings"]["NotificationsDue"]["FirstTime"]:
                with suppress(Forbidden):
                    await msg.author.send(embed=Embed(
                        title=localization[user_language]["notifications_due"]["first_time_tip"]["title"],
                        description=localization[user_language]["notifications_due"]["first_time_tip"]["description"]))
                
                self.bot.user_data["UserData"][str(msg.author.id)]["Settings"]["NotificationsDue"]["FirstTime"] = True

            self.bot.inactive = 0
        
            await self.bot.process_commands(msg)
            return

    # Errors
    # --------------------------------------------------------------------------------------------------------------------------
    @Cog.listener()
    async def on_command_error(self, ctx: Context, error: Exception):
        if not isinstance(error, CommandNotFound):
            with suppress(Forbidden, NotFound):
                await ctx.message.add_reaction("❌")
            
        if not isinstance(error, CommandOnCooldown) and ctx.command:
            ctx.command.reset_cooldown(ctx)
            
        if self.bot.config['debug_mode']:
            try:
                raise error.original
            except AttributeError:
                raise error
            
        if not self.bot.config['debug_mode']:
            msg = ctx.message
            em = Embed(title="Error", color=0xff0000)
            if isinstance(error, BotMissingPermissions):
                em.description = f"This bot is missing one or more permissions listed in `{self.bot.command_prefix}help` " \
                                 f"under `Required Permissions` or you are trying to use the command in a DM channel.\n" \
                                 f"\n" \
                                 f"**Pleae note that `doujin_info` and `search_doujins` can only be used in servers. Try creating a private one.**"

            elif isinstance(error, MissingPermissions):
                em.description = "You are missing a required permission, or you are trying to use the command in a DM channel."

            elif isinstance(error, NotOwner):
                em.description = "That command is not listed in the help menu and is to be used by the owner only."

            elif isinstance(error, MissingRequiredArgument):
                em.description = f"\"{error.param.name}\" is a required argument for command " \
                                 f"\"{ctx.command.name}\" that is missing."

            elif isinstance(error, BadArgument):
                em.description = f"You didn't type something correctly. Details below:\n" \
                                 f"{error}"

            elif isinstance(error, CommandNotFound):
                supposed_command = msg.content.split()[0]
                try:
                    if supposed_command.startswith("n!") and \
                    not supposed_command.startswith("n!T"):  # stable
                        code = int(supposed_command.strip("n!"))
                        msg.content = f"n!code {code}"
                        await self.bot.process_commands(msg)
                        return
                    elif supposed_command.startswith("n!T"):  # experimental
                        code = int(supposed_command.strip("n!T"))
                        msg.content = f"n!Tcode {code}"
                        await self.bot.process_commands(msg)
                        return
                except ValueError:
                    return
            
            elif isinstance(error, CommandOnCooldown):
                em.description = f"That command is on a {round(error.cooldown.per)} second cooldown.\n" \
                                 f"Retry in {round(error.retry_after)} seconds."
            
            elif isinstance(error, MaxConcurrencyReached):
                to_str = {
                    BucketType.user: "user",
                    BucketType.guild: "server",
                    BucketType.channel: "channel",
                    BucketType.channel: "member",
                    BucketType.channel: "category",
                    BucketType.channel: "role",
                }

                em.description = f"That command can only have up to {error.number} instances per {to_str[error.per]}.\n" \
                                 f"Look for and click the {self.bot.get_emoji(853668227175546952)} (STOP) icon to stop the command, or let it time out, before executing it again."

            elif isinstance(error, CheckFailure):
                return

            else:
                try:
                    em.description = f"**{type(error.original).__name__}**: {error.original}\n" \
                                     f"\n" \
                                     f"If you keep getting this error, please join the support server."
                except AttributeError:
                    em.description = f"**{type(error).__name__}**: {error}\n" \
                                     f"\n" \
                                     f"If you keep getting this error, please join the support server."
                
                # Raising the exception causes the progam 
                # to think about the exception in the wrong way, so we must 
                # target the exception indirectly.
                if not self.bot.config["debug_mode"]:
                    try:
                        if hasattr(error, "original"):
                            raise error.original
                        else:
                            raise error
                    except Exception:
                        error = exc_info()

                    await self.bot.errorlog.send(error, ctx=ctx, event=f"Command: {ctx.command.name}")
                
                else:
                    if hasattr(error, "original"):
                        raise error.original
                    else:
                        raise error
            
            try:
                await ctx.send(embed=em)
            except Forbidden:
                with suppress(Forbidden):
                    await ctx.author.send(
                        content="This error was sent likely because I "
                                "was blocked from sending messages there.",
                        embed=em)

def setup(bot):
    bot.add_cog(Events(bot))