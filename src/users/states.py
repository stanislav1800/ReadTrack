from aiogram.fsm.state import State, StatesGroup


class ListUsers(StatesGroup):
    list_users = State()
    user_info = State()
    search = State()


class Search(StatesGroup):
    main = State()
