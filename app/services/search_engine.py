import re
from typing import List, Tuple
from sqlalchemy import select, or_, and_, func, desc, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
from ..database.models import Document

def normalize_persian(text: str) -> str:
    if not text:
        return ""
    # Remove Persian/Arabic diacritics
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
    # Convert Arabic characters to Persian equivalent
    text = text.replace('ك', 'ک').replace('ي', 'ی').replace('ى', 'ی')
    text = text.replace('۰', '0').replace('۱', '1').replace('۲', '2').replace('۳', '3').replace('۴', '4')
    text = text.replace('۵', '5').replace('۶', '6').replace('۷', '7').replace('۸', '8').replace('۹', '9')
    return text.strip().lower()

class SQLiteSearchEngine:
    @staticmethod
    def calculate_relevance(doc: Document, normalized_query: str, query_tokens: list[str]) -> int:
        score = 0
        if not query_tokens:
            return 0

        # Safely extract keywords
        raw_kw = doc.keywords or []
        if isinstance(raw_kw, str):
            doc_keywords = [normalize_persian(raw_kw)]
        elif isinstance(raw_kw, list):
            doc_keywords = [normalize_persian(str(kw)) for kw in raw_kw if kw]
        else:
            doc_keywords = []

        # 1. Keywords (+ tag) match - Highest Priority
        for kw in doc_keywords:
            if normalized_query in kw or kw in normalized_query:
                score += 30
            for token in query_tokens:
                if token in kw:
                    score += 15

        # 2. Normalized Title / Title match
        norm_title = doc.normalized_title or normalize_persian(doc.title or "")
        if normalized_query in norm_title:
            score += 25
        for token in query_tokens:
            if token in norm_title:
                score += 8

        # 3. Caption / Description match
        norm_desc = normalize_persian(doc.description or "")
        if normalized_query in norm_desc:
            score += 15
        for token in query_tokens:
            if token in norm_desc:
                score += 4

        # 4. File name & metadata fields match
        metadata_str = normalize_persian(f"{doc.file_name or ''} {doc.publisher or ''} {doc.subject or ''} {doc.grade or ''} {doc.year or ''}")
        for token in query_tokens:
            if token in metadata_str:
                score += 5

        return score

    @staticmethod
    async def search_documents(
        session: AsyncSession,
        query: str,
        publisher: str | None = None,
        subject: str | None = None,
        grade: str | None = None,
        year: str | None = None,
        page: int = 1,
        page_size: int = 5
    ) -> Tuple[List[Document], int]:
        normalized_q = normalize_persian(query)
        tokens = [t for t in normalized_q.split() if len(t) > 0]

        stmt = select(Document)
        filters = []

        if tokens:
            token_conditions = []
            for token in tokens:
                pattern = f"%{token}%"
                token_conditions.append(
                    or_(
                        Document.normalized_title.like(pattern),
                        Document.title.like(pattern),
                        Document.file_name.like(pattern),
                        Document.publisher.like(pattern),
                        Document.subject.like(pattern),
                        Document.grade.like(pattern),
                        Document.authors.like(pattern),
                        Document.description.like(pattern),
                        cast(Document.keywords, String).like(pattern)
                    )
                )
            filters.append(or_(*token_conditions))

        if publisher:
            filters.append(Document.publisher == publisher)
        if subject:
            filters.append(Document.subject == subject)
        if grade:
            filters.append(Document.grade == grade)
        if year:
            filters.append(Document.year == year)

        if filters:
            stmt = stmt.where(and_(*filters))

        result = await session.execute(stmt)
        candidates = list(result.scalars().all())

        # Rank candidates by relevance score
        scored_docs = []
        for doc in candidates:
            score = SQLiteSearchEngine.calculate_relevance(doc, normalized_q, tokens)
            scored_docs.append((doc, score))

        # If tokens are present, keep docs with score > 0. Fallback to candidates if score filter yields empty list but candidates exist.
        matched_docs = [item for item in scored_docs if item[1] > 0]
        if not matched_docs and candidates:
            matched_docs = [(doc, 1) for doc in candidates]

        matched_docs.sort(key=lambda item: (item[1], item[0].views, item[0].downloads, item[0].created_at), reverse=True)

        total_count = len(matched_docs)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_docs = [doc for doc, score in matched_docs[start_idx:end_idx]]

        return paginated_docs, total_count

    @staticmethod
    async def search_by_field_and_grade(
        session: AsyncSession,
        field_code: str,  # 'math', 'exp', 'hum'
        grade_code: str, # '10', '11', '12'
        page: int = 1,
        page_size: int = 5
    ) -> Tuple[List[Document], int]:
        grade_map = {
            "10": ["10", "دهم", "پایه 10", "پایه دهم"],
            "11": ["11", "یازدهم", "پایه 11", "پایه یازدهم"],
            "12": ["12", "دوازدهم", "پایه 12", "پایه دوازدهم"]
        }
        grade_tokens = grade_map.get(str(grade_code), [str(grade_code)])

        field_map = {
            "math": ["ریاضی", "حسابان", "هندسه", "گسسته", "آمار"],
            "exp": ["تجربی", "زیست", "شیمی", "فیزیک", "زمین"],
            "hum": ["انسانی", "معارف", "فلسفه", "منطق", "عربی", "تاریخ", "جغرافیا", "جامعه", "اقتصاد", "روانشناسی", "دین و زندگی", "دینی"]
        }
        field_tokens = field_map.get(str(field_code), [])

        stmt = select(Document)

        grade_conds = []
        for gt in grade_tokens:
            p = f"%{gt}%"
            grade_conds.append(Document.grade.like(p))
            grade_conds.append(Document.title.like(p))
            grade_conds.append(Document.normalized_title.like(p))
            grade_conds.append(Document.description.like(p))
            grade_conds.append(cast(Document.keywords, String).like(p))

        field_conds = []
        for ft in field_tokens:
            p = f"%{ft}%"
            field_conds.append(Document.subject.like(p))
            field_conds.append(Document.title.like(p))
            field_conds.append(Document.normalized_title.like(p))
            field_conds.append(Document.description.like(p))
            field_conds.append(cast(Document.keywords, String).like(p))

        stmt = stmt.where(and_(or_(*grade_conds), or_(*field_conds)))
        result = await session.execute(stmt)
        candidates = list(result.scalars().all())

        candidates.sort(key=lambda d: (d.views, d.downloads, d.created_at), reverse=True)

        total_count = len(candidates)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_docs = candidates[start_idx:end_idx]

        return paginated_docs, total_count



