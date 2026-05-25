import urllib.request
import urllib.parse
import json

params = {'track_name': 'test', 'artist_name': 'test'}
qs = urllib.parse.urlencode(params)
url = f"https://lrclib.net/api/get?{qs}"

req = urllib.request.Request(url, headers={'User-Agent': 'LyricsTaskbar/1.0'})
try:
    with urllib.request.urlopen(req, timeout=5) as response:
        print(response.status)
except Exception as e:
    print("Error:", e)
