import json
import time
import datetime
from typing import Dict, List
import logging
from aiogram.exceptions import TelegramAPIError

from create_bot import bot
from data_base.lexicon import message_text, buttons_text
from keyboards.inline_keyboards import kb_pair_coinglass

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def check_alerts(
        users: List[Dict],
        redis_data: Dict[str, Dict],
):
    """Сравнивает данные пользователей с рыночными данными"""
    try:
        logger.info("Начало проверки алертов")
        if not users:
            logger.warning("Список пользователей пуст")
            return

        if not redis_data:
            logger.warning("Данные из Redis отсутствуют")
            return

        logger.debug(f"Получено {len(users)} пользователей и {len(redis_data)} пар из Redis")

        # Получаем текущее время
        current_datetime = datetime.datetime.now()
        current_time_str = current_datetime.strftime("%H:%M")

        for user in users:
            if user['role'] != 'free':
                try:
                    # Валидация данных пользователя
                    if not all(key in user for key in ['time_interval', 'percent_up', 'percent_down', 'telegram_id']):
                        logger.error(f"Некорректные данные пользователя: {user}")
                        continue

                    time_int = user['time_interval']
                    percent_up = user['percent_up']
                    percent_down = user['percent_down']
                    telegram_id = user['telegram_id']
                    lang = user['lang']

                    # Вычисляем историческое время (текущее время - time_int минут)
                    historical_datetime = current_datetime - datetime.timedelta(minutes=time_int)
                    historical_time_str = historical_datetime.strftime("%H:%M")

                    for pair, prices in redis_data.items():
                        try:
                            # Получаем текущую цену
                            current_price_data = prices.get(current_time_str)
                            if not current_price_data or len(current_price_data) < 1 or current_price_data[0] == 0:
                                logger.debug(f"Нет текущей цены для пары {pair} в {current_time_str}")
                                continue

                            current_price = current_price_data[0]

                            # Получаем историческую цену
                            historical_price_data = prices.get(historical_time_str)
                            if not historical_price_data or historical_price_data[0] == 0:
                                logger.debug(
                                    f"Нет исторической цены для пары {pair} за {time_int} мин (ищем {historical_time_str})")
                                continue

                            historical_price = historical_price_data[0]

                            # Расчет изменения цены
                            try:
                                change_percent = ((current_price - historical_price) / historical_price) * 100
                            except ZeroDivisionError:
                                logger.error(f"Деление на ноль при расчете для пары {pair}")
                                continue
                            print(f'{change_percent=}')
                            # Проверка триггеров
                            try:
                                if change_percent >= percent_up:
                                    message = (
                                        f"🏦 Binance - ⏱️ {time_int}M - <code>{pair}</code>\n"
                                        f"🔄 {buttons_text['Percentage_of_growth'][f'{lang}']}:⬆️ {change_percent:.2f}%\n"
                                        f"💵 {message_text['Current_Price'][f'{lang}']}: {current_price}"
                                    )
                                    await bot.send_message(
                                        chat_id=telegram_id,
                                        text=message,
                                        reply_markup=await kb_pair_coinglass(pair)
                                    )
                                    logger.info(f"Оповещение о росте {pair} для {telegram_id}")

                                elif change_percent <= -percent_down:
                                    message = (
                                        f"🏦 Binance - ⏱️ {time_int}M - <code>{pair}</code>\n"
                                        f"🔄 {buttons_text['Drawdown_percentage'][f'{lang}']}: ⬇️{change_percent:.2f}%\n"
                                        f"💵 {message_text['Current_Price'][f'{lang}']}: {current_price}"
                                    )
                                    await bot.send_message(
                                        chat_id=telegram_id,
                                        text=message,
                                        reply_markup=await kb_pair_coinglass(pair)
                                    )
                                    logger.info(f"Оповещение о падении {pair} для {telegram_id}")

                            except TelegramAPIError as e:
                                logger.error(f"Ошибка Telegram для {telegram_id}: {str(e)}")
                                break
                            except Exception as e:
                                logger.error(f"Неожиданная ошибка отправки: {str(e)}")

                        except Exception as e:
                            logger.error(f"Ошибка обработки пары {pair}: {str(e)}", exc_info=True)

                except Exception as e:
                    logger.error(f"Ошибка обработки пользователя {user.get('telegram_id', 'unknown')}: {str(e)}",
                                 exc_info=True)

    except Exception as e:
        logger.critical(f"Критическая ошибка check_alerts: {str(e)}", exc_info=True)
    finally:
        logger.info("Завершение проверки алертов")


def is_valid_period(text: str) -> bool:
    """
    Проверяет, что текст представляет собой целое число от 1 до 30

    :param text: Входной текст для проверки
    :return: True если текст соответствует требованиям, иначе False
    """
    try:
        number = int(text)
        return 1 <= number <= 30
    except ValueError:
        return False


def validate_percent_input(text: str) -> tuple[bool, float | None, str | None]:
    """
    Расширенная проверка с возвратом причины ошибки

    :param text: Входной текст
    :return: (валидность, число или None, сообщение об ошибке или None)
    """
    try:
        value = float(text)
    except ValueError:
        return False, None, "not_a_number"

    if value < 2.0:
        return False, None, "too_small"
    elif value > 100.0:
        return False, None, "too_large"

    return True, value, None

    # Функция для поиска ближайшего времени с данными
