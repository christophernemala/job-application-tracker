"""Configuration loader for the job agent.

Loads JSON config files and environment variables, providing
validated access to profile, rules, answers, and sources.
"""

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.utils.logger import get_logger

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"

# Load .env from project root
_env_path = PROJECT_ROOT / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
    logger.info("Loaded .env from %s", _env_path)


def _load_json(filename: str) -> dict:
    """Load a JSON file from the config directory.

    Args:
        filename: Name of the JSON file in config/.

    Returns:
        Parsed dict from the JSON file.

    Raises:
        FileNotFoundError: If the config file doesn't exist.
        json.JSONDecodeError: If the file contains invalid JSON.
    """
    filepath = CONFIG_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Config file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    logger.debug("Loaded config: %s (%d keys)", filename, len(data))
    return data


def load_profile() -> dict:
    """Load candidate profile configuration."""
    return _load_json("profile.json")


def load_rules() -> dict:
    """Load scoring and filtering rules."""
    return _load_json("rules.json")


def load_answers() -> dict:
    """Load pre-filled answers for application forms."""
    return _load_json("answers.json")


def load_sources() -> dict:
    """Load job source configurations."""
    return _load_json("sources.json")


def get_enabled_sources() -> list[dict]:
    """Return only enabled sources from sources.json."""
    sources_config = load_sources()
    enabled = [s for s in sources_config.get("sources", []) if s.get("enabled", False)]
    logger.info("Enabled sources: %s", [s["name"] for s in enabled])
    return enabled


def get_env(key: str, default: str = "") -> str:
    """Get an environment variable with a default.

    Args:
        key: Environment variable name.
        default: Default value if not set.

    Returns:
        The environment variable value or default.
    """
    return os.environ.get(key, default)


def get_db_path() -> Path:
    """Get the SQLite database file path."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / "jobs.db"


def get_resume_path(variant: str) -> Path:
    """Get the path to a resume variant.

    Args:
        variant: Resume variant key from profile.json (e.g., 'ar_collections').

    Returns:
        Path to the resume file.

    Raises:
        KeyError: If the variant doesn't exist in profile config.
    """
    profile = load_profile()
    variants = profile.get("resume_variants", {})
    if variant not in variants:
        raise KeyError(
            f"Resume variant '{variant}' not found. Available: {list(variants.keys())}"
        )
    return DATA_DIR / variants[variant]


def get_scoring_weights() -> dict[str, int]:
    """Get scoring weights from rules config."""
    rules = load_rules()
    return rules.get("scoring_weights", {})
