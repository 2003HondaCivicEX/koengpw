# app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import random

# --- deps for translation & hangul ---
from googletrans import Translator
import hgtk

app = FastAPI(title="Korean Keyboard Password Generator")

# Allow your WP domain to call the API
# Replace with your actual domain, e.g., "https://example.com"
ALLOWED_ORIGINS = [
    "*"  # For quick testing. Later, lock to your real domain.
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mapping of jamo characters to English keyboard layout
JAMO_TO_KEYBOARD = {
    'ㄱ': 'r', 'ㄲ': 'R', 'ㄴ': 's', 'ㄷ': 'e', 'ㄸ': 'E', 'ㄹ': 'f', 'ㅁ': 'a', 'ㅂ': 'q', 'ㅃ': 'Q',
    'ㅅ': 't', 'ㅆ': 'T', 'ㅇ': 'd', 'ㅈ': 'w', 'ㅉ': 'W', 'ㅊ': 'c', 'ㅋ': 'z', 'ㅌ': 'x', 'ㅍ': 'v', 'ㅎ': 'g',
    'ㅏ': 'k', 'ㅐ': 'o', 'ㅑ': 'i', 'ㅒ': 'O', 'ㅓ': 'j', 'ㅔ': 'p', 'ㅕ': 'u', 'ㅖ': 'P', 'ㅗ': 'h',
    'ㅘ': 'hk', 'ㅙ': 'ho', 'ㅚ': 'hl', 'ㅛ': 'y', 'ㅜ': 'n', 'ㅝ': 'nj', 'ㅞ': 'np', 'ㅟ': 'nl', 'ㅠ': 'b',
    'ㅡ': 'm', 'ㅢ': 'ml', 'ㅣ': 'l'
}

class GenerateRequest(BaseModel):
    word1: str
    symbol: str
    word2: str

class GenerateResponse(BaseModel):
    korean_word1: str
    korean_word2: str
    keyboard_word1: str
    keyboard_word2: str
    raw_password: str
    final_password: str

# --- Translation ---
translator = Translator()

def translate_to_korean(word: str) -> str:
    # googletrans can occasionally fail; you can add try/except & fallback here.
    result = translator.translate(word, src='en', dest='ko')
    return result.text

# Convert Hangul syllables to US keyboard typing format

def korean_to_keyboard_typing(hangul_text: str) -> str:
    us_keyboard_text = []
    for ch in hangul_text:
        if hgtk.checker.is_hangul(ch):
            try:
                initial, medial, final = hgtk.letter.decompose(ch)
                us_keyboard_text.append(JAMO_TO_KEYBOARD.get(initial, initial))
                us_keyboard_text.append(JAMO_TO_KEYBOARD.get(medial, medial))
                if final:
                    us_keyboard_text.append(JAMO_TO_KEYBOARD.get(final, final))
            except hgtk.exception.NotHangulException:
                us_keyboard_text.append(ch)
        else:
            us_keyboard_text.append(ch)
    return ''.join(us_keyboard_text)

# Randomly capitalize one alphabetic character in the password

def randomly_capitalize_one_letter(password: str) -> str:
    letters = [i for i, c in enumerate(password) if c.isalpha()]
    if not letters:
        return password
    idx = random.choice(letters)
    return password[:idx] + password[idx].upper() + password[idx+1:]

@app.post("/generate", response_model=GenerateResponse)
async def generate(data: GenerateRequest):
    word1 = (data.word1 or "").strip()
    word2 = (data.word2 or "").strip()
    symbol = (data.symbol or "").strip()

    # Hard limits for sanity
    if len(word1) > 50 or len(word2) > 50 or len(symbol) > 5:
        # In production, return HTTPException 400; here we just clip
        word1 = word1[:50]
        word2 = word2[:50]
        symbol = symbol[:5]

    korean_word1 = translate_to_korean(word1)
    korean_word2 = translate_to_korean(word2)

    keyboard_word1 = korean_to_keyboard_typing(korean_word1).replace(" ", "")
    keyboard_word2 = korean_to_keyboard_typing(korean_word2).replace(" ", "")

    raw_password = f"{keyboard_word1}{symbol}{keyboard_word2}"
    final_password = randomly_capitalize_one_letter(raw_password)

    return GenerateResponse(
        korean_word1=korean_word1,
        korean_word2=korean_word2,
        keyboard_word1=keyboard_word1,
        keyboard_word2=keyboard_word2,
        raw_password=raw_password,
        final_password=final_password,
    )
