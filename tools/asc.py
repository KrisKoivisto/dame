#!/usr/bin/env python3
"""Small App Store Connect API helper for CI. Reads ASC_KEY_ID, ASC_ISSUER_ID and the key file at ASC_KEY_PATH.

  asc.py team <bundle-id> [name]   print the team id, registering the bundle id first if it is new
  asc.py app <bundle-id>           exit 0 if an App Store Connect app record exists for the bundle id, 3 if not
  asc.py testers <bundle-id> <n>   wait for build n to finish processing, then hand it to every internal TestFlight group
  asc.py certs                     revoke development certificates earlier cloud builds left behind ("Created via API")
"""
import json, os, sys, time, urllib.request, urllib.error, urllib.parse
import jwt  # PyJWT

API = 'https://api.appstoreconnect.apple.com/v1/'

def token():
    key = open(os.environ['ASC_KEY_PATH']).read()
    now = int(time.time())
    return jwt.encode({'iss': os.environ['ASC_ISSUER_ID'], 'iat': now, 'exp': now + 1100, 'aud': 'appstoreconnect-v1'}, key,
                      algorithm='ES256', headers={'kid': os.environ['ASC_KEY_ID'], 'typ': 'JWT'})

def call(method, path, body=None, ok=()):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={'Authorization': 'Bearer ' + token(), 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read(); return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        msg = e.read().decode()[:600]
        if e.code in ok: sys.stderr.write('App Store Connect said %s (fine): %s\n' % (e.code, msg[:200])); return {}
        sys.stderr.write('App Store Connect said %s: %s\n' % (e.code, msg)); raise SystemExit(2)

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

def testers(bundle, number, wait_min=60):
    """Builds only reach testers once they're in a group. Wait for Apple to finish processing, then add it."""
    app_id = call('GET', 'apps?' + urllib.parse.urlencode({'filter[bundleId]': bundle}))['data'][0]['id']
    q = urllib.parse.urlencode({'filter[app]': app_id, 'filter[version]': number, 'limit': 5})
    deadline = time.time() + wait_min * 60
    while True:
        found = call('GET', 'builds?' + q)['data']
        state = found[0]['attributes']['processingState'] if found else 'not showing yet'
        print('Build %s: %s' % (number, state), flush=True)
        if state == 'VALID': break
        if state in ('FAILED', 'INVALID'):
            sys.stderr.write('Apple could not process build %s (%s).\n' % (number, state)); raise SystemExit(4)
        if time.time() > deadline:
            sys.stderr.write('Build %s still not ready after %s minutes.\n' % (number, wait_min)); raise SystemExit(5)
        time.sleep(60)
    build = found[0]['id']
    note = os.environ.get('WHATS_NEW', '').strip()
    if note:
        locs = call('GET', 'builds/%s/betaBuildLocalizations' % build).get('data', [])
        if locs:
            call('PATCH', 'betaBuildLocalizations/' + locs[0]['id'], {'data': {'type': 'betaBuildLocalizations', 'id': locs[0]['id'], 'attributes': {'whatsNew': note}}})
        else:
            call('POST', 'betaBuildLocalizations', {'data': {'type': 'betaBuildLocalizations', 'attributes': {'locale': 'en-US', 'whatsNew': note},
                                                          'relationships': {'build': {'data': {'type': 'builds', 'id': build}}}}})
        print('What to Test: ' + note)
    detail = call('GET', 'builds/%s/buildBetaDetail' % build)['data']
    print('TestFlight state: %s, notify testers: %s' % (detail['attributes'].get('internalBuildState'), detail['attributes'].get('autoNotifyEnabled')))
    if not detail['attributes'].get('autoNotifyEnabled'):
        call('PATCH', 'buildBetaDetails/' + detail['id'], {'data': {'type': 'buildBetaDetails', 'id': detail['id'], 'attributes': {'autoNotifyEnabled': True}}})
        print('Turned on tester notifications for this build')
    groups = call('GET', 'betaGroups?' + urllib.parse.urlencode({'filter[app]': app_id, 'filter[isInternalGroup]': 'true', 'limit': 50}))['data']
    if not groups:
        print('No internal tester group yet, making one')
        groups = [call('POST', 'betaGroups', {'data': {'type': 'betaGroups', 'attributes': {'name': 'Dame testers', 'isInternalGroup': True, 'hasAccessToAllBuilds': True},
                                                       'relationships': {'app': {'data': {'type': 'apps', 'id': app_id}}}}})['data']]
    for g in groups:
        a = g['attributes']
        link = call('GET', 'betaGroups/%s/relationships/betaTesters?limit=1' % g['id'])
        count = link.get('meta', {}).get('paging', {}).get('total', len(link.get('data', [])))
        print('Group "%s": %s tester(s), gets every build on its own: %s' % (a['name'], count, a.get('hasAccessToAllBuilds')))
        if count == 0:
            # add the App Store Connect team (Apple's own list) so someone actually gets the build
            users = call('GET', 'users?limit=50', ok=(403,)).get('data', [])
            for u in users:
                call('POST', 'betaTesters', {'data': {'type': 'betaTesters', 'attributes': {'email': u['attributes']['username'],
                     'firstName': u['attributes'].get('firstName') or '', 'lastName': u['attributes'].get('lastName') or ''},
                     'relationships': {'betaGroups': {'data': [{'type': 'betaGroups', 'id': g['id']}]}}}}, ok=(409,))
            print('  added %s team member(s) as testers' % len(users))
        if not a.get('hasAccessToAllBuilds'):
            call('POST', 'betaGroups/%s/relationships/builds' % g['id'], {'data': [{'type': 'builds', 'id': build}]}, ok=(409, 422))
            print('  added build %s to this group' % number)
    print('Done. Build %s is with testers.' % number)

def certs():
    """Every cloud build makes an Apple Development certificate whose private key dies with the build machine.
    They pile up until Apple refuses to make more. Only these build-made ones are revoked, never one made on a Mac."""
    found = call('GET', 'certificates?' + urllib.parse.urlencode({'filter[certificateType]': 'DEVELOPMENT,IOS_DEVELOPMENT', 'limit': 200}))['data']
    stale = [c for c in found if 'Created via API' in ((c['attributes'].get('displayName') or '') + ' ' + (c['attributes'].get('name') or ''))]
    print('Development certificates: %s, left by cloud builds: %s' % (len(found), len(stale)))
    for c in stale:
        call('DELETE', 'certificates/' + c['id'], ok=(404, 409))
    if stale: print('Revoked %s certificate(s) from earlier cloud builds' % len(stale))

if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'team': team(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else 'Dame Dolla')
    elif cmd == 'app': app(sys.argv[2])
    elif cmd == 'testers': testers(sys.argv[2], sys.argv[3])
    elif cmd == 'certs': certs()
