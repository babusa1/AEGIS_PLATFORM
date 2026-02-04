import pytest
import asyncio

from aegis.mcp.adapter import MCPAdapter


@pytest.mark.asyncio
async def test_mcp_adapter_connect_and_send():
    adapter = MCPAdapter(url="http://localhost:12345")
    connected = await adapter.connect()
    assert connected is True

    resp = await adapter.send({"cmd": "ping"})
    assert isinstance(resp, dict)
    assert resp.get("status") == "ok"

    await adapter.close()
    assert adapter._connected is False
