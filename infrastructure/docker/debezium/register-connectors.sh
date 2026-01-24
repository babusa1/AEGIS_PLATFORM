#!/bin/bash
# Register Debezium connectors for CDC

CONNECT_URL=${CONNECT_URL:-http://localhost:8083}

# Wait for Kafka Connect to be ready
echo "Waiting for Kafka Connect..."
until curl -s $CONNECT_URL/connectors > /dev/null 2>&1; do
  sleep 5
done
echo "Kafka Connect is ready"

# Register PostgreSQL connector
curl -X POST $CONNECT_URL/connectors \
  -H "Content-Type: application/json" \
  -d '{
    "name": "aegis-postgres-connector",
    "config": {
      "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
      "database.hostname": "postgres",
      "database.port": "5432",
      "database.user": "aegis",
      "database.password": "${POSTGRES_PASSWORD}",
      "database.dbname": "aegis",
      "database.server.name": "aegis-db",
      "topic.prefix": "aegis",
      "table.include.list": "public.patients,public.encounters,public.observations",
      "plugin.name": "pgoutput",
      "slot.name": "aegis_slot",
      "publication.name": "aegis_publication",
      "transforms": "unwrap",
      "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState"
    }
  }'

echo "PostgreSQL connector registered"
