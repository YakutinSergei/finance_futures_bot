import asyncio
import datetime
import json
import logging
import time
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
    for ticker in tickers:
        try:
            await handle_ticker(ticker, alerts, historical_prices)
        except Exception as e:
            logger.exception(f"[process_tickers] Ошибка при обработке тикера: {ticker.get('s')}")


async def get_bulk_price_history(pairs: set[str]) -> dict[str, dict[str, list[Any]]]:
    """
    Получает историю цен из Redis для всех переданных пар.
    :param pairs: Сет тикеров (напр. {'BTCUSDT', 'ETHUSDT'})
    :return: Словарь формата { "BTCUSDT": { "12:00:00": [price, %], ... }, ... }
    """
    result = {}
    for pair in pairs:
        redis_key = f"{pair}"
        raw_data = await redis_client.get(redis_key)
        if raw_data:
            try:
                result[pair] = json.loads(raw_data)
            except json.JSONDecodeError:
                logger.warning(f"[get_bulk_price_history] Ошибка декодирования JSON для пары {pair}")
                result[pair] = {}
        else:
            result[pair] = {}

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
    Сохраняются только последние значения уникальных торговых пар.
    """
    logger.info("[binance_ws_listener] Подключение к Binance WebSocket...")

    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(BINANCE_WS_URL) as ws:
                    logger.info("[binance_ws_listener] Подключено к WebSocket Binance")

                    ticker_dict = {}  # формат: { "BTCUSDT": { ...текущий тикер... }, ... }
                    last_process_time = time.time()

                    async for msg in ws:
                        now = time.time()

                        if msg.type == aiohttp.WSMsgType.TEXT:
                            try:
                                data = json.loads(msg.data)

                                if isinstance(data, list):
                                    for ticker in data:
                                        pair = ticker.get("s")
                                        if pair:
                                            ticker_dict[pair] = ticker  # сохраняем только последний тикер по паре
                                else:
                                    logger.warning("[binance_ws_listener] Получены данные не в виде списка")

                            except json.JSONDecodeError as e:
                                logger.warning(f"[binance_ws_listener] Ошибка декодирования JSON: {e}")
                            except Exception as e:
                                logger.exception(f"[binance_ws_listener] Ошибка при обработке сообщения: {e}")

                            if now - last_process_time >= 10:
                                if ticker_dict:
                                    logger.info(f"[binance_ws_listener] Обработка {len(ticker_dict)} тикеров")

                                    alerts = await get_cached_alerts_with_users(ttl=15)
                                
                                    all_pairs = set(ticker_dict.keys())
                                    historical_prices = await get_bulk_price_history(all_pairs)

                                    await process_tickers(
                                        list(ticker_dict.values()),  # только уникальные тикеры
                                        alerts,
                                        historical_prices
                                    )

                                    ticker_dict.clear()

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
