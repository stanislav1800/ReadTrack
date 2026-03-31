from aiogram import Router
from aiogram.enums import ButtonStyle
from aiogram_dialog import Dialog, Window, StartMode
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.style import Style
from aiogram_dialog.widgets.kbd import (
    Back,
    Button,
    Cancel,
    Column,
    Next,
    NextPage,
    PrevPage,
    Row,
    ScrollingGroup,
    Multiselect,
    Select,
    Start,
    SwitchTo,
    Toggle,
    Radio,
)
from aiogram_dialog.widgets.text import Const, Format, Jinja
from magic_filter import F

from src.book_tracking import states
from src.book_tracking.database.models import ReadingStatus
from src.core.config import settings

from .getters import (
    get_book,
    get_list_books,
    get_my_list_books,
    get_tags_for_m_select,
    get_book_pre_create,
)
from .handlers import (
    on_add_to_list,
    on_book_selected,
    on_find_more_click,
    on_new_search_click,
    on_status_toggle,
    on_search_success,
    on_cancel_filter,
    on_start_book_detail,
    on_create_book,
    on_next_or_update_book,
    on_check_update_book,
    on_start_update_book,
    on_error_data_not_int,
    on_change_reading_status,
    on_update_minutes_read,
    on_delete_my_book,
)

main = Dialog(
    Window(
        Const("Вот что я могу предложить"),
        Start(Const("Отслеживаемые книги"), id="start_my_books", state=states.MyBooks.list_books),
        Start(Const("Просмотреть список книг"), id="start_list_books", state=states.ListBooks.list_books),
        Start(Const("Добавить новую книгу"), id="start_add_book", state=states.CreateBook.title),
        # Start(Const("Поиск книг с помощью ИИ"), id="start_ii_search", state=states.SearchBooks.input_request),
        state=states.ReadTracker.main
    )
)

list_books_dialog = Dialog(
    Window(
        Const("Выберите интересующую вас литературу"),
        ScrollingGroup(
            Select(
                Format("{item.author} - {item.title}"),
                id="s_book_id",
                item_id_getter=lambda x: x.id,
                items="books",
                on_click=on_book_selected,
            ),
            id="scrolling_list_books",
            width=1,
            height=5,
            hide_pager=True,
        ),
        Row(
            PrevPage(
                scroll="scrolling_list_books",
                text=Const("<<"),
                when=lambda data, widget, manager: data["current_page"] > 0,
            ),
            SwitchTo(Const("🔎"), id="search", state=states.ListBooks.search_books),
            NextPage(
                scroll="scrolling_list_books",
                text=Const(">>"),
                when=lambda data, widget, manager: data["current_page"] < data["pages"] - 1,
            ),
        ),
        Cancel(Const("Отмена")),
        getter=get_list_books,
        state=states.ListBooks.list_books
    ),
    Window(
        Jinja("""
📚 <b>{{ book.title }}</b>

👤 <b>Автор:</b> {{ book.author }}
📅 <b>Год публикации:</b> {{ book.published_year }}

📝 <b>Описание:</b>
{{ book.description }}

⏱ <b>Время чтения:</b>
{% if book.minutes_read %}
    {{ book.minutes_read }} мин.
{% else %}
    Пока не указано
{% endif %}

<b>Тэги:</b>
{% if book.tags %}
{% for tag in book.tags %}
- {{ tag.name }}
{% endfor %}
{% else %}Не указано{% endif %}
        """),
        Column(
            Button(Const("Добавить в список"), id="add_to_list", on_click=on_add_to_list, when=~F["is_my_book"]),
            Button(Const("Перейти к книге"), id="start_book_detail", on_click=on_start_book_detail, when=F["is_my_book"]),
            Back(Const("Назад")),
        ),
        getter=get_book,
        state=states.ListBooks.book_detail,
        parse_mode="html",
    ),
    Window(
        Const("Введите название книги или автора, которую хотите найти:"),
        TextInput("search_book", on_success=on_search_success),
        Button(Const("Отменить фильтр"), id="cancel_filter", on_click=on_cancel_filter),
        state=states.ListBooks.search_books,
    ),
)


