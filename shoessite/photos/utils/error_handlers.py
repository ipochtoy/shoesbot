"""
Centralized error handling utilities for consistent API responses.
"""
import logging
from typing import Optional, Any, Dict
from django.http import JsonResponse
from functools import wraps

logger = logging.getLogger('photos.errors')


def api_success(data: Optional[Dict[str, Any]] = None, message: Optional[str] = None, status: int = 200) -> JsonResponse:
    """
    Return standardized success response.

    Args:
        data: Response data dictionary
        message: Optional success message
        status: HTTP status code (default 200)

    Returns:
        JsonResponse with success=True
    """
    response = {'success': True}

    if message:
        response['message'] = message

    if data:
        response.update(data)

    return JsonResponse(response, status=status)


def api_error(
    error: str,
    details: Optional[Any] = None,
    status: int = 400,
    log_error: bool = True
) -> JsonResponse:
    """
    Return standardized error response.

    Args:
        error: Error message
        details: Optional error details (string, dict, or list)
        status: HTTP status code (default 400)
        log_error: Whether to log the error (default True)

    Returns:
        JsonResponse with success=False
    """
    response = {
        'success': False,
        'error': error,
    }

    if details:
        response['details'] = details

    if log_error:
        logger.error(f"API Error: {error} (status={status}, details={details})")

    return JsonResponse(response, status=status)


def api_validation_error(message: str, field_errors: Optional[Dict[str, str]] = None) -> JsonResponse:
    """
    Return validation error response.

    Args:
        message: General validation error message
        field_errors: Dict mapping field names to error messages

    Returns:
        JsonResponse with 400 status
    """
    response = {
        'success': False,
        'error': message,
    }

    if field_errors:
        response['field_errors'] = field_errors

    return JsonResponse(response, status=400)


def api_not_found(resource: str = 'Resource') -> JsonResponse:
    """
    Return 404 not found response.

    Args:
        resource: Name of the resource that wasn't found

    Returns:
        JsonResponse with 404 status
    """
    return JsonResponse({
        'success': False,
        'error': f'{resource} not found',
    }, status=404)


def handle_exceptions(func):
    """
    Decorator для автоматической обработки исключений в API views.

    Использование:
        @handle_exceptions
        def my_api_view(request):
            # Your code here
            return api_success({'result': 'ok'})
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            return api_error('Invalid value', str(e), status=400)
        except KeyError as e:
            return api_validation_error('Missing required field', {str(e): 'This field is required'})
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}: {str(e)}")
            return api_error('Internal server error', str(e), status=500)

    return wrapper


# Common error responses for reuse
def error_missing_parameter(param_name: str) -> JsonResponse:
    """Return error for missing required parameter."""
    return api_validation_error(
        'Missing required parameter',
        {param_name: 'This parameter is required'}
    )


def error_invalid_json() -> JsonResponse:
    """Return error for invalid JSON in request body."""
    return api_error('Invalid JSON in request body', status=400)


def error_file_too_large(max_size_mb: int) -> JsonResponse:
    """Return error for file too large."""
    return api_error(
        'File too large',
        f'Maximum file size is {max_size_mb}MB',
        status=413
    )


def error_unsupported_format(supported_formats: list) -> JsonResponse:
    """Return error for unsupported file format."""
    return api_error(
        'Unsupported file format',
        f"Supported formats: {', '.join(supported_formats)}",
        status=415
    )
