from NHentai.nhentai import Tag

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

def language_to_flag(languages: Union[Tag, List[Tag]]):
    """Given a language, convert it into a 2-emoji string of a respective flag."""
    
    if isinstance(language, list):
        language_to_flag = {"japanese": "🇯🇵", "english": "🇬🇧", "chinese": "🇨🇳"}
        try:
            if "translated" in [tag.name for tag in languages]:
                return f"{language_to_flag[language[1]]}🔄"

            elif "text cleaned" in [tag.name for tag in languages]:
                return "💬🧹"

            elif "speechless" in [tag.name for tag in languages]:
                return "💬❌"

            elif "translated" not in [tag.name for tag in languages]:
                return f"{language_to_flag[language[0]]}💬"

            elif not languages:
                return "🏳❔"
                
        except Exception:
            return "🏳❔"

    elif isinstance(languages, str):     
        try:
            if languages.name == "japanese":
                return "🇯🇵🔹"

            elif languages.name == "english":
                return "🇬🇧🔹"

            elif languages.name == "chinese": 
                return "🇨🇳🔹"

            else:
                return "🏳❔"
                
        except Exception:
            return "🏳❔"
    
    else:
        return "🏳❔"