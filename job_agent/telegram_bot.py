"""Telegram bot integration for the job application tracker."""

from __future__ import annotations

import os
import logging
import requests

from job_agent.database import get_application, list_applications

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
WEBHOOK_URL = os.getenv("TELEGRAM_WEBHOOK_URL", "")

_TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def _api(method: str, **kwargs) -> dict:
    url = _TELEGRAM_API.format(token=TELEGRAM_BOT_TOKEN, method=method)
    resp = requests.post(url, json=kwargs, timeout=10)
    return resp.json()


def set_webhook() -> None:
    if not TELEGRAM_BOT_TOKEN or not WEBHOOK_URL:
        logger.warning("Telegram bot not configured — skipping webhook registration")
        return
    result = _api("setWebhook", url=f"{WEBHOOK_URL}/webhook/telegram/{TELEGRAM_BOT_TOKEN}")
    if result.get("ok"):
        logger.info("Telegram webhook registered: %s", WEBHOOK_URL)
    else:
        logger.error("Telegram webhook registration failed: %s", result)


def send_message(chat_id: int | str, text: str) -> None:
    if not TELEGRAM_BOT_TOKEN:
        return
    _api("sendMessage", chat_id=chat_id, text=text, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def _handle_start(chat_id: int | str) -> None:
    send_message(chat_id, (
        "*Job Application Tracker Bot*\n\n"
        "Track your job applications right from Telegram.\n\n"
        "Type /help to see available commands."
    ))


def _handle_help(chat_id: int | str) -> None:
    send_message(chat_id, (
        "*Available commands*\n\n"
        "/status — summary of applications by status\n"
        "/recent — last 5 applications\n"
        "/app <id> — details for a specific application\n"
        "/help — show this message"
    ))


def _handle_status(chat_id: int | str) -> None:
    apps = list_applications()
    if not apps:
        send_message(chat_id, "No applications tracked yet.")
        return

    counts: dict[str, int] = {}
    for a in apps:
        counts[a["status"]] = counts.get(a["status"], 0) + 1

    lines = [f"*Application summary* ({len(apps)} total)\n"]
    for status, count in sorted(counts.items()):
        lines.append(f"• {status}: {count}")
    send_message(chat_id, "\n".join(lines))


def _handle_recent(chat_id: int | str) -> None:
    apps = list_applications()[:5]
    if not apps:
        send_message(chat_id, "No applications tracked yet.")
        return

    lines = ["*Recent applications*\n"]
    for a in apps:
        score = f" ({a['match_score']}%)" if a.get("match_score") else ""
        lines.append(f"[{a['id']}] {a['job_title']} @ {a['company']}{score} — _{a['status']}_")
    send_message(chat_id, "\n".join(lines))


def _handle_app(chat_id: int | str, args: str) -> None:
    if not args.strip().isdigit():
        send_message(chat_id, "Usage: /app <id>  (e.g. /app 3)")
        return

    app = get_application(int(args.strip()))
    if not app:
        send_message(chat_id, f"No application found with id {args.strip()}.")
        return

    score = f"{app['match_score']}%" if app.get("match_score") else "n/a"
    url_line = f"\nURL: {app['job_url']}" if app.get("job_url") else ""
    notes_line = f"\nNotes: {app['notes']}" if app.get("notes") else ""

    send_message(chat_id, (
        f"*{app['job_title']}* @ {app['company']}\n"
        f"Platform: {app['platform']}\n"
        f"Status: _{app['status']}_\n"
        f"Match score: {score}\n"
        f"Applied: {app['applied_date']}"
        f"{url_line}{notes_line}"
    ))


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def handle_update(update: dict) -> None:
    """Route an incoming Telegram update to the appropriate handler."""
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    chat_id = message["chat"]["id"]
    text: str = message.get("text", "").strip()

    if not text.startswith("/"):
        return

    command, _, args = text.partition(" ")
    command = command.split("@")[0].lower()

    if command == "/start":
        _handle_start(chat_id)
    elif command == "/help":
        _handle_help(chat_id)
    elif command == "/status":
        _handle_status(chat_id)
    elif command == "/recent":
        _handle_recent(chat_id)
    elif command == "/app":
        _handle_app(chat_id, args)
    else:
        send_message(chat_id, "Unknown command. Type /help for a list of commands.")
