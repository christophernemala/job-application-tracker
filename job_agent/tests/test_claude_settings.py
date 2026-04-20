"""Tests for .claude/settings.json configuration file.

Verifies the structure, schema reference, and plugin configuration
introduced in this PR.
"""

import json
import re
from pathlib import Path

# Resolve the settings file relative to this test file.
# test file: <repo>/.claude/settings.json
# this file: <repo>/job_agent/tests/test_claude_settings.py
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SETTINGS_PATH = _REPO_ROOT / ".claude" / "settings.json"

EXPECTED_SCHEMA_URL = "https://json.schemastore.org/claude-code-settings.json"
EXPECTED_PLUGIN = "claude-mem@thedotmack"
EXPECTED_TOP_LEVEL_KEYS = {"$schema", "enabledPlugins"}


def _load_settings():
    """Parse and return the settings JSON as a dict."""
    return json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# File existence and basic validity
# ---------------------------------------------------------------------------


def test_settings_file_exists():
    """The .claude/settings.json file must exist in the repository."""
    assert _SETTINGS_PATH.exists(), f"Settings file not found at {_SETTINGS_PATH}"


def test_settings_file_is_not_empty():
    """The settings file must not be empty."""
    assert _SETTINGS_PATH.stat().st_size > 0, "Settings file is empty"


def test_settings_is_valid_json():
    """The settings file must contain syntactically valid JSON."""
    content = _SETTINGS_PATH.read_text(encoding="utf-8")
    try:
        json.loads(content)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"settings.json is not valid JSON: {exc}") from exc


def test_settings_parsed_as_dict():
    """The top-level JSON value must be an object (dict)."""
    data = _load_settings()
    assert isinstance(data, dict), f"Expected dict, got {type(data).__name__}"


# ---------------------------------------------------------------------------
# Schema reference
# ---------------------------------------------------------------------------


def test_settings_has_schema_field():
    """settings.json must declare a $schema field."""
    data = _load_settings()
    assert "$schema" in data, "Missing '$schema' key in settings.json"


def test_settings_schema_url_value():
    """The $schema field must reference the Claude Code settings schema."""
    data = _load_settings()
    assert data["$schema"] == EXPECTED_SCHEMA_URL, (
        f"Unexpected $schema value: {data['$schema']!r}"
    )


def test_settings_schema_url_is_string():
    """The $schema value must be a string."""
    data = _load_settings()
    assert isinstance(data["$schema"], str), (
        f"$schema should be str, got {type(data['$schema']).__name__}"
    )


# ---------------------------------------------------------------------------
# enabledPlugins section
# ---------------------------------------------------------------------------


def test_settings_has_enabled_plugins_key():
    """settings.json must contain an 'enabledPlugins' section."""
    data = _load_settings()
    assert "enabledPlugins" in data, "Missing 'enabledPlugins' key in settings.json"


def test_enabled_plugins_is_dict():
    """'enabledPlugins' must be a JSON object (dict), not a list or scalar."""
    data = _load_settings()
    plugins = data["enabledPlugins"]
    assert isinstance(plugins, dict), (
        f"'enabledPlugins' should be dict, got {type(plugins).__name__}"
    )


def test_claude_mem_plugin_is_present():
    """The 'claude-mem@thedotmack' plugin entry must exist."""
    data = _load_settings()
    assert EXPECTED_PLUGIN in data["enabledPlugins"], (
        f"Plugin '{EXPECTED_PLUGIN}' not found in enabledPlugins: "
        f"{list(data['enabledPlugins'].keys())}"
    )


def test_claude_mem_plugin_is_enabled():
    """The 'claude-mem@thedotmack' plugin must be set to true."""
    data = _load_settings()
    assert data["enabledPlugins"][EXPECTED_PLUGIN] is True, (
        f"Expected plugin '{EXPECTED_PLUGIN}' to be True, "
        f"got {data['enabledPlugins'][EXPECTED_PLUGIN]!r}"
    )


def test_claude_mem_plugin_value_is_boolean():
    """The plugin value must be a native boolean, not a string or integer."""
    data = _load_settings()
    value = data["enabledPlugins"][EXPECTED_PLUGIN]
    assert isinstance(value, bool), (
        f"Plugin value should be bool, got {type(value).__name__}: {value!r}"
    )


# ---------------------------------------------------------------------------
# Structure / regression guards
# ---------------------------------------------------------------------------


def test_settings_top_level_keys_are_expected():
    """No unexpected keys should appear at the top level of settings.json."""
    data = _load_settings()
    extra = set(data.keys()) - EXPECTED_TOP_LEVEL_KEYS
    assert not extra, f"Unexpected top-level keys found: {extra}"


def test_plugin_name_follows_name_at_author_format():
    """Plugin names must follow the '<name>@<author>' convention."""
    data = _load_settings()
    pattern = re.compile(r"^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+$")
    for plugin_name in data["enabledPlugins"]:
        assert pattern.match(plugin_name), (
            f"Plugin name '{plugin_name}' does not match '<name>@<author>' format"
        )


def test_enabled_plugins_has_at_least_one_entry():
    """'enabledPlugins' must not be an empty object."""
    data = _load_settings()
    assert len(data["enabledPlugins"]) >= 1, (
        "'enabledPlugins' is empty — expected at least one plugin entry"
    )


def test_settings_schema_url_uses_https():
    """The schema URL must use HTTPS, not HTTP."""
    data = _load_settings()
    assert data["$schema"].startswith("https://"), (
        f"$schema URL should use HTTPS: {data['$schema']!r}"
    )