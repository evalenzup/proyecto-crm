import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# cargar tu settings si usas Pydantic
from app.config import Settings
from app.models.base import Base  # aquí está tu metadata con todos los modelos

# this is the Alembic Config object
config = context.config

# Interpretar sqlalchemy.url de config o de Settings
settings = Settings()                     # lee .env
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Setup logging
fileConfig(config.config_file_name)

# metadata con todas las tablas
target_metadata = Base.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()