import asyncio
import logging

from aiogram import Bot
from aiogram.types import BotCommand
from environs import Env

from create_bot import bot, dp
from handlers import start
from pars.Coinglass import get_coinglass
from pars.binance import binance_api_listener
from pars.function import process_market_data

env = Env()
env.read_env()

# Инициализируем логгер
logger = logging.getLogger(__name__)

async def set_main_menu(bot: Bot):
    main_menu_commands = [
        BotCommand(command='/start', description='Перезапустить бота')]
    await bot.set_my_commands(main_menu_commands)


async def periodic_tasks():
    """Запускает get_coinglass, затем binance_api_listener, с интервалом в 1 минуту."""
    while True:
        try:
            coinglass_data = await get_coinglass()  # Сначала получаем данные Coinglass

            binance_data = await binance_api_listener()  # Затем получаем данные Binance
            print(coinglass_data)

            result = await process_market_data(coinglass_data, binance_data)
            #print(result)  # Выводим результаты на экран

            await asyncio.sleep(60)  # Ждем 60 секунд перед следующим запуском


        except Exception as e:
            logger.error(f"Ошибка в фоновых задачах: {e}")


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(filename)s:%(lineno)d #%(levelname)-8s '
               '[%(asctime)s] - %(name)s - %(message)s')

    logger.info('Starting bot')

    dp.include_router(start.router)

    await bot.delete_webhook(drop_pending_updates=True)
    dp.startup.register(set_main_menu)

    # Запускаем фоновые задачи
    asyncio.create_task(periodic_tasks())

    # Запускаем Telegram-бота
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
