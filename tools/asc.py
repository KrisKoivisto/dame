#!/usr/bin/env python3
"""Small App Store Connect API helper for CI. Reads ASC_KEY_ID, ASC_ISSUER_ID and the key file at ASC_KEY_PATH.

  asc.py team <bundle-id> [name]   print the team id, registering the bundle id first if it is new
  asc.py app <bundle-id>           exit 0 if an App Store Connect app record exists for the bundle id, 3 if not
"""
import json, os, sys, time, urllib.request, urllib.error, urllib.parse
import jwt  # PyJWT

API = 'https://api.appstoreconnect.apple.com/v1/'

def token():
    key = open(os.environ['ASC_KEY_PATH']).read()
    now = int(time.time())
    return jwt.encode({'iss': os.environ['ASC_ISSUER_ID'], 'iat': now, 'exp': now + 1100, 'aud': 'appstoreconnect-v1'}, key,
                      algorithm='ES256', headers={'kid': os.environ['ASC_KEY_ID'], 'typ': 'JWT'})

def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={'Authorization': 'Bearer ' + token(), 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r: return json.load(r)
    except urllib.error.HTTPError as e:
        sys.stderr.write('App Store Connect said %s: %s\n' % (e.code, e.read().decode()[:600])); raise SystemExit(2)

def team(bundle, name):
    found = call('GET', 'bundleIds?' + urllib.parse.urlencode({'filter[identifier]': bundle, 'limit': 5}))['data']
    found = [b for b in found if b['attributes']['identifier'] == bundle]
    if not found:
        sys.stderr.write('Registering bundle id %s\n' % bundle)
        found = [call('POST', 'bundleIds', {'data': {'type': 'bundleIds', 'attributes': {'identifier': bundle, 'name': name, 'platform': 'IOS'}}})['data']]
    print(found[0]['attributes']['seedId'])

def app(bundle):
    found = call('GET', 'apps?' + urllib.parse.urlencode({'filter[bundleId]': bundle}))['data']
    if found:
        print(found[0]['attributes']['name']); return
    raise SystemExit(3)

if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'team': team(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else 'Dame Dolla')
    elif cmd == 'app': app(sys.argv[2])
