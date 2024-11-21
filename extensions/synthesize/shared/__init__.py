
import re
from io import BytesIO
from typing import List, Tuple
from gtts import gTTS
from jishaku.functools import executor_function

from ..shared.constants import ACCENT_TO_TLD

@executor_function
def synthesize(text: str, language: str = "en", accent: str = "us") -> BytesIO:
    """Synthesize text into an audio buffer."""

    tld = ACCENT_TO_TLD.get(accent, "com")
    try:
        tts = gTTS(text=text, lang=language, tld=tld)
    except Exception as exc:
        raise ValueError(f"Error with TTS conversion: {exc,}")
    
    buffer = BytesIO()
    tts.write_to_fp(buffer)
    buffer.seek(0)
    return buffer

def escape_text(text: str) -> str:
    """Clean text by removing URLs and Discord emojis."""

    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"<a?:\w+:\d+>", "", text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s]', '', text) 
    return text.strip()

def is_scrambled_text(text: str, min_length: int = 8) -> bool:
    """Detect scrambled/nonsense text with improved heuristics."""

    text = text.lower().strip()
    if len(text) < min_length:
        return False
        
    vowels = set('aeiou')
    consonants = set('bcdfghjklmnpqrstvwxz')
    
    char_freq = {}
    for c in text:
        if c.isalpha():
            char_freq[c] = char_freq.get(c, 0) + 1
    
    if not char_freq:
        return True
        
    vowel_count = sum(char_freq.get(v, 0) for v in vowels)
    consonant_count = sum(char_freq.get(c, 0) for c in consonants)
    
    if vowel_count == 0 or consonant_count == 0:
        return True
        
    ratio = vowel_count / (consonant_count or 1)
    if ratio < 0.25 or ratio > 0.75:
        return True
    
    for i in range(len(text) - 2):
        if all(c in consonants for c in text[i:i+3]):
            return True
        if all(c in vowels for c in text[i:i+3]):
            return True
            
    unique_chars = len(set(text))
    if unique_chars / len(text) > 0.8: 
        return True
        
    return False

def get_word_groups(text: str) -> List[Tuple[str, int]]:
    """Group similar words and count their frequencies."""

    words = text.lower().split()
    word_groups = {}
    
    for word in words:
        simplified = ''.join(c for c in word if c.isalnum())
        if simplified:
            word_groups[simplified] = word_groups.get(simplified, 0) + 1
            
    return sorted(word_groups.items(), key=lambda x: x[1], reverse=True)

def has_excessive_repetition(text: str, max_repeats: int = 4, max_length: int = 100) -> bool:
    """Detect spam patterns with improved pattern recognition."""

    text = text.lower().strip()
    words = text.split()
    
    scrambled_count = sum(1 for word in words if is_scrambled_text(word))
    if scrambled_count >= 2:
        return True

    if any(len(word) > 15 for word in words):
        return True
    
    single_chars = [w for w in words if len(w) == 1]
    if len(single_chars) >= 3:
        return True

    if len(words) > max_length:
        return True
        
    word_groups = get_word_groups(text)
    if word_groups and word_groups[0][1] >= max_repeats:
        return True
        
    text_no_spaces = text.replace(" ", "")
    for i in range(len(text_no_spaces) - 2):
        if text_no_spaces[i] * 3 in text_no_spaces[i:i+3]:
            return True
            
    return False

def is_spam(text: str) -> bool:
    """Main spam detection function combining all checks."""

    cleaned_text = escape_text(text)
    if not cleaned_text or len(cleaned_text) < 4:
        return False
        
    return (
        has_excessive_repetition(cleaned_text) or
        sum(1 for word in cleaned_text.split() if is_scrambled_text(word)) >= 2 or
        len(set(cleaned_text.split())) < len(cleaned_text.split()) / 2 
    )