from sqlalchemy.ext.asyncio import AsyncSession

from data_base.database import async_session, engine_asinc, Base
from sqlalchemy import select, func, update, extract, delete
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from data_base.model import UserORM, ObjectORM, WorkORM, ObjectUserORM


async def create_tables():
    # Начинаем асинхронную транзакцию с базой данных
    async with engine_asinc.begin() as conn:
        existing_tables = await conn.run_sync(Base.metadata.reflect)
        print(Base.metadata)
        # Проверяем, есть ли информация о существующих таблицах
        if existing_tables is not None:
            for table_name, table in Base.metadata.tables.items():
                # Проверяем, есть ли текущая таблица в списке существующих таблиц
                if table_name not in existing_tables:
                    await conn.run_sync(table.create)
        else:
            # Если информация о существующих таблицах отсутствует,
            # создаем все таблицы из метаданных
            await conn.run_sync(Base.metadata.create_all)