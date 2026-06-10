#!/bin/bash
# =============================================================================
# Initialize Multiple PostgreSQL Databases
# =============================================================================
# This script is used by docker-compose to create multiple databases
# on first run.
#
# Usage: Automatically run by PostgreSQL container entrypoint
# =============================================================================

set -e
set -u

create_database() {
    local database=$1
    echo "Creating database '$database'..."
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
        CREATE DATABASE $database;
        GRANT ALL PRIVILEGES ON DATABASE $database TO $POSTGRES_USER;
EOSQL
    echo "Database '$database' created successfully!"
}

# Main
if [ -n "$POSTGRES_MULTIPLE_DATABASES" ]; then
    echo "Creating multiple databases: $POSTGRES_MULTIPLE_DATABASES"
    for db in $(echo $POSTGRES_MULTIPLE_DATABASES | tr ',' ' '); do
        create_database $db
    done
    echo "All databases created!"
fi

