from asyncio import sleep
from datetime import datetime

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
                name=f"{self.bot.text_status} | UTC: {time}")

        await self.bot.change_presence(status=status, activity=activity)

    @loop(seconds=57.5)
    async def save_data(self):
        # If the repl is exited while saving, data may be corrupted or reset.
        print("[HRB: 🟢Saving, do not quit...", end="\r")
        await sleep(2)
        print("[HRB: ⚠Saving, do not quit...", end="\r")
        time = datetime.now().strftime("%H:%M, %m/%d/%Y")

        self.bot.database.update(self.bot.user_data)

        self.bot.inactive = self.bot.inactive + 1
        print(f"[HRB: {time}] Running.")
    
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


def setup(bot):
    bot.add_cog(BackgroundTasks(bot))