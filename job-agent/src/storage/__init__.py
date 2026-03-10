"""Storage module – SQLite database operations."""

from src.storage.database import (
    init_database,
    get_connection,
)
from src.storage.jobs_repo import (
    insert_job,
    upsert_job,
    get_job_by_id,
    get_jobs_by_status,
    update_job_score,
    update_job_route,
    is_duplicate_job,
    list_recent_jobs,
)
from src.storage.applications_repo import (
    insert_application,
    get_application_by_job_id,
    list_applications,
    update_application_result,
)
from src.storage.run_logs_repo import (
    insert_run_log,
    update_run_log,
    get_latest_run_log,
)
