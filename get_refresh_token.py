# get_refresh_token.py
import os
from flask import Flask, redirect, request
import requests
import threading
import webbrowser

CLIENT_ID = os.environ.get("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.environ.get("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = "http://127.0.0.1:5000/callback"
SCOPE = "user-read-playback-state user-read-currently-playing"
TOKEN_URL = "https://accounts.spotify.com/api/token"
AUTH_URL = "https://accounts.spotify.com/authorize"

app = Flask(__name__)
result = {}

@app.route("/")
def index():
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "scope": SCOPE,
        "redirect_uri": REDIRECT_URI
    }
    qs = "&".join([f"{k}={requests.utils.quote(v)}" for k,v in params.items()])
    return redirect(AUTH_URL + "?" + qs)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "No code provided", 400

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    r = requests.post(TOKEN_URL, data=data)
    if r.status_code != 200:
        return f"Token exchange failed: {r.status_code} {r.text}", 500
    j = r.json()
    refresh = j.get("refresh_token")
    return f"Success. Copy this refresh token and paste it into Render env var SPOTIFY_REFRESH_TOKEN:<br><pre>{refresh}</pre>"

def open_browser():
    webbrowser.open("http://127.0.0.1:5000/")

if __name__ == "__main__":
    if not CLIENT_ID or not CLIENT_SECRET:
        print("Set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET in env.")
        raise SystemExit(2)
    threading.Timer(1.0, open_browser).start()
    app.run(host="127.0.0.1", port=5000)
