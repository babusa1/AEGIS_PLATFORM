"""
Questions Endpoint Tests
========================

Tests for the /api/v1/questions endpoints (Questions to Ask Doctor feature).
"""

import pytest
from fastapi.testclient import TestClient


class TestQuestionsEndpoints:
    """Tests for patient questions endpoints."""

    @pytest.mark.unit
    def test_list_questions_empty(self, client: TestClient):
        """Should return empty list when no questions exist."""
        response = client.get("/api/v1/questions")
        
        assert response.status_code == 200
        data = response.json()
        assert data["questions"] == []
        assert data["total"] == 0

    @pytest.mark.unit
    def test_create_question(self, client: TestClient, sample_question: dict):
        """Should create a new question."""
        response = client.post("/api/v1/questions", json=sample_question)
        
        assert response.status_code == 201
        data = response.json()
        assert data["question_text"] == sample_question["question_text"]
        assert data["share_with_physician"] == sample_question["share_with_physician"]
        assert data["category"] == sample_question["category"]
        assert data["is_answered"] == False
        assert "id" in data

    @pytest.mark.unit
    def test_create_question_minimal(self, client: TestClient):
        """Should create question with only required fields."""
        response = client.post("/api/v1/questions", json={
            "question_text": "Simple question"
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["question_text"] == "Simple question"
        assert data["share_with_physician"] == False  # Default
        assert data["category"] == "other"  # Default

    @pytest.mark.unit
    def test_create_question_validation_empty_text(self, client: TestClient):
        """Should reject question with empty text."""
        response = client.post("/api/v1/questions", json={
            "question_text": ""
        })
        
        assert response.status_code == 422  # Validation error

    @pytest.mark.unit
    def test_list_questions_after_create(self, client: TestClient, sample_question: dict):
        """Should list created questions."""
        # Create a question
        client.post("/api/v1/questions", json=sample_question)
        
        # List questions
        response = client.get("/api/v1/questions")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["questions"]) == 1
        assert data["questions"][0]["question_text"] == sample_question["question_text"]

    @pytest.mark.unit
    def test_update_question(self, client: TestClient, sample_question: dict):
        """Should update an existing question."""
        # Create
        create_response = client.post("/api/v1/questions", json=sample_question)
        question_id = create_response.json()["id"]
        
        # Update
        response = client.patch(f"/api/v1/questions/{question_id}", json={
            "question_text": "Updated question text",
            "is_answered": True
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["question_text"] == "Updated question text"
        assert data["is_answered"] == True

    @pytest.mark.unit
    def test_delete_question(self, client: TestClient, sample_question: dict):
        """Should soft-delete a question."""
        # Create
        create_response = client.post("/api/v1/questions", json=sample_question)
        question_id = create_response.json()["id"]
        
        # Delete
        response = client.delete(f"/api/v1/questions/{question_id}")
        assert response.status_code == 204
        
        # Verify not in list
        list_response = client.get("/api/v1/questions")
        assert list_response.json()["total"] == 0

    @pytest.mark.unit
    def test_toggle_share_question(self, client: TestClient, sample_question: dict):
        """Should toggle sharing status."""
        # Create with share=True
        create_response = client.post("/api/v1/questions", json=sample_question)
        question_id = create_response.json()["id"]
        
        # Toggle to False
        response = client.post(f"/api/v1/questions/{question_id}/share?share=false")
        
        assert response.status_code == 200
        assert response.json()["share_with_physician"] == False

    @pytest.mark.unit
    def test_filter_shared_only(self, client: TestClient):
        """Should filter to only shared questions."""
        # Create shared question
        client.post("/api/v1/questions", json={
            "question_text": "Shared question",
            "share_with_physician": True
        })
        
        # Create private question
        client.post("/api/v1/questions", json={
            "question_text": "Private question",
            "share_with_physician": False
        })
        
        # Filter shared only
        response = client.get("/api/v1/questions?shared_only=true")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["questions"][0]["question_text"] == "Shared question"

    @pytest.mark.unit
    def test_question_not_found(self, client: TestClient, random_uuid: str):
        """Should return 404 for non-existent question."""
        response = client.patch(f"/api/v1/questions/{random_uuid}", json={
            "question_text": "Updated"
        })
        
        assert response.status_code == 404

    @pytest.mark.unit
    def test_invalid_category(self, client: TestClient):
        """Should reject invalid category."""
        response = client.post("/api/v1/questions", json={
            "question_text": "Test question",
            "category": "invalid_category"
        })
        
        assert response.status_code == 422

