"""
Global IP-based rate limiting middleware.

Uses Django's cache framework to track requests per IP address within a
fixed time window. When a client exceeds the configured limit a
429 Too Many Requests response is returned.

Settings (optional, applied if set):
    RATE_LIMIT_MAX_REQUESTS   int   default: 300
    RATE_LIMIT_WINDOW_SECONDS int   default: 60
    RATE_LIMIT_EXEMPT_PATHS   list  e.g. ['/static/', '/media/', '/favicon.ico']
"""

from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError, OperationalError
from django.http import HttpResponse


class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.max_requests = getattr(settings, 'RATE_LIMIT_MAX_REQUESTS', 300)
        self.window = getattr(settings, 'RATE_LIMIT_WINDOW_SECONDS', 60)
        self.exempt_paths = tuple(getattr(settings, 'RATE_LIMIT_EXEMPT_PATHS', ['/static/', '/media/']))

    def __call__(self, request):
        path = request.path_info
        if path.startswith(self.exempt_paths):
            return self.get_response(request)

        ip = self._get_client_ip(request)
        key = f'ratelimit:{ip}:{path}'
        try:
            count = cache.get(key, 0)
            if count >= self.max_requests:
                response = HttpResponse('Too Many Requests', status=429)
                response['Retry-After'] = str(self.window)
                return response
            cache.add(key, 0, timeout=self.window)
            cache.incr(key)
        except (DatabaseError, OperationalError, TypeError):
            pass
        return self.get_response(request)

    @staticmethod
    def _get_client_ip(request):
        forwarded = request.headers.get('X-Forwarded-For', '')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')