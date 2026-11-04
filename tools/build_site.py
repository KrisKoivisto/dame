#!/usr/bin/env python3
"""Wrap src/app.html (the artifact source: no doctype/head) into index.html for dame.kriskoivisto.com."""
import re, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = 'https://dame.kriskoivisto.com/'
a = (ROOT / 'src' / 'app.html').read_text()
a = re.sub(r'^<title>.*?</title>\n', '', a)
for pat in (r'^<meta name="viewport"[^>]*>\n', r'^<meta name="theme-color"[^>]*>\n', r'^<link rel="(icon|apple-touch-icon)"[^>]*>\n'):
    a = re.sub(pat, '', a, flags=re.M)
head = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Dame Dolla</title>
<meta name="description" content="Be in reach. Hoops, music, kicks, Oakland, and every game night. A fan app concept for Damian Lillard.">
<link rel="canonical" href="{BASE}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Dame Dolla">
<meta property="og:title" content="Dame Dolla">
<meta property="og:description" content="Be in reach. Hoops, music, kicks, Oakland, and every game night. A fan app concept for Damian Lillard.">
<meta property="og:url" content="{BASE}">
<meta property="og:image" content="{BASE}og.jpg">
<meta property="og:image:secure_url" content="{BASE}og.jpg">
<meta property="og:image:type" content="image/jpeg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Damian Lillard reaching toward the camera. Be in reach.">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Dame Dolla">
<meta name="twitter:description" content="Be in reach. Hoops, music, kicks, Oakland, and every game night.">
<meta name="twitter:image" content="{BASE}og.jpg">
<meta name="theme-color" content="#0b0b0c">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Dame Dolla">
<link rel="apple-touch-icon" href="{BASE}img/icon180.png">
<link rel="icon" type="image/png" sizes="64x64" href="{BASE}img/icon64.png">
<link rel="manifest" href="{BASE}manifest.json">
<style>html,body{{height:100%;margin:0;background:#0b0b0c}}</style>
</head>
<body>
'''
(ROOT / 'index.html').write_text(head + a + '\n</body>\n</html>\n')
import shutil
if (ROOT / 'tools' / 'games.json').exists(): shutil.copy(ROOT / 'tools' / 'games.json', ROOT / 'games.json')
print('built index.html from src/app.html')
