import asyncio
import json
import logging
from typing import Any

import aiohttp

from ConfigData.redis import update_redis_data, get_redis_data_for_pair
from data_base.orm import get_cached_alerts_with_users
from pars.function import check_alert_for_user

BINANCE_WS_URL = "wss://fstream.binance.com/ws/!ticker@arr"

# Настройка логгера
logger = logging.getLogger(__name__)


async def handle_ticker(ticker: dict[str, Any], alerts: list[dict[str, Any]]):
    """
    Обработка одного тикера Binance: обновление Redis, получение истории, проверка алертов.
    """
    try:
        pair = ticker.get("s")  # Пример: BTCUSDT
        price = float(ticker.get("c"))
        event_time = int(ticker.get("E"))

        logger.debug(f"[handle_ticker] Обработка пары {pair} | Цена: {price} | Время: {event_time}")

        # Обновляем Redis
        await update_redis_data(pair, price, event_time)

        # История цен
        redis_data = await get_redis_data_for_pair(pair)

        # Проверка алертов
        tasks = [
            check_alert_for_user(alert, pair, redis_data, price)
            for alert in alerts
        ]
        await asyncio.gather(*tasks)

    except Exception as e:
        logger.exception(f"[handle_ticker] Ошибка при обработке тикера {ticker}: {e}")


async def binance_ws_listener():
    """
    Слушает Binance WebSocket и обрабатывает обновления тикеров.
    """
    logger.info("[binance_ws_listener] Подключение к Binance WebSocket...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(BINANCE_WS_URL) as ws:
                logger.info("[binance_ws_listener] Подключено к WebSocket Binance")

                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            data = json.loads(msg.data)

                            if not isinstance(data, list):
                                logger.warning("[binance_ws_listener] Получены данные не в виде списка")
                                continue

                            alerts = await get_cached_alerts_with_users(ttl=15)
                            logger.debug(f"[binance_ws_listener] Получено {len(data)} тикеров, {len(alerts)} алертов")

                            tasks = [handle_ticker(ticker, alerts) for ticker in data]
                            await asyncio.gather(*tasks)

                        except json.JSONDecodeError as e:
                            logger.warning(f"[binance_ws_listener] Ошибка декодирования JSON: {e}")
                        except Exception as e:
                            logger.exception(f"[binance_ws_listener] Ошибка при обработке сообщения: {e}")

                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logger.error(f"[binance_ws_listener] Ошибка WebSocket-сообщения: {msg}")
                        break

    except aiohttp.ClientConnectorError as e:
        logger.critical(f"[binance_ws_listener] Ошибка подключения к Binance WebSocket: {e}")
    except Exception as e:
        logger.exception(f"[binance_ws_listener] Необработанная ошибка: {e}")
