import asyncio
import json
import logging
from typing import Optional

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from src.core.config import settings


logger = logging.getLogger()

SYSTEM_PROMPT_TEMPLATE = """ВАЖНО: Весь твой ответ должен быть ТОЛЬКО на русском языке.
Все объяснения, описания, теги — исключительно на русском.
Ты — эксперт по литературе. Отвечай строго JSON-объектом формата {"books": [...]} без пояснений.

Жёсткие правила:
- Только реальные книги. Ничего не выдумывай.
- Если запрос бессмысленный/мусорный/не про книги — верни {"books": []}.
- Если релевантных книг нет — верни {"books": []}.
- Не подставляй «классику по умолчанию».
- Включай только книги, которые прямо соответствуют запросу.
- Сортируй от наиболее релевантной к менее релевантной.
- Описание очень короткое: 1–2 предложения.
- Теги: 3–6 коротких тегов.

Если есть риск длинного ответа — верни только ту часть списка, которая помещается, и выставь has_more=true.
Формат ответа: {"books": [...], "has_more": true|false}."""

USER_PROMPT_TEMPLATE = """Запрос: {query}

ВАЖНО: Ответ должен быть полностью на русском языке.
Даже если название книги на другом языке — описания, объяснения и теги должны быть на русском.

Если запрос бессмысленный (случайные символы, нечитаемый текст, не связан с книгами) — верни {{"books": []}}.
Если ничего не подходит — верни {{"books": []}}.
Найди ВСЕ подходящие книги, но верни только ту часть, которая помещается в текущий ответ.
Если не все книги поместились, поставь has_more=true, иначе has_more=false.
Обязательно соблюдай формат каждой книги: title, author, description, published_year, estimated_minutes_read, tags."""

COMPACT_USER_PROMPT_SUFFIX = """
Режим сжатия: сократи description до 1 короткого предложения и tags до 2–4, чтобы JSON точно поместился.
"""

MODEL = "arcee-ai/trinity-large-preview:free"
MAX_TOKENS = 2500
MAX_TOKENS_FALLBACK = 1200
MAX_ITERATIONS = 8

class BookSearchResult(BaseModel):
    """Точная структура, которая будет возвращаться из LLM"""
    title: str = Field(..., description="Название книги")
    author: str = Field(..., description="Автор книги")
    description: Optional[str] = Field(None, description="Краткое описание 2–4 предложения")
    published_year: Optional[int] = Field(None, description="Год первого издания")
    estimated_minutes_read: Optional[int] = Field(
        None, description="Примерное время чтения в минутах (средняя скорость ~250 слов/мин)"
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Список тегов на русском: жанр, тема, настроение и т.д."
    )
    # why_fits: str = Field(..., description="Почему эта книга подходит под запрос пользователя (1–2 предложения)")


class BookSearchResponse(BaseModel):
    books: list[BookSearchResult]


async def find_books(
    query: str,
    excluded_books: list[str] | None = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    temperature: float = 0.65
) -> BookSearchResponse:
    """
    Находит реальные книги, максимально похожие на описание.
    """
    if model is None:
        model = MODEL
        
    if not api_key:
        api_key = settings.open_api_key

    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
    )

    def _build_user_prompt(excluded: list[str], compact: bool = False) -> str:
        prompt = USER_PROMPT_TEMPLATE.format(query=query)
        if excluded:
            excluded_text = ", ".join(excluded)
            prompt += f"\n\nИСКЛЮЧИ ЭТИ КНИГИ (не повторяй их ни в коем случае):\n{excluded_text}"
        if compact:
            prompt += COMPACT_USER_PROMPT_SUFFIX
        return prompt

    all_books: list[BookSearchResult] = []
    seen: set[tuple[str, str]] = set()
    running_excluded = list(excluded_books or [])

    for iteration in range(1, MAX_ITERATIONS + 1):
        logger.info(f"Book search iteration: {iteration}")
        system_prompt = SYSTEM_PROMPT_TEMPLATE
        user_prompt = _build_user_prompt(running_excluded, compact=False)

        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=MAX_TOKENS,
                response_format={"type": "json_object"}
            )
            logger.info(f"Response: {response}")

            if response.choices[0].finish_reason == "length":
                logger.warning("Ответ обрезан, повторяем итерацию в сжатом режиме")
                response = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": _build_user_prompt(running_excluded, compact=True)}
                    ],
                    temperature=0.3,
                    max_tokens=MAX_TOKENS_FALLBACK,
                    response_format={"type": "json_object"}
                )
                logger.info(f"Response: {response}")

                if response.choices[0].finish_reason == "length":
                    logger.warning("Сжатый ответ тоже обрезан; возвращаем уже собранные книги")
                    break

            content = response.choices[0].message.content
            data = json.loads(content)
            parsed_chunk = BookSearchResponse(**{"books": data.get("books", [])})
            has_more = bool(data.get("has_more", False))

            new_count = 0
            for book in parsed_chunk.books:
                key = (book.title.strip().lower(), book.author.strip().lower())
                if key in seen:
                    continue
                seen.add(key)
                all_books.append(book)
                running_excluded.append(f"{book.title}|{book.author}")
                new_count += 1

            logger.info(f"Итерация {iteration}: получено новых книг {new_count}, всего {len(all_books)}")

            if not has_more:
                break
            if new_count == 0:
                logger.warning("Модель не вернула новых книг при has_more=true; завершаем, чтобы не зациклиться")
                break
            break

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error on iteration {iteration}: {e}")
            if all_books:
                break
            raise ValueError(f"API вернул неправильный JSON: {e}")
        except Exception as e:
            logger.error(f"API error on iteration {iteration}: {type(e).__name__}: {e}", exc_info=True)
            if all_books:
                break
            raise

    return BookSearchResponse(books=all_books)



if __name__ == "__main__":
    # query = input("Опиши книгу, которую хочешь найти:\n> ").strip()
    query = "бегущий в лабиринте"

    if query:
        results = asyncio.run(find_books(
            query=query,
            temperature=0.6,
        ))

        print("\n" + "═" * 70 + "\nНайденные книги:\n")

        for i, book in enumerate(results.books, 1):
            print(f"{i}. {book.title} — {book.author} ({book.published_year})")
            print(f"   Время чтения: ~{book.estimated_minutes_read} мин")
            print(f"   Теги: {', '.join(book.tags)}")
            # print(f"   Почему подходит: {book.why_fits}")
            print(f"   Описание: {book.description[:200]}...\n")
