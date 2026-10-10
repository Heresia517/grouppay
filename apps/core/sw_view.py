"""Vue pour servir sw.js depuis la racine."""
from django.http import HttpResponse
from django.views.decorators.cache import never_cache
from django.conf import settings
from pathlib import Path


def _serve_sw(filename):
    """Helper interne : sert un SW depuis /static/."""
    sw_path = Path(settings.BASE_DIR) / "static" / filename

    if not sw_path.exists():
        return HttpResponse("// " + filename + " not found", content_type="application/javascript", status=404)

    content = sw_path.read_text(encoding="utf-8")
    response = HttpResponse(content, content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


@never_cache
def service_worker(request):
    """Sert /sw.js avec scope racine."""
    return _serve_sw("sw.js")


@never_cache
def service_worker_v4(request):
    """Sert /sw-v4.js avec scope racine."""
    return _serve_sw("sw-v4.js")
