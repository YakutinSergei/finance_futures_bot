import asyncio
import datetime
from typing import Dict, List
import logging
from aiogram.exceptions import TelegramAPIError

from ConfigData.redis import get_redis_data
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
                    #percent_down = user['percent_down']
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

                                elif change_percent <= -percent_up:
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


async def monitor_prices():
    """Основная функция для периодического мониторинга"""
    while True:
        try:
            logger.info("Начало цикла мониторинга цен")

            # 1. Получаем данные пользователей
            try:
                users = await get_users_alerts()
                logger.debug(f"Получено {len(users)} пользователей из БД")
            except Exception as e:
                logger.error(f"Ошибка получения пользователей из БД: {e}")
                users = []

            # 2. Получаем данные из Redis
            try:
                redis_data = await get_redis_data()
                logger.debug(f"Получено {len(redis_data)} пар из Redis")
            except Exception as e:
                logger.error(f"Ошибка получения данных из Redis: {e}")
                redis_data = {}

            # 3. Проверяем условия
            if users and redis_data:
                await check_alerts(users, redis_data)
            else:
                logger.warning("Пропуск проверки алертов из-за отсутствия данных")

        except asyncio.CancelledError:
            logger.info("Мониторинг цен остановлен")
            break
        except Exception as e:
            logger.critical(f"Критическая ошибка в monitor_prices: {e}", exc_info=True)
        finally:
            # Ожидаем 1 минуту перед следующей проверкой
            try:
                logger.info("Ожидание следующей итерации...")
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                logger.info("Мониторинг цен остановлен")
                break
            except Exception as e:
                logger.critical(f"Ошибка при ожидании: {e}")
                await asyncio.sleep(60)  # Повторная попытка после ошибки


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

    if value < 3.0:
        return False, None, "too_small"
    elif value > 100.0:
        return False, None, "too_large"

    return True, value, None