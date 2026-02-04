"""GraphQL endpoint using Strawberry (prototype)

Exposes a simple GraphQL query to fetch the workflow name. This is a
small prototype to validate GraphQL integration (AppSync/managed GraphQL
can replace this later).
"""

import strawberry
from strawberry.asgi import GraphQL

from aegis.agents.workflows import HealthcareWorkflow


@strawberry.type
class Query:
    @strawberry.field
    def workflow_name(self) -> str:
        return HealthcareWorkflow().get_workflow_definition().get("name", "unknown")


schema = strawberry.Schema(query=Query)
graphql_app = GraphQL(schema)
