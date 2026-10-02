import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import settings

client = TestClient(app)

def test_session_lifecycle_and_deletion():
    test_id = "test-session-delete-lifecycle"
    
    # 1. Ensure clean slate for test session
    client.delete(f"/api/chat/{test_id}")
    
    # 2. Sync / create session
    payload = {
        "thread_id": test_id,
        "title": "Test Cycling Adventure",
        "model": "Gemini 3.8 Flash",
        "messages": [
            {"id": "m1", "sender": "user", "text": "Can I cycle in Bhopal today?"},
            {"id": "m2", "sender": "advisor", "text": "Moderate heat advisory active."}
        ]
    }
    sync_resp = client.post("/api/chat/sync", json=payload)
    assert sync_resp.status_code == 200
    assert sync_resp.json()["status"] == "success"

    # 3. Verify session file exists on disk
    session_file = settings.BASE_DIR / "sessions" / f"{test_id}.json"
    assert session_file.exists()

    # 4. Retrieve session via GET
    get_resp = client.get(f"/api/chat/{test_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["thread_id"] == test_id
    assert len(data["messages"]) == 2

    # 5. Verify session listed in GET /api/sessions
    list_resp = client.get("/api/sessions")
    assert list_resp.status_code == 200
    sessions = list_resp.json()["sessions"]
    matching = [s for s in sessions if s["id"] == test_id]
    assert len(matching) == 1
    assert matching[0]["title"] == "Test Cycling Adventure"

    # 6. Delete session via DELETE /api/chat/{thread_id}
    del_resp = client.delete(f"/api/chat/{test_id}")
    assert del_resp.status_code == 200
    del_data = del_resp.json()
    assert del_data["status"] == "success"
    assert del_data["thread_id"] == test_id
    assert del_data["file_deleted"] is True

    # 7. Verify session file is gone from disk
    assert not session_file.exists()

    # 8. Subsequent GET returns 404
    get_after = client.get(f"/api/chat/{test_id}")
    assert get_after.status_code == 404

    # 9. Deleting non-existent or already deleted session is idempotent (returns 200 with file_deleted=False)
    del_again = client.delete(f"/api/chat/{test_id}")
    assert del_again.status_code == 200
    assert del_again.json()["file_deleted"] is False

    # 10. Path traversal validation
    traversal_resp = client.delete("/api/chat/invalid..id")
    assert traversal_resp.status_code == 400
    assert "Invalid thread ID" in traversal_resp.json()["detail"]
