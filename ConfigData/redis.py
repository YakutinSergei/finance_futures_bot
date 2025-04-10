import json
from datetime import datetime, timedelta
from typing import Dict

from redis.asyncio import Redis

redis_client = Redis(host='localhost', port=6379, db=0, decode_responses=True)


def calculate_percentage_diff(current_price, old_price):
    if old_price == 0:
        return 0
    return ((current_price - old_price) / old_price) * 100


def get_time_keys():
    """Генерирует список временных ключей за последние 30 минут"""
    now = datetime.now()
    time_keys = []
    for minutes_ago in range(0, 31):
        time = now - timedelta(minutes=minutes_ago)
        time_keys.append(time.strftime("%H:%M"))
    return time_keys


async def update_redis_data(pair, current_price):
    current_time = datetime.now().strftime("%H:%M")
    existing_data = await redis_client.get(pair)

    if existing_data:
        price_history = json.loads(existing_data)
    else:
        price_history = {}
        await redis_client.expire(pair, 1860)  # TTL 31 минута

    updated_history = {}
    updated_history[current_time] = [current_price, 0]  # Текущее время и цена

    # Получаем список временных меток за последние 30 минут
    time_keys = get_time_keys()

    for time_key in time_keys[1:]:  # Пропускаем текущее время (первый элемент)
        if time_key in price_history:
            old_price = price_history[time_key][0]
            percent_diff = calculate_percentage_diff(current_price, old_price)
            updated_history[time_key] = [old_price, round(percent_diff, 4)]
        else:
            updated_history[time_key] = [0, 0]

    # Удаляем старые записи (старше 30 минут)
    for key in list(updated_history.keys()):
        if key not in time_keys:
            del updated_history[key]
    await redis_client.set(pair, json.dumps(updated_history))
    await redis_client.expire(pair, 1860)


# 2. Получение данных из Redis
async def get_redis_data() -> Dict[str, Dict]:
    """Получает все данные по парам из Redis"""
    data = {}
    # Получаем все ключи (пары)
    keys = await redis_client.keys("*")

    for pair in keys:
        value = await redis_client.get(pair)
        if value:
            data[pair] = json.loads(value)

    return data