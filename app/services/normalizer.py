import re

DIGITS_MAP = {
    '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
    '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9',
    '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
    '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9',
}

CHAR_MAP = {
    'ك': 'ک',
    'ي': 'ی',
    'ى': 'ی',
    'ئ': 'ی',
    'ؤ': 'و',
    'أ': 'ا',
    'إ': 'ا',
    'آ': 'ا',
    'ة': 'ه',
    'ۀ': 'ه',
}

def normalize_persian_text(text: str) -> str:
    if not text:
        return ""
    
    text = text.strip().lower()
    
    # 1. Digits
    for k, v in DIGITS_MAP.items():
        text = text.replace(k, v)
        
    # 2. Characters
    for k, v in CHAR_MAP.items():
        text = text.replace(k, v)
        
    # 3. Diacritics
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
    
    # 4. Zero-width non-joiner -> space
    text = text.replace('\u200c', ' ')
    
    # 5. Punctuation
    text = re.sub(r'[^\w\s\u0600-\u06FF]', ' ', text)
    
    # 6. Collapse spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def tokenize_text(text: str) -> list[str]:
    normalized = normalize_persian_text(text)
    if not normalized:
        return []
    stop_words = {'و', 'در', 'از', 'به', 'با', 'که', 'برای'}
    return [t for t in normalized.split(' ') if t and t not in stop_words]
