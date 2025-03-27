import json


# Пример функции для обработки данных
async def process_market_data(coinglass_data, binance_data):
    # Словарь для итоговых данных
    result = {}

    for pair, binance_values in binance_data.items():
        # Парсим название пары (например, 'PARTIUSDC' => 'PARTIUSDC')
        symbol = pair

        # Получаем цену из данных Coinglass
        if symbol[:3] in coinglass_data:  # Проверка, если такая пара есть в coinglass
            coinglass_price = float(coinglass_data[symbol[:3]].replace('$', '').replace('B', '').replace('T',
                                                                                                         '').replace('M',
                                                                                                         ''))  # Преобразуем цену в float
        else:
            coinglass_price = None  # Если нет данных по этой паре в coinglass

        # Результат для каждой пары
        pair_result = {}

        # Перебираем значения от 0 до 30
        for minute in range(30, -1, -1):
            # Получаем цену и открытый интерес для текущей минуты
            price, OI = binance_values.get(str(minute), ["-", "-"])

            # Если цена и OI доступны
            if price != "-" and price != "-" and OI != "-":
                price = float(price)
                OI = float(OI)
                percent_price_change = 0
                percent_OI_change = 0

                # Если есть значение для 0 минуты, считаем разницу
                if minute == 0 and coinglass_price is not None:
                    percent_price_change = ((price - coinglass_price) / coinglass_price) * 100
                    percent_OI_change = 0  # Для первого элемента отклонение от OI не рассчитываем

                elif minute != 0:
                    # Рассчитываем изменения в процентах от предыдущей минуты
                    prev_price = float(binance_values.get(str(minute - 1), [None, None])[0])
                    prev_OI = float(binance_values.get(str(minute - 1), [None, None])[1])

                    if prev_price and prev_price != "-":
                        percent_price_change = ((price - prev_price) / prev_price) * 100

                    if prev_OI and prev_OI != "-":
                        percent_OI_change = ((OI - prev_OI) / prev_OI) * 100

                pair_result[minute] = {
                    'price': price,
                    'percent_price': round(percent_price_change, 2),
                    'OI': OI,
                    'percent_OI': round(percent_OI_change, 2),
                }
            else:
                # Если данных нет, добавляем символ "-" для всех значений
                pair_result[minute] = {
                    'price': "-",
                    'percent_price': "-",
                    'OI': "-",
                    'percent_OI': "-",
                }

        # Добавляем результаты по паре в итоговый результат
        result[symbol] = pair_result

    return result
