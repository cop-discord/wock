import re


def replace_slang(text: str) -> str:
    sorted_slang = sorted(SLANG_REPLACEMENT.items(), key=lambda x: len(x[0]), reverse=True)
    
    for slang, replacement in sorted_slang:
        pattern = rf'\b{re.escape(slang)}\b'
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    return text

SLANG_REPLACEMENT = {
    "rn": "right now",
    "fr": "for real",
    "ong": "on god",
    "smh": "shaking my head",
    "tbh": "to be honest",
    "tbf": "to be fair",
    "tmr": "tomorrow",
    "tmrw": "tomorrow",
    "idk": "i don't know",
}

ACCENT_TO_TLD = {
    "us": "com",
    "uk": "co.uk",
    "ca": "ca",
    "au": "com.au",
    "in": "co.in",
    "es": "es",
    "mx": "com.mx",
    "fr": "fr",
    "fr_ca": "ca",
    "de": "de",
    "it": "it",
    "pt": "pt",
    "br": "com.br",
    "ru": "ru",
    "jp": "jp",
    "kr": "ko",
    "cn": "cn",
    "ae": "ae",
    "pl": "pl",
    "nl": "nl",
    "tr": "tr",
    "se": "se",
    "fi": "fi",
    "no": "no",
    "dk": "dk",
    "cz": "cz",
    "gr": "gr",
}

SUPPORTED_LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese (Simplified)",
    "ar": "Arabic",
    "pl": "Polish",
    "nl": "Dutch",
    "tr": "Turkish",
    "sv": "Swedish",
    "fi": "Finnish",
    "no": "Norwegian",
    "da": "Danish",
    "cs": "Czech",
    "el": "Greek",
}

SUPPORTED_ACCENTS = {
    "us": "United States",
    "uk": "United Kingdom",
    "ca": "Canada",
    "au": "Australia",
    "in": "India",
    "es": "Spain",
    "mx": "Mexico",
    "fr": "France",
    "de": "Germany",
    "it": "Italy",
    "pt": "Portugal",
    "br": "Brazil",
    "ru": "Russia",
    "jp": "Japan",
    "kr": "Korea",
    "cn": "China",
    "ae": "United Arab Emirates",
    "pl": "Poland",
    "nl": "Netherlands",
    "tr": "Turkey",
    "se": "Sweden",
    "fi": "Finland",
    "no": "Norway",
    "dk": "Denmark",
    "gr": "Greece",
}
