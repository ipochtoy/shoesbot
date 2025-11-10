"""
Error handling middleware - catches exceptions and returns consistent JSON responses.
"""
import logging
import traceback
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.exceptions import ValidationError, PermissionDenied
from django.http import Http404

logger = logging.getLogger('photos.errors')


class ErrorHandlingMiddleware(MiddlewareMixin):
    """Middleware для централизованной обработки ошибок."""

    def process_exception(self, request, exception):
        """Handle exceptions and return JSON response for API endpoints."""
        # Only handle API endpoints
        if not request.path.startswith('/photos/api/'):
            return None

        # Log the exception
        logger.error(
            f"Exception in {request.method} {request.path}: {str(exception)}",
            extra={
                'exception_type': type(exception).__name__,
                'traceback': traceback.format_exc(),
                'user': str(request.user) if hasattr(request, 'user') else 'Anonymous',
            }
        )

        # Determine response based on exception type
        if isinstance(exception, ValidationError):
            return JsonResponse({
                'success': False,
                'error': 'Validation error',
                'details': exception.messages if hasattr(exception, 'messages') else str(exception),
            }, status=400)

        elif isinstance(exception, PermissionDenied):
            return JsonResponse({
                'success': False,
                'error': 'Permission denied',
            }, status=403)

        elif isinstance(exception, Http404):
            return JsonResponse({
                'success': False,
                'error': 'Resource not found',
            }, status=404)

        elif isinstance(exception, ValueError):
            return JsonResponse({
                'success': False,
                'error': 'Invalid value',
                'details': str(exception),
            }, status=400)

        # Generic server error for all other exceptions
        return JsonResponse({
            'success': False,
            'error': 'Internal server error',
            'details': str(exception) if hasattr(exception, '__str__') else 'An unexpected error occurred',
        }, status=500)
