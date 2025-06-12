import asyncio
import json
import time
import datetime
from typing import Dict, List
import logging
from aiogram.exceptions import TelegramAPIError

from create_bot import bot
from data_base.lexicon import message_text, buttons_text
from keyboards.inline_keyboards import kb_pair_coinglass
semaphore = asyncio.Semaphore(20)  # Максимум 20 одновременных задач

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

async def check_alert_for_user(
    alert_dict: dict,
    pair: str,
    prices: dict,
    price_now: float,
    sorted_price_keys: list,
    now_dt: datetime.datetime,
    now_ts: float
):
    print("check_alert_for_user запущен")

    try:
        user = alert_dict["user"]
        telegram_id = user["telegram_id"]
        lang = user["language"]

        interval = alert_dict["time_interval"]
        up = alert_dict["percent_up"]
        down = alert_dict["percent_down"]

        # Рассчитываем историческое время
        hist_dt = now_dt - datetime.timedelta(minutes=interval)
        hist_time_str = hist_dt.strftime("%H:%M:%S")
        nearest_time = get_nearest_available_price(sorted_price_keys, hist_time_str)

        # Извлекаем цену
        hist_price_data = prices.get(nearest_time)

        if not hist_price_data:
            return

        hist_price = hist_price_data[0]
        if hist_price == 0:
            return

        percent = ((price_now - hist_price) / hist_price) * 100

        last_sent_time = sent_alerts_cache.get(telegram_id, {}).get(pair)
        if last_sent_time and now_ts - last_sent_time < 5 * 60:
            return

        print(f'{percent=} {now_ts=} {last_sent_time=}')
        # Готовим текст
        grow_text = buttons_text['Percentage_of_growth'].get(lang, 'Growth')
        drop_text = buttons_text['Drawdown_percentage'].get(lang, 'Drop')
        price_text = message_text['Current_Price'].get(lang, 'Price')

        if percent >= up:
            msg = (
                f"🏦 Binance - ⏱️ {interval}M - <code>{pair}</code>\n"
                f"🔄 {grow_text}: ⬆️ {percent:.2f}%\n"
                f"💵 {price_text}: {price_now}"
            )
        elif percent <= -down:
            msg = (
                f"🏦 Binance - ⏱️ {interval}M - <code>{pair}</code>\n"
                f"🔄 {drop_text}: ⬇️ {percent:.2f}%\n"
                f"💵 {price_text}: {price_now}"
            )
        else:
            return

        # Отправка сообщения
        async with semaphore:
            await bot.send_message(
                chat_id=telegram_id,
                text=msg,
                reply_markup=await kb_pair_coinglass(pair)
            )

        # Обновляем кэш
        sent_alerts_cache.setdefault(telegram_id, {})[pair] = now_ts

    except TelegramAPIError:
        logger.warning(f"[check_alert_for_user] Не удалось отправить сообщение пользователю {telegram_id}")
    except Exception as e:
        logger.exception(f"[check_alert_for_user] Ошибка: {e}")
