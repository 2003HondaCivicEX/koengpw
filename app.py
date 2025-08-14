# app.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import random
import time

# --- deps for translation & hangul ---
from googletrans import Translator
import hgtk

app = FastAPI(title="Korean Keyboard Password Generator")

# === CORS ===
# Lock this down to your site once you're done testing.
ALLOWED_ORIGINS = [
    "https://sudosdomain.com",
    "https://www.sudosdomain.com",
    # "http://localhost:3000",  # uncomment if testing locally
]
# For quick testing from anywhere, you can temporarily set: ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Models ===
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

# === Keyboard mapping ===
JAMO_TO_KEYBOARD = {
    'ㄱ': 'r', 'ㄲ': 'R', 'ㄴ': 's', 'ㄷ': 'e', 'ㄸ': 'E', 'ㄹ': 'f',
    'ㅁ': 'a', 'ㅂ': 'q', 'ㅃ': 'Q', 'ㅅ': 't', 'ㅆ': 'T', 'ㅇ': 'd',
    'ㅈ': 'w', 'ㅉ': 'W', 'ㅊ': 'c', 'ㅋ': 'z', 'ㅌ': 'x', 'ㅍ': 'v', 'ㅎ': 'g',
    'ㅏ': 'k', 'ㅐ': 'o', 'ㅑ': 'i', 'ㅒ': 'O', 'ㅓ': 'j', 'ㅔ': 'p', 'ㅕ': 'u',
    'ㅖ': 'P', 'ㅗ': 'h', 'ㅘ': 'hk', 'ㅙ': 'ho', 'ㅚ': 'hl', 'ㅛ': 'y',
    'ㅜ': 'n', 'ㅝ': 'nj', 'ㅞ': 'np', 'ㅟ': 'nl', 'ㅠ': 'b', 'ㅡ': 'm',
    'ㅢ': 'ml', 'ㅣ': 'l'
}

# === Translator (with retries) ===
translator = Translator()

def translate_to_korean(word: str, retries: int = 3, delay_sec: float = 0.4) -> str:
    """Translate EN->KO with light retry. If all fail, fall back to original."""
    last_err = None
    for _ in range(retries):
        try:
            if not word:
                return word
            res = translator.translate(word, src='en', dest='ko')
            return res.text or word
        except Exception as e:
            last_err = e
            time.sleep(delay_sec)
    # Fallback: don’t kill the request—just return original word
    return word

# === Hangul syllables -> US keyboard typing ===
def korean_to_keyboard_typing(hangul_text: str) -> str:
    out = []
    for ch in hangul_text:
        # Only decompose full Hangul syllables
        if hgtk.checker.is_hangul(ch):
            try:
                initial, medial, final = hgtk.letter.decompose(ch)
                out.append(JAMO_TO_KEYBOARD.get(initial, initial))
                out.append(JAMO_TO_KEYBOARD.get(medial, medial))
                if final:
                    out.append(JAMO_TO_KEYBOARD.get(final, final))
            except hgtk.exception.NotHangulException:
                out.append(ch)
        else:
            out.append(ch)
    return ''.join(out)

def randomly_capitalize_one_letter(password: str) -> str:
    idxs = [i for i, c in enumerate(password) if c.isalpha()]
    if not idxs:
        return password
    i = random.choice(idxs)
    return password[:i] + password[i].upper() + password[i+1:]

# === Health check ===
@app.get("/")
def health():
    return {"ok": True}

# === Main endpoint ===
@app.post("/generate", response_model=GenerateResponse)
async def generate(data: GenerateRequest):
    word1 = (data.word1 or "").strip()
    word2 = (data.word2 or "").strip()
    symbol = (data.symbol or "").strip()

    # Input guards
    if not word1 or not word2 or not symbol:
        raise HTTPException(status_code=400, detail="word1, symbol, and word2 are required")
    if len(word1) > 50 or len(word2) > 50 or len(symbol) > 5:
        raise HTTPException(status_code=400, detail="Inputs too long (limits: word<=50, symbol<=5)")

    # Translate
    korean_word1 = translate_to_korean(word1)
    korean_word2 = translate_to_korean(word2)

    # Convert to US keyboard typing & strip spaces
    keyboard_word1 = korean_to_keyboard_typing(korean_word1).replace(" ", "")
    keyboard_word2 = korean_to_keyboard_typing(korean_word2).replace(" ", "")

    # Build password
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
