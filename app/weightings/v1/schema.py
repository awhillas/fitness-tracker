from sqlalchemy import REAL, Index, Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Weighing(Base):
    __tablename__ = "weighings"
    __table_args__ = (Index("idx_weighings_date", "date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[str] = mapped_column(Text, nullable=False)
    weight_kg: Mapped[float] = mapped_column(REAL, nullable=False)
    created_at: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("(datetime('now'))")
    )
    updated_at: Mapped[str | None] = mapped_column(Text)
