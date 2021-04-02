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

def language_to_flag(languages: list):
    """Given a list of languages, convert it into a 2-emoji string of respective flags. Bound to have KeyError exceptions."""
    
    language_to_flag = {"japanese": "🇯🇵", "english": "🇺🇸", "chinese": "🇨🇳"}
    if "translated" in languages:
        return f"{language_to_flag[languages[1]]}🔄"
    elif "text cleaned" in languages:
        return "💬🧹"
    elif "speechless" in languages:
        return "💬❌"
    elif "translated" not in languages:
        return f"{language_to_flag[languages[0]]}💬"
    elif not languages:
        return "🏳❔"
