"""Response cache + per-client rate limit for the API — in-process, no extra deps.

CacheMiddleware   caches successful JSON responses of deterministic POST/GET endpoints by (method, path, query, body);
                  the key also carries today's date so date-relative casts (transits, 流日) roll over at midnight.
                  Streams and `/ask` without an explicit `at` are never cached. Header `X-Cache: HIT | MISS | BYPASS`.
RateLimiter       token bucket per client (X-Forwarded-For aware), two tiers: general and LLM (reading / synthesis / consult /
                  love / ask / annual / zeri-with-reading). 429 + Retry-After when exhausted. Limits are mutable at runtime
                  (`app.state.limiter.per_minute`) so operators and tests can tune them.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import OrderedDict
from datetime import date

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

LLM_PREFIXES = ("/reading/", "/synthesis", "/consult", "/love", "/ask/", "/annual-report", "/annual-overview", "/zeri", "/day")
NO_CACHE_PREFIXES = ("/reading/", "/health", "/docs", "/openapi", "/redoc", "/web", "/static")


class TTLCache:
    def __init__(self, max_entries: int = 512, ttl: float = 600.0):
        self.max_entries, self.ttl = max_entries, ttl
        self._d: OrderedDict[str, tuple[float, bytes, str, int]] = OrderedDict()
        self._lock = threading.Lock()
        self.hits = self.misses = 0

    def get(self, key: str):
        with self._lock:
            v = self._d.get(key)
            if not v:
                self.misses += 1
                return None
            exp, body, media, status = v
            if exp < time.monotonic():
                del self._d[key]
                self.misses += 1
                return None
            self._d.move_to_end(key)
            self.hits += 1
            return body, media, status

    def put(self, key: str, body: bytes, media: str, status: int) -> None:
        with self._lock:
            self._d[key] = (time.monotonic() + self.ttl, body, media, status)
            self._d.move_to_end(key)
            while len(self._d) > self.max_entries:
                self._d.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._d.clear()

    def __len__(self) -> int:
        return len(self._d)


class RateLimiter:
    """Token bucket per (client, tier). `per_minute` / `llm_per_minute` can be changed at runtime."""

    def __init__(self, per_minute: int = 240, llm_per_minute: int = 30, burst: float = 1.0):
        self.per_minute, self.llm_per_minute, self.burst = per_minute, llm_per_minute, burst
        self._b: dict[tuple[str, str], tuple[float, float]] = {}
        self._lock = threading.Lock()
        self.rejected = 0

    def _limit(self, tier: str) -> int:
        return self.llm_per_minute if tier == "llm" else self.per_minute

    def take(self, client: str, tier: str) -> tuple[bool, float]:
        """(allowed, retry_after_seconds)."""
        limit = self._limit(tier)
        if limit <= 0:
            return True, 0.0
        cap = max(1.0, limit * self.burst)
        rate = limit / 60.0
        now = time.monotonic()
        with self._lock:
            tokens, last = self._b.get((client, tier), (cap, now))
            tokens = min(cap, tokens + (now - last) * rate)
            if tokens >= 1.0:
                self._b[(client, tier)] = (tokens - 1.0, now)
                return True, 0.0
            self._b[(client, tier)] = (tokens, now)
            self.rejected += 1
            if len(self._b) > 10000:                      # forget idle clients
                cutoff = now - 600
                for k in [k for k, (_t, l) in self._b.items() if l < cutoff]:
                    del self._b[k]
            return False, round((1.0 - tokens) / rate, 1)

    def reset(self) -> None:
        with self._lock:
            self._b.clear()


def client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "anon"


def tier_of(path: str) -> str:
    return "llm" if path.startswith(LLM_PREFIXES) else "general"


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limiter: RateLimiter):
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS" or request.url.path in ("/health", "/systems", "/openapi.json", "/docs", "/redoc"):
            return await call_next(request)
        tier = tier_of(request.url.path)
        ok, retry = self.limiter.take(client_ip(request), tier)
        if not ok:
            return JSONResponse({"detail": f"rate limit exceeded ({tier}) / 請求過於頻繁，請 {retry:.0f} 秒後再試"}, status_code=429,
                                headers={"Retry-After": str(max(1, int(retry + 0.5))), "X-RateLimit-Tier": tier})
        resp = await call_next(request)
        resp.headers["X-RateLimit-Tier"] = tier
        return resp


class CacheMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, cache: TTLCache):
        super().__init__(app)
        self.cache = cache

    @staticmethod
    def _cacheable(request: Request, body: bytes) -> bool:
        p = request.url.path
        if request.method not in ("POST", "GET") or p.startswith(NO_CACHE_PREFIXES) or p.endswith("/stream"):
            return False
        if p.startswith("/ask/"):
            try:
                return bool(json.loads(body or b"{}").get("at"))
            except Exception:  # noqa: BLE001
                return False
        return True

    async def dispatch(self, request: Request, call_next):
        if request.headers.get("cache-control", "").lower() == "no-cache":
            resp = await call_next(request)
            resp.headers["X-Cache"] = "BYPASS"
            return resp
        body = await request.body() if request.method == "POST" else b""
        if not self._cacheable(request, body):
            resp = await call_next(request)
            resp.headers["X-Cache"] = "BYPASS"
            return resp
        key = hashlib.sha256(f"{request.method} {request.url.path}?{request.url.query}|{date.today().isoformat()}|".encode() + body).hexdigest()
        hit = self.cache.get(key)
        if hit:
            b, media, status = hit
            return Response(content=b, status_code=status, media_type=media, headers={"X-Cache": "HIT"})
        resp = await call_next(request)
        chunks = [c async for c in resp.body_iterator]      # type: ignore[attr-defined]
        content = b"".join(chunks)
        media = resp.headers.get("content-type", "application/json")
        if resp.status_code == 200 and media.startswith("application/json"):
            self.cache.put(key, content, media, resp.status_code)
        headers = {k: v for k, v in resp.headers.items() if k.lower() not in ("content-length",)}
        headers["X-Cache"] = "MISS"
        return Response(content=content, status_code=resp.status_code, headers=headers, media_type=media)
