import asyncio
import json
import time

from datetime import datetime, timedelta, UTC
from typing import List

from sqlalchemy.orm import selectinload

from ConfigData.redis import redis_client
from data_base.database import engine_asinc, Base
from sqlalchemy import update, delete

from data_base.model import User, Alert, PriceData


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


async def clean_old_data():
    while True:
        async with async_session() as db:
            time_threshold = datetime.now(UTC) - timedelta(minutes=30)  # Теперь используем datetime.UTC
            await db.execute(delete(PriceData).where(PriceData.timestamp < time_threshold))
            await db.commit()
        await asyncio.sleep(60)  # Чистим каждую минуту


from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from data_base.database import async_session


async def add_user_with_alert(
        telegram_id: int,
        time_interval: int = 5,
        percent_up: float = 5.0,
        percent_down: float = 5.0,
        role: str = "free"
) -> str:
    """
    Добавляет нового пользователя и настройки оповещений по умолчанию

    :param telegram_id: ID пользователя в Telegram
    :param time_interval: Интервал отслеживания в минутах (по умолчанию 5)
    :param percent_up: Порог роста цены в % (по умолчанию 5)
    :param percent_down: Порог падения цены в % (по умолчанию 5)
    :param role: Роль пользователя (по умолчанию "free")
    :return: True если успешно, False если ошибка
    """
    async with async_session() as session:
        try:
            # Проверяем существующего пользователя
            existing_user = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            existing_user = existing_user.scalar_one_or_none()

            if existing_user is not None:
                return existing_user.language  # Возвращаем текущий язык пользователя

            # Создаем нового пользователя
            new_user = User(
                telegram_id=telegram_id,
                role=role,
            )
            session.add(new_user)
            await session.flush()

            # Создаем настройки оповещений
            new_alert = Alert(
                user_id=new_user.id,
                time_interval=time_interval,
                percent_up=percent_up,
                percent_down=percent_down
            )
            session.add(new_alert)

            await session.commit()
            return 'en'  # Возвращаем язык по умолчанию для нового пользователя

        except Exception as e:
            await session.rollback()
            print(f"Error in create_or_get_user: {e}")
            return 'en'  # В случае ошибки возвращаем язык по умолчанию


async def get_users_alerts():
    async with async_session() as session:
        try:
            current_date = datetime.now()

            # 1. Проверка и обновление просроченных подписок
            expired_users = await session.execute(
                select(User)
                .where(
                    (User.role == "premium") &
                    (User.subscription < current_date)
                )
            )

            for user in expired_users.scalars():
                user.role = "free"

            await session.flush()  # Частичное сохранение изменений

            # 2. Получение актуальных данных пользователей
            result = await session.execute(
                select(
                    User.telegram_id,
                    User.language,
                    User.role,
                    User.subscription,
                    Alert.time_interval,
                    Alert.percent_up,
                    Alert.percent_down
                ).join(Alert.user)
            )

            await session.commit()  # Финализация всех изменений

            return [
                {
                    'telegram_id': row.telegram_id,
                    'time_interval': row.time_interval,
                    'percent_up': row.percent_up,
                    'percent_down': row.percent_down,
                    'lang': row.language,
                    'subscription': row.subscription,
                    'role': row.role,
                }
                for row in result.all()
            ]

        except Exception as e:
            await session.rollback()
            print(f"Ошибка в get_users_alerts: {e}")
            return False


async def change_user_language(tg_id: int, language: str) -> bool:
    """
        Изменяет язык пользователя в базе данных.

        :param tg_id: Telegram ID пользователя
        :param language: Новый язык ('ru' или 'en')
        :return: True если обновление прошло успешно, False если пользователь не найден
        """
    async with async_session() as session:
        try:
            if language not in ('ru', 'en'):
                raise ValueError("Language must be either 'ru' or 'en'")

            stmt = (
                update(User)
                .where(User.telegram_id == tg_id)
                .values(language=language)
            )

            result = await session.execute(stmt)
            await session.commit()

        except Exception as e:
            await session.rollback()
            print(f"Ошибка в change_user_language: {e}")
            return False


async def update_growth_period(tg_id: int, new_period: int) -> bool:
    """
    Обновляет период роста для пользователя

    :param tg_id: Telegram ID пользователя
    :param new_period: Новый период роста (1-30 минут)
    :return: True если обновление прошло успешно, False если ошибка
    """
    # Проверяем что период в допустимом диапазоне
    if not (1 <= new_period <= 30):
        return False

    async with async_session() as session:
        try:
            # Находим пользователя
            user = await session.execute(
                select(User).where(User.telegram_id == tg_id)
            )
            user = user.scalar_one_or_none()

            if not user:
                return False

            # Находим его настройки оповещений
            alert = await session.execute(
                select(Alert).where(Alert.user_id == user.id)
            )
            alert = alert.scalar_one_or_none()

            if not alert:
                return False

            # Обновляем период роста
            alert.time_interval = new_period
            await session.commit()
            return True

        except Exception as e:
            await session.rollback()
            print(f"Error in update_growth_period: {e}")
            return False


'''Изменение процента роста'''


