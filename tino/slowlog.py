'''Diagnostics for slow responses and a blocked event loop.'''

import asyncio
import logging
import time

logger = logging.getLogger(__name__)

_SLOW_REQUEST_SECONDS = 1.0
_LAG_INTERVAL_SECONDS = 0.5
_LAG_WARN_SECONDS = 1.0


class SlowRequestMiddleware:  # pylint: disable=too-few-public-methods
    '''Log requests that take longer than a second to finish sending.

    Time spent waiting for a blocked event loop before the request reached this
    middleware is not included; :func:`watch_event_loop` reports that.
    '''

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        started = time.monotonic()
        status = None

        async def send_wrapper(message):
            nonlocal status
            if message['type'] == 'http.response.start':
                status = message['status']
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed = time.monotonic() - started
            if elapsed >= _SLOW_REQUEST_SECONDS:
                logger.warning('Slow request: %s %s -> %s in %.1fs',
                               scope['method'], scope['path'], status, elapsed)


async def watch_event_loop() -> None:
    '''Log whenever the event loop was blocked for a second or more.

    A blocking call in a route (e.g. a subprocess run) stalls every other
    request and the collab websockets until it returns.
    '''
    loop = asyncio.get_running_loop()

    while True:
        started = loop.time()
        await asyncio.sleep(_LAG_INTERVAL_SECONDS)
        lag = loop.time() - started - _LAG_INTERVAL_SECONDS
        if lag >= _LAG_WARN_SECONDS:
            logger.warning('Event loop blocked for %.1fs', lag)
