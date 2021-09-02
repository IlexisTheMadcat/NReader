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

                try:
                    try:
                        raise error.original
                    except AttributeError:
                        raise error
                except Exception:
                    error = exc_info()
                
                await self.bot.errorlog.send(error, ctx=ctx, event="Load Module")

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
            await self.bot.errorlog.send(error, ctx=ctx, event="Load Module")

        else:
            em = Embed(
                title="Administration: Load Module",
                description=f"Module `{module}` loaded successfully",
                color=0x00ff00
            )
            print(f"[HRB] Loaded module \"{module}\".")

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

            try:
                try:
                    raise error.original
                except AttributeError:
                    raise error
            except Exception:
                error = exc_info()
            
            await self.bot.errorlog.send(error, ctx=ctx, event="Reload Module")

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
            await self.bot.errorlog.send(error, ctx=ctx, event="Reload Module")

        else:
            em = Embed(
                title="Administration: Reload Module",
                description=f"Module `{module}` reloaded successfully",
                color=0x00ff00
            )
            print(f"[HRB] Reloaded module \"{module}\".")
    
        await ctx.send(embed=em)

    @is_owner()
    @command()
    async def config(self, ctx: Context, mode="view", setting=None, new_value=None):
        """View and change bot settings"""
        if mode == "view":
            message_lines = list()

            for setting, value in self.bot.config.items():
                message_lines.append(f"{setting}:\n{type(value).__name__}({value})")
            
            message_lines.insert(0, "```")
            message_lines.append("```")
            
            newline = "\n"
            em = Embed(
                title="Administration: Config",
                description=f"The options and values are listed below:\n"
                            f"{str(newline+newline).join(message_lines)}",
                color=0x0000ff)
            
            return await ctx.send(embed=em)
        
        elif mode == "change":
            if not setting or not new_value:
                return await ctx.send("Specify the setting and value to change.")
            
            if setting not in self.bot.config:
                return await ctx.send("That setting option doesn't exist.")

            if type(self.bot.config[setting]).__name__ == "int":
                try: self.bot.config[setting] = int(new_value)
                except ValueError: 
                    return await ctx.send("Invalid value type. Setting value should be of type `int`.")
            
            elif type(self.bot.config[setting]).__name__ == "float":
                try: self.bot.config[setting] = float(new_value)
                except ValueError: 
                    return await ctx.send("Invalid value type. Setting value should be of type `float`.")
            
            elif type(self.bot.config[setting]).__name__ == "bool":
                if new_value == "True":
                    self.bot.config[setting] = True
                elif new_value == "False":
                    self.bot.config[setting] = False
                else: 
                    return await ctx.send("Invalid value type. Setting value should be of type `bool`.")
            
            elif type(self.bot.config[setting]).__name__ == "str":
                self.bot.config[setting] = new_value
            
            else:
                return await ctx.send(f"Unknown config value type ({type(self.bot.config[setting]).__name__}).")
            
            await ctx.send(f"Changed `{setting}` to `{new_value}`")
    
    @is_owner()
    @group(name="say", invoke_without_command=True)
    async def say(self, ctx: Context, *, msg: str = ""):
        """Makes the bot send a message
        If self.say_dest is set, it will send the message there
        If it is not, it will send to ctx.channel"""
        dest = self.say_dest
        
        if dest:
            await ctx.send("I will await your words. Type `-stop` to cancel.")
        else:
            await ctx.send("I don't know where to send your message to!")
            return
        
        if isinstance(self.say_dest, TextChannel):
            while True:
                try:
                    m = await self.bot.wait_for("message", timeout=500, 
                        check=lambda m: m.channel.id==ctx.channel.id and m.author.id==ctx.author.id)
                except TimeoutError:
                    await ctx.send("Timed out.")
                    break
                else:
                    if m.content == "-stop" or m.content.startswith(self.bot.command_prefix):
                        await m.add_reaction("✅")
                        break
                    
                    await m.add_reaction("🕗")
                    await sleep(2)
                    if (len(m.content) / 5) * (60/self.say_wpm)-2 > 2:
                        async with dest.typing():
                            await sleep((len(m.content) / 5) * (60/self.say_wpm)-2)
                    await m.remove_reaction("🕗", self.bot.user)
                    
                    files = [await i.to_file() for i in m.attachments if m.attachments]
                    await dest.send(m.content, files=files)

        elif isinstance(dest, DMChannel):
            while True:
                try:
                    m = await self.bot.wait_for("message", timeout=500, 
                        check=lambda m: m.channel.id in [ctx.channel.id, dest.id] and m.author.id in [ctx.author.id, dest.recipient.id])
                except TimeoutError:
                    await ctx.send("Timed out.")
                    break
                else:
                    if m.author.id == ctx.author.id:
                        if m.content == "-stop" or m.content.startswith(self.bot.command_prefix):
                            await m.add_reaction("✅")
                            break
                        
                        await m.add_reaction("🕗")
                        await sleep(2)
                        if (len(m.content) / 5) * (60/self.say_wpm)-2 > 2:
                            async with dest.typing():
                                await sleep((len(m.content) / 5) * (60/self.say_wpm)-2)
                        
                        files = [await i.to_file() for i in m.attachments if m.attachments]
                        await dest.send(m.content, files=files)
                        await m.remove_reaction("🕗", self.bot.user)
                    
                    elif m.author.id == dest.recipient.id:
                        files = [await i.to_file() for i in m.attachments if m.attachments]
                        await ctx.author.send(f"**{dest.recipient.name}:** {m.content if m.content else '[No Content]'}", files=files)

    @is_owner()
    @say.command(name="_in")
    async def say_in(self, ctx: Context, dest:int = None):
        """Sets the destination for messages from `[p]say`"""
        if dest:
            try:
                self.say_dest = await self.bot.fetch_channel(dest)
            except NotFound:
                user = await self.bot.fetch_user(dest)
                self.say_dest = await user.create_dm()
            except Exception:
                em = Embed(
                    title="Administration: Set `say` Destination",
                    description=f"Error: `say` destination not found.",
                    color=0xFF0000)
                await ctx.send(embed=em)
                return
            
            if not self.say_dest or self.say_dest.id == ctx.author.id:
                em = Embed(
                    title="Administration: Set `say` Destination",
                    description=f"Error: `say` destination not found.",
                    color=0xFF0000)
                await ctx.send(embed=em)
                return
            
            if isinstance(self.say_dest, TextChannel):
                em = Embed(
                    title="Administration: Set `say` Destination",
                    description=f"__Say destination set__\n"
                                f"Guild: {self.say_dest.guild.name}\n"
                                f"Channel: {self.say_dest.mention}\n"
                                f"ID: {self.say_dest.id}",
                    color=0x00FF00)
                await ctx.send(embed=em)
                return
            
            elif isinstance(self.say_dest, DMChannel):
                em = Embed(
                    title="Administration: Set `say` Destination",
                    description=f"__Say destination set__\n"
                                f"User: {self.say_dest.recipient.mention}\n"
                                f"DMChannel ID: {self.say_dest.id}",
                    color=0x00FF00)
                await ctx.send(embed=em)
                return

        else:
            self.say_dest = None
            em = Embed(
                title="Administration: Set `say` Destination",
                description="Say destination has been unset",
                color=0x00FF00
            )
            await ctx.send(embed=em)
            return


def setup(bot):
    bot.add_cog(Admin(bot))
