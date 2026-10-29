from sqlalchemy import (
    REAL,
    CheckConstraint,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class EatingTarget(Base):
    __tablename__ = "eating_targets"
    __table_args__ = (
        UniqueConstraint("username", "start_date"),
        Index("idx_eating_targets_user_date", "username", "start_date"),
        CheckConstraint("kcal_target > 0", name="ck_eating_targets_kcal_positive"),
        CheckConstraint("protein_target_g > 0", name="ck_eating_targets_protein_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(Text, nullable=False)
    start_date: Mapped[str] = mapped_column(Text, nullable=False)
    kcal_target: Mapped[float] = mapped_column(REAL, nullable=False)
    protein_target_g: Mapped[float] = mapped_column(REAL, nullable=False)
    created_at: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("(datetime('now'))")
    )


class Food(Base):
    __tablename__ = "foods"
    __table_args__ = (
        Index("idx_foods_name", "name"),
        CheckConstraint("source_type IN ('natural', 'product')", name="ck_foods_source_type"),
        CheckConstraint("basis_unit IN ('g', 'ml')", name="ck_foods_basis_unit"),
        CheckConstraint("energy_kcal >= 0", name="ck_foods_energy_nonnegative"),
        CheckConstraint("protein_g >= 0", name="ck_foods_protein_nonnegative"),
        CheckConstraint(
            "total_fat_g IS NULL OR total_fat_g >= 0", name="ck_foods_total_fat_nonnegative"
        ),
        CheckConstraint(
            "saturated_fat_g IS NULL OR saturated_fat_g >= 0",
            name="ck_foods_saturated_fat_nonnegative",
        ),
        CheckConstraint(
            "trans_fat_g IS NULL OR trans_fat_g >= 0", name="ck_foods_trans_fat_nonnegative"
        ),
        CheckConstraint(
            "carbohydrate_g IS NULL OR carbohydrate_g >= 0",
            name="ck_foods_carbohydrate_nonnegative",
        ),
        CheckConstraint("sugars_g IS NULL OR sugars_g >= 0", name="ck_foods_sugars_nonnegative"),
        CheckConstraint(
            "dietary_fibre_g IS NULL OR dietary_fibre_g >= 0",
            name="ck_foods_fibre_nonnegative",
        ),
        CheckConstraint("sodium_g IS NULL OR sodium_g >= 0", name="ck_foods_sodium_nonnegative"),
        CheckConstraint("salt_g IS NULL OR salt_g >= 0", name="ck_foods_salt_nonnegative"),
        CheckConstraint(
            "source_type = 'natural' OR source_url IS NOT NULL", name="ck_foods_source_url"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    brand: Mapped[str | None] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, unique=True)
    basis_unit: Mapped[str] = mapped_column(Text, nullable=False)
    energy_kcal: Mapped[float] = mapped_column(REAL, nullable=False)
    protein_g: Mapped[float] = mapped_column(REAL, nullable=False)
    total_fat_g: Mapped[float | None] = mapped_column(REAL)
    saturated_fat_g: Mapped[float | None] = mapped_column(REAL)
    trans_fat_g: Mapped[float | None] = mapped_column(REAL)
    carbohydrate_g: Mapped[float | None] = mapped_column(REAL)
    sugars_g: Mapped[float | None] = mapped_column(REAL)
    dietary_fibre_g: Mapped[float | None] = mapped_column(REAL)
    sodium_g: Mapped[float | None] = mapped_column(REAL)
    salt_g: Mapped[float | None] = mapped_column(REAL)
    nutrients_json: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'{}'"))
    created_at: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("(datetime('now'))")
    )
    updated_at: Mapped[str | None] = mapped_column(Text)
