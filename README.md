# intervals-strava-sync

Script-first automation to sync Intervals.icu activity context into Strava with minimal/no LLM cost.

## What it does

- Receives Intervals webhooks
- Validates webhook secret
- Deduplicates events
- Matches Strava activity with Intervals source-of-truth
- Updates Strava:
  - **name**: planned workout title
  - **description**: workout structure (warmup/main/cooldown/notes)

## Why

Designed for low operational cost:
- deterministic scripts do the heavy lifting
- LLM is optional and should only be used for edge cases

## Included

- `scripts/doctor.py` — env + auth checks
- `scripts/sync_activity.py` — dry-run/apply sync for activities
- `scripts/handle_webhook.py` — webhook processor + dedup
- `references/setup.md` — setup walkthrough
- `references/.env.example` — configuration template

## Quick start

```bash
python3 scripts/doctor.py --env-file /path/to/.env
python3 scripts/sync_activity.py --env-file /path/to/.env --dry-run
python3 scripts/sync_activity.py --env-file /path/to/.env --apply
```

## Security

- Never commit `.env` or tokens
- Rotate leaked tokens immediately
- Always validate webhook secret

## License

MIT

## Prebuilt skill package

This repository also includes a prebuilt `.skill` package: `intervals-strava-sync.skill`
for direct installation in OpenClaw plugin/skill workflows.
