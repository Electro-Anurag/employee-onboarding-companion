from pathlib import Path
from django.conf import settings
from django.db import connection
from django.http import FileResponse, HttpResponse, JsonResponse


def index(request):
    compiled = Path(settings.STATIC_ROOT) / "index.html"
    if not compiled.is_file():
        return HttpResponse("Frontend not built; execute npm run build", status=503)
    response = FileResponse(compiled.open("rb"), content_type="text/html; charset=utf-8")
    response["Cache-Control"] = "no-store"
    return response


def health_live(request):
    return JsonResponse({"status": "live"})


def health_ready(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ready"})
