'''Tests for the slow-request and blocked-event-loop logging.'''

import asyncio
import logging
import time

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from tino import slowlog


def _client():
    async def hello(_request):
        return PlainTextResponse('hi')

    app = Starlette(routes=[Route('/hello', hello)])
    app.add_middleware(slowlog.SlowRequestMiddleware)
    return TestClient(app)


def test_slow_request_is_logged(monkeypatch, caplog):
    monkeypatch.setattr(slowlog, '_SLOW_REQUEST_SECONDS', 0)

    with caplog.at_level(logging.WARNING, logger='tino.slowlog'):
        assert _client().get('/hello').status_code == 200

    assert 'Slow request: GET /hello -> 200' in caplog.text


def test_fast_request_is_not_logged(caplog):
    with caplog.at_level(logging.WARNING, logger='tino.slowlog'):
        _client().get('/hello')

    assert not caplog.records


@pytest.mark.anyio
async def test_blocked_loop_is_logged(monkeypatch, caplog):
    monkeypatch.setattr(slowlog, '_LAG_INTERVAL_SECONDS', 0.01)
    monkeypatch.setattr(slowlog, '_LAG_WARN_SECONDS', 0.05)
    task = asyncio.create_task(slowlog.watch_event_loop())

    with caplog.at_level(logging.WARNING, logger='tino.slowlog'):
        await asyncio.sleep(0)
        time.sleep(0.2)
        await asyncio.sleep(0.05)

    task.cancel()
    assert 'Event loop blocked for' in caplog.text
