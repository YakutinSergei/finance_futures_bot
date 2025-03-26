import asyncio
import json
import aiohttp

BINANCE_WS_URL = "wss://fstream.binance.com/ws/!ticker@arr"

# Функция для получения данных о ценах с Binance через WebSocket
async def binance_ws_listener(latest_data=None):
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(BINANCE_WS_URL) as ws:
            async for msg in ws:
                data = json.loads(msg.data)  # Разбор JSON-данных
                print(data)
                for ticker in data:
                    pair = ticker["s"]  # Символ торговой пары
                    price = float(ticker["c"])  # Текущая цена

                    #latest_data[pair] = {"price": price}  # Сохранение данных о цене


asyncio.run(binance_ws_listener())