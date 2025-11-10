"""
Request logging middleware - logs all incoming requests.
"""
import logging
import json
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('photos.requests')


class RequestLoggingMiddleware(MiddlewareMixin):
    """Middleware для логирования всех входящих запросов."""

    def process_request(self, request):
        """Log incoming request details."""
        # Skip logging for static files
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return None

        # Build log message
        log_data = {
            'method': request.method,
            'path': request.path,
            'user': str(request.user) if hasattr(request, 'user') else 'Anonymous',
            'ip': self._get_client_ip(request),
        }

        # Add query params if present
        if request.GET:
            log_data['query_params'] = dict(request.GET)

        # Log POST data for API endpoints (but not file uploads)
        if request.method == 'POST' and request.path.startswith('/photos/api/'):
            content_type = request.META.get('CONTENT_TYPE', '')
            if 'application/json' in content_type:
                try:
                    log_data['body_preview'] = json.loads(request.body)[:200] if request.body else None
                except:
                    pass

        logger.info(f"Request: {json.dumps(log_data)}")
        return None

    def process_response(self, request, response):
        """Log response status."""
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return response

        log_data = {
            'method': request.method,
            'path': request.path,
            'status': response.status_code,
        }

        # Log errors with more detail
        if response.status_code >= 400:
            logger.warning(f"Response: {json.dumps(log_data)}")
        else:
            logger.debug(f"Response: {json.dumps(log_data)}")

        return response

    @staticmethod
    def _get_client_ip(request):
        """Extract client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
