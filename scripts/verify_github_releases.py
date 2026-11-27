"""
Verify live GitHub releases status
"""
import json
import subprocess
import urllib.request

p = subprocess.Popen(['git', 'credential', 'fill'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
out, _ = p.communicate(input='protocol=https\nhost=github.com\n\n')
token = ''
for line in out.splitlines():
    if line.startswith('password='):
        token = line.split('=', 1)[1]

headers = {'Authorization': f'Bearer {token}', 'User-Agent': 'OmniCheck', 'Accept': 'application/vnd.github.v3+json'}
req = urllib.request.Request('https://api.github.com/repos/rajvisual/OmniCapture/releases', headers=headers)
with urllib.request.urlopen(req) as resp:
    releases = json.loads(resp.read().decode())
    print(f'Total releases returned by API: {len(releases)}')
    for r in releases:
        assets = [f"{a.get('name')} ({a.get('size') / (1024*1024):.2f} MB)" for a in r.get('assets', [])]
        print(f"Tag: {r.get('tag_name')}, ID: {r.get('id')}, Name: '{r.get('name')}', Draft: {r.get('draft')}, Pre-Release: {r.get('prerelease')}, HTML: {r.get('html_url')}")
        print(f"  Assets: {assets}")
