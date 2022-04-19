from copy import deepcopy
from textwrap import shorten

from cogs.localization import *

restricted_tags = [
    "rape",
    "lolicon", 
    "shotacon",
    "incest"
]

def is_int(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

def is_float(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def language_to_flag(languages):
    """Given a language, convert it into a 2-emoji string of a respective flag."""
    is_translated = False
    main_language = None
    language_to_flag_dict = {
        "japanese": "🇯🇵", 
        "english": "🇬🇧", 
        "chinese": "🇨🇳", 
        "arabic": "🇪🇬",
        "cebuano": "🇵🇭",
        "javanese": "🇮🇩",
        "translated": "🔄"}

    if isinstance(languages, list):
        languages = deepcopy(languages)
        if "translated" in [tag.name for tag in languages] or "rewrite" in [tag.name for tag in languages]:
            is_translated = True
            [languages.remove(tag) for tag in languages if tag.name in ["translated", "rewrite"]]
            if not languages:
                return "🏳❔"

        [languages.remove(tag) for tag in languages if tag.name == "translated"]
        if "text cleaned" in [tag.name for tag in languages]:
            return "💬🧹"

        elif "speechless" in [tag.name for tag in languages]:
            return "💬❌"
        
        elif languages[0].name not in language_to_flag_dict:
            return "🏳❔"

        elif is_translated:
            return f"{language_to_flag_dict[languages[0].name]}🔁"

        elif not is_translated:
            return f"{language_to_flag_dict[languages[0].name]}💬"

    else:
        return "🏳❔"


def show_values(obj, value_width=200, value_oversize_placeholder="...", include_methods=True):
    items = []
    for i in dir(obj):
        if include_methods and callable(getattr(obj, i)):
            items.append(f"attr: {type(obj).__name__}.{i}: {shorten(str(getattr(obj, i)), width=value_width, placeholder=value_oversize_placeholder)}")
        else:
            continue

    if include_methods:
        for i in dir(obj):
            if callable(getattr(obj, i)):
                continue
            else:
                items.append(f"method: {type(obj).__name__}.{i}")

    return items

def repair_uniform_dict(reference, target):
    """Repairs `target` dict with `reference` dict data structure."""
    def recursive_repair(ref_dict: dict, target_dict: dict):
        for key, value in enumerate(ref_dict.values):
            # Missing key
            if key not in target_dict:
                target_dict[key] = value
                continue

            # Unmatching type
            if type(value) != type(target_dict[key]):
                # If not a dict, just use the reference dict.
                if isinstance(value, dict) and not isinstance(target_dict[key], dict):
                    target_dict[key] = value
                    continue

                # If not matching, try to convert
                if type(value) != type(target_dict[key]):
                    try:
                        target_dict[key] = type(value)(target_dict[key])
                    except Exception:
                        pass

                    continue

                
            
            if isinstance(value, dict):
                recursive_repair(value, target_dict[key])