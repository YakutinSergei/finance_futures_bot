import datetime

from sqlalchemy.orm import Mapped, mapped_column, relationship
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

# Модель данных по торговым парам
class PriceData(Base):
    __tablename__ = "price_data"
    id: Mapped[int] = mapped_column(primary_key=True)
    pair: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[float] = mapped_column(nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())  # Автоматическое время записи

