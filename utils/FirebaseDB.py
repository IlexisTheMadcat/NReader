import firebase_admin
from firebase_admin import credentials, db
from os.path import exists
from copy import deepcopy
from typing import Union

# Now create a class to perform CRUD operations on
class FirebaseDB:
    """Create a simple CRUD operations helper for Google Firebase Realtime Databases.\n
    **Initiate with these arguments:**\n
    `databaseURL` - Works with Realtime Databases. Open it and copy its link.\n
    `fp_accountkey_json` - Fetch this file from the Project settings:\n
        Service Accounts > Firebase Admin SDK > Python > Generate new private key.\n
    `app_name` - Initialize the app with this name. *Note that no two instances of this class can have the same name.*\n
    `dbroot_path` - Choose the path of the database dict to start from. This is the destination key whose value will be overwritten.\n

    **Returns:**\n 
    ー Attr:`FirebaseDB.project_id` - The project ID that this class is operating on. Useful to check if 2 instances are running on the same project.\n
    ー Attr: `FirebaseDB.instance_name` - Returns `app_name` from `__init__` for later use. Again, no two instances with the same name can co-exist.\n
    ー Attr: `FirebaseDB.refer` - The Reference object that this class operates on. You can perform manual operations with it if you know how to use the SDK.\n
    ー Attr: `FirebaseDB._dbroot_path` - Returns `dbroot_path` from `__init__` for later use. Used to stay persistant with the root key.\n
    
    **Reading (HTTP GET):**\n
    ー Func: `FirebaseDB.get(key, default=None)` - Equal to dict().get(); Returns the requested value. If `value` is not found, returns `default`.\n
    ー Func: `FirebaseDB.keys()` - Equal to dict().keys(); Returns list of keys at the root.\n
    ー Func: `FirebaseDB.values()` - Equal to dict().values(); Returns list of values at the root.\n
    ー Func: `FirebaseDB.items()` - Equal to dict().items(); Returns list of keys at the root.\n
    ー Func: `FirebaseDB.copy()` - Equal to dict().copy(); Returns an exact copy of the database.\n
    
    **Writing (HTTP GET>WRITE>POST):**\n
    ー Func: `FirebaseDB.update(json)` - Equal to dict().update(); Returns the class instance.\n
    ー Func: `FirebaseDB.clear()` - Equal to dict().clear(); Returns the class instance.\n
    ー Func: `FirebaseDB.pop(key)` - Equal to dict().pop(); Returns the deleted key's value.\n
    ー Func: `FirebaseDB.popitem()` - Equal to dict().popitem(); Returns the last (key, value) added.\n
    ー Func: `FirebaseDB.overwrite(json)` - Additional method to completely overwrite the database with `json`. 
        If `json` is omitted, alias for `FirebaseDB.clear()`.
        Functionally identical to `FirebaseDB.clear().update(json)`.\n
    
    **Notes**:\n
    While a dictionary can have nested values, editing values in nested levels will **NOT** 
        send updates to the database and you may lose your data. To counter this, `.copy()` the database and 
        make any pythonic change to the returned dictionary. Then, call `.overwrite(json)`, where `json` is your
        updated dictionary.
    """
    def __init__(self, 
        databaseURL:str, 
        fp_accountkey_json:Union[str,dict]="serviceAccountKeyJSON.json", 
        app_name:str="[DEFAULT]", 
        dbroot_path:str="/",
    ) -> dict:
        if isinstance(fp_accountkey_json, str) and not exists(fp_accountkey_json):
            raise FileNotFoundError("The service account key could not be found. Make sure you entered the right location and try again.")
        
        try:
            cred = credentials.Certificate(fp_accountkey_json)
        except ValueError:
            raise ValueError("Something is wrong with the service account key provided. Please verify that it came from your Project setings.")
        try:
            database_app = firebase_admin.initialize_app(
                cred, {"databaseURL":databaseURL})
        except ValueError:
            raise ValueError(f"An instance of the FirebaseDB class already exists in this execution loop with the app_name \"{app_name}\". "
                             f"Create this class with a different app_name.")

        self.refer = db.reference(dbroot_path)
        self.project_id = database_app.project_id
        self.instance_name = database_app.name
        self._dbroot_path = dbroot_path
    
    def __dict__(self):
        data = self.refer.get(self._dbroot_path)[0]
        if not isinstance(data, dict):
            data = {}
        
        return data
    
    # Reading
    def __getitem__(self, key):
        """Dict-like `__getitem__` designed for Firebase. Returns the requested value."""
        data = self.refer.get(self._dbroot_path)[0]
        if not isinstance(data, dict):
            data = {}

        return data.__getitem__(key)

    def get(self, key, default=None):
        """Dict-like `get` designed for Firebase. Returns the requested value. If `value` is not found, returns `default`."""
        data = self.refer.get(self._dbroot_path)[0]
        if not isinstance(data, dict):
            data = {}
        
        return data.get(key, default)
    
    def __len__(self):
        """Dict-like `__len__` designed for Firebase. Returns an integer noting how many keys are at the root."""
        data = self.refer.get(self._dbroot_path)[0]
        if not isinstance(data, dict):
            data = {}
        
        return data.__len__()
    
    def keys(self) -> list:
        """Dict-like `keys` designed for Firebase. Returns list of keys at the root."""
        data = self.refer.get(self._dbroot_path)[0]
        if not isinstance(data, dict):
            data = {}
        
        return data.keys()
    
    def values(self) -> list:
        """Dict-like `values` designed for Firebase. Returns list of values at the root."""
        data = self.refer.get(self._dbroot_path)[0]
        if not isinstance(data, dict):
            data = {}
        
        return data.values()
    
    def items(self):
        """Dict-like `items` designed for Firebase. Returns a `dict_items()` instance."""
        data = self.refer.get(self._dbroot_path)[0]
        if not isinstance(data, dict):
            data = {}
        
        return data.items()
    
    def copy(self) -> dict:
        """Dict-like `copy` designed for Firebase. Returns an exact copy of the database."""
        data = self.refer.get(self._dbroot_path)[0]
        if not isinstance(data, dict):
            data = {}
        
        return deepcopy(data)
    
    # Writing
    def __setitem__(self, key, value):
        """Dict-like `__setitem__` designed for Firebase. Returns None."""
        data = self.refer.get(self._dbroot_path)[0]
        if not isinstance(data, dict):
            data = {}
        
        data[key] = value
        self.refer.set(data)
        return None
    
    def update(self, json:dict) -> dict:
        """Dict-like `update` designed for Firebase. Returns the class instance rather than None for fluent chaining."""
        data = self.refer.get(self._dbroot_path)[0]
        if not isinstance(data, dict):
            data = {}

        data.update(json)
        self.refer.set(data)
        return self
    
    def pop(self, key):
        """Dict-like `pop` designed for Firebase. Returns the deleted key's value."""
        data = self.refer.get(self._dbroot_path)[0]
        if not isinstance(data, dict):
            data = {}

        value = data.pop(key)
        self.refer.set(data)
        return value
    
    def popitem(self) -> tuple:
        """Dict-like `popitem` designed for Firebase. Returns the last (key, value) added."""
        data = self.refer.get(self._dbroot_path)[0]
        if not isinstance(data, dict):
            data = {}

        value = data.popitem()
        self.refer.set(data)
        return value
    
    def clear(self) -> dict:
        """Dict-like `clear` designed for Firebase. Returns the class instance rather than None for fluent chaining."""
        data = self.refer.get(self._dbroot_path)[0]
        if not isinstance(data, dict):
            data = {}

        data.clear()
        self.refer.set(data)
        return self

    # Custom method
    def overwrite(self, json:dict={}):
        """Custom method to clear the database and overwrite it entirely with `json`.\n
        If `json` is not provided, act as an alies for `FirebaseDB.clear()`.\n
        Equivalent to `FirebaseDB.clear().update(json)`.\n
        Can also be used when you need to make a bulk change, 
            instead of making many requests, send a new json over in one request."""
        self.refer.set(json)
        return 

