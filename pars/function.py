import json
import time
import datetime
from typing import Dict, List
import logging
from aiogram.exceptions import TelegramAPIError

from ConfigData.redis import redis_client
# from ConfigData.redis import get_redis_data
from create_bot import bot
from data_base.lexicon import message_text, buttons_text
from data_base.orm import get_users_alerts
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


# async def monitor_prices():
#     """Основная функция для периодического мониторинга"""
#     while True:
#         try:
#             logger.info("Начало цикла мониторинга цен")
#
#             # 1. Получаем данные пользователей
#             try:
#                 users = await get_users_alerts()
#                 logger.debug(f"Получено {len(users)} пользователей из БД")
#             except Exception as e:
#                 logger.error(f"Ошибка получения пользователей из БД: {e}")
#                 users = []
#
#             # 2. Получаем данные из Redis
#             try:
#                 redis_data = await get_redis_data()
#                 logger.debug(f"Получено {len(redis_data)} пар из Redis")
#             except Exception as e:
#                 logger.error(f"Ошибка получения данных из Redis: {e}")
#                 redis_data = {}
#
#             # 3. Проверяем условия
#             if users and redis_data:
#                 await check_alerts(users, redis_data)
#             else:
#                 logger.warning("Пропуск проверки алертов из-за отсутствия данных")
#
#         except asyncio.CancelledError:
#             logger.info("Мониторинг цен остановлен")
#             break
#         except Exception as e:
#             logger.critical(f"Критическая ошибка в monitor_prices: {e}", exc_info=True)
#         finally:
#             # Ожидаем 1 минуту перед следующей проверкой
#             try:
#                 logger.info("Ожидание следующей итерации...")
#                 await asyncio.sleep(60)
#             except asyncio.CancelledError:
#                 logger.info("Мониторинг цен остановлен")
#                 break
#             except Exception as e:
#                 logger.critical(f"Ошибка при ожидании: {e}")
#                 await asyncio.sleep(60)  # Повторная попытка после ошибки


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


async def check_alert_for_user(alert_dict: dict, pair: str, prices: dict, price_now: float):
    """
    Проверяет, нужно ли отправить оповещение конкретному пользователю по данной паре.
    Сравнивает текущую цену и цену N минут назад, рассчитывает процентное изменение.

    :param alert_dict: словарь, представляющий данные об алерте
    :param pair: название пары, например "BTCUSDT"
    :param prices: словарь из Redis формата { "HH:MM:SS": [price, %change] }
    """
    user_data = alert_dict['user']  # Извлекаем информацию о пользователе
    telegram_id = user_data['telegram_id']
    lang = user_data['language']
    time_interval = alert_dict['time_interval']
    percent_up = alert_dict['percent_up']
    percent_down = alert_dict['percent_down']

    # Получаем данные о сработавших парах для пользователя из Redis
    user_alert_key = f"{telegram_id}_alerts"  # Ключ для хранения информации о сработавших парах
    user_alerts = await redis_client.get(user_alert_key)

    # Если данных нет, создаем новый словарь для хранения
    if user_alerts:
        user_alerts = json.loads(user_alerts)
    else:
        user_alerts = {}

    # Проверка, если эта пара уже была проверена в последние N минут
    current_time = time.time()  # Текущее время в секундах
    if pair in user_alerts:
        last_check_time = user_alerts[pair]
        if current_time - last_check_time < time_interval * 60:
            #print(f"Пара {pair} уже проверялась недавно. Пропускаем.")
            return  # Пропускаем выполнение, если пара уже проверялась недавно

    # Текущее время в формате HH:MM:SS
    current_datetime = datetime.datetime.now()
    historical_time = (current_datetime - datetime.timedelta(minutes=time_interval)).strftime("%H:%M:%S")

    # Пытаемся получить историческую цену для запрашиваемого времени
    historical_time = get_nearest_available_price(prices, historical_time)
    historical_price_data = prices.get(historical_time)

    # Если нет исторической цены, выходим
    if not historical_price_data:
        return

    current_price = price_now
    historical_price = historical_price_data[0]

    if historical_price == 0:
        return  # Защита от деления на ноль

    # Расчёт процентного изменения цены
    change_percent = ((current_price - historical_price) / historical_price) * 100

    # Проверка условия "рост >= порога"
    if change_percent >= percent_up:
        message = (
            f"🏦 Binance - ⏱️ {time_interval}M - <code>{pair}</code>\n"
            f"🔄 {buttons_text['Percentage_of_growth'][f'{lang}']}: ⬆️ {change_percent:.2f}%\n"
            f"💵 {message_text['Current_Price'][f'{lang}']}: {current_price}"
        )
        try:
            await bot.send_message(chat_id=telegram_id, text=message, reply_markup=await kb_pair_coinglass(pair))

            # Обновляем время последней проверки для этой пары
            user_alerts[pair] = current_time
            await redis_client.set(user_alert_key, json.dumps(user_alerts), ex=time_interval * 60)  # Устанавливаем TTL

        except TelegramAPIError as e:
            print('Ошибка отправки сообщения')

    # Проверка условия "падение >= порога"
    elif change_percent <= -percent_down:
        message = (
            f"🏦 Binance - ⏱️ {time_interval}M - <code>{pair}</code>\n"
            f"🔄 {buttons_text['Drawdown_percentage'][f'{lang}']}: ⬇️ {change_percent:.2f}%\n"
            f"💵 {message_text['Current_Price'][f'{lang}']}: {current_price}"
        )
        try:
            await bot.send_message(chat_id=telegram_id, text=message, reply_markup=await kb_pair_coinglass(pair))

            # Обновляем время последней проверки для этой пары
            user_alerts[pair] = current_time
            await redis_client.set(user_alert_key, json.dumps(user_alerts), ex=time_interval * 60)  # Устанавливаем TTL

        except TelegramAPIError as e:
            print('Ошибка отправки сообщения')