create_book_dialog = Dialog(
    Window(
        Const("Введите название книги:"),
        TextInput("title", on_success=on_next_or_update_book),
        Cancel(Const("Назад"), when=F["start_data"]),
        state=states.CreateBook.title,
    ),
    Window(
        Const("Введите автора книги:"),
        TextInput("author", on_success=on_next_or_update_book),
        Cancel(Const("Назад"), when=F["start_data"]),
        state=states.CreateBook.author,
    ),
    Window(
        Const("Введите описание книги:"),
        TextInput("description", on_success=on_next_or_update_book),
        Cancel(Const("Назад"), when=F["start_data"]),
        Next(Const("Пропустить"), when=~F["start_data"]),
        state=states.CreateBook.description,
    ),
    Window(
        Const("Введите год публикации книги:"),
        TextInput("published_year", on_success=on_next_or_update_book, type_factory=int, on_error=on_error_data_not_int),
        Cancel(Const("Назад"), when=F["start_data"]),
        state=states.CreateBook.published_year,
    ),
    Window(
        Const("Введите время чтения книги:"),
        TextInput("minutes_read", on_success=on_next_or_update_book, type_factory=int, on_error=on_error_data_not_int),
        Cancel(Const("Назад"), when=F["start_data"]),
        Next(Const("Пропустить"), when=~F["start_data"]),
        state=states.CreateBook.minutes_read,
    ),
    Window(
        Const("Выберите теги для книги:"),
        ScrollingGroup(
            Multiselect(
                checked_text=Format("✅ {item.name}"),
                unchecked_text=Format("{item.name}"),
                id="tags",
                item_id_getter=lambda x: x.id,
                items="tags",
            ),
            id="scrolling_list_tags",
            width=2,
            height=5,
            hide_pager=True,
        ),
        Row(
            Button(Const("Подтвердить"), id="update_tags", on_click=on_next_or_update_book),
            Cancel(Const("Назад"), when=F["start_data"]),
        ),
        state=states.CreateBook.tags,
        getter=get_tags_for_m_select
    ),
    Window(
        Jinja("""
Введенные данные:

📚 <b>{{ book.title }}</b>

👤 <b>Автор:</b> {{ book.author }}
📅 <b>Год публикации:</b> {{ book.published_year }}

📝 <b>Описание:</b>
{% if book.description %}{{ book.description }}{% else %}Пока не указано{% endif %}\n

⏱ <b>Время чтения:</b> {% if book.minutes_read %}{{ book.minutes_read }} мин.{% else %}Пока не указано{% endif %}\n

<b>Тэги:</b>
{% if book.tags %}
{% for tag in book.tags %}
- {{ tag }}
{% endfor %}
{% else %}Пока не указано{% endif %}
"""),
        Column(
            Button(Const("Сохранить"), id="create_book", on_click=on_create_book, when=~F["dialog_data"]["book_id"]),
            Button(Const("Обновить"), id="update_book", on_click=on_check_update_book, when=F["dialog_data"]["book_id"]),
            when=~F["dialog_data"]["update_book"],
        ),
        Column(
            Button(Const("Обновить название"), id="update_title", on_click=on_start_update_book),
            Button(Const("Обновить автора"), id="update_author", on_click=on_start_update_book),
            Button(Const("Обновить описание"), id="update_description", on_click=on_start_update_book),
            Button(Const("Обновить год публикации"), id="update_published_year", on_click=on_start_update_book),
            Button(Const("Обновить время чтения"), id="update_minutes_read", on_click=on_start_update_book),
            Button(Const("Обновить теги"), id="update_tags", on_click=on_start_update_book),
            when=F["dialog_data"]["update_book"],
        ),
        Start(Const("Создать еще"), id="reset_book", state=states.CreateBook.title, mode=StartMode.RESET_STACK),
        Start(Const("Выйти в главное меню"), id="exit", state=states.ReadTracker.main, mode=StartMode.RESET_STACK),
        state=states.CreateBook.detail,
        getter=get_book_pre_create,
        parse_mode="html",
    )
)



# search_book = Dialog(
#     Window(
#         Const("Опиши книгу, которую хочешь найти(напишите название книги или автора, или опишите книгу):"),
#         TextInput("search_book", on_success=Next()),
#         state=states.SearchBooks.input_request,
#     ),
#     Window(
#         Const("Выберите интересующую вас литературу"),
#         ScrollingGroup(
#             Select(
#                 Format("{item.author} - {item.title}"),
#                 id="s_book_id",
#                 item_id_getter=lambda x: x.id,
#                 items="books",
#                 on_click=on_book_selected,
#             ),
#             id="scrolling_list_books",
#             width=1,
#             height=5,
#             hide_pager=True,
#         ),
#         Row(
#             PrevPage(
#                 scroll="scrolling_list_books",
#                 text=Const("<<"),
#                 when=lambda data, widget, manager: data["current_page"] > 0,
#             ),
#             NextPage(
#                 scroll="scrolling_list_books",
#                 text=Const(">>"),
#                 when=lambda data, widget, manager: data["current_page"] < data["pages"] - 1,
#             ),
#         ),
#         Column(
#             SwitchTo(Const("Найти еще"), id="search", state=states.SearchBooks.list_books, on_click=on_find_more_click),
#             SwitchTo(Const("Найти другое"), id="new_search", state=states.SearchBooks.input_request, on_click=on_new_search_click),
#             Cancel(Const("Выйти в главное меню")),
#         ),
#         state=states.SearchBooks.list_books,
#         getter=get_list_books,
#     ),
#     Window(
#         Jinja(
#             """
# 📚 <b>{{ book.title }}</b>

