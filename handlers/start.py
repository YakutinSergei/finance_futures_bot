from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery

from create_bot import bot
from data_base.lexicon import message_text, buttons_text
from data_base.orm import add_user_with_alert, change_user_language, update_growth_period, update_growth_percent, \
    update_down_percent, get_admin_ids, extend_subscription
from keyboards.keyboards import start_keyboard, setting_keyboard, keyboard_lang_choice, create_inline_kb, \
    create_price_kb, enter_price_kb, support_kb
from pars.function import is_valid_period, validate_percent_input

router: Router = Router()


class FSMSettings(StatesGroup):
    period_up = State()  # Состояние комментария
    period_down = State()  # Состояние комментария
    procent_up = State()  # Состояние комментария
    procent_down = State()  # Состояние комментария
    screenshot = State()  # Состояние комментария

'''Кнопка отмена'''
@router.callback_query(F.data.startswith('Cancel'))
async def cancel_FSM(callback: CallbackQuery, state: FSMContext):
    try:
        await bot.delete_message(chat_id=callback.message.chat.id, message_id=callback.message.message_id)
    except TelegramBadRequest:
        pass  # Сообщение уже удалено или недоступно

    await state.clear()
    await callback.answer()

@router.message(F.text == "/start")
async def process_start_command(message: Message):
    tg_id = message.from_user.id
    lang = await add_user_with_alert(telegram_id=tg_id)
    await message.answer(text=message_text['start'][f'{lang}'],
                         reply_markup=await start_keyboard(lang=lang))


@router.message(
    (F.text == buttons_text['settings']['ru']) |
    (F.text == buttons_text['settings']['en']))
async def process_settings_command(message: Message):
    '''
    Срабатывает если настройки
    ДАЛЕЕ НЕБХОДИМО ПЕРЕНЕСТИ В СООТВЕТСВУЮЩИЙ ХЕНДЛЕР
    :param message:
    :return:
    '''
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    tg_id = message.from_user.id
    lang = await add_user_with_alert(telegram_id=tg_id)
    await message.answer(text=message_text['action_setting'][f'{lang}'],
                         reply_markup=await setting_keyboard(lang))

'''Поддержка'''
@router.message(
    (F.text == buttons_text['support']['ru']) |
    (F.text == buttons_text['support']['en']))
async def process_support_command(message: Message):
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    tg_id = message.from_user.id
    lang = await add_user_with_alert(telegram_id=tg_id)
    await message.answer(text=message_text['support_response'][f'{lang}'].format(tg_id),
                         reply_markup=await support_kb(lang))

@router.message(
    (F.text == buttons_text['settings_back']['ru']) |
    (F.text == buttons_text['settings_back']['en'])
)
async def process_settings_command(message: Message):
    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    except TelegramBadRequest:
        pass  # Сообщение уже удалено или недоступно
    tg_id = message.from_user.id
    lang = await add_user_with_alert(telegram_id=tg_id)
    await message.answer(text=message_text['Home_screen'][f'{lang}'],
                         reply_markup=await start_keyboard(lang))


'''Настройка языка'''


@router.message(
    (F.text == buttons_text['language']['ru']) |
    (F.text == buttons_text['language']['en'])
)
async def process_language_command(message: Message):
    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    except TelegramBadRequest:
        pass  # Сообщение уже удалено или недоступно
    tg_id = message.from_user.id
    lang = await add_user_with_alert(telegram_id=tg_id)
    await message.answer(text=message_text['choose_language'][f'{lang}'],
                         reply_markup=await keyboard_lang_choice(lang))


'''Если выбрали русский язык'''


@router.message(
    (F.text == buttons_text['language_ru']['ru']) |
    (F.text == buttons_text['language_ru']['en'])
)
async def process_language_command_ru(message: Message):
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    tg_id = message.from_user.id
    lang = 'ru'
    await change_user_language(tg_id=tg_id, language=lang)
    await message.answer(text=message_text['language_selected_ru'][f'{lang}'],
                         reply_markup=await setting_keyboard(lang))


'''Если выбрали английский язык'''


@router.message(
    (F.text == buttons_text['language_en']['ru']) |
    (F.text == buttons_text['language_en']['en'])
)
async def process_language_command_ru(message: Message):
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    tg_id = message.from_user.id
    lang = 'en'
    await change_user_language(tg_id=tg_id, language=lang)
    await message.answer(text=message_text['language_selected_en'][f'{lang}'],
                         reply_markup=await setting_keyboard(lang))


'''Периоды роста и просадки'''


