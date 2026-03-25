#!/usr/bin/env python3
import argparse, json, time, re
from pathlib import Path
import requests
from _lib import load_env, getenv, pdt, norm_type, strava_refresh_token, jlog


def choose_cached_match(cache_dir, strava_activity):
    stype = norm_type(strava_activity.get('sport_type') or strava_activity.get('type'))
    sstart = pdt(strava_activity.get('start_date_local')) or pdt(strava_activity.get('start_date'))
    selapsed = float(strava_activity.get('elapsed_time') or 0)

    best=None; best_score=10**18; best_file=None
    for f in sorted(Path(cache_dir).glob('*.json')):
        try:
            item=json.loads(f.read_text(encoding='utf-8'))
            ev=item.get('event') or {}
            act=ev.get('activity') or {}
            astart=pdt(act.get('start_date_local')) or pdt(act.get('start_date'))
            if not astart:
                continue
            score=abs((astart-sstart).total_seconds())
            if norm_type(act.get('type')) != stype:
                score += 10800
            if act.get('elapsed_time') is not None:
                score += abs(float(act.get('elapsed_time')) - selapsed) * 3
            if score < best_score:
                best_score=score; best=act; best_file=f
        except Exception:
            continue
    return best, best_file, best_score


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
    return '\n'.join(parts)[:1900]


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--env-file')
    ap.add_argument('--strava-activity-id', type=int, required=True)
    ap.add_argument('--apply', action='store_true')
    args=ap.parse_args()
    load_env(args.env_file)

    cid=getenv('STRAVA_CLIENT_ID', required=True)
    cs=getenv('STRAVA_CLIENT_SECRET', required=True)
    rt=getenv('STRAVA_REFRESH_TOKEN', required=True)
    ik=getenv('INTERVALS_API_KEY', required=True)
    ia=getenv('INTERVALS_ATHLETE_ID', required=True)
    cache_dir=getenv('SYNC_CACHE_DIR','/home/andrebbruno/.openclaw/workspace/data/intervals_sync_cache')
    logf=getenv('SYNC_LOG_FILE','/tmp/intervals_strava_sync_log.jsonl')

    tok=strava_refresh_token(cid, cs, rt)
    access=tok['access_token']
    sr=requests.get(f'https://www.strava.com/api/v3/activities/{args.strava_activity_id}', headers={'Authorization':f'Bearer {access}'}, timeout=20)
    sr.raise_for_status()
    sa=sr.json()

    act, act_file, score = choose_cached_match(cache_dir, sa)
    conf='low'
    if score <= 1200: conf='high'
    elif score <= 3600: conf='medium'

    date_local=(sa.get('start_date_local') or '')[:10]
    events=requests.get(f'https://intervals.icu/api/v1/athlete/{ia}/events?oldest={date_local}&newest={date_local}',auth=('API_KEY',ik),timeout=20).json()
    workouts=[e for e in (events if isinstance(events,list) else []) if e.get('category')=='WORKOUT']
    planned=None
    if workouts and act:
        target=(act.get('name') or '').lower()
        for e in workouts:
            n=(e.get('name') or '').lower()
            if target and (target in n or n in target):
                planned=e; break
        if not planned:
            same=[e for e in workouts if norm_type(e.get('type')) == norm_type(sa.get('sport_type') or sa.get('type'))]
            if len(same)==1:
                planned=same[0]

    out={
        'strava_activity_id': sa.get('id'),
        'old_name': sa.get('name'),
        'new_name': act.get('name') if act else sa.get('name'),
        'confidence': conf,
        'score_sec': score,
        'intervals_match': act.get('name') if act else None,
        'planned_event': planned.get('name') if planned else None,
    }

    if not act or conf == 'low' or not planned:
        out['write_skipped']=True
        out['reason']='no_confident_planned_match'
        jlog(logf, out)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    if args.apply:
        payload={'name': act.get('name')}
        desc=build_description(planned)
        if desc:
            payload['description']=desc
        ur=requests.put(f'https://www.strava.com/api/v3/activities/{sa["id"]}', headers={'Authorization':f'Bearer {access}'}, data=payload, timeout=20)
        out['write_status']=ur.status_code
        out['write_ok']=ur.status_code==200
        if act_file and ur.status_code==200:
            try:
                Path(act_file).unlink(missing_ok=True)
            except Exception:
                pass
    jlog(logf, out)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
