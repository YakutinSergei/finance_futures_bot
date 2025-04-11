import asyncio
import datetime
import json

import aiohttp
from sqlalchemy import select, update, and_

from ConfigData.redis import update_redis_data, get_redis_data_for_pair
from data_base.database import async_session
from data_base.model import PriceData
from data_base.orm import get_cached_alerts_with_users
from pars.function import check_alert_for_user

BINANCE_WS_URL = "wss://fstream.binance.com/ws/!ticker@arr"  # URL для WebSocket Binance Futures


def get_current_time_without_seconds():
    now = datetime.datetime.now()
    return now.replace(second=0, microsecond=0)


# async def update_or_create_price(db, pair, price):
#     current_time = get_current_time_without_seconds()
#
#     # Пытаемся обновить существующую запись
#     stmt = (
#         update(PriceData)
#         .where(and_(
#             PriceData.pair == pair,
#             PriceData.timestamp == current_time
#         ))
#         .values(price=price)
#         .execution_options(synchronize_session="fetch")
#     )
#
#     result = await db.execute(stmt)
#
#     # Если не было обновления (запись не существует), создаём новую
#     if result.rowcount == 0:
#         new_data = PriceData(
#             pair=pair,
#             price=price,
#             timestamp=current_time
#         )
#         db.add(new_data)
#
#     await db.commit()


async def binance_ws_listener():
    """
    Подключается к WebSocket Binance Futures и обрабатывает поток данных.
    Для каждой валютной пары:
    - сохраняет цену в Redis;
    - извлекает из Redis историю цен по паре;
    - проверяет условия оповещения для всех пользователей.
    """
    # Загружаем все настройки алертов с привязанными пользователями

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(BINANCE_WS_URL) as ws:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)  # Декодируем JSON-массив тикеров
                    alerts = await get_cached_alerts_with_users(ttl=15)
                    for ticker in data:
                        pair = ticker["s"]  # Название торговой пары, например "BTCUSDT"
                        price = float(ticker["c"])  # Текущая цена
                        time = ticker["E"]  # Время события в миллисекундах



                        # Обновляем Redis-хранилище цен
                        await update_redis_data(pair, price, time)

                        # Получаем историю цен из Redis по конкретной паре
                        redis_data = await get_redis_data_for_pair(pair)

                        # Собираем все задачи проверки алертов для каждого пользователя
                        tasks = []
                        for alert in alerts:
                            task = check_alert_for_user(alert, pair, redis_data, price)
                            tasks.append(task)

                        # Запускаем все задачи одновременно
                        await asyncio.gather(*tasks)
