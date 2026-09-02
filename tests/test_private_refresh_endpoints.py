import asyncio
from types import SimpleNamespace

import httpx
import pytest

import src.api.economic_indicators as economic_module
import src.main as main_module
from src.main import app

API_AUTH_KEY = "test-api-auth-key-value"


class FakeSummaryJobDatabase:
    def __init__(self):
        self.jobs = {}

    async def create_summary_refresh_job(self, job_id, *, time_of_day, refresh):
        job = {
            "id": job_id,
            "status": "queued",
            "time_of_day": time_of_day,
            "refresh": refresh,
            "requested_at": "2026-08-17T10:00:00-04:00",
            "started_at": None,
            "finished_at": None,
            "result": None,
            "error_message": None,
        }
        self.jobs[job_id] = job
        return job

    async def mark_summary_refresh_job_running(self, job_id):
        self.jobs[job_id]["status"] = "running"
        self.jobs[job_id]["started_at"] = "2026-08-17T10:00:01-04:00"

    async def finish_summary_refresh_job(self, job_id, result):
        self.jobs[job_id]["status"] = "success"
        self.jobs[job_id]["finished_at"] = "2026-08-17T10:00:02-04:00"
        self.jobs[job_id]["result"] = result

    async def fail_summary_refresh_job(self, job_id, error_message):
        self.jobs[job_id]["status"] = "failed"
        self.jobs[job_id]["finished_at"] = "2026-08-17T10:00:02-04:00"
        self.jobs[job_id]["error_message"] = error_message

    async def get_summary_refresh_job(self, job_id):
        return self.jobs.get(job_id)

    async def get_active_summary_refresh_job(self):
        for job in self.jobs.values():
            if job["status"] in ("queued", "running"):
                return job
        return None


@pytest.fixture
def fake_summary_app_instance():
    original = main_module.app_instance
    calls = []
    db = FakeSummaryJobDatabase()

    async def send_summaries(time_of_day="manual", refresh=False, *, deliver=True):
        calls.append((time_of_day, refresh, deliver))
        return {
            "collected": 4,
            "processed": 3,
            "summaries": 2,
            "sent": 1 if deliver else 0,
        }

    async def deliver_cached_summaries(hour=None):
        calls.append(("delivery", hour))
        return {
            "collected": 0,
            "summaries": 2,
            "sent": 1,
            "used_cached_summaries": True,
        }

    main_module.app_instance = SimpleNamespace(
        settings=SimpleNamespace(
            api_auth_key=API_AUTH_KEY,
            summary_candidates_extended_limit=8,
            summary_candidates_extended_categories="politica, economia",
            summary_candidates_per_category=8,
        ),
        db=db,
        send_summaries=send_summaries,
        deliver_cached_summaries=deliver_cached_summaries,
        summary_refresh_running=False,
    )
    try:
        yield calls
    finally:
        main_module.app_instance = original


@pytest.fixture
def fake_economic_app_instance(monkeypatch):
    original = main_module.app_instance

    class FakeCollector:
        def __init__(self, timeout):
            self.timeout = timeout

        async def fetch_all(self):
            return [
                {
                    "source": "bcb",
                    "indicator_code": "bcb_unidad_de_fomento_a_la_vivienda_ufv",
                    "indicator_name": "UFV",
                    "indicator_group": "Unidad de fomento a la vivienda",
                    "value": "3.27232",
                }
            ]

    class FakeRepository:
        def __init__(self, session_maker):
            self.session_maker = session_maker

        async def save_values(self, indicators):
            return {"inserted": len(indicators), "unchanged": 0, "skipped": 0}

        async def get_latest_values(self, target_date=None):
            return [{"indicator_code": "bcb_unidad_de_fomento_a_la_vivienda_ufv", "value": 3.27232}]

    monkeypatch.setattr(economic_module, "EconomicIndicatorCollector", FakeCollector)
    monkeypatch.setattr(economic_module, "EconomicIndicatorRepository", FakeRepository)

    main_module.app_instance = SimpleNamespace(
        db=SimpleNamespace(session_maker=object()),
        settings=SimpleNamespace(
            api_auth_key=API_AUTH_KEY,
            summary_candidates_extended_limit=8,
            summary_candidates_extended_categories="politica, economia",
            scraper_timeout=30,
            summary_candidates_per_category=8,
        ),
    )
    try:
        yield
    finally:
        main_module.app_instance = original


@pytest.mark.asyncio
async def test_trigger_summary_rejects_missing_cron_key(fake_summary_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/trigger/summary", params={"refresh": "true"})

    assert response.status_code == 401
    assert fake_summary_app_instance == []


@pytest.mark.asyncio
async def test_trigger_summary_accepts_valid_cron_key(fake_summary_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/trigger/summary",
            params={"refresh": "true", "time_of_day": "manual"},
            headers={"X-API-Key": API_AUTH_KEY},
        )

    assert response.status_code == 200
    assert response.json()["result"]["summaries"] == 2
    assert fake_summary_app_instance == [("manual", True, False)]


@pytest.mark.asyncio
async def test_trigger_summary_ignores_delivery_query_param(fake_summary_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/trigger/summary",
            params={"refresh": "true", "time_of_day": "manual", "deliver": "true"},
            headers={"X-API-Key": API_AUTH_KEY},
        )

    assert response.status_code == 200
    assert response.json()["result"]["sent"] == 0
    assert fake_summary_app_instance == [("manual", True, False)]


@pytest.mark.asyncio
async def test_trigger_summary_async_mode_returns_job_and_processes_in_background(
    fake_summary_app_instance,
):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/trigger/summary",
            params={"refresh": "true", "time_of_day": "manual", "async_mode": "true"},
            headers={"X-API-Key": API_AUTH_KEY},
        )

        assert response.status_code == 202
        payload = response.json()
        job_id = payload["job"]["id"]
        assert payload["status"] == "accepted"
        assert payload["status_url"] == f"/trigger/summary/jobs/{job_id}"

        for _ in range(5):
            status_response = await client.get(
                f"/trigger/summary/jobs/{job_id}",
                headers={"X-API-Key": API_AUTH_KEY},
            )
            if status_response.json()["job"]["status"] == "success":
                break
            await asyncio.sleep(0)

    assert status_response.status_code == 200
    assert status_response.json()["job"]["result"]["summaries"] == 2
    assert fake_summary_app_instance == [("manual", True, False)]


