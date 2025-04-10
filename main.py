import asyncio
import logging

from aiogram import Bot
from aiogram.types import BotCommand
from environs import Env

from create_bot import bot, dp
from data_base.orm import create_tables, clean_old_data
from handlers import start
from pars.binance import binance_ws_listener
from pars.function import monitor_prices

env = Env()
env.read_env()


# Инициализируем логгер
logger = logging.getLogger(__name__)

async def set_main_menu(bot: Bot):
    main_menu_commands = [
        BotCommand(command='/start', description='Перезапустить бота')]
    await bot.set_my_commands(main_menu_commands)

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(filename)s:%(lineno)d #%(levelname)-8s '
               '[%(asctime)s] - %(name)s - %(message)s')

    logger.info('Starting bot')
    '''Подключаем базу данных'''
    await create_tables()  # Создание таблиц

    dp.include_router(start.router)

    await bot.delete_webhook(drop_pending_updates=True)
    dp.startup.register(set_main_menu)

    # # Запускаем фоновые задачи
    asyncio.create_task(binance_ws_listener())
    asyncio.create_task(clean_old_data())
    asyncio.create_task(monitor_prices())


    # Запускаем Telegram-бота
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
