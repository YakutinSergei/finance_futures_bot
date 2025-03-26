import asyncio
import json
import aiohttp
import redis.asyncio as redis

BINANCE_API_URL = "https://api.binance.com/api/v3/ticker/24hr"
REDIS_URL = "redis://localhost:6379/0"

async def binance_api_listener():
    redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

    async with aiohttp.ClientSession() as session:
        while True:
            async with session.get(BINANCE_API_URL) as response:
                data = await response.json()

                for ticker in data:
                    pair = ticker["symbol"]  # Название торговой пары
                    current_price = float(ticker["lastPrice"])  # Текущая цена

                    # Если текущая цена равна нулю, пропускаем эту пару
                    if current_price == 0:
                        continue

                    # Получаем текущее состояние цен в Redis
                    history = await redis_client.hget("crypto_prices", pair)
                    history = json.loads(history) if history else {}

                    # Сдвигаем все значения (от 30 до 1)
                    for i in range(30, 0, -1):
                        if str(i - 1) in history:
                            old_price = history[str(i - 1)][0]  # Цена i-1 минуту назад
                            if old_price != "-" and old_price != 0:  # Проверка на ноль
                                old_price = float(old_price)
                                price_change = ((old_price - current_price) / current_price) * 100
                                history[str(i)] = [old_price, round(price_change, 2)]
                        else:
                            history[str(i)] = ["-", "-"]

                    # Записываем новую цену в "0"
                    history["0"] = [current_price, 0]

                    # Сохраняем в Redis
                    await redis_client.hset("crypto_prices", pair, json.dumps(history))
            print('Я проверил')
            # Ожидаем 60 секунд перед следующим обновлением
            await asyncio.sleep(60)

    await redis_client.close()

asyncio.run(binance_api_listener())
