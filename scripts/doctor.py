#!/usr/bin/env python3
import argparse, json
from _lib import load_env, getenv, strava_refresh_token, intervals_get


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--env-file')
    args=ap.parse_args()
    load_env(args.env_file)

    cid=getenv('STRAVA_CLIENT_ID', required=True)
    cs=getenv('STRAVA_CLIENT_SECRET', required=True)
    rt=getenv('STRAVA_REFRESH_TOKEN', required=True)
    ik=getenv('INTERVALS_API_KEY', required=True)
    ia=getenv('INTERVALS_ATHLETE_ID', required=True)

    tok=strava_refresh_token(cid, cs, rt)
    acts=intervals_get(f'/api/v1/athlete/{ia}/activities?oldest=2026-01-01&newest=2026-01-02', ik)

    print(json.dumps({
        'ok': True,
        'strava_token_refresh': True,
        'strava_scopes_hint': 'Ensure activity:write was granted during OAuth.',
        'intervals_api': True,
        'intervals_sample_count': len(acts) if isinstance(acts,list) else None,
    }, ensure_ascii=False, indent=2))


if __name__=='__main__':
    main()
