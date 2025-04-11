import json
from datetime import datetime, timedelta
from typing import Dict

from redis.asyncio import Redis

redis_client = Redis(host='localhost', port=6379, db=0, decode_responses=True)


def calculate_percentage_diff(current_price: float, old_price: float) -> float:
    if old_price == 0:
        return 0.0
    return ((current_price - old_price) / old_price) * 100


def get_time_keys() -> list:
    """Генерирует список ключей формата HH:MM:SS за последние 30 минут (по секундам)"""
    now = datetime.now()
    return [
        (now - timedelta(seconds=i)).strftime("%H:%M:%S")
        for i in range(0, 31 * 60)  # 31 минута в секундах
    ]


async def update_redis_data(pair: str, current_price: float, event_time_ms: int):
    """
    Обновляет Redis-ключ с историей цен для торговой пары в формате HH:MM:SS.

    :param pair: Название пары, например 'BTCUSDT'
    :param current_price: Последняя цена
    :param event_time_ms: Время события в миллисекундах
    """
    # Время события в формате HH:MM:SS
    event_time = datetime.fromtimestamp(int(event_time_ms) / 1000)
    event_time_str = event_time.strftime("%H:%M:%S")

    # Получаем историю цен из Redis
    existing_data = await redis_client.get(pair)
    price_history = json.loads(existing_data) if existing_data else {}

    # Обновляем цену на текущее время
    price_history[event_time_str] = [current_price, 0]

    # Получаем ключи за последние 30 минут (по секундам)
    time_keys = get_time_keys()

    # Пересчитываем процент изменений по отношению к текущей цене
    for time_key in time_keys:
        if time_key == event_time_str:
            continue
        if time_key in price_history:
            old_price = price_history[time_key][0]
            percent_diff = calculate_percentage_diff(current_price, old_price)
            price_history[time_key] = [old_price, round(percent_diff, 4)]

    # Удаляем ключи старше 31 минуты
    price_history = {k: v for k, v in price_history.items() if k in time_keys}

    # Сохраняем в Redis и обновляем TTL
    await redis_client.set(pair, json.dumps(price_history))
    await redis_client.expire(pair, 1860)  # 31 минута


async def get_redis_data_for_pair(pair: str) -> dict:
    """
    Получает историю цен для конкретной пары из Redis.

    :param pair: Название торговой пары, например 'BTCUSDT'.
    :return: История цен для пары в виде словаря, например:
             {
                 'HH:MM:SS': [price, percent_diff],
                 ...
             }
    """
    # Получаем данные из Redis для указанной пары
    data = await redis_client.get(pair)

    if data:
        # Если данные есть, парсим JSON и возвращаем
        return json.loads(data)
    else:
        # Если данных нет, возвращаем пустой словарь
        return {}