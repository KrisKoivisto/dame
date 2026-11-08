#!/usr/bin/env python3
"""Fill the ALBUMS and KICKS blocks in src/app.html from the research JSON, and stage images into img/.

Usage: python3 tools/build_data.py <music/albums.json | -> <kicks/shoes.json | -> [clips/clips.json]
Product shots on white studio backgrounds get their background knocked out (PNG with alpha) so they sit on the dark UI.
"""
import json, re, sys, pathlib, shutil
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMG = ROOT / 'img'
APP = ROOT / 'src' / 'app.html'
ALBUM_YT = {'letter-o': 'v2QoU54tKK4', 'confirmed': 'ZVBTEIu8F4c', 'big-dolla': 'fyttopyG7Y4', 'doltla': 'JC-2jPdEBt0', 'don-dolla': 'DWCvAvp2SAk'}
import urllib.parse
def genius(t): return t['genius'] if t.get('genius') else 'https://genius.com/search?q=' + urllib.parse.quote('Dame D.O.L.L.A. ' + t['title'])
SHOE_VIDEO = {'d-lillard-1': ['xdF74W0hHJE'], 'dame-9': ['e3sj9FYiSTQ'], 'dame-x': ['PLHYJPJ4RmA']}
NAME = {'pe-2012-2014': ('The PEs', "Real Deal 'ROY' · Crazy 8 · Crazy 1 · Crazyquick"), 'd-lillard-1': ('D Lillard 1', 'The first signature'), 'd-lillard-2': ('D Lillard 2', ''), 'dame-3': ('Dame 3', "First to carry the name Dame"), 'dame-4': ('Dame 4', ''), 'dame-5': ('Dame 5', ''), 'dame-6': ('Dame 6', 'First on Lightstrike'), 'dame-7': ('Dame 7', 'The NBA 2K21 shoe'), 'dame-8': ('Dame 8', ''), 'dame-certified-1': ('Dame Certified', 'The family line'), 'dame-8-extply': ('Dame 8 EXTPLY', 'Extended play'), 'dame-certified-2': ('Certified 2.0', ''), 'dame-9': ('Dame 9', ''), 'dame-certified-3': ('Certified 3', 'The Dame 9 takedown'), 'dame-x': ('Dame X', 'The tenth, under $100')}
def norm(x): return re.sub(r'[^a-z0-9]+', '', (x or '').lower())
HERO = {'d-lillard-2': 'raw/d-lillard-2--rose-city-1.jpg', 'dame-x': 'raw/dame-x--brookfield-1.png'}
TECH = {'pe-2012-2014': 'Retro PEs', 'd-lillard-1': 'adiprene+', 'd-lillard-2': 'Bounce', 'dame-3': 'Bounce', 'dame-4': 'Bounce', 'dame-5': 'Bounce', 'dame-6': 'Lightstrike', 'dame-7': 'Lightstrike', 'dame-8': 'Bounce Pro', 'dame-certified-1': 'Bounce', 'dame-8-extply': 'Bounce Pro', 'dame-certified-2': 'Bounce', 'dame-9': 'Lightstrike', 'dame-certified-3': 'Bounce', 'dame-x': 'Lightstrike'}
def short(x, n=28):
    if not x: return x
    x = re.split(r' \(|; ', x)[0].strip(); return x if len(x) <= n else re.split(r', ', x)[0][:n].rstrip(' ,')


def jsq(x): return "'" + str(x).replace('\\', '\\\\').replace("'", "\\'").replace('\n', ' ') + "'"

