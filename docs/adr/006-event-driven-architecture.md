# ADR-006: Event-Driven Architecture

## Status
Accepted

## Context
AEGIS needs to handle asynchronous workflows: data ingestion, agent execution, notifications, and integrations. We need an event streaming solution.

## Decision
**Apache Kafka (MSK in production) for event streaming**

### Why Kafka?

| Requirement | Kafka Solution |
|-------------|----------------|
| High throughput | Millions of events/sec |
| Durability | Replicated, persistent |
| Ordering | Partition-level ordering |
| Replay | Consumer can replay from any offset |
| Cloud-native | AWS MSK managed service |

### Event Topics

```
aegis.ingest.fhir          # FHIR bundle ingestion
aegis.ingest.hl7           # HL7 message ingestion
aegis.ingest.batch         # Batch file processing

aegis.entity.patient       # Patient created/updated
aegis.entity.encounter     # Encounter events
aegis.entity.claim         # Claim events

aegis.rcm.denial           # Denial detected
aegis.rcm.appeal           # Appeal created/submitted
aegis.rcm.outcome          # Appeal outcome

aegis.quality.gap          # Care gap identified
aegis.quality.closure      # Gap closed

aegis.agent.task           # Agent task queued
aegis.agent.result         # Agent task completed

aegis.audit.access         # Data access audit log
aegis.notification.alert   # User notifications
```

### Event Schema (CloudEvents)

```python
@dataclass
class AegisEvent:
    """Base event following CloudEvents spec."""
    id: str                      # UUID
    source: str                  # "aegis/ingestion/fhir"
    type: str                    # "aegis.entity.patient.created"
    time: datetime               # Event timestamp
    tenant_id: str               # Multi-tenant isolation
    data: dict                   # Event payload
    
    # Optional
    subject: str | None = None   # e.g., patient ID
    correlation_id: str | None = None  # Request tracing
```

### Consumer Groups

```python
CONSUMER_GROUPS = {
    "aegis-graph-writer": ["aegis.ingest.*"],
    "aegis-search-indexer": ["aegis.entity.*"],
    "aegis-agent-executor": ["aegis.agent.task"],
    "aegis-notification-sender": ["aegis.notification.*"],
    "aegis-audit-writer": ["aegis.audit.*"],
}
```

### Implementation

```python
# Producer
class EventPublisher:
    async def publish(self, topic: str, event: AegisEvent):
        await self.producer.send(
            topic=topic,
            key=event.tenant_id.encode(),  # Partition by tenant
            value=event.to_json().encode(),
        )

# Consumer
class EventConsumer:
    async def consume(self, topics: list[str], handler: Callable):
        async for message in self.consumer:
            event = AegisEvent.from_json(message.value)
            await handler(event)
```

## Consequences
- Decoupled services communicate via events
- Reliable message delivery with replay capability
- Easy to add new consumers without changing producers
- Audit trail through event log
- AWS MSK for production (managed Kafka)

## References
- [Apache Kafka](https://kafka.apache.org/)
- [AWS MSK](https://aws.amazon.com/msk/)
- [CloudEvents](https://cloudevents.io/)