async def update_growth_percent(
        telegram_id: int,
        new_percent: float
) -> bool:
    """
    Улучшенная версия с обработкой ошибок
    """
    async with async_session() as session:
        try:
            if not (3.0 <= new_percent <= 100.0):
                raise ValueError("Invalid percentage value")

            stmt = (
                update(Alert)
                .where(Alert.user_id == User.id)
                .where(User.telegram_id == telegram_id)
                .values(percent_up=new_percent)
            )

            result = await session.execute(stmt)
            await session.commit()

            return result.rowcount > 0

        except Exception as e:
            await session.rollback()
            print(f"Error updating growth percent: {e}")
            return False


'''Изменение процента просадки'''


async def update_down_percent(
        telegram_id: int,
        new_percent: float
) -> bool:
    """
    Улучшенная версия с обработкой ошибок
    """
    async with async_session() as session:
        try:
            if not (3.0 <= new_percent <= 100.0):
                raise ValueError("Invalid percentage value")

            stmt = (
                update(Alert)
                .where(Alert.user_id == User.id)
                .where(User.telegram_id == telegram_id)
                .values(percent_down=new_percent)
            )

            result = await session.execute(stmt)
            await session.commit()

            return result.rowcount > 0

        except Exception as e:
            await session.rollback()
            print(f"Error updating growth percent: {e}")
            return False


'''получаем админов'''


async def get_admin_ids() -> list[int]:
    """
    Получает список telegram_id всех администраторов

    :param session: Асинхронная сессия SQLAlchemy
    :return: Список telegram_id администраторов
    """
    async with async_session() as session:
        try:
            stmt = select(User.telegram_id).where(User.role == "admin")
            result = await session.execute(stmt)
            admin_ids = result.scalars().all()
            return list(admin_ids)
        except Exception as e:
            await session.rollback()
            print(f"Error updating growth percent: {e}")
            return []


'''Изменение подписки'''


async def extend_subscription(
        telegram_id: int,
        months: int,
) -> str:
    """
    Продлевает подписку пользователя

    :param telegram_id: Telegram ID пользователя
    :param months: Количество месяцев для продления
    :param session: Асинхронная сессия SQLAlchemy
    :return: Дата окончания подписки в формате дд.мм.гг
    """
    async with async_session() as session:
        try:
            # Получаем текущие данные пользователя
            stmt = select(User).where(User.telegram_id == telegram_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                raise ValueError("Пользователь не найден")

            current_date = datetime.now()

            # Определяем новую дату окончания подписки
            if user.subscription < current_date:
                new_subscription_date = current_date + timedelta(days=30 * months)
            else:
                new_subscription_date = user.subscription + timedelta(days=30 * months)

            # Обновляем данные в базе
            update_stmt = (
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(
                    subscription=new_subscription_date,
                    role='premium' if user.role != 'admin' else 'admin'
                )
            )

            await session.execute(update_stmt)
            await session.commit()

            # Форматируем дату для возврата
            return new_subscription_date.strftime("%d.%m.%Y")

        except Exception as e:
            await session.rollback()
            print(f"Error updating growth percent: {e}")
            raise Exception(f"Ошибка при продлении подписки: {str(e)}")


'''Кэширование объектов'''
# Ключи для хранения данных и времени последнего обновления
ALERTS_KEY = "alerts_cache"
LAST_ALERTS_UPDATE_KEY = "last_alerts_update"


async def get_cached_alerts_with_users(ttl: int = 15) -> List[dict]:
    """
    Получает алерты из кэша, если не истёк TTL (время жизни).
    Если TTL истёк — обновляет из базы.
    """
    current_time = time.time()

    # Получаем время последнего обновления из Redis
    last_update = await redis_client.get(LAST_ALERTS_UPDATE_KEY)
    if last_update:
        # Конвертируем время последнего обновления из строки в float
        last_update = float(last_update)
    else:
        last_update = 0

    if current_time - last_update > ttl:
        print("🔄 Обновление кэша алертов из базы...")
        async with async_session() as session:
            result = await session.execute(
                select(Alert, User)  # Мы явно выбираем нужные сущности
                .join(User)
                .filter(User.role != 'free')  # Фильтруем пользователей с ролью, не равной 'free'
                .options(selectinload(Alert.user))  # Заранее подгружаем связь Alert.user
            )

            # Сформируем список словарей из результата запроса
            alerts = []
            for alert, user in result.all():
                alert_dict = alert.to_dict()  # Преобразуем Alert в словарь
                user_dict = {
                    "id": user.id,
                    "telegram_id": user.telegram_id,
                    "role": user.role,
                    "subscription": user.subscription.strftime('%Y-%m-%d %H:%M:%S'),
                    "language": user.language
                }
                alert_dict["user"] = user_dict  # Добавляем информацию о пользователе в alert_dict
                alerts.append(alert_dict)

            # Кэшируем данные и время последнего обновления
            await redis_client.set(ALERTS_KEY, json.dumps(alerts))
            await redis_client.set(LAST_ALERTS_UPDATE_KEY, current_time)

            # Устанавливаем TTL на кэшированные данные
            await redis_client.expire(ALERTS_KEY, ttl)
            await redis_client.expire(LAST_ALERTS_UPDATE_KEY, ttl)

    else:
        print("✅ Используем кэш алертов")
        cached_data = await redis_client.get(ALERTS_KEY)
        if cached_data:
            # Если кэш есть, преобразуем его обратно в список словарей
            alerts = json.loads(cached_data)
        else:
            alerts = []

    return alerts