import datetime

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.future import select
from sqlalchemy import ForeignKey, BigInteger, String, Float, DateTime, func
from data_base.database import Base


# Модель пользователя
class User(Base):
    """Модель пользователя системы. Хранит основную информацию о пользователе телеграм."""
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String, default="free")  # free, premium, admin,
    subscription: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    language: Mapped[str] = mapped_column(String, default="en")
    alerts = relationship("Alert", back_populates="user")


# Модель для хранения настроек оповещений
class Alert(Base):
    """Настройки оповещений пользователей."""
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    time_interval: Mapped[int] = mapped_column(nullable=False, default=5)  # Время отслеживания в минутах (от 1 до 30)
    percent_up: Mapped[float] = mapped_column(nullable=False, default= 5)  # Процент роста цены
    percent_down: Mapped[float] = mapped_column(nullable=False, default= 5)  # Процент падения цены
    user = relationship("User", back_populates="alerts")

    def to_dict(self):
        """Преобразует объект Alert в словарь для сериализации."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "time_interval": self.time_interval,
            "percent_up": self.percent_up,
            "percent_down": self.percent_down,
            "user": {
                "id": self.user.id,
                "telegram_id": self.user.telegram_id,
                "role": self.user.role,
                "subscription": self.user.subscription.strftime('%Y-%m-%d %H:%M:%S'),  # Преобразуем datetime в строку
                "language": self.user.language
            }
        }

    @classmethod
    async def from_dict(cls, alert_dict: dict, session):
        """Создает объект Alert из словаря."""
        user_data = alert_dict.get("user", {})

        # Используем асинхронный select для загрузки пользователя
        result = await session.execute(
            select(User).filter_by(id=user_data.get("id"))
        )
        user = result.scalars().first()

        if not user:
            raise ValueError("User not found for the alert.")

        return cls(
            id=alert_dict.get("id"),
            user_id=user.id,
            time_interval=alert_dict.get("time_interval"),
            percent_up=alert_dict.get("percent_up"),
            percent_down=alert_dict.get("percent_down"),
            user=user  # Связываем с пользователем
        )

# Модель данных по торговым парам
class PriceData(Base):
    __tablename__ = "price_data"
    id: Mapped[int] = mapped_column(primary_key=True)
    pair: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[float] = mapped_column(nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())  # Автоматическое время записи

