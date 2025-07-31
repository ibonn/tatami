import time

from starlette.middleware.base import BaseHTTPMiddleware


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.monotonic()
        response = await call_next(request)
        response.headers['x-process-time'] = str(time.monotonic() - start_time)
        return response