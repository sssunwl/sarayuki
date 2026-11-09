#!/usr/bin/env python3
"""Deterministic shape-only snow-night covers, no external dependencies."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import random
import re

ROOT = Path(__file__).resolve().parent.parent
ACCENTS = {'beginner': '#3d7fe0', 'resort': '#7ce0d3', 'advanced': '#6b5bbf', 'travel': '#e98a7a'}


def cover(slug, category):
    rng = random.Random(int.from_bytes(hashlib.sha256(slug.encode()).digest(), 'big'))
    accent = ACCENTS.get(category, ACCENTS['beginner'])
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 675">',
             '<defs><linearGradient id="sky" x2="0" y2="1"><stop stop-color="#0a1628"/><stop offset=".55" stop-color="#12284a"/><stop offset="1" stop-color="#2b4a7a"/></linearGradient><mask id="moon"><rect width="1200" height="675" fill="white"/><circle cx="984" cy="105" r="37" fill="black"/></mask></defs>',
             '<path fill="url(#sky)" d="M0 0H1200V675H0Z"/>']
    for _ in range(100):
        parts.append(f'<circle cx="{rng.randrange(1200)}" cy="{rng.randrange(630)}" r="{rng.uniform(.6,2.4):.1f}" fill="#f5f8fc" opacity="{rng.uniform(.25,.85):.2f}"/>')
    if rng.random() > .3:
        parts.append('<circle cx="960" cy="120" r="38" fill="#e7eff8" mask="url(#moon)" opacity=".8"/>')
    for layer, color in enumerate(('#2b4a7a', '#8fd3ff', '#e7eff8')):
        base = 355 + layer * 105
        points = [(-80, base+90)]
        peaks = []
        for x in range(80, 1300, 240):
            peak = (x+rng.randrange(-50,50), base-rng.randrange(40,135))
            peaks.append(peak)
            points.extend([peak, (peak[0]+120,base+70)])
        d = 'M'+' L'.join(f'{x},{y}' for x,y in points)+' L1280,675 L-80,675Z'
        parts.append(f'<path d="{d}" fill="{color}" opacity="{.65 if layer < 2 else 1}"/>')
        for x,y in peaks:
            parts.append(f'<path d="M{x},{y} l-40,48 26,-9 17,15 20,-18 26,13Z" fill="#f5f8fc" opacity=".85"/>')
    if category == 'beginner':
        parts.append('<path d="M0 490 Q500 465 1200 660V675H0Z" fill="#f5f8fc"/>')
        for x in range(220,1050,135):
            y = int(490 + (x/1200)**2*160)
            parts.append(f'<path d="M{x},{y}v-45" stroke="#12284a" stroke-width="3"/><path d="M{x},{y-45}l28,8 -28,10Z" fill="{accent}"/>')
    elif category == 'resort':
        y = rng.randrange(170,240)
        parts.append(f'<path d="M0,{y+110}L1200,{y}" stroke="#e7eff8" stroke-width="3"/>')
        for x in range(210,1100,240):
            cy = y+110-x*110/1200
            parts.append(f'<path d="M{x},{cy:.1f}v28" stroke="#e7eff8" stroke-width="3"/><rect x="{x-23}" y="{cy+28:.1f}" width="46" height="37" rx="8" fill="{accent}"/><path d="M{x-17},{cy+35:.1f}h34v14h-34Z" fill="#12284a"/>')
    elif category == 'advanced':
        parts.append('<path d="M0 310L880 675H0Z" fill="#f5f8fc"/>')
        for x in range(30,850,37):
            y = 330+x*.40
            h = rng.randrange(48,95)
            parts.append(f'<path d="M{x},{y-h:.1f}l-22,{h*.7:.1f}h10l-19,{h*.3:.1f}h62l-19,{-h*.3:.1f}h10Z" fill="#12284a"/>')
        parts.append(f'<path d="M250 375Q300 430 480 475T700 580" fill="none" stroke="{accent}" stroke-width="4"/>')
    else:
        x=rng.randrange(160,360)
        parts.append(f'<path d="M80 610H850" stroke="#12284a" stroke-width="6"/><rect x="{x}" y="524" width="345" height="74" rx="19" fill="#12284a"/>')
        for dx in range(20,310,46):
            parts.append(f'<rect x="{x+dx}" y="539" width="32" height="24" rx="4" fill="#8fd3ff"/>')
        parts.append(f'<path d="M{x} 579h345" stroke="{accent}" stroke-width="6"/>')
        for dx in (55,285):
            parts.append(f'<circle cx="{x+dx}" cy="599" r="12" fill="#12284a"/>')
        for sx in (960,1000,1040):
            parts.append(f'<path d="M{sx} 558c-28,-28 28,-40 0,-75" fill="none" stroke="#f5f8fc" stroke-width="5" stroke-linecap="round"/>')
    return ''.join(parts)+'</svg>\n'


def generate(root=ROOT, all_covers=False, slug=None):
    index = root/'content/index.json'
    data = json.loads(index.read_text(encoding='utf-8'))
    out = root/'content/covers'
    out.mkdir(parents=True, exist_ok=True)
    if slug and not any(a['slug'] == slug for a in data['articles']):
        raise ValueError(f'Unknown slug: {slug}')
    for article in data['articles']:
        name = article['slug']
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name):
            raise ValueError('Invalid slug')
        article['cover'] = f'content/covers/{name}.svg'
        path = out/f'{name}.svg'
        if (slug is None or slug == name) and (all_covers or not path.exists()):
            path.write_text(cover(name, article['category']), encoding='utf-8')
    index.write_text(json.dumps(data,ensure_ascii=False,indent=1)+'\n',encoding='utf-8')
    cards = ''.join(f'<figure><img src="{a["slug"]}.svg" alt=""><figcaption>{html.escape(a["title"])}</figcaption></figure>' for a in data['articles'])
    (out/'preview.html').write_text('<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Sarayuki 封面總覽</title><style>body{margin:0;padding:24px;background:#0a1628;color:#f5f8fc;font-family:sans-serif}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));gap:24px}figure{margin:0}img{width:100%;aspect-ratio:16/9;border-radius:12px}figcaption{padding:12px 0;line-height:1.5}</style><main>'+cards+'</main></html>',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--all',action='store_true')
    parser.add_argument('--slug')
    args=parser.parse_args()
    generate(all_covers=args.all,slug=args.slug)

if __name__ == '__main__':
    main()
