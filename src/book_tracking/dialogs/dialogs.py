from aiogram import Router
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.input import TextInput
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
    Select,
    Start,
    SwitchTo,
    Toggle,
)
from aiogram_dialog.widgets.text import Const, Format, Jinja
from magic_filter import F

from src.book_tracking import states
from src.core.config import settings

from .getters import (
    get_book,
    get_list_books,
    get_my_list_books,
)
from .handlers import (
    on_add_to_list,
    on_book_selected,
    on_find_more_click,
    on_new_search_click,
    on_status_toggle,
)

main = Dialog(
    Window(
        Const("Вот что я могу предложить"),
        Start(Const("Посмотреть мою литературу"), id="start_my_books", state=states.MyBooks.list_books),
        Start(Const("Найти литературу"), id="start_search_book", state=states.SearchBooks.input_request),
        state=states.ReadTracker.main
    )
)


search_book = Dialog(
    Window(
        Const("Опиши книгу, которую хочешь найти(напишите название книги или автора, или опишите книгу):"),
        TextInput("search_book", on_success=Next()),
        state=states.SearchBooks.input_request,
    ),
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
            NextPage(
                scroll="scrolling_list_books",
                text=Const(">>"),
                when=lambda data, widget, manager: data["current_page"] < data["pages"] - 1,
            ),
        ),
        Column(
            SwitchTo(Const("Найти еще"), id="search", state=states.SearchBooks.list_books, on_click=on_find_more_click),
            SwitchTo(Const("Найти другое"), id="new_search", state=states.SearchBooks.input_request, on_click=on_new_search_click),
            Cancel(Const("Выйти в главное меню")),
        ),
        state=states.SearchBooks.list_books,
        getter=get_list_books,
    ),
    Window(
        Jinja(
            """
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
"""
        ),
        Button(Const("Добавить в свой список"), id="add_to_list", on_click=on_add_to_list, when=~F["dialog_data"]["book_added"]),
        Back(Const("Назад")),
        Cancel(Const("Выйти в главное меню")),
        state=states.SearchBooks.book_detail,
        getter=get_book,
        parse_mode="html",
    )
)


my_books = Dialog(
    Window(
        Const("Список ваших книг:"),
        ScrollingGroup(
            Select(
                Format("{item.book.title}"),
                id="s_book_id",
                item_id_getter=lambda x: x.book.id,
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
            NextPage(
                scroll="scrolling_list_books",
                text=Const(">>"),
                when=lambda data, widget, manager: data["current_page"] < data["pages"] - 1,
            ),
        ),
        Cancel(Const("Выйти в главное меню")),
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

⏱ <b>Время чтения:</b>
{% if book.minutes_read %}
    {{ book.minutes_read }} мин.
{% else %}
    Пока не указано
{% endif %}
"""
        ),
        Toggle(
            Format("{item.emoji} {item.name}"),
            id="toggle_change_status",
            items="book_status",
            item_id_getter=lambda x: x.id,
            on_click=on_status_toggle,
        ),
        # Button(Const("Удалить"), id=""),
        Back(Const("Назад")),
        state=states.MyBooks.book_detail,
        getter=get_book,
        parse_mode="html",
    )
)


router = Router(name=__name__)

router.include_router(main)
router.include_router(search_book)
router.include_router(my_books)
