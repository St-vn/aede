import pytest
from aede.server import app


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    return TestClient(app)


def test_daemon_status_endpoint(client):
    resp = client.get("/api/daemon/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "running" in data
    assert "pid" in data
    assert "port" in data


async def test_daemon_start_stop(tmp_home):
    from httpx import AsyncClient, ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        start = await client.post("/api/daemon/start")
        assert start.status_code == 200
        status = (await client.get("/api/daemon/status")).json()
        assert status["running"] is True
        stop = await client.post("/api/daemon/stop")
        assert stop.status_code == 200


async def test_timer_crud(tmp_home):
    from httpx import AsyncClient, ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/daemon/start")
        resp = await client.post("/api/daemon/timers", json={"delay_s": 60, "action": "ping", "label": "test"})
        assert resp.status_code == 200
        data = resp.json()
        assert "timer" in data
        timer_id = data["timer"]["id"]
        lst = await client.get("/api/daemon/timers")
        assert lst.status_code == 200
        lst_data = lst.json()
        assert "timers" in lst_data
        assert any(t["id"] == timer_id for t in lst_data["timers"])
        rm = await client.delete(f"/api/daemon/timers/{timer_id}")
        assert rm.status_code == 200
        await client.post("/api/daemon/stop")


async def test_cron_crud(tmp_home):
    from httpx import AsyncClient, ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/daemon/start")
        resp = await client.post("/api/daemon/cron", json={"schedule": "0 9 * * *", "action": "daily", "label": "test"})
        assert resp.status_code == 200
        data = resp.json()
        assert "job" in data
        job_id = data["job"]["id"]
        lst = await client.get("/api/daemon/cron")
        assert lst.status_code == 200
        lst_data = lst.json()
        assert "jobs" in lst_data
        assert any(j["id"] == job_id for j in lst_data["jobs"])
