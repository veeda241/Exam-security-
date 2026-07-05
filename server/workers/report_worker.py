"""Report generation worker — WeasyPrint HTML to PDF."""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timezone

_server_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _server_dir not in sys.path:
    sys.path.insert(0, _server_dir)

from workers.celery_app import celery_app
from workers.utils import publish_session_message
from supabase_client import get_supabase


def _render_html(session: dict, events: list[dict]) -> str:
    rows = "".join(
        f"<tr><td>{e.get('created_at', '')}</td><td>{e.get('type', '')}</td>"
        f"<td>{e.get('weight', 0)}</td></tr>"
        for e in events
    )
    return f"""
    <!DOCTYPE html>
    <html><head><meta charset="utf-8"><title>ExamGuard Report</title>
    <style>
      body {{ font-family: sans-serif; margin: 2rem; }}
      h1 {{ color: #1e3a5f; }}
      table {{ border-collapse: collapse; width: 100%; }}
      th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
      th {{ background: #f0f4f8; }}
    </style></head><body>
    <h1>ExamGuard Pro — Session Report</h1>
    <p><strong>Session ID:</strong> {session.get('id')}</p>
    <p><strong>Risk Score:</strong> {session.get('risk_score', 0)} ({session.get('risk_level', 'safe')})</p>
    <p><strong>Generated:</strong> {datetime.now(timezone.utc).isoformat()}</p>
    <h2>Events</h2>
    <table><tr><th>Time</th><th>Type</th><th>Weight</th></tr>{rows}</table>
    </body></html>
    """


@celery_app.task(name="workers.report_worker.generate_report", bind=True, max_retries=2)
def generate_report(self, session_id: str) -> dict:
    sb = get_supabase()
    if not sb:
        return {"session_id": session_id, "status": "error", "detail": "no database"}

    session_res = sb.table("sessions").select("*").eq("id", session_id).execute()
    if not session_res.data:
        return {"session_id": session_id, "status": "error", "detail": "session not found"}

    session = session_res.data[0]
    events_res = sb.table("v2_events").select("*").eq("session_id", session_id).order("created_at").execute()
    events = events_res.data or []

    html = _render_html(session, events)

    pdf_path = None
    try:
        from weasyprint import HTML
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            pdf_path = tmp.name
        HTML(string=html).write_pdf(pdf_path)
    except ImportError:
        # Fallback: write HTML as pseudo-report
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as tmp:
            pdf_path = tmp.name
            tmp.write(html)

    storage_path = f"reports/{session_id}.pdf"
    bucket = os.getenv("REPORTS_BUCKET", "reports")

    try:
        with open(pdf_path, "rb") as f:
            sb.storage.from_(bucket).upload(
                storage_path,
                f.read(),
                {"content-type": "application/pdf", "upsert": "true"},
            )
    except Exception as exc:
        storage_path = f"local/{session_id}.html"
        # Still record report row for dev without storage
        pass

    report_row = {
        "session_id": session_id,
        "storage_path": storage_path,
    }
    res = sb.table("reports").insert(report_row).execute()
    report = res.data[0] if res.data else report_row

    publish_session_message(session_id, {
        "type": "report_ready",
        "session_id": session_id,
        "report_id": report.get("id"),
        "storage_path": storage_path,
    })

    if pdf_path:
        try:
            os.unlink(pdf_path)
        except OSError:
            pass

    return {"session_id": session_id, "status": "generated", "storage_path": storage_path}
