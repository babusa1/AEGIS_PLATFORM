#!/bin/bash
# AEGIS Kafka Topic Creation Script
# Run this after Kafka is up: docker exec aegis-kafka /scripts/create-topics.sh

KAFKA_BOOTSTRAP="localhost:9092"

echo "Creating AEGIS Kafka topics..."

# ===========================================
# FHIR Ingestion Topics
# ===========================================
kafka-topics --create --if-not-exists \
  --bootstrap-server $KAFKA_BOOTSTRAP \
  --topic fhir.raw \
  --partitions 6 \
  --replication-factor 1 \
  --config retention.ms=604800000

kafka-topics --create --if-not-exists \
  --bootstrap-server $KAFKA_BOOTSTRAP \
  --topic fhir.validated \
  --partitions 6 \
  --replication-factor 1 \
  --config retention.ms=604800000

kafka-topics --create --if-not-exists \
  --bootstrap-server $KAFKA_BOOTSTRAP \
  --topic fhir.dlq \
  --partitions 3 \
  --replication-factor 1 \
  --config retention.ms=2592000000

# ===========================================
# HL7v2 Ingestion Topics
# ===========================================
kafka-topics --create --if-not-exists \
  --bootstrap-server $KAFKA_BOOTSTRAP \
  --topic hl7.raw \
  --partitions 6 \
  --replication-factor 1 \
  --config retention.ms=604800000

kafka-topics --create --if-not-exists \
  --bootstrap-server $KAFKA_BOOTSTRAP \
  --topic hl7.validated \
  --partitions 6 \
  --replication-factor 1 \
  --config retention.ms=604800000

kafka-topics --create --if-not-exists \
  --bootstrap-server $KAFKA_BOOTSTRAP \
  --topic hl7.dlq \
  --partitions 3 \
  --replication-factor 1 \
  --config retention.ms=2592000000

# ===========================================
# X12 Claims Topics
# ===========================================
kafka-topics --create --if-not-exists \
  --bootstrap-server $KAFKA_BOOTSTRAP \
  --topic x12.claims.raw \
  --partitions 6 \
  --replication-factor 1 \
  --config retention.ms=604800000

kafka-topics --create --if-not-exists \
  --bootstrap-server $KAFKA_BOOTSTRAP \
  --topic x12.claims.validated \
  --partitions 6 \
  --replication-factor 1 \
  --config retention.ms=604800000

kafka-topics --create --if-not-exists \
  --bootstrap-server $KAFKA_BOOTSTRAP \
  --topic x12.remit.raw \
  --partitions 3 \
  --replication-factor 1 \
  --config retention.ms=604800000

# ===========================================
# Device/Wearable Topics
# ===========================================
kafka-topics --create --if-not-exists \
  --bootstrap-server $KAFKA_BOOTSTRAP \
  --topic devices.raw \
  --partitions 6 \
  --replication-factor 1 \
  --config retention.ms=604800000

kafka-topics --create --if-not-exists \
  --bootstrap-server $KAFKA_BOOTSTRAP \
  --topic devices.validated \
  --partitions 6 \
  --replication-factor 1 \
  --config retention.ms=604800000

# ===========================================
# Graph Events (CDC-style)
# ===========================================
kafka-topics --create --if-not-exists \
  --bootstrap-server $KAFKA_BOOTSTRAP \
  --topic graph.events \
  --partitions 12 \
  --replication-factor 1 \
  --config retention.ms=604800000

# ===========================================
# Audit Events
# ===========================================
kafka-topics --create --if-not-exists \
  --bootstrap-server $KAFKA_BOOTSTRAP \
  --topic audit.events \
  --partitions 6 \
  --replication-factor 1 \
  --config retention.ms=2592000000

echo "Topics created successfully!"
kafka-topics --list --bootstrap-server $KAFKA_BOOTSTRAP
