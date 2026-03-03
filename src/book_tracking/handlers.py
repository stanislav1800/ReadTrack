import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode

from src.book_tracking import states
from src.users.database.schemas import UserSchema

logger = logging.getLogger()
router = Router(name=__name__)


@router.message(CommandStart())
async def users_cmd_start(
    message: Message,
    dialog_manager: DialogManager,
    command: CommandObject,
    current_user: UserSchema,
):
    await dialog_manager.start(states.ReadTracker.main, mode=StartMode.RESET_STACK)
