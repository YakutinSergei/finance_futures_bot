import asyncio
import logging
import sys

from aiogram import Bot
from aiogram.types import BotCommand
from environs import Env

from create_bot import bot, dp
from data_base.orm import create_tables, clean_old_data
from handlers import start
from pars.binance import binance_ws_listener
# from pars.function import monitor_prices

env = Env()
env.read_env()

# === Настройка логирования ===
LOG_FILENAME = "bot.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILENAME, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# === Обработка необработанных исключений ===
def handle_exception(loop, context):
    msg = context.get("exception", context["message"])
    logger.error(f"Caught exception: {msg}", exc_info=True)

async def set_main_menu(bot: Bot):
    main_menu_commands = [
        BotCommand(command='/start', description='Перезапустить бота')]
    await bot.set_my_commands(main_menu_commands)

async def main():
    logger.info('Starting bot...')

    # Подключаем базу данных
    await create_tables()

    # Подключаем роутеры
    dp.include_router(start.router)

    # Удаляем вебхук и настраиваем меню
    await bot.delete_webhook(drop_pending_updates=True)
    dp.startup.register(set_main_menu)

    # Запускаем фоновые задачи
    asyncio.create_task(binance_ws_listener())
    # asyncio.create_task(clean_old_data())
    # asyncio.create_task(monitor_prices())

    # Запускаем Telegram-бота
    await dp.start_polling(bot)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)
    try:
        loop.run_until_complete(main())
    except Exception as e:
        logger.exception(f"Unhandled exception in main: {e}")
