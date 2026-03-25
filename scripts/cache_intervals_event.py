#!/usr/bin/env python3
import argparse, json, time, uuid
from pathlib import Path
from _lib import load_env, getenv


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--env-file')
    ap.add_argument('--stdin', action='store_true')
    ap.add_argument('--payload-file')
    args=ap.parse_args()
    load_env(args.env_file)

    cache_dir=Path(getenv('SYNC_CACHE_DIR','/home/andrebbruno/.openclaw/workspace/data/intervals_sync_cache'))
    cache_dir.mkdir(parents=True, exist_ok=True)

    if args.stdin:
        raw = __import__('sys').stdin.read()
    elif args.payload_file:
        raw = Path(args.payload_file).read_text(encoding='utf-8')
    else:
        raise SystemExit('Provide --stdin or --payload-file')

    payload=json.loads(raw)
    for ev in payload.get('events', []):
        activity=ev.get('activity') or {}
        if not activity:
            continue
        item={'cached_at': time.time(), 'event': ev}
        name=f"{activity.get('id','noid')}-{uuid.uuid4().hex}.json"
        (cache_dir / name).write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding='utf-8')
    print('CACHE_OK')


if __name__ == '__main__':
    main()
