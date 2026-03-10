"""Report generator – Terminal and HTML summary reports.

Generates run summaries from the database showing job collection,
scoring, routing, and application statistics.
"""

import html
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.storage.database import get_connection
from src.storage.run_logs_repo import list_run_logs
from src.utils.logger import get_logger, PROJECT_ROOT

logger = get_logger(__name__)

REPORTS_DIR = PROJECT_ROOT / "logs" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def get_summary_stats() -> dict:
    """Gather summary statistics from the database.

    Returns:
        Dict with counts and breakdowns.
    """
    with get_connection() as conn:
        # Total jobs
        total_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]

        # By route status
        route_counts = {}
        rows = conn.execute(
            "SELECT route_status, COUNT(*) as cnt FROM jobs GROUP BY route_status"
        ).fetchall()
        for row in rows:
            route_counts[row["route_status"]] = row["cnt"]

        # By source
        source_counts = {}
        rows = conn.execute(
            "SELECT source, COUNT(*) as cnt FROM jobs GROUP BY source"
        ).fetchall()
        for row in rows:
            source_counts[row["source"]] = row["cnt"]

        # Score distribution
        score_brackets = {"90-100": 0, "70-89": 0, "50-69": 0, "30-49": 0, "0-29": 0}
        rows = conn.execute("SELECT score FROM jobs WHERE score > 0").fetchall()
        for row in rows:
            s = row["score"]
            if s >= 90:
                score_brackets["90-100"] += 1
            elif s >= 70:
                score_brackets["70-89"] += 1
            elif s >= 50:
                score_brackets["50-69"] += 1
            elif s >= 30:
                score_brackets["30-49"] += 1
            else:
                score_brackets["0-29"] += 1

        # Applications
        total_applied = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        successful = conn.execute(
            "SELECT COUNT(*) FROM applications WHERE result = 'success'"
        ).fetchone()[0]
        failed = conn.execute(
            "SELECT COUNT(*) FROM applications WHERE result = 'failure'"
        ).fetchone()[0]

        # Top scoring jobs
        top_jobs = conn.execute(
            """
            SELECT title, company, location, score, route_status, url
            FROM jobs
            WHERE score > 0
            ORDER BY score DESC
            LIMIT 10
            """
        ).fetchall()

        # Recent applications
        recent_apps = conn.execute(
            """
            SELECT j.title, j.company, a.result, a.applied_at, a.failure_reason
            FROM applications a
            JOIN jobs j ON a.job_id = j.id
            ORDER BY a.applied_at DESC
            LIMIT 10
            """
        ).fetchall()

        # Recent runs
        run_logs = list_run_logs(limit=5)

    return {
        "generated_at": datetime.now().isoformat(),
        "total_jobs": total_jobs,
        "route_counts": route_counts,
        "source_counts": source_counts,
        "score_brackets": score_brackets,
        "total_applied": total_applied,
        "successful_apps": successful,
        "failed_apps": failed,
        "top_jobs": [dict(r) for r in top_jobs],
        "recent_applications": [dict(r) for r in recent_apps],
        "recent_runs": run_logs,
    }


def print_terminal_report(stats: Optional[dict] = None) -> None:
    """Print a formatted report to the terminal.

    Args:
        stats: Pre-computed stats dict. Computed if None.
    """
    if stats is None:
        stats = get_summary_stats()

    print("\n" + "=" * 60)
    print("  JOB AGENT – RUN SUMMARY REPORT")
    print(f"  Generated: {stats['generated_at']}")
    print("=" * 60)

    # Overview
    print(f"\n  Total jobs collected:     {stats['total_jobs']}")
    print(f"  Total applications:       {stats['total_applied']}")
    print(f"    Successful:             {stats['successful_apps']}")
    print(f"    Failed:                 {stats['failed_apps']}")

    # By route
    print("\n  Routing Breakdown:")
    for status, count in sorted(stats["route_counts"].items()):
        print(f"    {status:20s}  {count}")

    # By source
    print("\n  Jobs by Source:")
    for source, count in sorted(stats["source_counts"].items()):
        print(f"    {source:20s}  {count}")

    # Score distribution
    print("\n  Score Distribution:")
    for bracket, count in stats["score_brackets"].items():
        bar = "#" * min(count, 40)
        print(f"    {bracket:10s}  {count:4d}  {bar}")

    # Top jobs
    if stats["top_jobs"]:
        print("\n  Top Scoring Jobs:")
        for i, job in enumerate(stats["top_jobs"][:5], 1):
            print(f"    {i}. [{job['score']:.0f}] {job['title']} @ {job['company'] or '?'}"
                  f" ({job['route_status']})")

    # Recent applications
    if stats["recent_applications"]:
        print("\n  Recent Applications:")
        for app in stats["recent_applications"][:5]:
            icon = "OK" if app["result"] == "success" else "FAIL"
            print(f"    [{icon}] {app['title']} @ {app['company'] or '?'}")
            if app.get("failure_reason"):
                print(f"           Reason: {app['failure_reason'][:60]}")

    # Recent runs
    if stats["recent_runs"]:
        print("\n  Recent Runs:")
        for run in stats["recent_runs"][:3]:
            print(f"    [{run.get('source', '?')}] "
                  f"found={run.get('total_found', 0)} "
                  f"new={run.get('total_new', 0)} "
                  f"applied={run.get('total_applied', 0)} "
                  f"failed={run.get('total_failed', 0)}")

    print("\n" + "=" * 60 + "\n")


