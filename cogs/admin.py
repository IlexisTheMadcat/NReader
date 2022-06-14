from imp import reload
from sys import exc_info
from asyncio import sleep
from asyncio.exceptions import TimeoutError

from discord import TextChannel, Embed, DMChannel
from discord.errors import NotFound
from discord.ext.commands import command
from discord.ext.commands.cog import Cog
from discord.ext.commands.context import Context
from discord.ext.commands.core import group, is_owner
from discord.ext.commands.errors import (
    ExtensionAlreadyLoaded,
    ExtensionFailed,
    ExtensionNotFound,
    ExtensionNotLoaded,
    NoEntryPointError,
)


class Admin(Cog):
    """Administrative Commands"""

    def __init__(self, bot):
        self.bot = bot
        self.say_dest = None
        self.say_wpm = 120

        # If a dependancy is included in a depended cog's dependencies, it does not have to be added to a cog that depends on it.
        # Put dependances of a module in load order. THIS SHOULD NOT BE A NESTED DICT.
        self.dependencies = {
            "Tcommands*": [
                "Tlocalization",
                "Tclasses",
                "Tcommands"
            ],
            "Tclasses*": [
                "Tlocalization"
                "Tclasses"
            ],

            "commands*": [
                "localization",
                "classes",
                "commands"
            ],
            "classes*": [
                "localization"
                "classes"
            ],
        }

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
    @module.command(name="load", aliases=["reload"])
    async def load(self, ctx: Context, module: str):
        """load a module"""

        load_order = self.dependencies[module] if module in self.dependencies else [module]
        for mod in load_order:
            module = mod
            module_path = f"cogs.{module}"

            is_reload = False
            if module_path in [module.__module__ for cog, module in self.bot.cogs.items()]:
                is_reload = True

            try:
                if not is_reload:
                    await self.bot.load_extension(module_path)
                elif is_reload:
                    await self.bot.reload_extension(module_path)

            except ExtensionNotFound:
                em = Embed(
                    title=f"Administration: {'Rel' if is_reload else 'L'}oad Module Failed",
                    description=f"**__ExtensionNotFound__**\n"
                                f"No module `{module}` found in cogs directory",
                    color=0xff0000
                )

            except NoEntryPointError:
                em = Embed(
                    title=f"Administration: {'Rel' if is_reload else 'L'}oad Module Failed",
                    description=f"**__NoEntryPointError__**\n"
                                f"Module `{module}` does not define a `setup` function",
                    color=0xff0000
                )

            except ExtensionFailed as error:
                em = Embed(
                    title=f"Administration: {'Rel' if is_reload else 'L'}oad Module Failed",
                    description=f"**__ExtensionFailed__**\n"
                                f"An execution error occurred during module `{module}`'s setup function",
                    color=0xff0000
                )

                try:
                    try:
                        raise error.original
                    except AttributeError:
                        raise error
                except Exception:
                    error = exc_info()
                
                await self.bot.errorlog.send(error, ctx=ctx, event=f"{'Rel' if is_reload else 'L'}oad Module")

            except Exception as error:
                em = Embed(
                    title=f"Administration: {'Rel' if is_reload else 'L'}oad Module Failed",
                    description=f"**__{type(error).__name__}__**\n"
                                f"```py\n"
                                f"{error}\n"
                                f"```",
                    color=0xff0000
                )
                
                error = exc_info()
                await self.bot.errorlog.send(error, ctx=ctx, event=f"{'Rel' if is_reload else 'L'}oad Module")

            else:
                em = Embed(
                    title=f"Administration: {'Rel' if is_reload else 'L'}oad Module",
                    description=f"Module `{module}` {'re' if is_reload else ''}loaded successfully",
                    color=0x00ff00
                )
                print(f"[HRB] Loaded module \"{module}\".")

            await ctx.send(embed=em)

    @is_owner()
    @module.command(name="unload")
    async def unload(self, ctx: Context, module: str):
        """Unload a module"""

        module = f"cogs.{module}"

        try:
            await self.bot.unload_extension(module)

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

            try:
                try:
                    raise error.original
                except AttributeError:
                    raise error
            except Exception:
                error = exc_info()
            
            await self.bot.errorlog.send(error, ctx=ctx, event="Unload Module")

        else:
            em = Embed(
                title="Administration: Unload Module",
                description=f"Module `{module}` unloaded successfully",
                color=0x00ff00
            )
            print(f"[HRB] Unloaded module \"{module}\".")
        
        await ctx.send(embed=em)


async def setup(bot):
    await bot.add_cog(Admin(bot))
