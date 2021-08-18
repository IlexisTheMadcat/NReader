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