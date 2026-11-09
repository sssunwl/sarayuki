#!/usr/bin/env python3
"""Publish unmodified JMA observations; standard library only."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
JST = dt.timezone(dt.timedelta(hours=9))
BASE = 'https://www.jma.go.jp/bosai/amedas/data/'


def request(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Sarayuki/1.0 (AMeDAS observation reader)'})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.read().decode('utf-8').strip()
    finally:
        time.sleep(.5)


def station_observation(code, station, latest, getter=request):
    block = latest.replace(hour=latest.hour // 3 * 3, minute=0, second=0, microsecond=0)
    for offset in (0, 3):
        when = block - dt.timedelta(hours=offset)
        data = json.loads(getter(f'{BASE}point/{code}/{when:%Y%m%d}_{when:%H}.json'))
        keys = [k for k, v in data.items() if ('temp' in v or 'snow' in v or 'precipitation10m' in v) and k <= latest.strftime('%Y%m%d%H%M%S')]
        if not keys:
            continue
        stamp = max(keys)
        values = data[stamp]
        def value(field):
            pair = values.get(field)
            return pair[0] if isinstance(pair, list) and len(pair) >= 2 and pair[1] == 0 else None
        return {'name': station['name'], 'alt': station['alt'],
                'observedAt': dt.datetime.strptime(stamp, '%Y%m%d%H%M%S').replace(tzinfo=JST).isoformat(),
                **{field: value(field) for field in ('snow', 'snow24h', 'temp')}}
    raise ValueError('No observation in either block')


def collect(resorts, getter=request, now=None):
    latest = dt.datetime.fromisoformat(getter(BASE + 'latest_time.txt')).astimezone(JST)
    unique = {}
    for resort in resorts:
        station = resort.get('amedas')
        if station:
            unique.setdefault(station['code'], station)
    stations = {}
    for code, station in unique.items():
        try:
            stations[code] = station_observation(code, station, latest, getter)
        except (OSError, ValueError, KeyError, TypeError) as error:
            print(f'Warning: {code}: {error}', file=sys.stderr)
            stations[code] = None
    if not any(stations.values()):
        raise RuntimeError('Every station failed; previous output retained')
    headline = {'text': '各觀測站目前還沒有積雪紀錄'}
    for field, prefix in (('snow24h', '過去 24 小時降雪最多：'), ('snow', '目前積雪最深：')):
        eligible = [(code, s) for code, s in stations.items() if s and s[field] is not None and s[field] >= 1]
        if eligible:
            code, station = max(eligible, key=lambda item: (item[1][field], item[1].get('snow') or 0))
            headline = {'text': f"{prefix}{station['name']} {station[field]:g} cm", 'stationCode': code}
            break
    return {'generated': (now or dt.datetime.now(JST)).isoformat(),
            'source': '気象庁 アメダス（観測値をそのまま掲載）', 'stations': stations,
            'headline': headline, 'season': 'stationCode' in headline}


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, delete=False) as out:
            name = out.name
            json.dump(data, out, ensure_ascii=False, indent=2)
            out.write('\n')
        os.replace(name, path)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    try:
        data = collect(json.loads((ROOT / 'data/resorts.json').read_text())['resorts'])
        if args.dry_run:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            atomic_json(ROOT / 'data/snow.json', data)
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        print(error, file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