def knockout(src, dst, maxw=1000):
    import cv2
    im = Image.open(src).convert('RGB'); im.thumbnail((maxw, maxw), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32); h, w = a.shape[:2]
    border = np.concatenate([a[:4].reshape(-1, 3), a[-4:].reshape(-1, 3), a[:, :4].reshape(-1, 3), a[:, -4:].reshape(-1, 3)])
    if border.std(0).mean() > 38:  # a photo with a real background: keep it
        im.save(dst.with_suffix('.jpg'), quality=88); return dst.with_suffix('.jpg').name
    bgr = cv2.cvtColor(np.asarray(im), cv2.COLOR_RGB2BGR)
    mask = np.zeros((h, w), np.uint8); bgm = np.zeros((1, 65), np.float64); fgm = np.zeros((1, 65), np.float64)
    rect = (int(w * .03), int(h * .03), int(w * .94), int(h * .94))
    cv2.grabCut(bgr, mask, rect, bgm, fgm, 6, cv2.GC_INIT_WITH_RECT)
    fg = ((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)).astype(np.uint8)
    # drop specks, fill holes
    lab, n = ndimage.label(fg)
    if n > 1:
        sizes = ndimage.sum(fg, lab, range(1, n + 1)); keep = [i + 1 for i, sz in enumerate(sizes) if sz > 0.02 * sizes.max()]
        fg = np.isin(lab, keep).astype(np.uint8)
    fg = ndimage.binary_fill_holes(fg)
    fg = ndimage.binary_erosion(fg, iterations=2).astype(np.uint8)  # eat the light fringe left by the cut
    if fg.mean() < 0.08 or fg.mean() > 0.92:  # cut went wrong: keep the photo
        im.save(dst.with_suffix('.jpg'), quality=88); return dst.with_suffix('.jpg').name
    alpha = Image.fromarray(fg * 255).filter(ImageFilter.GaussianBlur(0.8))
    o = Image.fromarray(np.dstack([a.astype(np.uint8), np.asarray(alpha)]), 'RGBA'); o = o.crop(o.getbbox())
    o.save(dst.with_suffix('.png'), optimize=True); return dst.with_suffix('.png').name

def albums(path):
    data = json.load(open(path)); out = []
    for a in data:
        img = 'cover_' + a['id']
        if a.get('cover'):
            im = Image.open(pathlib.Path(path).parent / a['cover']).convert('RGB'); im.thumbnail((800, 800), Image.LANCZOS); im.save(IMG / (img + '.jpg'), quality=88)
        tr = []
        for t in a['tracks']:
            tr.append('{ n: %d, title: %s, feat: %s, spotify: %s, durationMs: %s, preview: %s, yt: %s, genius: %s, facts: [%s] }' % (
                int(t['n']), jsq(t['title']), jsq(', '.join(x.title() if x.isupper() else x for x in (t.get('feat') or '').split(', '))), jsq(t['spotify']) if t.get('spotify') else 'null', int(t.get('durationMs') or 0),
                jsq(t['previewUrl']) if t.get('previewUrl') else 'null', jsq(t['yt']) if t.get('yt') else 'null', jsq(genius(t)),
                ', '.join(jsq(f['text'] if isinstance(f, dict) else f) for f in (t.get('facts') or []))))
        out.append('    { id: %s, t: %s, y: %s, released: %s, spotify: %s, yt: %s, img: %s, note: %s, tracks: [\n      %s\n    ] }' % (
            jsq(a['id']), jsq(a['title']), jsq(a['year']), jsq(a.get('released') or a['year']), jsq(a['spotify']) if a.get('spotify') else 'null',
            jsq(ALBUM_YT[a['id']]) if a['id'] in ALBUM_YT else 'null', jsq(img), jsq(a.get('note') or ''), ',\n      '.join(tr)))
    return '  // ALBUMS:start (generated by tools/build_data.py)\n  var ALBUMS = [\n' + ',\n'.join(out) + '\n  ];\n  // ALBUMS:end\n'

