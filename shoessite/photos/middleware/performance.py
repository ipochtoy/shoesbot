"""
Performance monitoring middleware - logs slow requests.
"""
import logging
import time
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('photos.performance')


class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """Middleware для мониторинга производительности запросов."""

    # Thresholds in seconds
    SLOW_REQUEST_THRESHOLD = 2.0  # Log warning if request takes > 2s
    VERY_SLOW_REQUEST_THRESHOLD = 5.0  # Log error if request takes > 5s

    def process_request(self, request):
        """Mark request start time."""
        request._start_time = time.time()
        return None

    def process_response(self, request, response):
        """Calculate request duration and log if slow."""
        # Skip if no start time (e.g., static files)
        if not hasattr(request, '_start_time'):
            return response

        duration = time.time() - request._start_time

        # Log slow requests
        if duration >= self.VERY_SLOW_REQUEST_THRESHOLD:
            logger.error(
                f"VERY SLOW REQUEST: {request.method} {request.path} took {duration:.2f}s",
                extra={
                    'duration': duration,
                    'method': request.method,
                    'path': request.path,
                    'status': response.status_code,
                }
            )
        elif duration >= self.SLOW_REQUEST_THRESHOLD:
            logger.warning(
                f"Slow request: {request.method} {request.path} took {duration:.2f}s",
                extra={
                    'duration': duration,
                    'method': request.method,
                    'path': request.path,
                    'status': response.status_code,
                }
            )
        else:
            # Log all requests at debug level
            logger.debug(
                f"{request.method} {request.path} - {duration:.3f}s - {response.status_code}"
            )

        # Add duration header for debugging
        response['X-Request-Duration'] = f"{duration:.3f}s"

        return response
