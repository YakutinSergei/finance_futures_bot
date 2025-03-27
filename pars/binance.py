import asyncio
import json
import aiohttp

BINANCE_API_URL = "https://api.binance.com/api/v3/ticker/24hr"

async def binance_api_listener():
    crypto_data = {}  # Словарь для хранения данных

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(BINANCE_API_URL) as response:
                if response.status != 200:
                    print(f"Ошибка API Binance: {response.status}")
                    return []

                data = await response.json()

                for ticker in data:
                    pair = ticker["symbol"]  # Название торговой пары
                    current_price = float(ticker["lastPrice"])  # Текущая цена

                    # Пропускаем нулевые цены
                    if current_price == 0:
                        continue

                    # Создаём словарь для хранения 30 минутных изменений
                    history = {}

                    # Заполняем исторические данные заглушками "-"
                    for i in range(30, 0, -1):
                        history[str(i)] = ["-", "-"]

                    # Записываем текущую цену в "0"
                    history["0"] = [current_price, 0]

                    # Добавляем данные в общий словарь
                    crypto_data[pair] = history

        except Exception as e:
            print(f"Ошибка при получении данных с Binance: {e}")
            return []

    return crypto_data  # Возвращаем собранные данные


