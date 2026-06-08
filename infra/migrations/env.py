"""Alembic environment (async, autogenerate-ready).

Run from apps/api (where alembic.ini lives):  uv run alembic revision --autogenerate -m "init"
Then:  uv run alembic upgrade head

The initial migration is generated via autogenerate (needs a Python toolchain). The integration
tests build the schema directly from the ORM metadata, so they do not depend on a committed migration.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# Import the app's metadata + settings (prepend_sys_path=. makes `app` importable).
from app.db import Base
from app.models import *  # noqa: F401,F403  (register all tables on Base.metadata)
from app.settings import settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection) -> None:  # type: ignore[no-untyped-def]
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
