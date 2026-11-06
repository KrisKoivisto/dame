#!/usr/bin/env python3
"""Build www/ for the iPhone app: src/app.html wrapped in a plain head, plus img/. Capacitor copies www/ into the Xcode project."""
import hashlib, pathlib, re, shutil
ROOT = pathlib.Path(__file__).resolve().parent.parent
W = ROOT / 'www'
if W.exists(): shutil.rmtree(W)
W.mkdir()
a = (ROOT / 'src' / 'app.html').read_text()
a = re.sub(r'^<title>.*?</title>\n', '', a)
for pat in (r'^<meta name="viewport"[^>]*>\n', r'^<meta name="theme-color"[^>]*>\n', r'^<link rel="(icon|apple-touch-icon)"[^>]*>\n'):
    a = re.sub(pat, '', a, flags=re.M)
head = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover, user-scalable=no">
<title>Dame Dolla</title>
<meta name="theme-color" content="#0b0b0c">
<style>html,body{height:100%;margin:0;background:#0b0b0c}*{-webkit-touch-callout:none}</style>
<script>window.DD_BUILD = '%%STAMP%%';</script>
</head>
<body>
'''
import hashlib
head = head.replace('%%STAMP%%', hashlib.sha1((ROOT / 'src' / 'app.html').read_bytes()).hexdigest()[:12])
(W / 'index.html').write_text(head + a + '\n</body>\n</html>\n')
shutil.copytree(ROOT / 'img', W / 'img')
print('www built:', sum(f.stat().st_size for f in W.rglob('*') if f.is_file()) // 1024 // 1024, 'MB')
