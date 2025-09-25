# test_refresh.py
import os
import requests
import sys

CLIENT_ID = os.environ.get("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.environ.get("SPOTIPY_CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("SPOTIFY_REFRESH_TOKEN")

TOKEN_URL = "https://accounts.spotify.com/api/token"

if not CLIENT_ID or not CLIENT_SECRET or not REFRESH_TOKEN:
    print("Set SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET and SPOTIFY_REFRESH_TOKEN in env before running.")
    sys.exit(2)

data = {
    "grant_type": "refresh_token",
    "refresh_token": REFRESH_TOKEN,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET
}

r = requests.post(TOKEN_URL, data=data)
print("HTTP", r.status_code)
try:
    print(r.json())
except:
    print(r.text)
