"""Health check endpoint for bot to verify Django is running."""
from django.http import JsonResponse
from django.utils import timezone


def health_check(request):
    """Simple health check endpoint."""
    return JsonResponse({
        'status': 'ok',
        'timestamp': timezone.now().isoformat(),
        'service': 'django',
    })