def get_nearest_available_price(prices, target_time):
    """Находит ближайшее доступное время с данными из Redis, максимум 10 секунд назад"""
    closest_time = target_time
    max_retries = 10  # Максимальное количество попыток (10 секунд)

    for _ in range(max_retries):
        if closest_time in prices:
            return closest_time
        # Уменьшаем время на одну секунду
        closest_time = (datetime.datetime.strptime(closest_time, "%H:%M:%S") - datetime.timedelta(seconds=1)).strftime("%H:%M:%S")

    return None  # Если не нашли время в пределах 10 секунд, возвращаем None

# Глобальный словарь-кэш, в котором храним время последней отправки уведомления
# Формат: {telegram_id: {pair: timestamp_of_last_send}}
sent_alerts_cache: dict[int, dict[str, float]] = {}

async def check_alert_for_user(alert_dict: dict, pair: str, prices: dict, price_now: float):
    """
    Проверяет, нужно ли отправить оповещение конкретному пользователю по данной паре.
    Ограничивает повторную отправку для одной пары на 5 минут (без Redis).
    """

    try:
        # Извлекаем данные пользователя из словаря алерта
        user_data = alert_dict['user']
        telegram_id = user_data['telegram_id']  # Telegram ID пользователя
        lang = user_data['language']  # Язык пользователя (например, "en", "ru")

        # Параметры из самого алерта
        time_interval = alert_dict['time_interval']  # Интервал (в минутах) для анализа изменений цены
        percent_up = alert_dict['percent_up']        # Порог повышения (в процентах)
        percent_down = alert_dict['percent_down']    # Порог понижения (в процентах)

        # Текущее время
        current_datetime = datetime.datetime.now()

        # Время, на которое нужно посмотреть назад (историческое)
        historical_time = (current_datetime - datetime.timedelta(minutes=time_interval)).strftime("%H:%M:%S")


        # Находим ближайшее время, доступное в истории
        historical_time = get_nearest_available_price(prices, historical_time)

        # Получаем данные цены из Redis для этого времени
        historical_price_data = prices.get(historical_time)

        # Если данные не найдены — выходим
        if not historical_price_data:
            return

        # Получаем текущую и историческую цену
        current_price = price_now
        historical_price = historical_price_data[0]

        # Защита от деления на ноль
        if historical_price == 0:
            return

        # Расчёт процентного изменения цены
        change_percent = ((current_price - historical_price) / historical_price) * 100

        # Текущее время в секундах (для сравнения с последними отправками)
        current_time = time.time()

        # Получаем из кэша словарь пар, которым уже отправляли уведомления этому пользователю
        user_alerts = sent_alerts_cache.get(telegram_id, {})

        # Получаем время последней отправки по этой паре (если было)
        last_sent_time = user_alerts.get(pair)

        # Если уведомление по этой паре уже было отправлено менее 5 минут назад — ничего не делаем
        if last_sent_time and current_time - last_sent_time < 5 * 60:
            return


        # Если цена выросла выше заданного порога — формируем сообщение на рост
        if change_percent >= percent_up:
            message = (
                f"🏦 Binance - ⏱️ {time_interval}M - <code>{pair}</code>\n"
                f"🔄 {buttons_text['Percentage_of_growth'][f'{lang}']}: ⬆️ {change_percent:.2f}%\n"
                f"💵 {message_text['Current_Price'][f'{lang}']}: {current_price}"
            )

        # Если цена упала ниже заданного порога — формируем сообщение на падение
        elif change_percent <= -percent_down:
            message = (
                f"🏦 Binance - ⏱️ {time_interval}M - <code>{pair}</code>\n"
                f"🔄 {buttons_text['Drawdown_percentage'][f'{lang}']}: ⬇️ {change_percent:.2f}%\n"
                f"💵 {message_text['Current_Price'][f'{lang}']}: {current_price}"
            )

        # Если ни одно условие не выполнено — выходим
        else:
            return

        # Отправка сообщения пользователю в Telegram
        try:
            await bot.send_message(
                chat_id=telegram_id,
                text=message,
                reply_markup=await kb_pair_coinglass(pair)  # Кнопки по паре (например, ссылка на Coinglass)
            )

            # Сохраняем время последней отправки уведомления по этой паре
            if telegram_id not in sent_alerts_cache:
                sent_alerts_cache[telegram_id] = {}  # Создаём словарь для нового пользователя

            # Обновляем время отправки по текущей паре
            sent_alerts_cache[telegram_id][pair] = current_time

        except TelegramAPIError:
            # Если не удалось отправить сообщение (например, пользователь заблокировал бота) — логируем
            logger.warning(f"[check_alert_for_user] Не удалось отправить сообщение пользователю {telegram_id}")

    except Exception as e:
        # Логируем любые неожиданные ошибки
        logger.exception(f"[check_alert_for_user] Ошибка при обработке алерта: {e}")
