import os
from flask import Flask, redirect, request, jsonify
import spotipy
from spotipy.oauth2 import SpotifyOAuth

app = Flask(__name__)

# Read secrets from env
CLIENT_ID = os.environ.get("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.environ.get("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("SPOTIPY_REDIRECT_URI")  # must exactly match Spotify Dashboard
CACHE_PATH = os.environ.get("SPOTIPY_CACHE_PATH", ".spotify-cache")  # use Render Disk path if attached

SCOPE = "user-read-currently-playing user-read-playback-state"

if not CLIENT_ID or not CLIENT_SECRET or not REDIRECT_URI:
    raise RuntimeError("Set SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET and SPOTIPY_REDIRECT_URI as env vars")

sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE,
    cache_path=CACHE_PATH
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
    error = request.args.get("error")
    if error:
        return f"Spotify returned an error: {error}", 400
    if not code:
        return "No code provided", 400

    token_info = sp_oauth.get_access_token(code)
    # token_info is cached automatically to cache_path by SpotifyOAuth
    return "Authenticated. You can close this tab."

@app.route("/nowplaying")
def nowplaying():
    token_info = sp_oauth.get_cached_token()
    if not token_info:
        return jsonify({"error": "not_authenticated"}), 401

    sp = spotipy.Spotify(auth_manager=sp_oauth)
    try:
        current = sp.current_user_playing_track()
    except Exception as e:
        return jsonify({"error": "api_error", "detail": str(e)}), 500

    if not current or not current.get("is_playing"):
        return jsonify({"is_playing": False, "song": None})

    item = current.get("item", {})
    artist = item.get("artists", [{}])[0].get("name", "")
    track = item.get("name", "")
    prog_ms = current.get("progress_ms", 0)
    dur_ms = item.get("duration_ms", 0)
    album_art = ""
    if item.get("album") and item["album"].get("images"):
        album_art = item["album"]["images"][0]["url"]

    return jsonify({
        "is_playing": True,
        "song": f"{artist} - {track}",
        "progress_ms": prog_ms,
        "duration_ms": dur_ms,
        "album_art": album_art
    })

if __name__ == "__main__":
    # Render sets PORT automatically in $PORT
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
