# IMPORTS
from os import walk, remove
from os.path import exists, join
from json import load
from sys import exc_info
from copy import deepcopy

from discord import __version__, Activity, ActivityType, Intents
from discord.enums import Status
from discord.permissions import Permissions
from discord.utils import oauth_url
from discord.ext.commands import ExtensionAlreadyLoaded
from discord_components import DiscordComponents
from discord_components.interaction import InteractionEventType

from utils.classes import Bot
from utils.errorlog import ErrorLog
from utils.FirebaseDB import FirebaseDB

# This bot is based on the NHentai-API module.
# https://pypi.org/project/NHentai-API/

DATA_DEFAULTS = {
    "UserData": {
        "UID": {  
            "Settings": {  # User Settings dict
                "UnrestrictedServers": [0],  # [int(serverID)]
                # Listings that are normally blocked for legal reasons in servers show in these servers.
                # Only the owner of the server can add its ID to this list.

                "SearchAppendage": " ",  # str(appendage)
                # Users may add a string to the end of searches. 
                # This string will be appended to all their searches no matter the case.

                "NotificationsDue": {
                    "FirstTime": False,
                    "LoliconViewingTip": False
                }  # dict of str:bool
                # A notification sent to users when they use a command for the first time.
                # These are set to true after being executed. Resets by command.

            },
            "nFavorites": {  # User favorites including bookmarks
                "Doujins": [0],  # [int(code)]
                "Bookmarks": {"placeholder": 1}  # {str(code):int(page)}
            },
            "History": (
                True,  # bool
                [0]  # [int(code)]
            ),
            # Keep a history of the user's reading.
            # "Bool"; Control whether or not the bot should record the user's history.

            "Recall": 0x000001
        }
    },
    "Tokens": {  # Replace ONLY for initialization
        "BOT_TOKEN": "xxx"  # str(token)
    },
    "config": {
        "debug_mode": False,        
        # Print exceptions to stdout.

        "error_log_channel": 734499801697091654,
        # The channel that errors are sent to.

        "first_time_tip": "👋 It appears to be your first time using this bot!\n"
                          "⚠️ This bot is to be used by mature users only and in NSFW channels.\n"
                          "ℹ️ For more information and help, please use the `n!help` command.\n"
                          "ℹ️ For brief legal information, please use the `n!legal` command.\n"
                          "ℹ️ MechHub highly recommends you join the support server: **[MechHub/DJ4wdsRYy2](https://discord.gg/DJ4wdsRYy2)**\n"
                          "||(If you are receiving this notification again, a portion of your data has been reset due to storage issues. Join the support server if you have previous data you want to retain.)||", 
        
        "lolicon_viewing_tip": "Tip: To view lolicon/shotacon doujins on Discord, you need to invite me to a server that you "
                               "own and run the `n!whitelist <'add' or 'remove'>` (Server-owner only) command. \n"
                               "This will allow all users in your server to open lolicon/shotacon doujins.\n"
                               "This command is not in the help menu.\n"
                               "Lolicon/shotacon doujins are __only__ reflected on your history, favorites, bookmarks, or searches __**in whitelisted servers**__."
    }
}

INIT_EXTENSIONS = [
    "admin",
    "background",
    "commands",
    #"Tcommands",
    "classes",
    #"Tclasses",
    "events",
    "help",
    "repl",
    #"web"
]

if exists("Workspace/Files/ServiceAccountKey.json"):
    key = load(open("Workspace/Files/ServiceAccountKey.json", "r"))
else:  # If it doesn't exists assume running on replit
    try:
        from replit import db
        key = dict(db["SAK"])
    except Exception:
        raise FileNotFoundError("Could not find ServiceAccountKey.json.")

db = FirebaseDB(
    "https://nreader-database-default-rtdb.firebaseio.com/", 
    fp_accountkey_json=key)

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
for key in DATA_DEFAULTS['config']:
    if key not in config_data:
        config_data[key] = DATA_DEFAULTS['config'][key]
        print(f"[MISSING VALUE] Config '{key}' missing. "
              f"Inserted default '{DATA_DEFAULTS['config'][key]}'")
found_data = deepcopy(config_data)  # Duplicate to avoid RuntimeError exception
for key in found_data:
    if key not in DATA_DEFAULTS['config']:
        config_data.pop(key)  # Remove redundant data
        print(f"[REDUNDANCY] Invalid config \'{key}\' found. "
              f"Removed key from file.")
del found_data  # Remove variable from namespace

db.update(user_data)

intents = Intents.default()

bot = Bot(
    description="Search, overview, and read doujins in Discord.",
    owner_ids=[331551368789622784],  # Ilexis
    status=Status.idle,
    activity=Activity(type=ActivityType.watching, name="hentai before work"),
    command_prefix="n!",

    config=config_data,
    database=db,
    user_data=user_data,   
    defaults=DATA_DEFAULTS,
    auth=db["Tokens"],
)

# If a custom help command is created:
bot.remove_command("help")

print(f"[BOT INIT] Running in: {bot.cwd}\n"
      f"[BOT INIT] Discord API version: {__version__}")

mypath = "Storage"
for root, dirs, files in walk(mypath):
    for file in files:
        remove(join(root, file))

@bot.event
async def on_ready():
    bot.comp_ext = DiscordComponents(bot, change_discord_methods=False)

    async def on_socket_response(res):
        if (res["t"] != "INTERACTION_CREATE") or (res["d"]["type"] != 3):
            return

        ctx = bot.comp_ext._get_interaction(res)
        for key, value in InteractionEventType.items():
            if value == res["d"]["data"]["component_type"]:
                bot.dispatch(key, ctx)
                break

    bot.add_listener(on_socket_response, name="on_socket_response")


    app_info = await bot.application_info()
    bot.owner = app_info.owner

    permissions = Permissions()
    permissions.update(
        send_messages=True,
        embed_links=True,
        add_reactions=True,
        manage_roles=True,
        manage_channels=True,
        manage_messages=True)

    # Add the ErrorLog object if the channel is specified
    if bot.config["error_log_channel"]:
        error_channel = await bot.fetch_channel(bot.config["error_log_channel"])
        bot.errorlog = ErrorLog(bot, error_channel)

    print("\n"
          "#-------------------------------#\n"
          "| Loading initial cogs...\n"
          "#-------------------------------#")

    for cog in INIT_EXTENSIONS:
        try:
            bot.load_extension(f"cogs.{cog}")
            print(f"| Loaded initial cog {cog}")
        except ExtensionAlreadyLoaded:
            continue
        
        except Exception as e:
            try:
                print(f"| Failed to load extension {cog}\n|   {type(e.original).__name__}: {e.original}")
            except AttributeError:
                print(f"| Failed to load extension {cog}\n|   {type(e).__name__}: {e}")
            error = exc_info()
            if error:
                await bot.errorlog.send(error, event="Load Initial Cog")

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