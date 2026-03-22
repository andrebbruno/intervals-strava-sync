# Setup

## 1) Create Intervals app and webhooks

1. In Intervals: Settings → Manage App.
2. Set Webhook URL to your public endpoint.
3. Enable at least:
   - `ACTIVITY_UPLOADED`
   - `ACTIVITY_ANALYZED`
4. Save.
5. Authorize athlete via OAuth URL for your app (athlete appears as testing).

## 2) Configure tunnel and receiver

Use Cloudflare Tunnel (or equivalent) so Intervals can reach your endpoint.

Endpoint path expected by this skill workflow:
- `/webhooks/intervals`

## 3) Strava OAuth with write scope

Authorize with scopes including:
- `activity:read_all`
- `activity:write`

Exchange code for refresh token and store in `.env`.

## 4) Prepare env

Copy `references/.env.example` to a private `.env` and fill values.
Never commit `.env`.

## 5) Validate

```bash
python3 scripts/doctor.py --env-file /path/to/.env
```

Doctor checks:
- required variables
- Strava token refresh
- Intervals API access

## 6) Run dry-run

```bash
python3 scripts/sync_activity.py --env-file /path/to/.env --dry-run
```

## 7) Apply write

```bash
python3 scripts/sync_activity.py --env-file /path/to/.env --apply
```

## 8) Enable webhook worker

Use your existing webhook receiver to pass payloads to:

```bash
python3 scripts/handle_webhook.py --env-file /path/to/.env --stdin --apply
```

## Security notes

- Validate `INTERVALS_WEBHOOK_SECRET` on every webhook.
- Keep `STRAVA_CLIENT_SECRET` and refresh token private.
- Rotate leaked credentials immediately.
