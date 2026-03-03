from aiogram.fsm.state import State, StatesGroup


class ReadTracker(StatesGroup):
    main = State()

class SearchBooks(StatesGroup):
    input_request = State()
    list_books = State()
    book_detail = State()

class MyBooks(StatesGroup):
    list_books = State()
    search = State()
    book_detail = State()
