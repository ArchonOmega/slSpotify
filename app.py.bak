# app.py
import os
from flask import Flask, redirect, request, jsonify
import spotipy
from spotipy.oauth2 import SpotifyOAuth

app = Flask(__name__)

# Read from env (recommended)
SPOTIPY_CLIENT_ID = os.environ.get("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.environ.get("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.environ.get("SPOTIPY_REDIRECT_URI")  # must match Spotify app redirect

SCOPE = "user-read-currently-playing user-read-playback-state"

# Spotipy OAuth manager; uses a local cache file ('.cache') to store tokens and refresh them automatically
sp_oauth = SpotifyOAuth(
    client_id=SPOTIPY_CLIENT_ID,
    client_secret=SPOTIPY_CLIENT_SECRET,
    redirect_uri=SPOTIPY_REDIRECT_URI,
    scope=SCOPE,
    cache_path=".spotify-cache"
)

@app.route("/")
def index():
    return '<a href="/login">Login with Spotify</a>'

@app.route("/login")
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if code:
        token_info = sp_oauth.get_access_token(code)
        # token_info saved to cache_path by SpotifyOAuth automatically
        return "Authenticated. You can close this tab."
    return "No code - something went wrong", 400

@app.route("/nowplaying")
def nowplaying():
    token_info = sp_oauth.get_cached_token()
    if not token_info:
        return jsonify({"error": "not authenticated"}), 401

    sp = spotipy.Spotify(auth_manager=sp_oauth)

    # Try to fetch currently playing track
    current = sp.current_user_playing_track()  # or sp.currently_playing() on some versions
    if not current or not current.get("is_playing"):
        return jsonify({"is_playing": False, "song": None})

    item = current.get("item")
    if not item:
        return jsonify({"is_playing": False, "song": None})

    artist = item["artists"][0]["name"] if item["artists"] else ""
    track = item["name"]
    progress_ms = current.get("progress_ms", 0)
    duration_ms = item.get("duration_ms", 0)
    album_art = ""
    if item.get("album") and item["album"].get("images"):
        album_art = item["album"]["images"][0]["url"]

    return jsonify({
        "is_playing": True,
        "song": f"{artist} - {track}",
        "progress_ms": progress_ms,
        "duration_ms": duration_ms,
        "album_art": album_art
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
