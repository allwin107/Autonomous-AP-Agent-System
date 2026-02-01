import sys
import os
sys.path.append(os.getcwd())
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from app.main import app

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

@pytest.mark.asyncio
async def test_auth_token():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/auth/token", data={"username": "user", "password": "password"})
    assert response.status_code == 200
    assert "access_token" in response.json()

@pytest.mark.asyncio
async def test_list_invoices_unauthorized():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/invoices/")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_list_invoices_authorized():
    # 1. Get Token
    async with AsyncClient(app=app, base_url="http://test") as ac:
        auth_response = await ac.post("/api/auth/token", data={"username": "user", "password": "password"})
        token = auth_response.json()["access_token"]
        
        # 2. Mock DB (since endpoints hit DB)
        with patch("app.api.invoices.db") as mock_db:
             mock_db.invoices.find = AsyncMock(return_value=[])
             
             headers = {"Authorization": f"Bearer {token}"}
             response = await ac.get("/api/invoices/", headers=headers)
             
    assert response.status_code == 200
    assert response.json() == []

@pytest.mark.asyncio
async def test_upload_invoice():
    # 1. Get Token
    async with AsyncClient(app=app, base_url="http://test") as ac:
        auth_response = await ac.post("/api/auth/token", data={"username": "user", "password": "password"})
        token = auth_response.json()["access_token"]
        
        # 2. Mock DB & GridFS
        with patch("app.api.invoices.db") as mock_db:
             mock_db.fs.upload_from_stream = AsyncMock(return_value="file_id_123")
             mock_db.invoices.create = AsyncMock()
             
             files = {"file": ("test.pdf", b"fake pdf content", "application/pdf")}
             headers = {"Authorization": f"Bearer {token}"}
             
             # Mock Background Task (just verifying it doesn't crash, logic tested in workflow)
             with patch("app.api.invoices.trigger_workflow") as mock_workflow: 
                # Note: FastAPI BackgroundTasks hard to mock directly in integration tests without overriding app dependency
                # or just letting it run (it won't execute if we don't await/manage it, but here it adds to response)
                # Actually, BackgroundTasks are executed after response. Tests dealing with them usually use specific TestClient patterns.
                # For simplicity here, we assume it works if endpoint returns 201.
                
                response = await ac.post("/api/invoices/upload", files=files, headers=headers)
             
    assert response.status_code == 201
    assert response.json()["invoice_id"].startswith("INV-")
