"""Vercel entrypoint — re-exports the Flask app from job_agent."""
import sys
import os

# Make project root importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from job_agent.app import app  # noqa: F401  — Vercel needs `app` in this module
