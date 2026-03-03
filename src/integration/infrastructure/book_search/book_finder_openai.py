import asyncio
import logging
from typing import Optional

import httpx
from openai import OpenAI
from pydantic import BaseModel, Field

from src.core.config import settings

logger = logging.getLogger()

SYSTEM_PROMPT_TEMPLATE = """ВАЖНО: Весь твой ответ должен быть ТОЛЬКО на русском языке.
Все объяснения, описания, теги — исключительно на русском.
Ты — эксперт по мировой литературе.
Пользователь ищет книгу(и) по названию, автору или описанию.

Правила:
- Только реальные книги, никогда не выдумывай и не придумывай несуществующие произведения.
- Выводи **все** книги, которые реально и сильно соответствуют запросу. Не добавляй книги «ради количества», «похожести» или «на всякий случай».
- Если запрос касается конкретной книги, которая является частью серии — обязательно включи все основные книги этой серии (трилогию, тетралогию, продолжения, приквелы в хронологическом порядке издания), но только если они действительно связаны и соответствуют запросу.
- Не включай спин-оффы, фанфики, адаптации, книги «в похожем стиле» или «рекомендации», если они явно не запрашивались.
- Если подходящих книг очень много — выводи только самые релевантные (до 10–12 максимум), но старайся не обрезать искусственно, если их меньше.
- Год — год первого издания (можно приблизительно, но указывай источник приблизительности, если не уверен на 100%).
- estimated_minutes_read — разумная оценка на основе ~250 слов в минуту и среднего объёма книги.
- tags — от 3 до 12 тегов на русском языке, только те, которые действительно характеризуют книгу.
- Сортируй строго от самого подходящего к менее подходящему по степени соответствия запросу.

Не ограничивай себя заранее заданным числом книг — выводи столько, сколько реально подходит под критерии выше."""

USER_PROMPT_TEMPLATE = """Запрос: {query}

ВАЖНО: Ответ должен быть полностью на русском языке.
Даже если название книги на другом языке — описания, объяснения и теги должны быть на русском.

Верни список **всех** подходящих книг по правилам выше.
Если книг нет или подходят только 1–2 — так и напиши, не придумывай дополнительные."""

class BookSearchResult(BaseModel):
    """Точная структура, которая будет возвращаться из LLM"""
    title: str = Field(..., description="Название книги")
    author: str = Field(..., description="Автор книги")
    description: str = Field(..., description="Краткое описание 2–4 предложения")
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


def find_books(
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
        model = settings.model
    if not api_key:
        api_key = settings.open_api_key

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
    )

    system_prompt = SYSTEM_PROMPT_TEMPLATE
    user_prompt = USER_PROMPT_TEMPLATE.format(query=query)
    if excluded_books:
        excluded_text = "\n".join([f"- {ex.replace('|', ' — ')}" for ex in excluded_books])
        user_prompt += f"\n\nИСКЛЮЧИ ЭТИ КНИГИ (не повторяй их ни в коем случае):\n{excluded_text}"

    try:
        response = client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=2500,
            response_format=BookSearchResponse
        )

        parsed: BookSearchResponse = response.choices[0].message.parsed
        return parsed

    except Exception as e:
        print(f"Ошибка при работе с OpenAI: {type(e).__name__}: {e}")
        return []

async def find_books_async(
    query: str,
    lang: str = "ru",
    count: int = 7,
    model: str = "arcee-ai/trinity-large-preview:free",
    api_key: Optional[str] = None,
    temperature: float = 0.65
) -> BookSearchResponse:
    """
    Асинхронный поиск книг через OpenAI API.
    """
    if not api_key:
        api_key = settings.open_api_key
    if not api_key:
        raise ValueError("OPENAI_API_KEY не найден")

    system_prompt = SYSTEM_PROMPT_TEMPLATE
    user_prompt = USER_PROMPT_TEMPLATE.format(query=query)

    schema = BookSearchResponse.model_json_schema()
    url = "https://openrouter.ai/api/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "BookSearchResponse",
                "strict": True,
                "schema": schema,
            }
        },
        "plugins": [
            {"id": "response-healing"}  # исправление JSON
        ],
        "temperature": temperature,
        "max_tokens": 2500,
        # если используешь parse с pydantic, можно потом делать json.loads
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()

    # Получаем текст ответа от LLM
    text_response = data["choices"][0]["message"]["content"]

    # Преобразуем в BookSearchResponse (здесь можно использовать Pydantic через parse_raw)
    try:
        return BookSearchResponse.model_validate_json(text_response)
    except Exception as e:
        print(f"Ошибка парсинга ответа LLM: {e}")
        return BookSearchResponse(books=[])


if __name__ == "__main__":
    # asyncio.run(test())

    # query = input("Опиши книгу, которую хочешь найти:\n> ").strip()
    query = "бегущий в лабиринте"

    if query:
        results = find_books(
            query=query,
            temperature=0.6,
        )

        print("\n" + "═" * 70 + "\nНайденные книги:\n")

        for i, book in enumerate(results.books, 1):
            print(f"{i}. {book.title} — {book.author} ({book.published_year})")
            print(f"   Время чтения: ~{book.estimated_minutes_read} мин")
            print(f"   Теги: {', '.join(book.tags)}")
            # print(f"   Почему подходит: {book.why_fits}")
            print(f"   Описание: {book.description[:200]}...\n")
