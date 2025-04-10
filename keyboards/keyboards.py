from aiogram.types import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from data_base.lexicon import buttons_text

'''генератор клавиатур'''


async def create_inline_kb(width: int,
                           pref: str,
                           *args: str,
                           **kwargs: str) -> InlineKeyboardMarkup:
    # Инициализируем билдер
    kb_builder: InlineKeyboardBuilder = InlineKeyboardBuilder()
    # Инициализируем список для кнопок
    buttons: list[InlineKeyboardButton] = []

    # Заполняем список кнопками из аргументов args и kwargs
    if args:
        for button in args:
            buttons.append(InlineKeyboardButton(
                text=button,
                callback_data=pref + button))

    if kwargs:
        for button, text in kwargs.items():
            buttons.append(InlineKeyboardButton(
                text=text,
                callback_data=pref + button))

    # Распаковываем список с кнопками в билдер методом row c параметром width
    kb_builder.row(*buttons, width=width)

    # Возвращаем объект инлайн-клавиатуры
    return kb_builder.as_markup()


async def start_keyboard(lang: str):
    button_1 = KeyboardButton(text=buttons_text['settings'][f'{lang}'])
    button_2 = KeyboardButton(text=buttons_text['price'][f'{lang}'])
    button_3 = KeyboardButton(text=buttons_text['support'][f'{lang}'])

    keyboard_builder = ReplyKeyboardBuilder()

    keyboard_builder.row(button_2, button_1, button_3, width=2)

    keyboard: ReplyKeyboardMarkup = keyboard_builder.as_markup(
        one_time_keyboard=True,
        resize_keyboard=True
    )

    return keyboard


async def create_price_kb(lang) -> InlineKeyboardMarkup:
    # Инициализируем билдер
    kb_builder: InlineKeyboardBuilder = InlineKeyboardBuilder()
    # Инициализируем список для кнопок
    buttons: list[InlineKeyboardButton] = []

    buttons: list[InlineKeyboardButton] = [InlineKeyboardButton(
        text=buttons_text['subscription_1_month'][lang],
        callback_data=f"price_{buttons_text['subscription_1_month'][lang]}"
    ), InlineKeyboardButton(
        text=buttons_text['subscription_3_months'][lang],
        callback_data=f"price_{buttons_text['subscription_3_months'][lang]}"
    ), InlineKeyboardButton(
        text=buttons_text['subscription_6_months'][lang],
        callback_data=f"price_{buttons_text['subscription_6_months'][lang]}"
    )
    ]

    # Распаковываем список с кнопками в билдер методом row c параметром width
    kb_builder.row(*buttons, width=1)

    # Возвращаем объект инлайн-клавиатуры
    return kb_builder.as_markup()


'''перевод в поддержка'''


async def support_kb(lang) -> InlineKeyboardMarkup:
    # Инициализируем билдер
    kb_builder: InlineKeyboardBuilder = InlineKeyboardBuilder()
    # Инициализируем список для кнопок
    buttons: list[InlineKeyboardButton] = []

    buttons: list[InlineKeyboardButton] = [InlineKeyboardButton(
        text=buttons_text['support'][lang], url="https://t.me/UranTM")
    ]

    # Распаковываем список с кнопками в билдер методом row c параметром width
    kb_builder.row(*buttons, width=1)

    # Возвращаем объект инлайн-клавиатуры
    return kb_builder.as_markup()


'''подтверждение или отклонение оплаты'''


async def enter_price_kb(tg_id, validity_period) -> InlineKeyboardMarkup:
    # Инициализируем билдер
    kb_builder: InlineKeyboardBuilder = InlineKeyboardBuilder()
    # Инициализируем список для кнопок
    buttons: list[InlineKeyboardButton] = [InlineKeyboardButton(
        text='Подтвердить',
        callback_data=f"enter_{validity_period}_{tg_id}"
    ), InlineKeyboardButton(
        text='Отклонить',
        callback_data=f"enter_Reject_{tg_id}"
    ),
    ]

    # Распаковываем список с кнопками в билдер методом row c параметром width
    kb_builder.row(*buttons, width=1)

    # Возвращаем объект инлайн-клавиатуры
    return kb_builder.as_markup()


async def setting_keyboard(lang):
    button_1 = KeyboardButton(text=buttons_text['Growth_period'][f'{lang}'])
    button_2 = KeyboardButton(text=buttons_text['Percentage_of_growth'][f'{lang}'])
    button_4 = KeyboardButton(text=buttons_text['Drawdown_percentage'][f'{lang}'])
    button_5 = KeyboardButton(text=buttons_text['settings_back'][f'{lang}'])
    button_6 = KeyboardButton(text=buttons_text['language'][f'{lang}'])

    keyboard_builder = ReplyKeyboardBuilder()

    keyboard_builder.row(button_1, width=1)
    keyboard_builder.row(button_2, button_4, button_6, width=2)
    keyboard_builder.row(button_5, width=1)

    keyboard: ReplyKeyboardMarkup = keyboard_builder.as_markup(
        one_time_keyboard=True,
        resize_keyboard=True
    )

    return keyboard


'''Клавиатура с выбором языка'''


async def keyboard_lang_choice(lang):
    btn_1 = KeyboardButton(text=buttons_text['language_ru'][f'{lang}'])
    btn_2 = KeyboardButton(text=buttons_text['language_en'][f'{lang}'])
    btn_3 = KeyboardButton(text=buttons_text['settings_back'][f'{lang}'])

    keyboard_builder = ReplyKeyboardBuilder()

    keyboard_builder.row(btn_1, btn_2, btn_3, width=2)

    keyboard: ReplyKeyboardMarkup = keyboard_builder.as_markup(
        one_time_keyboard=True,
        resize_keyboard=True
    )
    return keyboard
