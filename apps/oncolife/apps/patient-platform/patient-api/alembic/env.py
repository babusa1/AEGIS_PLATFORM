"""
Alembic Environment Configuration
=================================

This module configures the Alembic migration environment.
It sets up database connections and model imports for autogenerate.
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
from db.base import Base
from db.patient_models import *  # noqa
from db.models.patient import *  # noqa
from db.models.conversation import *  # noqa
from db.models.education import *  # noqa
from db.models.medical import *  # noqa
from db.models.questions import *  # noqa
from db.models.referral import *  # noqa
from db.models.user import *  # noqa

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
    Supports both individual params and full URL.
    """
    # Check for full URL first
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    
    # Build from components
    host = os.getenv("PATIENT_DB_HOST", os.getenv("POSTGRES_HOST", "localhost"))
    port = os.getenv("PATIENT_DB_PORT", os.getenv("POSTGRES_PORT", "5432"))
    user = os.getenv("PATIENT_DB_USER", os.getenv("POSTGRES_USER", "oncolife_admin"))
    password = os.getenv("PATIENT_DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", "oncolife_dev_password"))
    database = os.getenv("PATIENT_DB_NAME", os.getenv("POSTGRES_PATIENT_DB", "oncolife_patient"))
    
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    
    This configures the context with just a URL and not an Engine,
    so we can generate SQL scripts without database connection.
    
    Usage: alembic upgrade head --sql
    """
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
    """
    Run migrations in 'online' mode.
    
    Creates an Engine and associates a connection with the context.
    """
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

