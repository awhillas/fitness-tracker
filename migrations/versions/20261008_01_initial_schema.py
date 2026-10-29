"""Create the fitness and eating tables, adopting an existing SQLite database.

Revision ID: 20261008_01
Revises:
Create Date: 2026-10-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text
from sqlalchemy.exc import NoInspectionAvailable

revision: str = "20261008_01"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(name: str) -> bool:
    try:
        return inspect(op.get_bind()).has_table(name)
    except NoInspectionAvailable:
        return False


def _ensure_index(table_name: str, index_name: str, columns: list[str]) -> None:
    try:
        indexes = {index["name"] for index in inspect(op.get_bind()).get_indexes(table_name)}
    except NoInspectionAvailable:
        indexes = set()
    if index_name not in indexes:
        op.create_index(index_name, table_name, columns)


def upgrade() -> None:
    if not _has_table("weighings"):
        op.create_table(
            "weighings",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("date", sa.Text(), nullable=False),
            sa.Column("weight_kg", sa.REAL(), nullable=False),
            sa.Column(
                "created_at", sa.Text(), server_default=text("(datetime('now'))"), nullable=False
            ),
            sa.Column("updated_at", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    _ensure_index("weighings", "idx_weighings_date", ["date"])

    if not _has_table("eating_targets"):
        op.create_table(
            "eating_targets",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("username", sa.Text(), nullable=False),
            sa.Column("start_date", sa.Text(), nullable=False),
            sa.Column("kcal_target", sa.REAL(), nullable=False),
            sa.Column("protein_target_g", sa.REAL(), nullable=False),
            sa.Column(
                "created_at", sa.Text(), server_default=text("(datetime('now'))"), nullable=False
            ),
            sa.CheckConstraint("kcal_target > 0", name="ck_eating_targets_kcal_positive"),
            sa.CheckConstraint("protein_target_g > 0", name="ck_eating_targets_protein_positive"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("username", "start_date"),
        )
    _ensure_index(
        "eating_targets",
        "idx_eating_targets_user_date",
        ["username", "start_date"],
    )

    if not _has_table("foods"):
        op.create_table(
            "foods",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("brand", sa.Text(), nullable=True),
            sa.Column("source_type", sa.Text(), nullable=False),
            sa.Column("source_url", sa.Text(), nullable=True),
            sa.Column("basis_unit", sa.Text(), nullable=False),
            sa.Column("energy_kcal", sa.REAL(), nullable=True),
            sa.Column("protein_g", sa.REAL(), nullable=True),
            sa.Column("total_fat_g", sa.REAL(), nullable=True),
            sa.Column("saturated_fat_g", sa.REAL(), nullable=True),
            sa.Column("trans_fat_g", sa.REAL(), nullable=True),
            sa.Column("carbohydrate_g", sa.REAL(), nullable=True),
            sa.Column("sugars_g", sa.REAL(), nullable=True),
            sa.Column("dietary_fibre_g", sa.REAL(), nullable=True),
            sa.Column("sodium_g", sa.REAL(), nullable=True),
            sa.Column("salt_g", sa.REAL(), nullable=True),
            sa.Column("nutrients_json", sa.Text(), server_default=text("'{}'"), nullable=False),
            sa.Column(
                "created_at", sa.Text(), server_default=text("(datetime('now'))"), nullable=False
            ),
            sa.Column("updated_at", sa.Text(), nullable=True),
            sa.CheckConstraint(
                "source_type IN ('natural', 'product')", name="ck_foods_source_type"
            ),
            sa.CheckConstraint("basis_unit IN ('g', 'ml')", name="ck_foods_basis_unit"),
            sa.CheckConstraint("energy_kcal >= 0", name="ck_foods_energy_nonnegative"),
            sa.CheckConstraint("protein_g >= 0", name="ck_foods_protein_nonnegative"),
            sa.CheckConstraint(
                "total_fat_g IS NULL OR total_fat_g >= 0", name="ck_foods_total_fat_nonnegative"
            ),
            sa.CheckConstraint(
                "saturated_fat_g IS NULL OR saturated_fat_g >= 0",
                name="ck_foods_saturated_fat_nonnegative",
            ),
            sa.CheckConstraint(
                "trans_fat_g IS NULL OR trans_fat_g >= 0", name="ck_foods_trans_fat_nonnegative"
            ),
            sa.CheckConstraint(
                "carbohydrate_g IS NULL OR carbohydrate_g >= 0",
                name="ck_foods_carbohydrate_nonnegative",
            ),
            sa.CheckConstraint(
                "sugars_g IS NULL OR sugars_g >= 0", name="ck_foods_sugars_nonnegative"
            ),
            sa.CheckConstraint(
                "dietary_fibre_g IS NULL OR dietary_fibre_g >= 0",
                name="ck_foods_fibre_nonnegative",
            ),
            sa.CheckConstraint(
                "sodium_g IS NULL OR sodium_g >= 0", name="ck_foods_sodium_nonnegative"
            ),
            sa.CheckConstraint("salt_g IS NULL OR salt_g >= 0", name="ck_foods_salt_nonnegative"),
            sa.CheckConstraint(
                "source_type = 'natural' OR source_url IS NOT NULL", name="ck_foods_source_url"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("source_url"),
        )
    _ensure_index("foods", "idx_foods_name", ["name"])


def downgrade() -> None:
    op.drop_table("foods")
    op.drop_table("eating_targets")
    op.drop_table("weighings")
