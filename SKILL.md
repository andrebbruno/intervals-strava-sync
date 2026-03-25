---
name: intervals-strava-sync
description: Sync completed activities from Intervals webhooks to Strava using script-first automation (no LLM by default). Use when setting up or operating webhook-driven updates that rename Strava activities and write workout structure into Strava descriptions based on Intervals as source of truth. Includes secure setup with environment variables, health checks, dry-run mode, deduplication, and optional LLM fallback only for low-confidence matches.
---

# Intervals → Strava Sync (Script-First)

## Quick start

1) Read setup checklist: `references/setup.md`
2) Create `.env` from `references/.env.example`
3) Run doctor:
```bash
python3 scripts/doctor.py --env-file /path/to/.env
```
4) Run dry-run sync for latest Strava activity:
```bash
python3 scripts/sync_activity.py --env-file /path/to/.env --dry-run
```

## Core commands

### Sync one activity (manual)

```bash
python3 scripts/sync_activity.py --env-file /path/to/.env --strava-activity-id 17789565443 --apply
```

- `--dry-run`: calculate/update preview only (default)
- `--apply`: write to Strava (`name` and optionally `description`)

### Process webhook payload (event-driven)

```bash
cat payload.json | python3 scripts/handle_webhook.py --env-file /path/to/.env --stdin --apply
```

Behavior:
- Validate Intervals webhook secret
- Deduplicate event IDs
- For supported event types, select candidate Strava activity and run sync
- Write execution log JSONL

## Matching policy (deterministic)

Use this order:
1. **Webhook activity.start_date_local** (or activity.start_date) as the primary start-time anchor
2. **Date + sport type** match (Ride/Run/Swim/Workout)
3. **Closest start time** (minimum delta seconds)
4. **Elapsed time comparison** (`Intervals.activity.elapsed_time` vs `Strava.elapsed_time`)
5. Fallback to webhook event `timestamp` only if activity start time is missing
6. Confidence thresholds:
   - `high`: <= 20 min
   - `medium`: <= 60 min
   - `low`: > 60 min

Default write policy:
- Update title only when confidence is `medium` or `high`
- Update description only when planned workout description exists
- Skip writes when confidence `low` unless `--force` is used
- Skip writes when no planned workout match exists (unplanned activity), unless `--force` is used

## Output policy for Strava

- Keep Strava title concise (planned workout name from Intervals)
- Put structure/steps/zones in Strava description
- Do not duplicate sport type in title (Strava UI already shows sport type)

## Optional LLM fallback

Disabled by default.
Only use LLM for low-confidence ambiguous matches if explicitly enabled with env flag.

## Files

- `scripts/doctor.py`: validate env + endpoints + OAuth refresh
- `scripts/sync_activity.py`: dry-run/apply for one activity
- `scripts/handle_webhook.py`: webhook event processor with dedup/log
- `references/setup.md`: complete setup flow
- `references/.env.example`: required variables template
