import calendar
from datetime import datetime, timedelta
from typing import Optional, Union

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


class NumbersCallbackFactory(CallbackData, prefix="fabnum"):
    action: str
    value: Optional[int] = None


class CalendarFactory(CallbackData, prefix="calendar"):
    action: str
    month: Optional[int] = None
    year: Optional[int] = None


def get_markup_inline(keyboards: list, menu: str, keyboards_add: list[list] = [], col=1):
    builder = InlineKeyboardBuilder()

    for keyboard in keyboards:
        builder.button(text=keyboard[0], callback_data=NumbersCallbackFactory(action=menu, value=keyboard[1]))

    builder.adjust(col)

    if keyboards_add:
        builder.button(
            text=keyboards_add[0][0], callback_data=NumbersCallbackFactory(action=menu, value=keyboards_add[0][1])
        )
        builder.adjust(1)

        for keyboard in keyboards_add[1:]:
            builder.button(text=keyboard[0], callback_data=NumbersCallbackFactory(action=menu, value=keyboard[1]))

    return builder.as_markup()


def gen_keyboard_button(keyboards: Union[list, str], adjust: Union[int, None] = 1):
    """
    :param keyboards: Клавиатура список с текстом
    :param adjust: Кол-во кнопок в строке
    :return: builder.as_markup()
    """
    builder = ReplyKeyboardBuilder()
    if type(keyboards) is list:
        for keyboard in keyboards:
            builder.add(KeyboardButton(text=str(keyboard)))
    else:
        builder.add(KeyboardButton(text=str(keyboards)))

    builder.adjust(adjust)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def generate_calendar(month=None, year=None):
    if month is None or year is None:
        now = datetime.now()
        month = now.month
        year = now.year

    cal = calendar.monthcalendar(year, month)
    builder = InlineKeyboardBuilder()

    month_name = calendar.month_name[month]
    builder.add(InlineKeyboardButton(text=f"{month_name} {year}", callback_data="no_action"))

    days_of_week = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    builder.row(*[InlineKeyboardButton(text=day, callback_data="no_action") for day in days_of_week])

    for week in cal:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="no_action"))
            else:
                callback_data = CalendarFactory(action="calendar_date", value=day, month=month, year=year).pack()
                row.append(InlineKeyboardButton(text=str(day), callback_data=callback_data))
        builder.row(*row)

    prev_month = datetime(year, month, 1) - timedelta(days=1)
    next_month = datetime(year, month, 1) + timedelta(days=31)

    builder.row(
        InlineKeyboardButton(
            text="<<",
            callback_data=CalendarFactory(
                action="calendar_prev_month", month=prev_month.month, year=prev_month.year
            ).pack(),
        ),
        InlineKeyboardButton(text="Отмена", callback_data="calendar_cancel"),
        InlineKeyboardButton(
            text=">>",
            callback_data=CalendarFactory(
                action="calendar_next_month", month=next_month.month, year=next_month.year
            ).pack(),
        ),
    )

    return builder.as_markup()
