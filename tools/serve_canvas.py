#!/usr/bin/env python3
"""Serve the repository documentation canvas locally with Django."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import django
from django.conf import settings
from django.core.management import execute_from_command_line
from django.http import FileResponse, Http404, HttpRequest, HttpResponse, JsonResponse
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent
CANVAS_SCRIPT = REPO_ROOT / ".claude/skills/repo-docs-canvas/scripts/repo_canvas.py"
MERMAID_JS = TOOLS_DIR / "node_modules/mermaid/dist/mermaid.min.js"
APPROVALS_FILE = TOOLS_DIR / ".approvals.json"

if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY="aad-docs-local-canvas-dev-key",
        ALLOWED_HOSTS=["*"],
        ROOT_URLCONF=__name__,
        MIDDLEWARE=["django.middleware.common.CommonMiddleware"],
    )
    django.setup()


def _load_approvals() -> dict:
    if APPROVALS_FILE.exists():
        try:
            return json.loads(APPROVALS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_approvals(data: dict) -> None:
    APPROVALS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


LOCAL_SHIM = """
<script src="/mermaid.min.js"></script>
<script>
window.claude = {
  use: async function(cap) {
    if (cap === 'user') return { isOwner: () => true };
    if (cap === 'db') {
      const listeners = [];
      const notify = async () => {
        const res = await fetch('/api/approvals/');
        const data = await res.json();
        const docs = Object.entries(data).map(([id, val]) => ({ id, data: () => val }));
        listeners.forEach(fn => fn({ docs }));
      };
      return {
        doc: (docPath) => {
          const id = docPath.replace(/^approvals\\//, '');
          return {
            set: async (payload) => {
              await fetch('/api/approvals/' + encodeURIComponent(id) + '/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
              });
              await notify();
            },
            delete: async () => {
              await fetch('/api/approvals/' + encodeURIComponent(id) + '/', { method: 'DELETE' });
              await notify();
            }
          };
        },
        collection: () => ({
          onSnapshot: (onNext, onErr) => {
            listeners.push(onNext);
            notify().catch(onErr);
          }
        })
      };
    }
    return null;
  }
};
document.addEventListener('DOMContentLoaded', () => {
  if (window.mermaid) {
    const dark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    window.mermaid.initialize({ startOnLoad: true, theme: dark ? 'dark' : 'default', securityLevel: 'strict' });
  }
});
</script>
"""


def canvas_view(request: HttpRequest) -> HttpResponse:
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        subprocess.run(
            [sys.executable, str(CANVAS_SCRIPT), str(REPO_ROOT), tmp_path, "--title", "AAD-docs", "--approvals"],
            check=True,
            capture_output=True,
            text=True,
        )
        html_content = Path(tmp_path).read_text(encoding="utf-8")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    full_html = (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        + LOCAL_SHIM
        + "</head>\n<body>\n"
        + html_content
        + "\n</body>\n</html>"
    )
    return HttpResponse(full_html, content_type="text/html; charset=utf-8")


def mermaid_js_view(request: HttpRequest) -> FileResponse:
    if not MERMAID_JS.is_file():
        raise Http404("Run tools/setup.sh first to install mermaid.")
    return FileResponse(MERMAID_JS.open("rb"), content_type="application/javascript")


@csrf_exempt
def approvals_list(request: HttpRequest) -> JsonResponse:
    return JsonResponse(_load_approvals())


@csrf_exempt
def approval_detail(request: HttpRequest, decision_id: str) -> JsonResponse:
    data = _load_approvals()
    if request.method == "POST":
        data[decision_id] = json.loads(request.body.decode("utf-8") or "{}")
        _save_approvals(data)
        return JsonResponse({"ok": True, "decision": decision_id})
    if request.method == "DELETE":
        data.pop(decision_id, None)
        _save_approvals(data)
        return JsonResponse({"ok": True, "deleted": decision_id})
    return JsonResponse(data.get(decision_id, {}))


urlpatterns = [
    path("", canvas_view),
    path("canvas.html", canvas_view),
    path("mermaid.min.js", mermaid_js_view),
    path("api/approvals/", approvals_list),
    path("api/approvals/<str:decision_id>/", approval_detail),
]

if __name__ == "__main__":
    addr = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:8765"
    execute_from_command_line([sys.argv[0], "runserver", addr, "--noreload"])
