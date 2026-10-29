from logging.config import fileConfig

from alembic import context
from sqlalchemy import URL, create_engine, pool

from app.config import settings
from app.db import Base, configure_sqlite_engine
from app.eating.v1.schema import EatingTarget, Food  # noqa: F401
from app.weightings.v1.schema import Weighing  # noqa: F401

config = context.config
if config.config_file_name and config.get_section("loggers"):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_object(object_, name, type_, reflected, compare_to):
    # SQLite reports INTEGER PRIMARY KEY columns as nullable during reflection.
    if (
        type_ == "column"
        and name == "id"
        and not reflected
        and compare_to is not None
        and getattr(object_, "primary_key", False)
    ):
        return False
    return True


def database_url() -> str:
    return URL.create("sqlite", database=str(settings.db_path)).render_as_string(
        hide_password=False
    )


def run_migrations_offline() -> None:
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(database_url(), poolclass=pool.NullPool)
    configure_sqlite_engine(connectable)
    try:
        with connectable.begin() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                include_object=include_object,
                render_as_batch=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
