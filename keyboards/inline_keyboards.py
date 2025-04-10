from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


async def kb_pair_coinglass(pair):

    # Инициализируем билдер
    inline_markup: InlineKeyboardBuilder = InlineKeyboardBuilder()
    buttons: list[InlineKeyboardButton] = [InlineKeyboardButton(
        text='Coinglass',
        url=f'https://www.coinglass.com/tv/ru/Binance_{pair}',
    ),
    ]
    inline_markup.row(*buttons, width=1)

    return inline_markup.as_markup()

