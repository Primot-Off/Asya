from aiogram import Router
from aiogram.types import Message, FSInputFile

from pathlib import Path


router = Router()


BASE_DIR = Path(__file__).resolve().parent.parent
gif = FSInputFile(BASE_DIR / "assets" / "никакогонегатива.gif")


@router.message()
async def start_command(message: Message):
    msg = "".join(message.text.lower().split())
    print(msg)
    if "безнегатив" in msg:
        return await message.reply_animation(animation=gif)