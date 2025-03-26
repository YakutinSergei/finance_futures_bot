from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

router: Router = Router()





@router.message(F.text == "/start")
async def process_start_command(message: Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("Настройки"))  # Кнопка "Настройки"
    await message.answer("Привет!", reply_markup=keyboard)
