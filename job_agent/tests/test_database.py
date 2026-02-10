from pathlib import Path

from job_agent import database


def test_init_and_insert_application(tmp_path: Path):
    test_db = tmp_path / "test.db"
    database.init_database(test_db)

    with database.get_connection(test_db) as conn:
        conn.execute(
            """
            INSERT INTO applications (job_title, company, platform, job_url, status)
            VALUES ('AR Specialist', 'ACME', 'LinkedIn', 'http://example.com', 'applied')
            """
        )

    with database.get_connection(test_db) as conn:
        row = conn.execute("SELECT COUNT(*) as c FROM applications").fetchone()
        assert row["c"] == 1
