"""
Alembic Environment Configuration - Doctor API
===============================================

This module configures the Alembic migration environment.
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add src to path for model imports
# For local: ../src, for Docker: /app (where src contents are mounted)
local_src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
docker_src_path = '/app'
if os.path.exists(local_src_path):
    sys.path.insert(0, local_src_path)
if os.path.exists(docker_src_path) and docker_src_path not in sys.path:
    sys.path.insert(0, docker_src_path)

# Import all models to ensure they're registered with Base.metadata
from db.base import DoctorBase as Base
from db.doctor_models import *  # noqa
from db.models.clinic import *  # noqa
from db.models.staff import *  # noqa
from db.models.analytics import *  # noqa

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model's MetaData object for 'autogenerate' support
target_metadata = Base.metadata


def get_url():
    """
    Get database URL from environment variables.
    """
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    
    # Support both DOCTOR_DB_* (docker-compose) and POSTGRES_* (legacy) env vars
    host = os.getenv("DOCTOR_DB_HOST", os.getenv("POSTGRES_HOST", "localhost"))
    port = os.getenv("DOCTOR_DB_PORT", os.getenv("POSTGRES_PORT", "5432"))
    user = os.getenv("DOCTOR_DB_USER", os.getenv("POSTGRES_USER", "oncolife_admin"))
    password = os.getenv("DOCTOR_DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", "oncolife_dev_password"))
    database = os.getenv("DOCTOR_DB_NAME", os.getenv("POSTGRES_DOCTOR_DB", "oncolife_doctor"))
    
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    
    connectable = engine_from_config(
        configuration,
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

