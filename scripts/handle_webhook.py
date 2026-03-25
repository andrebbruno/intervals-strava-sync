#!/usr/bin/env python3
import argparse, json, sys, uuid, time
from pathlib import Path
from _lib import load_env, getenv, jlog
import subprocess


def load_state(path):
    p=Path(path)
    if not p.exists():
        return {'seen': []}
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return {'seen': []}


def save_state(path, st):
    p=Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--env-file')
    ap.add_argument('--stdin', action='store_true')
    ap.add_argument('--payload-file')
    ap.add_argument('--apply', action='store_true')
    args=ap.parse_args()
    load_env(args.env_file)

    secret=getenv('INTERVALS_WEBHOOK_SECRET', required=True)
    allowed=[x.strip() for x in getenv('WEBHOOK_ALLOWED_EVENT_TYPES','ACTIVITY_UPLOADED,ACTIVITY_ANALYZED,ACTIVITY_UPDATED').split(',') if x.strip()]
    target_athlete=getenv('INTERVALS_ATHLETE_ID', required=True)
    state_file=getenv('SYNC_STATE_FILE','/tmp/intervals_strava_sync_state.json')
    logf=getenv('SYNC_LOG_FILE','/tmp/intervals_strava_sync_log.jsonl')
    notify_dir=Path(getenv('SYNC_NOTIFY_DIR','/home/andrebbruno/.openclaw/workspace/data/sync_notifications'))
    sync_delay_seconds=int(getenv('SYNC_DELAY_SECONDS','120'))

    raw=''
    if args.stdin:
        raw=sys.stdin.read()
    elif args.payload_file:
        raw=Path(args.payload_file).read_text(encoding='utf-8')
    else:
        raise SystemExit('Provide --stdin or --payload-file')

    payload=json.loads(raw)
    if payload.get('secret')!=secret:
        raise SystemExit('Invalid webhook secret')

    state=load_state(state_file)
    seen=set(state.get('seen',[]))
    processed=[]

    for ev in payload.get('events',[]):
        et=ev.get('type')
        athlete_id = str(ev.get('athlete_id') or '')
        ek=f"{athlete_id}|{et}|{ev.get('timestamp')}|{ev.get('activity',{}).get('id')}"
        if athlete_id != str(target_athlete):
            continue
        if et not in allowed:
            continue
        if ek in seen:
            continue

        # execute sync in dry-run/apply mode, anchored by webhook activity timing/type
        cmd=['python3', str(Path(__file__).with_name('sync_activity.py'))]
        if args.env_file:
            cmd += ['--env-file', args.env_file]
        activity = ev.get('activity') or {}
        # Primary anchor: activity start time from the webhook payload itself.
        # Only fall back to event timestamp if activity start time is unavailable.
        if activity.get('start_date_local'):
            cmd += ['--target-start', str(activity.get('start_date_local'))]
        elif activity.get('start_date'):
            cmd += ['--target-start', str(activity.get('start_date'))]
        elif ev.get('timestamp'):
            cmd += ['--target-start', str(ev.get('timestamp'))]
        if activity.get('type'):
            cmd += ['--target-type', str(activity.get('type'))]
        if activity.get('elapsed_time') is not None:
            cmd += ['--target-elapsed', str(activity.get('elapsed_time'))]
        if args.apply:
            cmd += ['--apply']
        else:
            cmd += ['--dry-run']

        # Give Strava time to ingest the corresponding activity before matching.
        if sync_delay_seconds > 0:
            time.sleep(sync_delay_seconds)

        r=subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        jlog(logf, {'webhook_event_key': ek, 'event_type': et, 'rc': r.returncode, 'stdout': r.stdout[:1200], 'stderr': r.stderr[:600]})

        notify_dir.mkdir(parents=True, exist_ok=True)
        note = {
            'event_type': et,
            'status': 'error',
            'stdout': (r.stdout or '')[:1200],
            'stderr': (r.stderr or '')[:600],
        }
        try:
            parsed = json.loads(r.stdout) if r.stdout else {}
            note.update(parsed if isinstance(parsed, dict) else {})
            if parsed.get('write_ok') or parsed.get('ok'):
                note['status'] = 'success'
            else:
                note['status'] = 'error'
        except Exception:
            pass
        note_path = notify_dir / f"{uuid.uuid4().hex}.json"
        note_path.write_text(json.dumps(note, ensure_ascii=False, indent=2), encoding='utf-8')

        processed.append(ek)
        seen.add(ek)

    # keep recent keys only
    state['seen']=list(seen)[-2000:]
    save_state(state_file, state)

    print(json.dumps({'ok': True, 'processed_events': len(processed)}, ensure_ascii=False))


if __name__=='__main__':
    main()
