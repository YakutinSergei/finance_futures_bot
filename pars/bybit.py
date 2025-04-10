import asyncio
import aiohttp

BASE_URL = "https://api.bybit.com"


async def get_tickers(session):
    """Получает список торговых пар с ценами."""
    url = f"{BASE_URL}/v5/market/tickers"
    params = {"category": "linear"}  # Для фьючерсов, можно заменить на "spot"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status != 200:
                print(f"Ошибка: {response.status}, текст: {await response.text()}")
                return {}

            data = await response.json()

            if "result" not in data or "list" not in data["result"]:
                print(f"Пустой или некорректный ответ: {data}")
                return {}

            return {item["symbol"]: float(item["lastPrice"]) for item in data["result"]["list"]}

    except Exception as e:
        print(f"Ошибка при запросе тикеров: {e}")
        return {}


async def main():
    async with aiohttp.ClientSession() as session:
        tickers = await get_tickers(session)

        if not tickers:
            print("Не удалось получить тикеры. Завершаем выполнение.")
            return

        print("Данные по тикерам:", tickers)


if __name__ == "__main__":
    asyncio.run(main())