def kicks(path):
    data = json.load(open(path)); base = pathlib.Path(path).parent; out = []
    for k in data:
        hero = [i for i in k.get('images', []) if i.get('kind') == 'hero'] or k.get('images', [])[:1]
        if k['id'] in HERO: hero = [{'file': HERO[k['id']]}]
        img = None
        if hero:
            img = knockout(base / hero[0]['file'] if not str(hero[0]['file']).startswith('/') else pathlib.Path(hero[0]['file']), IMG / ('shoe_' + k['id']))
        cws = []
        for c in k.get('colorways', []):
            ci = [i for i in k.get('images', []) if i.get('kind') == 'colorway' and (norm(i.get('colorway')) == norm(c['name']) or (norm(i.get('colorway')) and (norm(i.get('colorway')) in norm(c['name']) or norm(c['name']) in norm(i.get('colorway')))))]
            cimg = None
            if ci:
                p = base / ci[0]['file'] if not str(ci[0]['file']).startswith('/') else pathlib.Path(ci[0]['file'])
                cimg = knockout(p, IMG / ('shoe_' + k['id'] + '_' + re.sub(r'[^a-z0-9]+', '-', c['name'].lower()).strip('-')), 500)
            cws.append('{ name: %s, note: %s, date: %s, img: %s }' % (jsq(c['name']), jsq(c.get('note') or ''), jsq(c.get('date') or ''), jsq(cimg) if cimg else 'null'))
        story = [p.strip() for p in re.split(r'(?<=[.!?])\s+(?=[A-Z"“])', k.get('story') or '') if p.strip()]
        dek = story[0] if story else ''; rest = story[1:]
        # group the rest into one or two paragraphs
        paras = [' '.join(rest)] if rest else []
        nm = NAME.get(k['id'], (k['name'], ''))
        out.append('    { id: %s, n: %s, name: %s, sub: %s, released: %s, price: %s, tech: %s, techShort: %s, designer: %s, dek: %s, story: [%s], colorways: [%s], moment: %s, img: %s, media: [%s], link: %s }' % (
            jsq(k['id']), jsq(k['n']), jsq(nm[0]), jsq(nm[1]), jsq(short(k.get('released') or '', 40)), jsq(short(k['price'], 14)) if k.get('price') else 'null', jsq(k['tech']) if k.get('tech') else 'null', jsq(TECH.get(k['id']) or short(k.get('tech'), 24)) if k.get('tech') else 'null',
            jsq(short(k['designer'], 24)) if k.get('designer') else 'null', jsq(dek), ', '.join(jsq(p) for p in paras), ', '.join(cws), jsq(k['moment']) if k.get('moment') else 'null',
            jsq(img) if img else 'null', ', '.join(jsq(v) for v in SHOE_VIDEO.get(k['id'], [])), jsq(k['link']) if k.get('link') else 'null'))
    return '  // KICKS:start (generated by tools/build_data.py)\n  var KICKS = [\n' + ',\n'.join(out) + '\n  ];\n  // KICKS:end\n'

def clips(path):
    """Clip feed from the curated clips.json: one cropped thumbnail per video, captions and categories."""
    data = json.load(open(path)); base = pathlib.Path(path).parent; out = []
    for c in data:
        if not c.get('thumb') or not c.get('embeddable', True): continue
        src = base / c['thumb']
        if not src.exists(): continue
        im = Image.open(src).convert('RGB')
        w, h = im.size
        if abs(w / h - 16 / 9) > 0.05:
            nh = int(w * 9 / 16); t = (h - nh) // 2; im = im.crop((0, t, w, t + nh))
        im = im.resize((800, 450), Image.LANCZOS)
        name = 'clip_' + re.sub(r'[^A-Za-z0-9_-]', '', c['id'])
        im.save(IMG / (name + '.jpg'), quality=82)
        out.append("    { id: %s, cat: %s, caption: %s, channel: %s, year: %s, len: %s, img: %s }" % (
            jsq(c['id']), jsq(c['cat']), jsq(c['caption']), jsq(c.get('channel') or ''), int(c['year']) if c.get('year') else 'null',
            jsq(c['length']) if c.get('length') else 'null', jsq(name)))
    return '  // CLIPS:start (generated by tools/build_data.py)\n  var CLIPS = [\n' + ',\n'.join(out) + '\n  ];\n  // CLIPS:end\n'

if __name__ == '__main__':
    s = APP.read_text()
    if len(sys.argv) > 1 and sys.argv[1] != '-':
        s = re.sub(r'  // ALBUMS:start.*?  // ALBUMS:end\n', lambda m: albums(sys.argv[1]), s, flags=re.S)
    if len(sys.argv) > 2 and sys.argv[2] != '-':
        s = re.sub(r'  // KICKS:start.*?  // KICKS:end\n', lambda m: kicks(sys.argv[2]), s, flags=re.S)
    if len(sys.argv) > 3 and sys.argv[3] != '-':
        s = re.sub(r'  // CLIPS:start.*?  // CLIPS:end\n', lambda m: clips(sys.argv[3]), s, flags=re.S)
    APP.write_text(s); print('data blocks written')
