# IMPORTS
from sys import exc_info
from copy import deepcopy
from contextlib import suppress

from discord.message import Message
from discord.errors import Forbidden, HTTPException
from discord.ext.commands.cog import Cog
from discord.ext.commands.context import Context
from discord.ext.commands.errors import (
    BotMissingPermissions,
    CommandNotFound,
    CommandOnCooldown,
    MissingPermissions,
    MissingRequiredArgument,
    NotOwner, BadArgument,
    CheckFailure
)

from utils.classes import Embed

class Events(Cog):
    def __init__(self, bot):
        self.bot = bot

    # Message events
    # --------------------------------------------------------------------------------------------------------------------------
    @Cog.listener()
    async def on_message(self, msg: Message):
        # MechHub Bot Status response
        if msg.author.id == 805162807942709268 and \
            msg.content.startswith(f"[{self.bot.user.id}] [MechHub Message Ping]"):
            await msg.channel.send("Pong!")
            return
        
        if msg.author.id == self.bot.user.id:
            return  # Don't respond to bots.

        if msg.author.id == 726313554717835284:  
            # If bot listing supports webhooks
            ids = msg.content.split(";")
            voter = int(ids[0])
            voted_for = int(ids[1])

            if voted_for == self.bot.user.id:
                user = await self.bot.fetch_user(voter)
                try:
                    await user.send("Voting message")

                except HTTPException or Forbidden:
                    print(f"[❌] User \"{user}\" voted for \"{self.bot.user}\". DM Failed.")
                else:
                    print(f"[✅] User \"{user}\" voted for \"{self.bot.user}\".")

                return

        # Check if the message is a command. 
        # Terminates the event if so, so the command can run.
        # Excutes notification message.
        verify_command = await self.bot.get_context(msg)
        if verify_command.valid:
            if str(msg.author.id) not in self.bot.user_data["UserData"]:
                self.bot.user_data["UserData"][str(msg.author.id)] = self.bot.user_defaults

            # Check data structure without changing values.
            def convert(data, reference, copy=None):
                if not copy: copy = deepcopy(data)
                for key in data:  # Delete unnecessary keys
                    if key not in reference.keys():
                        copy.pop(key)
                    elif isinstance(key, dict):
                        convert(data[key], reference[key], copy[key])
                
                for key, value in reference:  # Add missing keys
                    if key not in data.keys():
                        copy.update({key:value})
                    elif isinstance(key, dict):
                        convert(data[key], reference[key], copy[key])
                    
                data = deepcopy(copy)
                return data
            
            self.bot.user_data["UserData"][str(msg.author.id)] = \
                convert(self.bot.user_data["UserData"][str(msg.author.id)], self.bot.user_defaults)


            if self.bot.user_data["UserData"][str(msg.author.id)]["NotificationDue"]:
                await msg.author.send(embed=Embed(
                    title="Notification",
                    description="👋 It appears to be your first time using this bot!\n" \
                                "⚠️ This bot is to be used by mature users only and in NSFW channels.\n" \
                                "ℹ️ For more information and help, please use the `n!help` command. For brief legal information, please use the `n!legal` command."))

                self.bot.user_data["UserData"][str(msg.author.id)]["NotificationDue"] = False
            
            self.bot.inactive = 0
            return

    # Errors
    # --------------------------------------------------------------------------------------------------------------------------
    @Cog.listener()
    async def on_command_error(self, ctx: Context, error: Exception):
        if not isinstance(error, CommandNotFound):
            with suppress(Forbidden):
                await ctx.message.add_reaction("❌")
            
        if not isinstance(error, CommandOnCooldown) and ctx.command:
            ctx.command.reset_cooldown(ctx)
            
        if self.bot.config['debug_mode']:
            raise error.original
            
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
                    code = int(supposed_command.strip("n!"))
                    msg.content = f"n!code {code}"
                    await self.bot.process_commands(msg)
                    return
                except ValueError:
                    return
            
            elif isinstance(error, CommandOnCooldown):
                await msg.author.send(embed=Embed(
                    description=f"That command is on a {round(error.cooldown.per)} second cooldown.\n"
                                f"Retry in {round(error.retry_after)} seconds."))
            
            elif isinstance(error, CheckFailure):
                return

            else:
                em.description = f"**{type(error.original).__name__}**: {error.original}\n" \
                                 f"\n" \
                                 f"If you keep getting this error, please join the support server located in the help message."

                # Raising the exception causes the progam 
                # to think about the exception in the wrong way, so we must 
                # target the exception indirectly.
                if not self.bot.config["debug_mode"]:
                    try:
                        raise error.original
                    except Exception:
                        error = exc_info()

                    await self.bot.errorlog.send(error, event=f"Command: {ctx.command.name}")
                else:
                    try:
                        raise error.original
                    except AttributeError:
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