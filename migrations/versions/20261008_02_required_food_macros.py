"""Require energy and protein values on each food record.

Revision ID: 20261008_02
Revises: 20261008_01
Create Date: 2026-10-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20261008_02"
down_revision: str | Sequence[str] | None = "20261008_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FOOD_CHECKS = (
    sa.CheckConstraint("source_type IN ('natural', 'product')", name="ck_foods_source_type"),
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
    sa.CheckConstraint("sugars_g IS NULL OR sugars_g >= 0", name="ck_foods_sugars_nonnegative"),
    sa.CheckConstraint(
        "dietary_fibre_g IS NULL OR dietary_fibre_g >= 0",
        name="ck_foods_fibre_nonnegative",
    ),
    sa.CheckConstraint("sodium_g IS NULL OR sodium_g >= 0", name="ck_foods_sodium_nonnegative"),
    sa.CheckConstraint("salt_g IS NULL OR salt_g >= 0", name="ck_foods_salt_nonnegative"),
    sa.CheckConstraint(
        "source_type = 'natural' OR source_url IS NOT NULL", name="ck_foods_source_url"
    ),
)


def _missing_food_checks() -> tuple[sa.CheckConstraint, ...]:
    existing_names = {
        constraint["name"]
        for constraint in inspect(op.get_bind()).get_check_constraints("foods")
        if constraint["name"]
    }
    return tuple(check for check in FOOD_CHECKS if check.name not in existing_names)


def upgrade() -> None:
    columns = {column["name"]: column for column in inspect(op.get_bind()).get_columns("foods")}
    required_columns = [name for name in ("energy_kcal", "protein_g") if columns[name]["nullable"]]
    if not required_columns:
        return

    null_count = (
        op.get_bind()
        .execute(
            sa.text("SELECT COUNT(*) FROM foods WHERE energy_kcal IS NULL OR protein_g IS NULL")
        )
        .scalar_one()
    )
    if null_count:
        raise RuntimeError(
            "Cannot require food energy/protein until every existing food row has both values."
        )

    with op.batch_alter_table("foods", table_args=_missing_food_checks()) as batch_op:
        for name in required_columns:
            batch_op.alter_column(
                name,
                existing_type=sa.REAL(),
                existing_nullable=True,
                nullable=False,
            )


def downgrade() -> None:
    columns = {column["name"]: column for column in inspect(op.get_bind()).get_columns("foods")}
    nullable_columns = [
        name for name in ("energy_kcal", "protein_g") if not columns[name]["nullable"]
    ]
    if not nullable_columns:
        return
    with op.batch_alter_table("foods", table_args=_missing_food_checks()) as batch_op:
        for name in nullable_columns:
            batch_op.alter_column(
                name,
                existing_type=sa.REAL(),
                existing_nullable=False,
                nullable=True,
            )
