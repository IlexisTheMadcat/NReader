from copy import deepcopy

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
    if isinstance(languages, list):
        languages = deepcopy(languages)
        if "translated" in [tag.name for tag in languages]:
            is_translated = True
            [languages.remove(tag) for tag in languages if tag.name == "translated"]
        
        language_to_flag = {"japanese": "🇯🇵", "english": "🇬🇧", "chinese": "🇨🇳", "translated": "🔄"}
        if "text cleaned" in [tag.name for tag in languages]:
            return "💬🧹"

        elif "speechless" in [tag.name for tag in languages]:
            return "💬❌"

        elif is_translated:
            return f"{language_to_flag[languages[0].name]}🔄"

        elif not is_translated:
            return f"{language_to_flag[languages[0].name]}💬"

        elif not languages:
            return "🏳❔"

    else:
        return "🏳❔"

def render_date(datetime):
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
    hour = deepcopy(datetime.hour)
    is_noon = False
    if hour > 12:
        hour -= 12
        is_noon = True

    return f"On {months[datetime.month]} {datetime.day}{suffixs[int(day[-1])]}, {datetime.year} at {hour}:{datetime.minute} {'PM' if is_noon else 'AM'}"