@router.message(
    (F.text == buttons_text['Growth_period']['ru']) |
    (F.text == buttons_text['Growth_period']['en'])
)
async def process_Growth_period_command(message: Message, state: FSMContext):
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    tg_id = message.from_user.id
    lang = await add_user_with_alert(telegram_id=tg_id)
    await message.answer(text=message_text['tracking_period_prompt'][f'{lang}'],
                         reply_markup=await create_inline_kb(width=1,
                                                             pref='Cancel',
                                                             arg = buttons_text['cancel'][f'{lang}']
                                                             ),
                         )
    await state.set_state(FSMSettings.period_up)


@router.message(StateFilter(FSMSettings.period_up))
async def process_period_up(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    lang = await add_user_with_alert(telegram_id=tg_id)
    if is_valid_period(message.text):
        # Действия при корректном вводе
        period = int(message.text)
        #Сохраняем период в базу данных
        success = await update_growth_period(tg_id, new_period=period)

        if success:
            await message.answer(
                text=message_text['Period_set_success'][f'{lang}'].format(period=period),
                reply_markup=await setting_keyboard(lang)
            )
        else:
            await message.answer(
                text=message_text['error_try_again'][f'{lang}'],
                reply_markup=await setting_keyboard(lang)
            )
        await state.clear()
    else:
        # Действия при некорректном вводе
        await message.answer(
            text=message_text['error_try_again'][f'{lang}'].format(min=1, max=30)
        )


'''Процент роста'''
@router.message(
    (F.text == buttons_text['Percentage_of_growth']['ru']) |
    (F.text == buttons_text['Percentage_of_growth']['en'])
)
async def process_Percentage_of_growth_command(message: Message, state: FSMContext):
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    tg_id = message.from_user.id
    lang = await add_user_with_alert(telegram_id=tg_id)
    await message.answer(text=message_text['enter_growth_percent'][f'{lang}'],
                         reply_markup=await create_inline_kb(width=1,
                                                             pref='Cancel',
                                                             arg = buttons_text['cancel'][f'{lang}']
                                                             ),
                         )
    await state.set_state(FSMSettings.procent_up)

@router.message(StateFilter(FSMSettings.procent_up))
async def process_Procent_up(message: Message, state: FSMContext):
    is_valid, value, error = validate_percent_input(message.text)
    tg_id = message.from_user.id
    lang = await add_user_with_alert(telegram_id=tg_id)

    if is_valid:
        await update_growth_percent(tg_id, value)
        await message.answer(
            text=message_text['percent_saved'][lang].format(value),
            reply_markup=await start_keyboard(lang)
        )
        await state.clear()
    else:
        error_messages = {
            "not_a_number": message_text['invalid_percent_format'][lang],
            "too_small": message_text['percent_out_of_range'][lang],
            "too_large": message_text['percent_out_of_range'][lang]
        }
        await message.answer(
            text=error_messages[error],
            reply_markup=await create_inline_kb(width=1,
                                                pref='Cancel',
                                                arg=buttons_text['cancel'][f'{lang}']
                                                ),
        )


'''Процент падения'''
@router.message(
    (F.text == buttons_text['Drawdown_percentage']['ru']) |
    (F.text == buttons_text['Drawdown_percentage']['en'])
)
async def process_Drawdown_percentage_command(message: Message, state: FSMContext):
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    tg_id = message.from_user.id
    lang = await add_user_with_alert(telegram_id=tg_id)
    await message.answer(text=message_text['enter_drawdown_percent'][f'{lang}'],
                         reply_markup=await create_inline_kb(width=1,
                                                             pref='Cancel',
                                                             arg = buttons_text['cancel'][f'{lang}']
                                                             ),
                         )
    await state.set_state(FSMSettings.procent_down)

@router.message(StateFilter(FSMSettings.procent_down))
async def process_Procent_down(message: Message, state: FSMContext):
    is_valid, value, error = validate_percent_input(message.text)
    tg_id = message.from_user.id
    lang = await add_user_with_alert(telegram_id=tg_id)

    if is_valid:
        await update_down_percent(tg_id, value)
        await message.answer(
            text=message_text['percent_drawdown'][lang].format(value),
            reply_markup=await start_keyboard(lang)
        )
        await state.clear()
    else:
        error_messages = {
            "not_a_number": message_text['invalid_percent_format'][lang],
            "too_small": message_text['percent_out_of_range'][lang],
            "too_large": message_text['percent_out_of_range'][lang]
        }
        await message.answer(
            text=error_messages[error],
            reply_markup=await create_inline_kb(width=1,
                                                pref='Cancel',
                                                arg=buttons_text['cancel'][f'{lang}']
                                                ),
        )


'''Обработка подписки'''
@router.message(
    (F.text == buttons_text['price']['ru']) |
    (F.text == buttons_text['price']['en'])
)
async def price_process(message: Message):
    tg_id = message.from_user.id
    lang = await add_user_with_alert(telegram_id=tg_id)
    await message.answer(text=message_text['choose_payment_period'][lang],
                         reply_markup=await create_price_kb(lang
                                                             ),
                         )


'''Выбор на сколько подписка'''
@router.callback_query(F.data.startswith('price'))
async def price_callback_query(callback: CallbackQuery, state: FSMContext):
    tg_id = callback.from_user.id
    lang = await add_user_with_alert(telegram_id=tg_id)
    await bot.edit_message_text(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        text=message_text['payment_instructions'][lang],
        reply_markup=await create_inline_kb(width=1,
                                            pref=f'Send_{callback.data[6:]}_',
                                            args=buttons_text['attach_screenshot'][lang])
    )


    await callback.answer()

'''Кнопка прикрепить'''
@router.callback_query(F.data.startswith('Send_'))
async def sales_callback_query(callback: CallbackQuery, state: FSMContext):
    tg_id = callback.from_user.id
    lang = await add_user_with_alert(telegram_id=tg_id)
    await bot.edit_message_text(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        text=message_text['attach_payment_proof'][lang],
        reply_markup=await create_inline_kb(width=1,
                                            pref='Cancel',
                                            arg=buttons_text['cancel'][f'{lang}']
                                            ),
    )
    await state.set_state(FSMSettings.screenshot)
    await state.update_data(screenshot=callback.data.split('_')[1])



'''Отправка сообщений админам'''
@router.message(StateFilter(FSMSettings.screenshot))
async def screenshot_callback_query(message: Message, state: FSMContext):
    price = await state.get_data()
    period = price['screenshot']
    tg_id = message.from_user.id
    lang = await add_user_with_alert(telegram_id=tg_id)
    admins = await get_admin_ids()

    if period ==  buttons_text['subscription_1_month']['ru'] or period == buttons_text['subscription_1_month']['en']:
        validity_period = 1
    elif period == buttons_text['subscription_3_months']['ru'] or period == buttons_text['subscription_3_months']['en']:
        validity_period = 3
    elif period == buttons_text['subscription_6_months']['ru'] or period == buttons_text['subscription_6_months']['en']:
        validity_period = 6
    else:
        validity_period = 0

    # Формируем информацию о пользователе для админов
    user_info = f"👤 Пользователь: @{message.from_user.username or 'нет'}\n"
    user_info += f"🆔 ID: {message.from_user.id}\n"
    user_info += f"📅 Дата: {message.date.strftime('%Y-%m-%d %H:%M')}\n\n"
    user_info += f"Период: {period}\n\n"
    # Отправляем разные типы контента админам
    if message.photo:
        # Если это фото - пересылаем оригинал с подписью
        for admin_id in admins:
            try:
                await bot.send_photo(
                    chat_id=admin_id,
                    photo=message.photo[-1].file_id,
                    caption=user_info + (message.caption or "Прислано фото оплаты"),
                    reply_markup= await enter_price_kb(tg_id, validity_period)
                )
            except Exception as e:
                print(f"Error sending photo to admin {admin_id}: {e}")

    elif message.document:
        # Если документ - пересылаем файл
        for admin_id in admins:
            try:
                await bot.send_document(
                    chat_id=admin_id,
                    document=message.document.file_id,
                    caption=user_info + (message.caption or "Прислан документ оплаты"),
                    reply_markup= await enter_price_kb(tg_id, validity_period)
                )
            except Exception as e:
                print(f"Error sending document to admin {admin_id}: {e}")

    else:
        # Если текстовое сообщение - просто пересылаем
        for admin_id in admins:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=user_info + message.text,
                    reply_markup= await enter_price_kb(tg_id, validity_period)
                )
            except Exception as e:
                print(f"Error sending message to admin {admin_id}: {e}")

    # Подтверждаем получение пользователю
    await message.answer(
        text=message_text['screenshot_received'][lang]
    )
    await state.clear()

'''Ответ админа'''
@router.callback_query(F.data.startswith('enter'))
async def enter_callback_query(callback: CallbackQuery):
    await bot.delete_message(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id
    )
    action = callback.data.split('_')[1]
    user_id = callback.data.split('_')[-1]
    lang = await add_user_with_alert(telegram_id=int(user_id))
    if action == 'Reject':
        try:
            await bot.send_message(
                chat_id=user_id,
                text=message_text['document_rejected'][lang],
            )
        except Exception as e:
            print(f"Error sending document to admin {user_id}: {e}")
    else:
        subscription = await extend_subscription(telegram_id=int(user_id),
                                                 months=int(action))
        try:
            await bot.send_message(
                chat_id=user_id,
                text=message_text['subscription_extended'][lang].format(action, subscription),
            )
        except Exception as e:
            print(f"Error sending document to admin {user_id}: {e}")
    await callback.answer()