@pytest.mark.asyncio
async def test_trigger_summary_rejects_concurrent_sync_run(fake_summary_app_instance):
    """Regression test: el cron y un trigger manual se solapaban y cada uno
    lanzaba su propio pipeline completo compitiendo por el mismo cupo de
    LLM (visto en vivo: 3 corridas simultaneas agotando groq+gemini). El
    candado se consulta en la BD (no en memoria) porque el backend corre
    con 4 workers de gunicorn en procesos separados -- una segunda corrida
    sincrona mientras hay una activa se rechaza con 409 en vez de arrancar
    otra, sin importar que worker la reciba."""

    main_module.app_instance.db.jobs["other-worker-job"] = {
        "id": "other-worker-job",
        "status": "running",
        "time_of_day": "manual",
        "refresh": True,
        "requested_at": "2026-08-17T10:00:00-04:00",
        "started_at": "2026-08-17T10:00:01-04:00",
        "finished_at": None,
        "result": None,
        "error_message": None,
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/trigger/summary",
            params={"refresh": "true", "time_of_day": "manual"},
            headers={"X-API-Key": API_AUTH_KEY},
        )

    assert response.status_code == 409
    assert fake_summary_app_instance == []


@pytest.mark.asyncio
async def test_trigger_summary_async_mode_returns_existing_job_instead_of_new_one(
    fake_summary_app_instance,
):
    main_module.app_instance.db.jobs["already-running-job"] = {
        "id": "already-running-job",
        "status": "running",
        "time_of_day": "manual",
        "refresh": True,
        "requested_at": "2026-08-17T10:00:00-04:00",
        "started_at": "2026-08-17T10:00:01-04:00",
        "finished_at": None,
        "result": None,
        "error_message": None,
    }

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/trigger/summary",
            params={"refresh": "true", "time_of_day": "manual", "async_mode": "true"},
            headers={"X-API-Key": API_AUTH_KEY},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "already_running"
    assert payload["job"]["id"] == "already-running-job"
    assert payload["status_url"] == "/trigger/summary/jobs/already-running-job"
    assert fake_summary_app_instance == []


@pytest.mark.asyncio
async def test_trigger_summary_releases_lock_after_sync_completion(fake_summary_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        first = await client.post(
            "/trigger/summary",
            params={"refresh": "true", "time_of_day": "manual"},
            headers={"X-API-Key": API_AUTH_KEY},
        )
        second = await client.post(
            "/trigger/summary",
            params={"refresh": "true", "time_of_day": "manual"},
            headers={"X-API-Key": API_AUTH_KEY},
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert main_module.app_instance.summary_refresh_running is False
    assert fake_summary_app_instance == [
        ("manual", True, False),
        ("manual", True, False),
    ]


@pytest.mark.asyncio
async def test_summary_refresh_job_status_returns_404_for_unknown_job(fake_summary_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get(
            "/trigger/summary/jobs/missing",
            headers={"X-API-Key": API_AUTH_KEY},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_trigger_delivery_rejects_missing_cron_key(fake_summary_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/trigger/delivery", params={"hour": 9})

    assert response.status_code == 401
    assert fake_summary_app_instance == []


@pytest.mark.asyncio
async def test_trigger_delivery_accepts_valid_cron_key(fake_summary_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/trigger/delivery",
            params={"hour": 16},
            headers={"X-API-Key": API_AUTH_KEY},
        )

    assert response.status_code == 200
    assert response.json()["result"]["used_cached_summaries"] is True
    assert fake_summary_app_instance == [("delivery", 16)]


@pytest.mark.asyncio
async def test_trigger_delivery_without_hour_means_manual_mode(fake_summary_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/trigger/delivery",
            headers={"X-API-Key": API_AUTH_KEY},
        )

    assert response.status_code == 200
    assert fake_summary_app_instance == [("delivery", None)]


@pytest.mark.asyncio
async def test_trigger_delivery_rejects_hour_outside_9_23(fake_summary_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/trigger/delivery",
            params={"hour": 3},
            headers={"X-API-Key": API_AUTH_KEY},
        )

    assert response.status_code == 422
    assert fake_summary_app_instance == []


@pytest.mark.asyncio
async def test_economic_refresh_rejects_missing_cron_key(fake_economic_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/economic-indicators/refresh")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_economic_refresh_accepts_valid_cron_key(fake_economic_app_instance):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/economic-indicators/refresh",
            headers={"X-API-Key": API_AUTH_KEY},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["collected"] == 1
    assert payload["inserted"] == 1


def test_private_refresh_endpoints_document_cron_header():
    schema = app.openapi()
    operations = (
        ("/api/economic-indicators/refresh", "post"),
        ("/trigger/summary", "post"),
        ("/trigger/summary/jobs/{job_id}", "get"),
        ("/trigger/delivery", "post"),
    )
    for path, method in operations:
        parameters = schema["paths"][path][method]["parameters"]
        cron_header = next(param for param in parameters if param["name"] == "X-API-Key")
        assert cron_header["in"] == "header"
        assert cron_header["required"] is False
