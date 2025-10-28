# alembic/env.py
from __future__ import annotations
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

from app.config import Settings
from app.models.base import Base

# IMPORTANTE: importar módulos que definen tablas

config = context.config

# Lee la URL desde Settings (.env) o variable de entorno
settings = Settings()
config.set_main_option(
    "sqlalchemy.url", os.getenv("DATABASE_URL", settings.DATABASE_URL)
)

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata objetivo
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
