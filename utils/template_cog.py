from discord.ext.commands.cog import Cog
from discord.ext.commands.core import (
    has_permissions, 
    bot_has_permissions, 
    command
)

class Commands(Cog):
    def __init__(self, bot):
        self.bot = bot

def setup(bot):
    bot.add_cog(Commands(bot))