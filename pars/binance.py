import asyncio
import datetime
import json
import logging
import time
from collections import defaultdict
from typing import Any

import aiohttp

from ConfigData.redis import update_redis_data, get_redis_data_for_pair, redis_client
from data_base.orm import get_cached_alerts_with_users
from pars.function import check_alert_for_user

BINANCE_WS_URL = "wss://fstream.binance.com/ws/!ticker@arr"

# Настройка логгера
logger = logging.getLogger(__name__)



async def process_tickers(tickers: list[dict], alerts: list[dict], historical_prices: dict):
    """
    Обрабатывает список тикеров без создания задач.
    """
    # Группируем алерты по паре
    alerts_by_pair = defaultdict(list)
    for alert in alerts:
        pair = alert.get('pair')
        if pair:
            alerts_by_pair[pair].append(alert)

    # Создаём задачи на обработку тикеров
    tasks = []
    for ticker in tickers:
        try:
            pair = ticker.get("s")
            pair_alerts = alerts_by_pair.get(pair, [])
            tasks.append(handle_ticker(ticker, pair_alerts, historical_prices))
        except Exception as e:
            logger.exception(f"[process_tickers] Ошибка при подготовке тикера: {ticker.get('s')}")

    # Параллельный запуск
    await asyncio.gather(*tasks, return_exceptions=True)

async def get_bulk_price_history(pairs: set[str]) -> dict[str, dict[str, list[Any]]]:
    """
    Получает историю цен из Redis для всех переданных пар.
    :param pairs: Сет тикеров (напр. {'BTCUSDT', 'ETHUSDT'})
    :return: Словарь формата { "BTCUSDT": { "12:00:00": [price, %], ... }, ... }
    """
    result = {}
    redis_keys = list(pairs)
    redis_data = await redis_client.mget(*redis_keys)


    for key, raw_data in zip(redis_keys, redis_data):
        if raw_data:
            try:
                result[key] = json.loads(raw_data)
            except json.JSONDecodeError:
                result[key] = {}
        else:
            result[key] = {}

    return result


async def handle_ticker(ticker: dict[str, Any], alerts: list[dict[str, Any]], historical_prices: dict[str, Any]):
    """
    Обрабатывает тикер Binance: обновление Redis, анализ алертов, проверка условий.
    """
    try:
        pair = ticker.get("s")
        price_now = float(ticker.get("c"))
        event_time = int(ticker.get("E"))

        logger.debug(f"[handle_ticker] Пара: {pair} | Цена: {price_now} | Время: {event_time}")

        # Обновляем Redis новой ценой
        await update_redis_data(pair, price_now, event_time)

        # Получаем сохранённую историю для этой пары
        redis_data = historical_prices.get(pair)
        if not redis_data:
            #logger.warning(f"[handle_ticker] Нет исторических данных по паре {pair}")
            return

        # Сортировка времени истории один раз
        sorted_price_keys = sorted(redis_data.keys())

        # Подготовка текущего времени
        now_dt = datetime.datetime.now()
        now_ts = time.time()

        # Создание задач
        tasks = [
            check_alert_for_user(alert, pair, redis_data, price_now, sorted_price_keys, now_dt, now_ts)
            for alert in alerts
        ]

        if tasks:
            await asyncio.gather(*tasks)

    except Exception as e:
        logger.exception(f"[handle_ticker] Ошибка при обработке тикера {ticker}: {e}")


async def binance_ws_listener():
    """
    Слушает Binance WebSocket, накапливает тикеры и обрабатывает их каждые 10 секунд.
    """
    logger.info("[binance_ws_listener] Подключение к Binance WebSocket...")

    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(BINANCE_WS_URL) as ws:
                    logger.info("[binance_ws_listener] Подключено к WebSocket Binance")

                    ticker_buffer = []
                    last_process_time = time.time()

                    async for msg in ws:
                        now = time.time()

                        if msg.type == aiohttp.WSMsgType.TEXT:
                            try:
                                data = json.loads(msg.data)

                                if isinstance(data, list):
                                    ticker_buffer.extend(data)
                                else:
                                    logger.warning("[binance_ws_listener] Получены данные не в виде списка")

                            except json.JSONDecodeError as e:
                                logger.warning(f"[binance_ws_listener] Ошибка декодирования JSON: {e}")
                            except Exception as e:
                                logger.exception(f"[binance_ws_listener] Ошибка при обработке сообщения: {e}")

                            if now - last_process_time >= 10:
                                if ticker_buffer:
                                    logger.info(f"[binance_ws_listener] Обработка {len(ticker_buffer)} тикеров")

                                    alerts = await get_cached_alerts_with_users(ttl=15)
                                    # Собираем все пары
                                    all_pairs = {ticker["s"] for ticker in ticker_buffer}
                                    historical_prices = await get_bulk_price_history(all_pairs)

                                    # Передаём сразу список тикеров, а не таски
                                    await process_tickers(ticker_buffer, alerts, historical_prices)

                                    ticker_buffer.clear()

                                last_process_time = now

                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            logger.error(f"[binance_ws_listener] Ошибка WebSocket-сообщения: {msg}")
                            break

        except aiohttp.ClientConnectorError as e:
            logger.critical(f"[binance_ws_listener] Ошибка подключения к Binance WebSocket: {e}")
        except Exception as e:
            logger.exception(f"[binance_ws_listener] Необработанная ошибка: {e}")

        logger.info("[binance_ws_listener] Попытка переподключения через 10 секунд...")
        await asyncio.sleep(10)
