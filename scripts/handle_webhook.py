#!/usr/bin/env python3
import argparse, json, sys
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

        # execute sync in dry-run/apply mode
        cmd=['python3', str(Path(__file__).with_name('sync_activity.py'))]
        if args.env_file:
            cmd += ['--env-file', args.env_file]
        if args.apply:
            cmd += ['--apply']
        else:
            cmd += ['--dry-run']

        r=subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        jlog(logf, {'webhook_event_key': ek, 'event_type': et, 'rc': r.returncode, 'stdout': r.stdout[:1200], 'stderr': r.stderr[:600]})
        processed.append(ek)
        seen.add(ek)

    # keep recent keys only
    state['seen']=list(seen)[-2000:]
    save_state(state_file, state)

    print(json.dumps({'ok': True, 'processed_events': len(processed)}, ensure_ascii=False))


if __name__=='__main__':
    main()