if __name__ == "__main__":
    discovering_mode = False  # Discovering or Testing mode.

    if discovering_mode:
        CONFIG_DEFAULTS = {
            "debug_mode": False,
            # Print exceptions to stdout.

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

        # Security token provided by Google Firebase project
        cred = credentials.Certificate("dumbshit.json") 

        # Initializes Firebase with the running program
        database_app = firebase_admin.initialize_app(
            cred, {"databaseURL":"https://discord-bot-data-hosting-default-rtdb.firebaseio.com/"})

        # Create the root reference point
        refer = db.reference("/") 

        # Discovering methods of refer
        print("Actions: ", dir(refer)) 

        # Discovering methods of database_app
        print("\nAttributes: ", dir(database_app))  

        # `refer.get(path: str)` returns tuple, first item is database dict
        data = refer.get("/") 

        # `refer.set(dict)` overwrites database with `dict`
        if not data[0]:
            refer.set(DATA_DEFAULTS)

        # Print returned dict
        print("\nDatabase: ", refer.get("/")[0])

    if not discovering_mode:
        # Initiate new class:
        database = FirebaseDB(
            "https://discord-bot-data-hosting-default-rtdb.firebaseio.com/",
            "dumbshit.json",
            "Test",
            "/")
        
        # C-reate
        print("- Create New Key -")
        database["New Key"] = "New Value"
        
        # R-ead
        print("- Reading -")
        print("New Key:", database["New Key"])
        print("Keys:", database.keys())
        print("Values:", database.values())
        print("Items:", database.items())
        print("Copied json:", database.copy())

        # U-pdate
        print("- Update New Key -")
        database["New Key"] = "Different Value"
        print(database["New Key"])
    
        # D-elete
        print("- Delete key -")
        print("New Key popped:", database.pop("New Key"))
        print("Database cleared: ", database.clear())