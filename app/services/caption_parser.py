import re
from pydantic import BaseModel
from .normalizer import normalize_persian_text

class ParsedCaption(BaseModel):
    title: str | None = None
    publisher: str | None = None
    subject: str | None = None
    grade: str | None = None
    year: str | None = None
    edition: str | None = None
    author: str | None = None
    series: str | None = None
    language: str = "fa"
    keywords: list[str] = []
    description: str | None = None
    is_valid: bool = False

def parse_telegram_caption(caption_text: str | None, filename: str | None = None) -> ParsedCaption:
    parsed = ParsedCaption()
    if not caption_text:
        if filename:
            parsed.title = clean_filename(filename)
            parsed.is_valid = True
        return parsed

    lines = caption_text.splitlines()
    kv_pattern = re.compile(r'^\s*([a-zA-Z_]+)\s*[:=]\s*(.+)$')
    has_kv = False

    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue
        match = kv_pattern.match(line_str)
        if match:
            has_kv = True
            key = match.group(1).lower().strip()
            val = match.group(2).strip()

            if key in ('title', 'نام', 'عنوان'):
                parsed.title = val
            elif key in ('publisher', 'ناشر', 'انتشارات'):
                parsed.publisher = val
            elif key in ('subject', 'درس', 'موضوع'):
                parsed.subject = val
            elif key in ('grade', 'پایه', 'کلاس'):
                parsed.grade = val
            elif key in ('year', 'سال', 'سال_چاپ'):
                parsed.year = val
            elif key in ('edition', 'ویرایش', 'چاپ'):
                parsed.edition = val
            elif key in ('author', 'authors', 'نویسنده', 'مولف'):
                parsed.author = val
            elif key in ('series', 'مجموعه', 'سری'):
                parsed.series = val
            elif key in ('keywords', 'تگ', 'کلیدواژه'):
                parsed.keywords = [k.strip() for k in re.split(r'[,،;]', val) if k.strip()]
            elif key in ('description', 'توضیحات'):
                parsed.description = val

    if not has_kv or not parsed.title:
        non_hashtags = [l.strip() for l in lines if l.strip() and not l.strip().startswith('#')]
        hashtags = [w.replace('#', '').replace('_', ' ').strip() for l in lines for w in l.split() if w.startswith('#')]

        if non_hashtags:
            parsed.title = non_hashtags[0]
            if len(non_hashtags) > 1 and not parsed.publisher:
                parsed.publisher = non_hashtags[1]
        elif filename:
            parsed.title = clean_filename(filename)

        if hashtags and not parsed.keywords:
            parsed.keywords = hashtags

    if parsed.title:
        parsed.is_valid = True

    return parsed

def clean_filename(filename: str) -> str:
    cleaned = re.sub(r'\.[^/.]+$', '', filename)
    cleaned = re.sub(r'[-_.]', ' ', cleaned)
    cleaned = re.sub(r'\[.*?\]|\(.*?\)', '', cleaned)
    return normalize_persian_text(cleaned)
