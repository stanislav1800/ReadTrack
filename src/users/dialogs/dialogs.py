from aiogram import Router
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.input import TextInput
from aiogram_dialog.widgets.kbd import (
    Back,
    Button,
    Cancel,
    NextPage,
    PrevPage,
    Row,
    ScrollingGroup,
    Select,
    Start,
)
from aiogram_dialog.widgets.text import Const, Format, Jinja
from magic_filter import F

from src.core.config import settings
from src.users import states

from .getters import (
    get_list_users,
    get_user,
)
from .handlers import (
    input_search_data,
    on_start,
    reset_search,
    selected_user_id,
    update_superuser,
    update_superuser_or_verified,
)

list_users = Dialog(
    Window(
        Const("Выберите пользователя"),
        ScrollingGroup(
            Select(
                Format("{item}"),
                id="s_user_id",
                item_id_getter=lambda x: x.telegram_id,
                items="users",
                on_click=selected_user_id,
            ),
            id="scrolling_list_users",
            width=1,
            height=5,
            hide_pager=True,
        ),
        Row(
            PrevPage(
                scroll="scrolling_list_users",
                text=Const("<<"),
                when=lambda data, widget, manager: data["current_page"] > 0,
            ),
            Start(Const("🔎"), id="search", state=states.Search.main),
            Cancel(Const("Отмена")),
            NextPage(
                scroll="scrolling_list_users",
                text=Const(">>"),
                when=lambda data, widget, manager: data["current_page"] < data["pages"] - 1,
            ),
        ),
        state=states.ListUsers.list_users,
        getter=get_list_users,
        on_process_result=on_start,
    ),
    Window(
        Jinja(
            """
Информация о пользователе:

id: {{user.telegram_id}}
{% if user.username %}username: @{{user.username}} 
{% endif %}
{% if user.first_name %}first_name: {{user.first_name}}
{% endif %}
{% if user.last_name %}last_name: {{user.last_name}}
{% endif %}
is_active: {% if user.is_active %} ✅ 
{% else %} ❌
{% endif %}
is_superuser: {% if user.is_superuser %} ✅ 
{% else %} ❌
{% endif %}
is_verified: {% if user.is_verified %} ✅ 
{% else %} ❌
{% endif %}

Дата регистрации: {{user.format_datetime()}}
""",
            when=F["user"],
        ),
        Const("Такого пользователя не существует", when=~F["user"]),
        Button(
            Jinja("{% if user.is_superuser %}Сделать обычным пользователем{% else %}Сделать админом{% endif %}"),
            id="update_is_superuser",
            on_click=update_superuser,
            when=F["user"],
        ),
        Button(
            Jinja("{% if user.is_verified %}Отменить верификацию{% else %}Верифицировать{% endif %}"),
            id="update_is_verified",
            on_click=update_superuser_or_verified,
            when=F["user"],
        ),
        Back(Const("Назад")),
        Cancel(Const("Выход")),
        state=states.ListUsers.user_info,
        getter=get_user,
        on_process_result=on_start,
    ),
)


search = Dialog(
    Window(
        Const("Введите текст для поиска"),
        Button(Const("Сбросить поиск"), id="reset", on_click=reset_search),
        TextInput(id="input_search", on_success=input_search_data),
        state=states.Search.main,
    ),
)


router = Router(name=__name__)

router.include_router(list_users)
router.include_router(search)
