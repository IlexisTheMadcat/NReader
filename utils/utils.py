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

def language_to_flag(language):
    """Given a language, convert it into a 1-emoji string of a respective flag."""
    
    if isinstance(language, list):
        language_to_flag = {"japanese": "🇯🇵", "english": "🇬🇧", "chinese": "🇨🇳"}
        try:
            if "translated" in language:
                return f"{language_to_flag[language[1]]}🔄"

            elif "text cleaned" in language:
                return "💬🧹"

            elif "speechless" in language:
                return "💬❌"

            elif "translated" not in language:
                return f"{language_to_flag[language[0]]}💬"

            elif not language:
                return "🏳❔"
                
        except Exception:
            return "🏳❔"

    elif isinstance(language, str):     
        try:
            if language == "japanese":
                return "🇯🇵🔹"

            elif language == "english":
                return "🇬🇧🔹"

            elif language == "chinese": 
                return "🇨🇳🔹"

            else:
                return "🏳❔"
                
        except Exception:
            return "🏳❔"
    
    else:
        return "🏳❔"