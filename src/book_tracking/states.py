from aiogram.fsm.state import State, StatesGroup


class ReadTracker(StatesGroup):
    main = State()

class ListBooks(StatesGroup):
    list_books = State()
    book_detail = State()
    search_books = State()

class CreateBook(StatesGroup):
    title = State()
    author = State()
    description = State()
    published_year = State()
    minutes_read = State()
    tags = State()
    detail = State()

class AISearchBooks(StatesGroup):
    input_request = State()
    list_books = State()
    book_detail = State()

class MyBooks(StatesGroup):
    list_books = State()
    search = State()
    book_detail = State()
    update_minutes_read = State()
