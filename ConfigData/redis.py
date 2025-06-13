import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List

from redis.asyncio import Redis

# Инициализация Redis клиента
redis_client = Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Логгер
logger = logging.getLogger(__name__)


def calculate_percentage_diff(current_price: float, old_price: float) -> float:
    """
    Вычисляет процентное изменение между двумя ценами.
    """
    if old_price == 0:
        return 0.0
    return ((current_price - old_price) / old_price) * 100


def get_time_keys(base_time: Optional[datetime] = None) -> List[str]:
    """
    Генерирует список ключей формата HH:MM:SS за последние 30 минут (по секундам).
    """
    now = base_time or datetime.now()
    return [
        (now - timedelta(seconds=i)).strftime("%H:%M:%S")
        for i in range(0, 31 * 60)
    ]


async def update_redis_data(pair: str, current_price: float, event_time_ms: int) -> None:
    """
    Обновляет Redis-ключ с историей цен для торговой пары в формате HH:MM:SS.

    :param pair: Название пары, например 'BTCUSDT'
    :param current_price: Последняя цена
    :param event_time_ms: Время события в миллисекундах
    """
    if event_time_ms is None:
        logger.warning(f"[update_redis_data] event_time_ms is None for pair {pair}")
        return

    try:
        event_time = datetime.fromtimestamp(int(event_time_ms) / 1000)
        event_time_str = event_time.strftime("%H:%M:%S")

        # Получаем историю цен из Redis
        existing_data = await redis_client.get(pair)
        price_history = json.loads(existing_data) if existing_data else {}

        # Обновляем цену на текущее время
        price_history[event_time_str] = [current_price, 0]

        # Обновляем проценты за последние 30 минут
        time_keys = get_time_keys(event_time)
        for time_key in time_keys:
            if time_key == event_time_str:
                continue
            if time_key in price_history:
                old_price = price_history[time_key][0]
                percent_diff = calculate_percentage_diff(current_price, old_price)
                price_history[time_key] = [old_price, round(percent_diff, 4)]

        # Удаляем устаревшие ключи
        price_history = {k: v for k, v in price_history.items() if k in time_keys}

        # Сохраняем обратно в Redis
        await redis_client.set(pair, json.dumps(price_history))
        await redis_client.expire(pair, 1860)  # 31 минута TTL

    except Exception as e:
        logger.error(f"[update_redis_data] Ошибка при обновлении данных Redis для {pair}: {e}")


async def get_redis_data_for_pair(pair: str) -> Dict[str, List[float]]:
    """
    Получает историю цен для конкретной пары из Redis.

    :param pair: Название пары, например 'BTCUSDT'
    :return: Словарь формата { 'HH:MM:SS': [price, percent_diff], ... }
    """
    try:
        data = await redis_client.get(pair)
        return json.loads(data) if data else {}
    except Exception as e:
        logger.error(f"[get_redis_data_for_pair] Ошибка при получении данных Redis для {pair}: {e}")
        return {}
