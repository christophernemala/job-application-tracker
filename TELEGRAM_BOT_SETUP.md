# Telegram Bot Setup Guide

The job application tracker now includes a Telegram bot that lets you query your applications directly from Telegram.

## 1. Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Choose a name (e.g., "Job Tracker Bot")
4. Choose a username (must end with `_bot`, e.g., `my_job_tracker_bot`)
5. Copy the **API token** (looks like `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

## 2. Set Environment Variables

### On Render (Production)

1. Go to your Render dashboard → **job-application-tracker** service
2. Click **Environment**
3. Add these two variables:
   - **`TELEGRAM_BOT_TOKEN`**: Paste the API token from step 1
   - **`TELEGRAM_WEBHOOK_URL`**: Your public Render URL (e.g., `https://job-tracker.onrender.com`)
4. Click **Save Changes**
5. Render will auto-redeploy with the new variables

### Locally (Development)

1. Copy `.env.example` to `.env`
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` and add:
   ```
   TELEGRAM_BOT_TOKEN=your_token_here
   TELEGRAM_WEBHOOK_URL=http://localhost:5001
   ```
3. For local testing with webhooks, you'll need a public tunnel (e.g., `ngrok`):
   ```bash
   ngrok http 5001
   ```
   Then use the ngrok URL as `TELEGRAM_WEBHOOK_URL`.

## 3. Verify the Connection

Once deployed, the webhook automatically registers with Telegram on startup (you'll see a log message).

Send your bot a test message:
- `/help` — shows all available commands

## 4. Available Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/help` | List all commands |
| `/status` | Summary of applications by status |
| `/recent` | Last 5 applications |
| `/app <id>` | Details for a specific application |

## Examples

**Check how many applications you've submitted:**
```
/status
```
→ Returns counts by status (applied, interview, rejected, etc.)

**Get your 5 most recent applications:**
```
/recent
```
→ Shows job title, company, match score, and status

**View details of application #3:**
```
/app 3
```
→ Shows full details: job title, company, platform, applied date, status, score, URL, and notes

## Troubleshooting

### Bot doesn't respond
- Check that `TELEGRAM_BOT_TOKEN` is set correctly in your environment
- Check that `TELEGRAM_WEBHOOK_URL` is your public server URL (must be HTTPS)
- Restart the app: the webhook registers on startup

### "Invalid webhook URL" error
- `TELEGRAM_WEBHOOK_URL` must be reachable over HTTPS
- If using Render, use `https://job-tracker-XXXXX.onrender.com` (your actual domain)
- If developing locally, use ngrok: `ngrok http 5001`

### Bot times out
- Ensure your server is running
- Check Render logs: **Logs** tab in your service

## Security

- The webhook route `/webhook/telegram/<token>` validates the token in the URL path
- Only requests matching your token are processed
- Never commit `.env` with the bot token to version control

## Disabling the Bot

To disable the bot without removing the code:
1. Leave `TELEGRAM_BOT_TOKEN` empty in your environment
2. The bot gracefully skips initialization if the token is missing
