#!/usr/bin/env python3
import json, os, datetime
from pathlib import Path
import requests


def load_env(env_file: str | None = None):
    if env_file:
        for line in Path(env_file).read_text(encoding='utf-8').splitlines():
            s=line.strip()
            if not s or s.startswith('#') or '=' not in s:
                continue
            k,v=s.split('=',1)
            os.environ.setdefault(k.strip(), v.strip())


def getenv(name:str, default:str|None=None, required=False):
    v=os.getenv(name, default)
    if required and (v is None or v==''):
        raise RuntimeError(f'Missing env: {name}')
    return v


def pdt(s:str|None):
    if not s:
        return None
    s=s.replace('Z','+00:00')
    dt=datetime.datetime.fromisoformat(s)
    if dt.tzinfo is not None:
        dt=dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return dt


def norm_type(t:str|None):
    t=(t or '').lower()
    if 'ride' in t or 'cycl' in t: return 'ride'
    if 'run' in t: return 'run'
    if 'swim' in t or 'nata' in t: return 'swim'
    if 'workout' in t or 'weight' in t or 'strength' in t: return 'workout'
    return t


def strava_refresh_token(client_id, client_secret, refresh_token):
    r=requests.post('https://www.strava.com/oauth/token', data={
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
    }, timeout=20)
    r.raise_for_status()
    return r.json()


def intervals_get(path:str, api_key:str):
    r=requests.get(f'https://intervals.icu{path}', auth=('API_KEY',api_key), timeout=20)
    r.raise_for_status()
    return r.json()


def jlog(path, obj):
    p=Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('a',encoding='utf-8') as f:
        f.write(json.dumps(obj, ensure_ascii=False)+'\n')
