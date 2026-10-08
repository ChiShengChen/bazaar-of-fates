"""API cache + rate limit + LLM concurrency gate."""

import threading
import time

import pytest
from fastapi.testclient import TestClient

from fortune.api.main import app
from fortune.shared import throttle as T

BIRTH = {"birth_date": "1990-06-15", "birth_time": "14:30", "gender": "female"}


@pytest.fixture
def client():
    app.state.cache.clear()
    app.state.limiter.reset()
    saved = (app.state.limiter.per_minute, app.state.limiter.llm_per_minute)
    yield TestClient(app)
    app.state.limiter.per_minute, app.state.limiter.llm_per_minute = saved
    app.state.limiter.reset()
    app.state.cache.clear()


def test_cast_is_cached_by_body(client):
    r1 = client.post("/cast/bazi", json=BIRTH)
    r2 = client.post("/cast/bazi", json=BIRTH)
    r3 = client.post("/cast/bazi", json={**BIRTH, "birth_time": "15:30"})
    assert r1.status_code == 200 and r1.headers["x-cache"] == "MISS"
    assert r2.headers["x-cache"] == "HIT" and r2.json() == r1.json()
    assert r3.headers["x-cache"] == "MISS" and r3.json()["chart"]["pillars"][3]["gz"] != r1.json()["chart"]["pillars"][3]["gz"]
    assert client.post("/cast/bazi", json=BIRTH, headers={"cache-control": "no-cache"}).headers["x-cache"] == "BYPASS"


def test_stream_and_ask_now_are_not_cached(client):
    r = client.post("/reading/bazi/stream", json={"birth": BIRTH})
    assert r.headers["x-cache"] == "BYPASS"
    r = client.post("/ask/xiaoliuren", json={"question": "今天順嗎", "read": False})
    assert r.headers["x-cache"] == "BYPASS"                     # no `at` → depends on the clock
    r = client.post("/ask/xiaoliuren", json={"question": "今天順嗎", "at": "2026-10-10T14:30", "read": False})
    assert r.headers["x-cache"] == "MISS"
    assert client.post("/ask/xiaoliuren", json={"question": "今天順嗎", "at": "2026-10-10T14:30", "read": False}).headers["x-cache"] == "HIT"


def test_errors_are_not_cached(client):
    assert client.post("/cast/nope", json=BIRTH).status_code == 404
    assert client.post("/cast/nope", json=BIRTH).headers["x-cache"] == "MISS"


def test_rate_limit_general_and_llm_tiers(client):
    app.state.limiter.per_minute = 3
    app.state.limiter.llm_per_minute = 1
    app.state.limiter.reset()
    codes = [client.post("/cast/bazi", json=BIRTH).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]
    r = client.post("/cast/bazi", json=BIRTH)
    assert r.status_code == 429 and int(r.headers["retry-after"]) >= 1 and "請求過於頻繁" in r.json()["detail"]
    # the LLM tier is counted separately and tighter
    assert client.post("/synthesis", json={"birth": BIRTH, "systems": ["bazi"]}).status_code == 200
    r = client.post("/synthesis", json={"birth": BIRTH, "systems": ["bazi"]})
    assert r.status_code == 429 and r.headers["x-ratelimit-tier"] == "llm"
    assert client.get("/health").status_code == 200              # never limited


def test_rate_limit_is_per_client(client):
    app.state.limiter.per_minute = 1
    app.state.limiter.reset()
    assert client.post("/cast/bazi", json=BIRTH, headers={"x-forwarded-for": "10.0.0.1"}).status_code == 200
    assert client.post("/cast/bazi", json=BIRTH, headers={"x-forwarded-for": "10.0.0.1"}).status_code == 429
    assert client.post("/cast/bazi", json=BIRTH, headers={"x-forwarded-for": "10.0.0.2"}).status_code == 200


def test_health_reports_stats(client):
    client.post("/cast/bazi", json=BIRTH); client.post("/cast/bazi", json=BIRTH)
    h = client.get("/health").json()
    assert h["cache"]["hits"] >= 1 and h["rate_limit"]["per_minute"] == app.state.limiter.per_minute and "max_concurrency" in h["llm"]


def test_token_bucket_refills():
    rl = T.RateLimiter(per_minute=60, llm_per_minute=60)
    rl._b[("c", "general")] = (0.0, time.monotonic() - 2.0)      # empty bucket, 2 s ago → 2 tokens refilled
    assert rl.take("c", "general")[0] and rl.take("c", "general")[0] and not rl.take("c", "general")[0]
    assert T.RateLimiter(per_minute=0).take("x", "general") == (True, 0.0)


def test_ttl_cache_expires_and_evicts():
    c = T.TTLCache(max_entries=2, ttl=0.05)
    c.put("a", b"1", "application/json", 200); c.put("b", b"2", "application/json", 200); c.put("c", b"3", "application/json", 200)
    assert len(c) == 2 and c.get("a") is None and c.get("c")[0] == b"3"
    time.sleep(0.06)
    assert c.get("c") is None


def test_llm_gate_serialises_calls(monkeypatch):
    from fortune.shared import llm
    monkeypatch.setattr(llm, "_sem", None)
    monkeypatch.setattr(llm.get_settings(), "llm_max_concurrency", 2, raising=False)
    peak = [0]; cur = [0]; lock = threading.Lock()
    def work():
        with llm._Slot():
            with lock:
                cur[0] += 1; peak[0] = max(peak[0], cur[0])
            time.sleep(0.05)
            with lock:
                cur[0] -= 1
    ts = [threading.Thread(target=work) for _ in range(6)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert peak[0] == 2 and llm.llm_stats()["in_flight"] == 0 and llm.llm_stats()["completed"] >= 6
