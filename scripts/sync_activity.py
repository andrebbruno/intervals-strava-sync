#!/usr/bin/env python3
import argparse, json, re, datetime
import requests
from _lib import load_env, getenv, pdt, norm_type, strava_refresh_token, intervals_get, jlog


def choose_strava_activity(access_token, activity_id=None):
    if activity_id:
        r=requests.get(f'https://www.strava.com/api/v3/activities/{activity_id}', headers={'Authorization':f'Bearer {access_token}'}, timeout=20)
        r.raise_for_status(); return r.json()
    r=requests.get('https://www.strava.com/api/v3/athlete/activities?per_page=20&page=1', headers={'Authorization':f'Bearer {access_token}'}, timeout=20)
    r.raise_for_status(); acts=r.json()
    return acts[0] if acts else None


def build_description(planned):
    if not planned:
        return None
    parts=['🎯 Treino planejado (Intervals)']
    if planned.get('name'):
        parts.append(f"• Sessão: {planned['name']}")
    desc=(planned.get('description') or '').strip()
    if desc:
        clean=re.sub(r'<[^>]+>','',desc)
        lines=[l.strip('-• \t') for l in clean.replace('\r','\n').splitlines() if l.strip()][:8]
        if lines:
            parts += ['', '🧩 Estrutura'] + [f'• {x}' for x in lines]
    parts += ['', '🤖 Atualizado automaticamente via integração Intervals → Strava']
    txt='\n'.join(parts)
    return txt[:1900]


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--env-file')
    ap.add_argument('--strava-activity-id', type=int)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--force', action='store_true')
    args=ap.parse_args()
    load_env(args.env_file)

    cid=getenv('STRAVA_CLIENT_ID', required=True)
    cs=getenv('STRAVA_CLIENT_SECRET', required=True)
    rt=getenv('STRAVA_REFRESH_TOKEN', required=True)
    ik=getenv('INTERVALS_API_KEY', required=True)
    ia=getenv('INTERVALS_ATHLETE_ID', required=True)
    logf=getenv('SYNC_LOG_FILE','/tmp/intervals_strava_sync_log.jsonl')
    update_desc=(getenv('SYNC_UPDATE_DESCRIPTION','true').lower()=='true')
    max_delta=int(getenv('SYNC_MAX_TIME_DELTA_SEC','3600'))

    tok=strava_refresh_token(cid, cs, rt)
    access=tok['access_token']

    sa=choose_strava_activity(access, args.strava_activity_id)
    if not sa:
        raise SystemExit('No Strava activity found')

    ls=pdt(sa.get('start_date_local')) or pdt(sa.get('start_date'))
    old=(ls.date()-datetime.timedelta(days=1)).isoformat(); new=(ls.date()+datetime.timedelta(days=1)).isoformat()

    arr=intervals_get(f'/api/v1/athlete/{ia}/activities?oldest={old}&newest={new}', ik)
    stype=norm_type(sa.get('sport_type') or sa.get('type'))

    best=None; best_score=10**9
    for a in arr if isinstance(arr,list) else []:
        ts=pdt(a.get('start_date_local'))
        if not ts: continue
        score=abs((ts-ls).total_seconds())
        if norm_type(a.get('type'))!=stype: score += 10800
        if score<best_score: best_score=score; best=a

    conf='low'
    if best_score<=1200: conf='high'
    elif best_score<=max_delta: conf='medium'

    date_local=(sa.get('start_date_local') or '')[:10]
    events=intervals_get(f'/api/v1/athlete/{ia}/events?oldest={date_local}&newest={date_local}', ik)
    workouts=[e for e in (events if isinstance(events,list) else []) if e.get('category')=='WORKOUT']
    planned=None
    if workouts:
        target=(best.get('name') if best else '').lower()
        for e in workouts:
            n=(e.get('name') or '').lower()
            if target and (target in n or n in target): planned=e; break
        if not planned:
            # prefer same type
            for e in workouts:
                if norm_type(e.get('type'))==stype:
                    planned=e; break
        if not planned: planned=workouts[0]

    new_name=(best.get('name') if best and best.get('name') else sa.get('name'))
    new_desc=build_description(planned) if update_desc else None

    out={
        'dry_run': not args.apply,
        'strava_activity_id': sa.get('id'),
        'old_name': sa.get('name'),
        'new_name': new_name,
        'confidence': conf,
        'score_sec': best_score,
        'intervals_match': best.get('name') if best else None,
        'planned_event': planned.get('name') if planned else None,
    }

    can_write = args.apply and (conf!='low' or args.force)
    if can_write:
        payload={'name': new_name}
        if new_desc: payload['description']=new_desc
        r=requests.put(f'https://www.strava.com/api/v3/activities/{sa["id"]}', headers={'Authorization':f'Bearer {access}'}, data=payload, timeout=20)
        out['write_status']=r.status_code
        out['write_ok']=r.status_code==200
    else:
        out['write_skipped']=True

    jlog(logf, out)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__=='__main__':
    main()
