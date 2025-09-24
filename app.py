import os
import time
import requests
from flask import Flask, redirect, request, session, jsonify

app = Flask(__name__)
app.secret_key = os.urandom(24)  # used for session handling

# Spotify app credentials (from https://developer.spotify.com/dashboard/)
CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")

# ⚠️ Replace this with your deployed Render URL (e.g., "https://myspotifybridge.onrender.com")
REDIRECT_URI = os.environ.get("SPOTIFY_REDIRECT_URI")

# Spotify endpoints
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
NOW_PLAYING_URL = "https://api.spotify.com/v1/me/player/currently-playing"

# Memory store for tokens
access_token = None
refresh_token = None
token_expires_at = 0


@app.route("/")
def index():
    return (
        "<h2>Spotify Bridge</h2>"
        "<a href='/login'>Log in with Spotify</a><br>"
        "<a href='/nowplaying'>Check Now Playing</a>"
    )


@app.route("/login")
def login():
    scope = "user-read-playback-state user-read-currently-playing"
    auth_query = {
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": scope,
        "client_id": CLIENT_ID
    }
    url_args = "&".join([f"{k}={requests.utils.quote(v)}" for k, v in auth_query.items()])
    auth_url = f"{AUTH_URL}?{url_args}"
    return redirect(auth_url)


@app.route("/callback")
def callback():
    global access_token, refresh_token, token_expires_at

    code = request.args.get("code")
    if not code:
        return "No code provided, something went wrong."

    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }

    r = requests.post(TOKEN_URL, data=token_data)
    if r.status_code != 200:
        return f"Error getting token: {r.text}"

    token_info = r.json()
    access_token = token_info["access_token"]
    refresh_token = token_info.get("refresh_token")
    token_expires_at = time.time() + token_info["expires_in"]

    return "<h3>Authenticated! 🎉</h3><a href='/nowplaying'>Check Now Playing</a>"


def refresh_access_token():
    global access_token, refresh_token, token_expires_at
    if not refresh_token:
        return False

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }

    r = requests.post(TOKEN_URL, data=data)
    if r.status_code != 200:
        print("Error refreshing token:", r.text)
        return False

    token_info = r.json()
    access_token = token_info.get("access_token", access_token)
    token_expires_at = time.time() + token_info.get("expires_in", 3600)
    return True


@app.route("/nowplaying")
def now_playing():
    global access_token, token_expires_at

    if not access_token:
        return jsonify({"error": "Not authenticated. Please /login first."})

    if time.time() > token_expires_at:
        refreshed = refresh_access_token()
        if not refreshed:
            return jsonify({"error": "Failed to refresh token. Please /login again."})

    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.get(NOW_PLAYING_URL, headers=headers)

    if r.status_code == 204:
        return jsonify({"status": "Not playing anything right now."})

    if r.status_code != 200:
        return jsonify({"error": r.text})

    data = r.json()
    track = data["item"]["name"]
    artist = ", ".join([a["name"] for a in data["item"]["artists"]])
    progress = data["progress_ms"] // 1000
    duration = data["item"]["duration_ms"] // 1000

    return jsonify({
        "track": track,
        "artist": artist,
        "progress": f"{progress // 60}:{progress % 60:02d}",
        "duration": f"{duration // 60}:{duration % 60:02d}"
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
