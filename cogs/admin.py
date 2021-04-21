from sys import exc_info
from copy import deepcopy

from discord.embeds import Embed
from discord.ext.commands.cog import Cog
from discord.ext.commands.context import Context
from discord.ext.commands.core import group, is_owner
from discord.ext.commands.errors import (
    ExtensionAlreadyLoaded,
    ExtensionFailed,
    ExtensionNotFound,
    ExtensionNotLoaded,
    NoEntryPointError
)


class Admin(Cog):
    """Administrative Commands"""

    def __init__(self, bot):
        self.bot = bot

    @is_owner()
    @group(name="module", aliases=["cog", "mod"], invoke_without_command=True)
    async def module(self, ctx: Context):
        """Base command for managing bot modules

        Use without subcommand to list currently loaded modules"""

        modules = {module.__module__: cog for cog, module in self.bot.cogs.items()}
        space = len(max(modules.keys(), key=len))

        fmt = "\n".join([f"{module}{' ' * (space - len(module))} : {cog}" for module, cog in modules.items()])

        em = Embed(
            title="Administration: Currently Loaded Modules",
            description=f"```py\n{fmt}\n```",
            color=0x00ff00
        )
        await ctx.send(embed=em)

    @is_owner()
    @module.command(name="load", usage="(module name)")
    async def load(self, ctx: Context, module: str):
        """load a module

        If `verbose=True` is included at the end, error tracebacks will
        be sent to the errorlog channel"""

        module = f"cogs.{module}"

        try:
            self.bot.load_extension(module)

        except ExtensionNotFound:
            em = Embed(
                title="Administration: Load Module Failed",
                description=f"**__ExtensionNotFound__**\n"
                            f"No module `{module}` found in cogs directory",
                color=0xff0000
            )

        except ExtensionAlreadyLoaded:
            em = Embed(
                title="Administration: Load Module Failed",
                description=f"**__ExtensionAlreadyLoaded__**\n"
                            f"Module `{module}` is already loaded",
                color=0xff0000
            )

        except NoEntryPointError:
            em = Embed(
                title="Administration: Load Module Failed",
                description=f"**__NoEntryPointError__**\n"
                            f"Module `{module}` does not define a `setup` function",
                color=0xff0000
            )

        except ExtensionFailed as error:
            if isinstance(error.original, TypeError):
                em = Embed(
                    title="Administration: Load Module Failed",
                    description=f"**__ExtensionFailed__**\n"
                                f"The cog loaded by `{module}` must be a subclass of discord.ext.commands.Cog",
                    color=0xff0000
                )
            else:
                em = Embed(
                    title="Administration: Load Module Failed",
                    description=f"**__ExtensionFailed__**\n"
                                f"An execution error occurred during module `{module}`'s setup function",
                    color=0xff0000
                )

                error = exc_info()
                await self.bot.errorlog.send(error, event="Load Module")

        except Exception as error:
            em = Embed(
                title="Administration: Load Module Failed",
                description=f"**__{type(error).__name__}__**\n"
                            f"```py\n"
                            f"{error}\n"
                            f"```",
                color=0xff0000
            )

            error = exc_info()
            await self.bot.errorlog.send(error, event="Load Module")

        else:
            em = Embed(
                title="Administration: Load Module",
                description=f"Module `{module}` loaded successfully",
                color=0x00ff00
            )
            print(f"[] Loaded module \"{module}\".")

        await ctx.send(embed=em)

    @is_owner()
    @module.command(name="unload", usage="(module name)")
    async def unload(self, ctx: Context, module: str):
        """Unload a module

        If `verbose=True` is included at the end, error tracebacks will
        be sent to the errorlog channel"""

        module = f"cogs.{module}"

        try:
            self.bot.unload_extension(module)

        except ExtensionNotLoaded:
            em = Embed(
                title="Administration: Unload Module Failed",
                description=f"**__ExtensionNotLoaded__**\n"
                            f"Module `{module}` is not loaded",
                color=0xff0000
            )

        except Exception as error:
            em = Embed(
                title="Administration: Unload Module Failed",
                description=f"**__{type(error).__name__}__**\n"
                            f"```py\n"
                            f"{error}\n"
                            f"```",
                color=0xff0000
            )

            error = exc_info()
            await self.bot.errolog.send(error, event="Unload Module")

        else:
            em = Embed(
                title="Administration: Unload Module",
                description=f"Module `{module}` unloaded successfully",
                color=0x00ff00
            )
            print(f"[] Unloaded module \"{module}\".")
        
        await ctx.send(embed=em)

    @is_owner()
    @module.command(name="reload", usage="(module name)")
    async def reload(self, ctx: Context, module: str):
        """Reload a module

        If `verbose=True` is included at the end, error tracebacks will
        be sent to the errorlog channel"""

        module = f"cogs.{module}"

        try:
            self.bot.reload_extension(module)

        except ExtensionNotLoaded:
            em = Embed(
                title="Administration: Reload Module Failed",
                description=f"**__ExtensionNotLoaded__**\n"
                            f"Module `{module}` is not loaded",
                color=0xff0000
            )

        except ExtensionNotFound:
            em = Embed(
                title="Administration: Reload Module Failed",
                description=f"**__ExtensionNotFound__**\n"
                            f"No module `{module}` found in cogs directory",
                color=0xff0000
            )

        except NoEntryPointError:
            em = Embed(
                title="Administration: Reload Module Failed",
                description=f"**__NoEntryPointError__**\n"
                            f"Module `{module}` does not define a `setup` function",
                color=0xff0000
            )

        except ExtensionFailed as error:
            if isinstance(error.original, TypeError):
                em = Embed(
                    title="Administration: Reload Module Failed",
                    description=f"**__ExtensionFailed__**\n"
                                f"The cog loaded by `{module}` must be a subclass of discord.ext.commands.Cog",
                    color=0xff0000
                )
            else:
                em = Embed(
                    title="Administration: Reload Module Failed",
                    description=f"**__ExtensionFailed__**\n"
                                f"An execution error occurred during module `{module}`'s setup function",
                    color=0xff0000
                )

                error = exc_info()
                await self.bot.errorlog.send(error, event="Reload Module")

        except Exception as error:
            em = Embed(
                title="Administration: Reload Module Failed",
                description=f"**__{type(error).__name__}__**\n"
                            f"```py\n"
                            f"{error}\n"
                            f"```",
                color=0xff0000
            )

            error = exc_info()
            await self.bot.errorlog.send(error, "Load Module")

        else:
            em = Embed(
                title="Administration: Reload Module",
                description=f"Module `{module}` reloaded successfully",
                color=0x00ff00
            )
            print(f"[] Reloaded module \"{module}\".")
    
        await ctx.send(embed=em)

    @is_owner()
    @group(name="config", aliases=["bot", "settings"], invoke_without_command=True)
    async def config(self, ctx: Context):
        """View Bot settings"""
        em = Embed(
            title="Administration: Config",
            description=f"The options and values are listed below:\n"
                        f"```"
                        f"debug_mode: {self.bot.config['debug_mode']}\n"
                        f"text_status: \"{self.bot.text_status}\" (namespace only)\n"
                        f"prefix: {self.bot.command_prefix} (namespace only)\n"
                        f"error_log_channel: {self.bot.config['error_log_channel']}"
                        f"```",
            color=0x0000ff
        )
        return await ctx.send(embed=em)

    @is_owner()
    @config.command(name="prefix", aliases=["command_prefix"])
    async def prefix(self, ctx: Context, *, val: str = None):
        """View or set bot prefix"""

        if val:
            orig = deepcopy(self.bot.command_prefix)
            self.bot.command_prefix = val

            em = Embed(
                title="Administration: Bot Prefix Config",
                description=f"New prefix: `{val}`\n"
                            f"Original prefix: `{orig}`",
                color=0x00ff00
            )
            print(f"[] Updated bot prefix to \"{val}\".")

        else:
            em = Embed(
                title="Administration: Bot Prefix Config",
                description=f"Bot prefix: `{self.bot.command_prefix}`",
                color=0x0000ff
            )

        return await ctx.send(embed=em)

    @is_owner()
    @config.command(name="debug", aliases=["debug_mode"])
    async def debug(self, ctx: Context, *, val: str = None):
        """View or set debug mode"""

        if val:
            if val in ["True", "False"]:
                val = True if val == "True" else False
                orig = deepcopy(self.bot.config['debug_mode'])
                self.bot.config['debug_mode'] = val

                em = Embed(
                    title="Administration: Bot Debug Mode Config",
                    description=f"New value: `{val}`\n"
                                f"Original value: `{orig}`",
                    color=0x00ff00
                )
                print(f"[] Updated debug_mode to \"{val}\".")

            else:
                em = Embed(
                    title="Administration: Bot Debug Mode Config",
                    description=f"Invalid value given: `{val}`\n"
                                f"Valid values: `True` `False`",
                    color=0xff0000
                )

        else:
            em = Embed(
                title="Administration: Bot Debug Mode Config",
                description=f"Debug Mode: `{self.bot.config['debug_mode']}`",
                color=0x0000ff
            )

        return await ctx.send(embed=em)

    @is_owner()
    @config.command(name="text_status", aliases=["status"])
    async def text_status(self, ctx, *, val: str = None):
        """View or set bot status"""

        if val:
            orig = deepcopy(self.bot.text_status)
            self.bot.text_status = val

            em = Embed(
                title="Administration: Text Status Config",
                description=f"New status: `{val}`\n"
                            f"Original status: `{orig}`",
                color=0x00ff00
            )
            print(f"[] Updated status to \"{val}\".")

        else:
            em = Embed(
                title="Administration: Text Status Config",
                description=f"Current status: `{self.bot.text_status}`",
                color=0x0000ff
            )

        return await ctx.send(embed=em)

    @is_owner()
    @config.command(name="error_log_channel")
    async def error_channel(self, ctx, val=None):
        if val:
            try:
                val = int(val)
            except ValueError:
                em = Embed(
                    title="Administration: ErrorLog Channel Config",
                    description="`ValueError`: `val` must be an integer.",
                    color=0xff0000
                )
                return await ctx.send(embed=em)

            orig = deepcopy(self.bot.config['error_log_channel'])
            self.bot.config['error_log_channel'] = val

            em = Embed(
                title="Administration: ErrorLog Channel Config",
                description=f"New error channel id: `{val}`\n"
                            f"Original error original channel id: `{orig}`",
                color=0x00ff00
            )

        else:
            err_channel = self.bot.get_channel(self.bot.config['error_log_channel'])
            if err_channel:
                em = Embed(
                    title="Administration: ErrorLog Channel Config",
                    description=f"Current error channel id: `{err_channel.id}`\n"
                                f"Located in guild: `{err_channel.guild.name}`\n"
                                f"Channel name: {err_channel.mention}",
                    color=0x0000ff
                )
            else:
                em = Embed(
                    title="Administration: ErrorLog Channel Config",
                    description=f"Current error channel id: `{err_channel.id}`\n"
                                f":warning: Channel does not exist!",
                    color=0xff0000
                )

        return await ctx.send(embed=em)

def setup(bot):
    bot.add_cog(Admin(bot))