def generate_html_report(stats: Optional[dict] = None) -> Path:
    """Generate an HTML summary report.

    Args:
        stats: Pre-computed stats dict. Computed if None.

    Returns:
        Path to the generated HTML file.
    """
    if stats is None:
        stats = get_summary_stats()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"report_{timestamp}.html"

    # Build HTML
    top_jobs_rows = ""
    for job in stats["top_jobs"]:
        top_jobs_rows += f"""
        <tr>
            <td>{html.escape(str(job.get('score', 0)))}</td>
            <td><a href="{html.escape(job.get('url', '#'))}">{html.escape(job.get('title', ''))}</a></td>
            <td>{html.escape(job.get('company', '') or 'N/A')}</td>
            <td>{html.escape(job.get('location', '') or 'N/A')}</td>
            <td>{html.escape(job.get('route_status', ''))}</td>
        </tr>"""

    recent_apps_rows = ""
    for app in stats["recent_applications"]:
        result_class = "success" if app["result"] == "success" else "failure"
        recent_apps_rows += f"""
        <tr class="{result_class}">
            <td>{html.escape(app.get('result', ''))}</td>
            <td>{html.escape(app.get('title', ''))}</td>
            <td>{html.escape(app.get('company', '') or 'N/A')}</td>
            <td>{html.escape(app.get('applied_at', ''))}</td>
            <td>{html.escape(app.get('failure_reason', '') or '')}</td>
        </tr>"""

    route_items = ""
    for status, count in sorted(stats["route_counts"].items()):
        route_items += f"<li><strong>{html.escape(status)}</strong>: {count}</li>"

    source_items = ""
    for source, count in sorted(stats["source_counts"].items()):
        source_items += f"<li><strong>{html.escape(source)}</strong>: {count}</li>"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Job Agent Report – {stats['generated_at']}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 1000px; margin: 40px auto; padding: 0 20px; background: #f5f5f5; color: #333; }}
        h1 {{ color: #1a1a2e; border-bottom: 3px solid #0f3460; padding-bottom: 10px; }}
        h2 {{ color: #0f3460; margin-top: 30px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin: 20px 0; }}
        .stat-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }}
        .stat-card .number {{ font-size: 2em; font-weight: bold; color: #0f3460; }}
        .stat-card .label {{ color: #666; font-size: 0.9em; margin-top: 5px; }}
        table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin: 15px 0; }}
        th {{ background: #0f3460; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 10px 12px; border-bottom: 1px solid #eee; }}
        tr:hover {{ background: #f8f9fa; }}
        tr.success td:first-child {{ color: #27ae60; font-weight: bold; }}
        tr.failure td:first-child {{ color: #e74c3c; font-weight: bold; }}
        ul {{ list-style: none; padding: 0; }}
        ul li {{ padding: 5px 0; }}
        a {{ color: #0f3460; }}
        .timestamp {{ color: #888; font-size: 0.85em; }}
    </style>
</head>
<body>
    <h1>Job Agent Report</h1>
    <p class="timestamp">Generated: {html.escape(stats['generated_at'])}</p>

    <div class="stats-grid">
        <div class="stat-card">
            <div class="number">{stats['total_jobs']}</div>
            <div class="label">Total Jobs</div>
        </div>
        <div class="stat-card">
            <div class="number">{stats['total_applied']}</div>
            <div class="label">Applications</div>
        </div>
        <div class="stat-card">
            <div class="number">{stats['successful_apps']}</div>
            <div class="label">Successful</div>
        </div>
        <div class="stat-card">
            <div class="number">{stats['failed_apps']}</div>
            <div class="label">Failed</div>
        </div>
    </div>

    <h2>Routing Breakdown</h2>
    <ul>{route_items}</ul>

    <h2>Jobs by Source</h2>
    <ul>{source_items}</ul>

    <h2>Top Scoring Jobs</h2>
    <table>
        <tr><th>Score</th><th>Title</th><th>Company</th><th>Location</th><th>Route</th></tr>
        {top_jobs_rows}
    </table>

    <h2>Recent Applications</h2>
    <table>
        <tr><th>Result</th><th>Title</th><th>Company</th><th>Applied At</th><th>Notes</th></tr>
        {recent_apps_rows}
    </table>
</body>
</html>"""

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    logger.info("HTML report saved to: %s", report_path)
    return report_path
