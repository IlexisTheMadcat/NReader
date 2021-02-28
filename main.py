# IMPORTS
from sys import exc_info
from copy import deepcopy

from discord import __version__, Activity, ActivityType, Intents
from discord.enums import Status
from discord.permissions import Permissions
from discord.utils import oauth_url

from utils.classes import Bot
from utils.errorlog import ErrorLog
from utils.FirebaseDB import FirebaseDB

# NOTES

CONFIG_DEFAULTS = {
    "debug_mode": False,        
    # Print exceptions to stdout.

    "muted_dms": [],  # List of UIDs.
    # Block support DMs from members who abuse the system.

    "error_log_channel": 734499801697091654
    # The channel that errors are sent to. 
}

DATA_DEFAULTS = {
    "UserData": {
        "authorID": {  # User Settings
            "Settings": {
                "Unrestricted Servers": ["serverID"]  
                # Listings that are normally blocked for legal reasons in servers show in these servers.
                # Only the owner of the server can add its ID to this list.
            },
            "nFavorites": {  # User favorites including bookmarks
                "Doujins": [
                    "code"
                ],
                "Bookmarks": {
                    "code": "Page"
                }
            },
            "History": ("Bool", ["code"])
            # Keep a history of the user's reading.
            # "Bool"; Control whether or not the bot should record the user's history.
            # ー Toggleable via command.
        }
    },
    "Tokens": {
        "BOT_TOKEN": "xxx"
    },
    "config": CONFIG_DEFAULTS
}

INIT_EXTENSIONS = [
    "admin",
    "background",
    "commands",
    "events",
    "help",
    "repl",
    "web"
]

db = FirebaseDB(
    "https://nreader-database-default-rtdb.firebaseio.com/", 
    fp_accountkey_json="Workspace/Files/dumbshit.json")

user_data = db.copy()
# Check the database
for key in DATA_DEFAULTS:
    if key not in user_data:
        user_data[key] = DATA_DEFAULTS[key]
        print(f"[MISSING VALUE] Data key '{key}' missing. "
              f"Inserted default '{DATA_DEFAULTS[key]}'")
found_data = deepcopy(user_data)  # Duplicate to avoid RuntimeError exception
for key in found_data:
    if key not in user_data:
        user_data.pop(key)  # Remove redundant data
        print(f"[REDUNDANCY] Invalid data \'{key}\' found. "
              f"Removed key from file.")
del found_data  # Remove variable from namespace
config_data = user_data["config"]
# Check the bot config
for key in CONFIG_DEFAULTS:
    if key not in config_data:
        config_data[key] = CONFIG_DEFAULTS[key]
        print(f"[MISSING VALUE] Config '{key}' missing. "
              f"Inserted default '{CONFIG_DEFAULTS[key]}'")
found_data = deepcopy(config_data)  # Duplicate to avoid RuntimeError exception
for key in found_data:
    if key not in CONFIG_DEFAULTS:
        config_data.pop(key)  # Remove redundant data
        print(f"[REDUNDANCY] Invalid config \'{key}\' found. "
              f"Removed key from file.")
del found_data  # Remove variable from namespace

db.update(user_data)

print("[] Configurations loaded.")


intents = Intents.default()
intents.presences = True

bot = Bot(
    description="Search, overview, and read doujins in Discord.",
    owner_ids=[331551368789622784],  # Ilexis
    status=Status.idle,
    activity=Activity(type=ActivityType.watching, name=""),
    command_prefix="n!",
    config=config_data,

    database=db,
    user_data=user_data,
    auth=db["Tokens"]
)

# If a custom help command is created:
bot.remove_command("help")

print(f"[BOT INIT] Running in: {bot.cwd}\n"
      f"[BOT INIT] Discord API version: {__version__}")

@bot.event
async def on_ready():
    app_info = await bot.application_info()
    bot.owner = bot.get_user(app_info.owner.id)

    permissions = Permissions()
    permissions.update(
        send_messages=True,
        embed_links=True,
        add_reactions=True,
        manage_roles=True,
        manage_channels=True,
        manage_messages=True)

    # Add the ErrorLog object if the channel is specified
    if bot.user_data["config"]["error_log_channel"]:
        bot.errorlog = ErrorLog(bot, bot.user_data["config"]["error_log_channel"])

    print("\n"
          "#-------------------------------#\n"
          "| Loading initial cogs...\n"
          "#-------------------------------#")

    for cog in INIT_EXTENSIONS:
        try:
            bot.load_extension(f"cogs.{cog}")
            print(f"| Loaded initial cog {cog}")
        except Exception as e:
            print(f"| Failed to load extension {cog}\n|   {type(e.original).__name__}: {e.original}")
            error = exc_info()
            if error:
                await bot.errorlog.send(error, event="Load Initial Cog")
            
            #print("[BOT FAILED] Check the ErrorLog for error details.")
            #await bot.logout()

    print(f"#-------------------------------#\n"
          f"| Successfully logged in.\n"
          f"#-------------------------------#\n"
          f"| User:      {bot.user}\n"
          f"| User ID:   {bot.user.id}\n"
          f"| Owner:     {bot.owner}\n"
          f"| Guilds:    {len(bot.guilds)}\n"
          f"| OAuth URL: {oauth_url(app_info.id, permissions)}\n"
          f"#------------------------------#\n")

if __name__ == "__main__":
    bot.run()