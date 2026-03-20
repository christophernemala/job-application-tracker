.PHONY: install run scrape shortlist tailor queue submit status export scheduler test mock-run

# ── Setup ────────────────────────────────────────────────────────────────────
install:
	pip install --user -r requirements_pipeline.txt

# ── Full pipeline ─────────────────────────────────────────────────────────────
run:
	python -m pipeline.cli run

run-submit:
	python -m pipeline.cli run --auto-submit

# ── Individual steps ──────────────────────────────────────────────────────────
scrape:
	python -m pipeline.cli scrape

shortlist:
	python -m pipeline.cli shortlist

tailor:
	python -m pipeline.cli tailor

queue:
	python -m pipeline.cli queue

submit:
	python -m pipeline.cli submit

status:
	python -m pipeline.cli status

export:
	python -m pipeline.cli export

# ── Scheduler ─────────────────────────────────────────────────────────────────
scheduler:
	python -m pipeline.cli scheduler

# ── Tests ─────────────────────────────────────────────────────────────────────
test:
	python -m pytest pipeline/tests/ -v

# ── Mock smoke-test (no API keys needed) ─────────────────────────────────────
mock-run:
	MOCK_MODE=true python -m pipeline.cli run
	MOCK_MODE=true python -m pipeline.cli status
	MOCK_MODE=true python -m pipeline.cli queue
