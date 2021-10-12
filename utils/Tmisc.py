from copy import deepcopy
from textwrap import shorten

from cogs.localization import *

restricted_tags = ["lolicon", "shotacon"]

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
        "translated": "🔄"}

    if isinstance(languages, list):
        languages = deepcopy(languages)
        if "translated" in [tag.name for tag in languages]:
            is_translated = True
            [languages.remove(tag) for tag in languages if tag.name == "translated"]
            if not languages:
                return "🏳❔"

        if "text cleaned" in [tag.name for tag in languages]:
            return "💬🧹"

        elif "speechless" in [tag.name for tag in languages]:
            return "💬❌"
        
        elif languages[0].name not in language_to_flag_dict:
            return "🏳❔"

        elif is_translated:
            return f"{language_to_flag_dict[languages[0].name]}🔄"

        elif not is_translated:
            return f"{language_to_flag_dict[languages[0].name]}💬"

    else:
        return "🏳❔"

def render_date(datetime, user_language):
    """Turn a datetime into a word-friendly string"""
    months = {
        1: "January",
        2: "February",
        3: "March",
        4: "April",
        5: "May",
        6: "June",
        7: "July",
        8: "August",
        9: "September",
        10: "October",
        11: "November",
        12: "December"
    }
    suffixs = {
        1: "st",
        2: "nd",
        3: "rd",
        4: "th",
        5: "th",
        6: "th",
        7: "th",
        8: "th",
        9: "th",
        0: "th"
    }

    day = str(datetime.day)
    hour = str(datetime.hour)
    if int(hour) > 12:
        hour = str(int(hour)-12)
        is_afternoon = True
    else:
        if user_language != "eng":
            hour = "0"+hour
        is_afternoon = False
    minute = str(datetime.minute)
    if len(minute) == 1:
        minute = "0"+minute

    # return f"On {months[datetime.month]} {datetime.day}{suffixs[int(day[-1])] if user_language=='eng' else ''}, {datetime.year} at {hour}:{datetime.minute} {'PM' if is_afternoon else 'AM'}"
    return localization[user_language]["doujin_info"]["fields"]["date_uploaded_format"].format(
        month_name=months[datetime.month] if user_language == "eng" else '',
        month_numeral=str(datetime.month),
        day=str(datetime.day)+(suffixs[int(day[-1])] if user_language=='eng' else ''),
        weekday=localization[user_language]["doujin_info"]["fields"]["date_uploaded_weekdays"][datetime.weekday()],
        year=str(datetime.year),
        hour=str(hour) if user_language=="eng" else str(datetime.hour),
        minute=str(minute),
        am_pm="PM" if is_afternoon else "AM"
    )


def show_values(obj, value_width=200, value_oversize_placeholder="...", include_methods=True):
    items = []
    for i in dir(obj):
        if not include_methods and callable(getattr(obj, i)):
            continue 

        items.append(f"{type(obj).__name__}.{i}: {shorten(str(getattr(obj, i)), width=value_width, placeholder=value_oversize_placeholder)}")

    return items
                