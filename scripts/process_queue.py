#!/usr/bin/env python3
import json, time, subprocess, uuid
from pathlib import Path
from _lib import load_env, getenv, jlog


def main():
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('--env-file')
    args=ap.parse_args()
    load_env(args.env_file)

    queue_dir=Path(getenv('SYNC_QUEUE_DIR','/home/andrebbruno/.openclaw/workspace/data/intervals_sync_queue'))
    processed_dir=queue_dir / 'processed'
    failed_dir=queue_dir / 'failed'
    queue_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    failed_dir.mkdir(parents=True, exist_ok=True)

    logf=getenv('SYNC_LOG_FILE','/tmp/intervals_strava_sync_log.jsonl')
    delay_seconds=int(getenv('SYNC_DELAY_SECONDS','120'))

    files=sorted(queue_dir.glob('*.json'))
    if not files:
        print('NO_QUEUE_ITEMS')
        return

    now=time.time()
    handled=0
    for f in files:
        try:
            payload=json.loads(f.read_text(encoding='utf-8'))
            created=float(payload.get('_queued_at', now))
            if now - created < delay_seconds:
                continue

            event=payload.get('event') or {}
            activity=event.get('activity') or {}
            cmd=['python3', str(Path(__file__).with_name('sync_activity.py'))]
            if args.env_file:
                cmd += ['--env-file', args.env_file]
            if activity.get('start_date_local'):
                cmd += ['--target-start', str(activity.get('start_date_local'))]
            elif activity.get('start_date'):
                cmd += ['--target-start', str(activity.get('start_date'))]
            if activity.get('type'):
                cmd += ['--target-type', str(activity.get('type'))]
            if activity.get('elapsed_time') is not None:
                cmd += ['--target-elapsed', str(activity.get('elapsed_time'))]
            cmd += ['--apply']

            r=subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            jlog(logf, {
                'queue_file': f.name,
                'event_type': event.get('type'),
                'activity_id': activity.get('id'),
                'rc': r.returncode,
                'stdout': (r.stdout or '')[:1200],
                'stderr': (r.stderr or '')[:600],
            })

            # create notification
            notify_dir=Path(getenv('SYNC_NOTIFY_DIR','/home/andrebbruno/.openclaw/workspace/data/sync_notifications'))
            notify_dir.mkdir(parents=True, exist_ok=True)
            note={'event_type': event.get('type'), 'status': 'error', 'stdout': (r.stdout or '')[:1200], 'stderr': (r.stderr or '')[:600]}
            try:
                parsed=json.loads(r.stdout) if r.stdout else {}
                if isinstance(parsed, dict):
                    note.update(parsed)
                if parsed.get('write_ok') or parsed.get('ok'):
                    note['status']='success'
            except Exception:
                pass
            (notify_dir / f'{uuid.uuid4().hex}.json').write_text(json.dumps(note,ensure_ascii=False,indent=2),encoding='utf-8')

            target = processed_dir if r.returncode == 0 else failed_dir
            f.rename(target / f.name)
            handled += 1
        except Exception as e:
            jlog(logf, {'queue_file': f.name, 'queue_error': str(e)})
            try:
                f.rename(failed_dir / f.name)
            except Exception:
                pass
    print(f'PROCESSED_QUEUE_ITEMS={handled}')


if __name__ == '__main__':
    main()
