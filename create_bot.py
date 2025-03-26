from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import SimpleEventIsolation

from ConfigData.config import Config, load_config

# Загружаем конфиг в переменную config
config: Config = load_config()

# Инициализируем бот и диспетчер
bot: Bot = Bot(token=config.tg_bot.token,
               default=DefaultBotProperties(parse_mode="HTML"))

dp: Dispatcher = Dispatcher(events_isolation=SimpleEventIsolation())