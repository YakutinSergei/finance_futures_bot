import asyncio
import datetime
import json

import aiohttp
from sqlalchemy import select
from sqlalchemy import select, update, and_

from ConfigData.redis import update_redis_data
from data_base.database import async_session
from data_base.model import PriceData

BINANCE_WS_URL = "wss://fstream.binance.com/ws/!ticker@arr"  # URL для WebSocket Binance Futures


def get_current_time_without_seconds():
    now = datetime.datetime.now()
    return now.replace(second=0, microsecond=0)


async def update_or_create_price(db, pair, price):
    current_time = get_current_time_without_seconds()

    # Пытаемся обновить существующую запись
    stmt = (
        update(PriceData)
        .where(and_(
            PriceData.pair == pair,
            PriceData.timestamp == current_time
        ))
        .values(price=price)
        .execution_options(synchronize_session="fetch")
    )

    result = await db.execute(stmt)

    # Если не было обновления (запись не существует), создаём новую
    if result.rowcount == 0:
        new_data = PriceData(
            pair=pair,
            price=price,
            timestamp=current_time
        )
        db.add(new_data)

    await db.commit()


async def binance_ws_listener():
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(BINANCE_WS_URL) as ws:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    async with async_session() as db:
                        for ticker in data:
                            pair = ticker["s"]
                            price = float(ticker["c"])

                            await update_redis_data(pair, price)
                            await update_or_create_price(db, pair, price)

                await asyncio.sleep(2)