"""
Chat/Symptom Checker Endpoint Tests
===================================

Tests for the /api/v1/chat endpoints.
"""

import pytest
from fastapi.testclient import TestClient


class TestChatSessionEndpoints:
    """Tests for chat session management."""

    @pytest.mark.unit
    def test_get_or_create_today_session(self, client: TestClient):
        """Should get or create today's session."""
        response = client.get("/api/v1/chat/session/today")
        
        assert response.status_code == 200
        data = response.json()
        assert "chat_uuid" in data
        assert "conversation_state" in data
        assert "messages" in data
        assert "is_new_session" in data

    @pytest.mark.unit
    def test_session_with_timezone(self, client: TestClient):
        """Should accept timezone parameter."""
        response = client.get("/api/v1/chat/session/today?timezone=America/New_York")
        
        assert response.status_code == 200

    @pytest.mark.unit
    def test_force_new_session(self, client: TestClient):
        """Should force create a new session."""
        # Get initial session
        initial = client.get("/api/v1/chat/session/today")
        initial_uuid = initial.json()["chat_uuid"]
        
        # Force new session
        response = client.post("/api/v1/chat/session/new")
        
        assert response.status_code == 201
        data = response.json()
        assert data["is_new_session"] == True
        # New session should have different UUID
        assert data["chat_uuid"] != initial_uuid


class TestChatMessageEndpoints:
    """Tests for chat message operations."""

    @pytest.mark.unit
    def test_get_full_chat(self, client: TestClient):
        """Should get full chat with messages."""
        # First create a session
        session = client.get("/api/v1/chat/session/today")
        chat_uuid = session.json()["chat_uuid"]
        
        # Get full chat
        response = client.get(f"/api/v1/chat/{chat_uuid}/full")
        
        assert response.status_code == 200

    @pytest.mark.unit
    def test_get_chat_state(self, client: TestClient):
        """Should get chat state without full messages."""
        # Create session
        session = client.get("/api/v1/chat/session/today")
        chat_uuid = session.json()["chat_uuid"]
        
        # Get state
        response = client.get(f"/api/v1/chat/{chat_uuid}/state")
        
        assert response.status_code == 200
        data = response.json()
        assert "conversation_state" in data

    @pytest.mark.unit
    def test_update_overall_feeling(self, client: TestClient):
        """Should update chat overall feeling."""
        # Create session
        session = client.get("/api/v1/chat/session/today")
        chat_uuid = session.json()["chat_uuid"]
        
        # Update feeling
        response = client.post(
            f"/api/v1/chat/{chat_uuid}/feeling",
            json={"feeling": "Happy"}
        )
        
        assert response.status_code == 204

    @pytest.mark.unit
    def test_delete_chat(self, client: TestClient):
        """Should delete a chat."""
        # Create session
        session = client.get("/api/v1/chat/session/today")
        chat_uuid = session.json()["chat_uuid"]
        
        # Delete
        response = client.delete(f"/api/v1/chat/{chat_uuid}")
        
        assert response.status_code == 204

    @pytest.mark.unit
    def test_chat_not_found(self, client: TestClient, random_uuid: str):
        """Should return 404 for non-existent chat."""
        response = client.get(f"/api/v1/chat/{random_uuid}/full")
        
        assert response.status_code == 404


class TestChatAuthentication:
    """Tests for chat authentication requirements."""

    @pytest.mark.auth
    def test_chat_session_requires_auth(self, unauthenticated_client: TestClient):
        """Chat endpoints should require authentication."""
        response = unauthenticated_client.get("/api/v1/chat/session/today")
        
        assert response.status_code in [401, 403]

