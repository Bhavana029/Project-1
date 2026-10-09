from django.http import JsonResponse


def health_check(_request):
    """Lightweight liveness check; no secrets or user data."""
    return JsonResponse({"status": "ok"})