# 👤 <b>Автор:</b> {{ book.author }}
# 📅 <b>Год публикации:</b> {{ book.published_year }}

# 📝 <b>Описание:</b>
# {{ book.description }}

# ⏱ <b>Время чтения:</b>
# {% if book.minutes_read %}
#     {{ book.minutes_read }} мин.
# {% else %}
#     Пока не указано
# {% endif %}
# """
#         ),
#         Button(Const("Добавить в свой список"), id="add_to_list", on_click=on_add_to_list, when=~F["dialog_data"]["book_added"]),
#         Back(Const("Назад")),
#         Cancel(Const("Выйти в главное меню")),
#         state=states.SearchBooks.book_detail,
#         getter=get_book,
#         parse_mode="html",
#     )
# )


my_books_dialog = Dialog(
    Window(
        Const("Список ваших книг:.............................................."),
        ScrollingGroup(
            Select(
                Format("{item.title}"),
                id="s_book_id",
                item_id_getter=lambda x: x.id,
                items="books",
                on_click=on_book_selected,
            ),
            id="scrolling_list_books",
            width=1,
            height=5,
            hide_pager=True,
        ),
        Row(
            PrevPage(
                scroll="scrolling_list_books",
                text=Const("<<"),
                when=lambda data, widget, manager: data["current_page"] > 0,
            ),
            SwitchTo(Const("🔎"), id="search", state=states.MyBooks.search),
            NextPage(
                scroll="scrolling_list_books",
                text=Const(">>"),
                when=lambda data, widget, manager: data["current_page"] < data["pages"] - 1,
            ),
        ),
        Start(Const("Отмена"), "__start__", state=states.ReadTracker.main, mode=StartMode.RESET_STACK),
        getter=get_my_list_books,
        state=states.MyBooks.list_books
    ),
    Window(
        Jinja(
    """
📚 <b>{{ book.title }}</b>

👤 <b>Автор:</b> {{ book.author }}
📅 <b>Год публикации:</b> {{ book.published_year }}

📝 <b>Описание:</b>
{{ book.description }}

⏱ <b>Предварительное время чтения:</b>
{% if book.minutes_read %}
    {{ book.minutes_read }} мин.
{% else %}
    Пока не указано
{% endif %}

⏱ <b>Мое время чтения:</b>
{% if user_books.minutes_read %}
    {{ user_books.minutes_read }} мин.
{% else %}
    Пока не указано
{% endif %}

"""
        ),
        Radio(
            Format("{item[1]}"),
            Format("{item[1]}"),
            id="r_reading_status",
            item_id_getter=lambda x: x[0].value,
            items=lambda data: [(s, s.label()) for s in ReadingStatus],
            on_click=on_change_reading_status,
            checked_style=Style(style=ButtonStyle.SUCCESS),
            # unchecked_style=Style(style=ButtonStyle.PRIMARY),
        ),
        SwitchTo(Const("Изменить время прочтения"), id="update_minutes_read", state=states.MyBooks.update_minutes_read),
        Button(Const("Удалить"), id="delete", on_click=on_delete_my_book, style=Style(style=ButtonStyle.DANGER),
),
        Back(Const("Назад")),
        state=states.MyBooks.book_detail,
        getter=get_book,
        parse_mode="html",
    ),
    Window(
        Const("Введите время чтения в минутах:"),
        TextInput("minutes_read", on_success=on_update_minutes_read, type_factory=int, on_error=on_error_data_not_int),
        state=states.MyBooks.update_minutes_read
    ),
    Window(
        Const("Введите название книги или автора, которую хотите найти:"),
        TextInput("search_book", on_success=on_search_success),
        Button(Const("Отменить фильтр"), id="cancel_filter", on_click=on_cancel_filter),
        state=states.MyBooks.search,
    ),
)


router = Router(name=__name__)

router.include_router(main)
router.include_router(list_books_dialog)
router.include_router(create_book_dialog)
router.include_router(my_books_dialog)
