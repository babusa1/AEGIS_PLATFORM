from fastapi.testclient import TestClient
from aegis.api.main import app


def test_graphql_workflow_name():
    client = TestClient(app)
    query = '{ workflowName }'
    resp = client.post('/v1/graphql', json={'query': query})
    assert resp.status_code == 200
    data = resp.json()
    assert 'data' in data
    # Accept either form of field
    assert data['data'].get('workflowName') or data['data'].get('workflow_name')
