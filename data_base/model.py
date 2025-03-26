import datetime

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import text, ForeignKey, BigInteger, String, Float
from data_base.database import Base


class UserORM(Base):
    __tablename__ = 'user'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(nullable=True)
    create_at: Mapped[datetime.datetime] = mapped_column(server_default=text("TIMEZONE('utc', now())"))
    referrer: Mapped[int | None] = mapped_column(ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    bet: Mapped[float] = mapped_column(default=0.0)
    role: Mapped[str] = mapped_column(String, default="user")  # admin, user, brigadier
    check: Mapped[bool] = mapped_column(default=False)
