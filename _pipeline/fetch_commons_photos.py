#!/usr/bin/env python3
"""Find reusable Wikimedia Commons photos; never downloads image files."""
import argparse
import html
import json
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from fetch_snow import atomic_json

ROOT = Path(__file__).resolve().parent.parent
ENGLISH_NAMES = {
    'niseko':'Niseko Grand Hirafu', 'rusutsu':'Rusutsu Resort', 'kiroro':'Kiroro',
    'teine':'Sapporo Teine', 'furano':'Furano Ski Resort', 'tomamu':'Tomamu',
    'appi':'Appi Kogen', 'zao':'Zao Onsen', 'hakkoda':'Hakkoda',
    'happo':'Hakuba Happo-one', 'hakuba47':'Hakuba 47', 'tsugaike':'Tsugaike Kogen',
    'cortina':'Hakuba Cortina', 'nozawa':'Nozawa Onsen', 'shiga':'Shiga Kogen',
    'madarao':'Madarao Kogen', 'karuizawa':'Karuizawa Prince Hotel Ski Resort',
    'akakura':'Akakura Onsen', 'arai':'Lotte Arai Resort', 'gala':'GALA Yuzawa',
    'naeba':'Naeba', 'kagura':'Kagura'
}


def plain(value):
    return re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]*>', '', value or ''))).strip()


def allowed_license(value):
    value = plain(value)
    return bool(re.fullmatch(r'(?:CC0(?: 1\.0)?|Public domain|CC BY(?:-SA)? \d+(?:\.\d+)?)', value, re.I))


def query(search):
    params={'action':'query','format':'json','generator':'search','gsrnamespace':6,
            'gsrsearch':search,'gsrlimit':20,'prop':'imageinfo','iiprop':'url|extmetadata|size','iiurlwidth':960}
    req=urllib.request.Request('https://commons.wikimedia.org/w/api.php?'+urllib.parse.urlencode(params),
                               headers={'User-Agent':'Sarayuki/1.0 (ski resort photo attribution tool)'})
    for wait in (10, 30, None):
        try:
            with urllib.request.urlopen(req,timeout=15) as response:
                return json.load(response).get('query',{}).get('pages',{}).values()
        except urllib.error.HTTPError as error:
            # Commons 連續查詢會回 429，等一下再試
            if error.code != 429 or wait is None:
                raise
            time.sleep(wait)
        finally:
            time.sleep(2)


def choose(pages, excluded):
    candidates=[]
    for page in pages:
        if page.get('title') in excluded:
            continue
        for info in page.get('imageinfo',[]):
            meta=info.get('extmetadata',{})
            get=lambda key: meta.get(key,{}).get('value','')
            license=plain(get('LicenseShortName'))
            if not allowed_license(license):
                continue
            thumb=info.get('thumburl','')
            if urllib.parse.urlparse(thumb).hostname not in ('upload.wikimedia.org', 'thumb.wikimedia.org'):
                continue
            text=page.get('title','')+' '+plain(get('ImageDescription'))
            landscape=info.get('width',0)>info.get('height',0)
            large=info.get('width',0)>=1200
            snowy=bool(re.search(r'snow|ski|スキー|雪',text,re.I))
            score=(landscape and large, snowy, landscape, large)
            candidates.append((score,{'thumb':thumb,
                'file':'https://commons.wikimedia.org/wiki/'+urllib.parse.quote(page['title'].replace(' ','_'),safe=':'),
                'author':plain(get('Artist')), 'license':license,'licenseUrl':html.unescape(get('LicenseUrl'))}))
    return max(candidates,key=lambda item:item[0])[1] if candidates else None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resort')
    parser.add_argument('--exclude-file',action='append',default=[])
    parser.add_argument('--force',action='store_true')
    args=parser.parse_args()
    resorts=json.loads((ROOT/'data/resorts.json').read_text())['resorts']
    if args.resort and not any(r['id']==args.resort for r in resorts):
        parser.error('Unknown resort id')
    path=ROOT/'data/photos.json'
    photos=json.loads(path.read_text()) if path.exists() else {}
    for resort in resorts:
        rid=resort['id']
        if args.resort and rid!=args.resort or rid in photos and not args.force:
            continue
        try:
            photo=None
            english=resort.get('nameEn') or ENGLISH_NAMES[rid]
            for search in (f'"{resort["nameJa"]}" スキー', f'{english} ski', f'{english.split()[0]} ski'):
                photo=choose(query(search),set(args.exclude_file))
                if photo:
                    break
            if photo:
                photos[rid]=photo
            elif args.force:
                photos.pop(rid,None)
            atomic_json(path,photos)
            print(f'{rid}: {photo["file"] if photo else "no match"}')
        except (OSError,ValueError,KeyError) as error:
            print(f'Warning: {rid}: {error}')

if __name__=='__main__':
    main()
