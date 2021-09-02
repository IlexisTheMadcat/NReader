import json
from asyncio import sleep
from aiohttp import ClientSession
from datetime import datetime

from discordspy import Post as DiscordsPost, Client as DiscordsClient
from discord.activity import Activity
from discord.enums import ActivityType, Status
from discord.ext.commands.cog import Cog
from discord.ext.tasks import loop


class BackgroundTasks(Cog):
    """Background loops"""

    def __init__(self, bot):
        self.bot = bot
        self.save_data.start()
        self.status_change.start()
        self.del_update_stats.start()

        self.discords = DiscordsClient(bot, DISCORDS_TOKEN)

    @loop(seconds=60)
    async def status_change(self):
        time = datetime.utcnow().strftime("%H:%M")

        if self.bot.inactive >= 5:
            status = Status.idle
        else:
            status = Status.online

        if self.bot.config['debug_mode']:
            activity = Activity(
                type=ActivityType.playing,
                name="in DEBUG MODE")

        else:
            activity = Activity(
                type=ActivityType.watching,
                name=f"{time}/UTC | {self.bot.command_prefix} | {len(self.bot.guilds)}")

        await self.bot.change_presence(status=status, activity=activity)

    @loop(seconds=57.5)
    async def save_data(self):
        # If the repl is exited while saving, data may be corrupted or reset.
        print("[HRB: ... Saving, do not quit...", end="\r")
        await sleep(2)
        print("[HRB: !!! Saving, do not quit...", end="\r")
        time = datetime.now().strftime("%H:%M, %m/%d/%Y")

        self.bot.database.update(self.bot.user_data)

        self.bot.inactive = self.bot.inactive + 1
        print(f"[HRB: {time}] Running.")
    
    @loop(minutes=30)
    async def del_update_stats(self):
        """ This automatically updates your server count to Discord Extreme List every 30 minutes. """
        await self.bot.wait_until_ready()
        async with ClientSession() as session:
            async with session.post(f'https://api.discordextremelist.xyz/v2/bot/{self.bot.user.id}/stats',
                headers={'Authorization': self.bot.auth['DEL_TOKEN'],
                "Content-Type": 'application/json'},
                data=json.dumps({'guildCount': len(self.bot.guilds)})
            ) as r:
                js = await r.json()
                if js['error'] == True:
                    print(f'Failed to post to discordextremelist.xyz\n{js}')
    
    @loop(minutes=30)
    def discords_update_stats(self):
        self.discords.post_servers()

    @Cog.listener()  # Callback with response code for the above loop
    async def on_discords_server_post(self, status):
        if status != 200:
            await print("[HRB] Failed to post the server count to Discords.com.")

    @status_change.before_loop
    async def sc_wait(self):
        await self.bot.wait_until_ready()
        await sleep(30)

    @save_data.before_loop
    async def sd_wait(self):
        await self.bot.wait_until_ready()
        await sleep(15)
    
    def cog_unload(self):
        self.status_change.cancel()
        self.save_data.cancel()
        self.del_update_stats.cancel()
        self.discords_update_stats.cancel()

def setup(bot):
    bot.add_cog(BackgroundTasks(bot))