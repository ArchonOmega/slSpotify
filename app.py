# app.py
import os
import time
import requests
from flask import Flask, redirect, request, jsonify

app = Flask(__name__)

# --- Config from env (set these in Render) ---
CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("SPOTIFY_REDIRECT_URI")  # e.g. https://your-render-service.onrender.com/callback

# Optional: persist a refresh token in env (recommended on ephemeral hosts)
# Set this in Render AFTER you obtain it locally or via /callback once.
STATIC_REFRESH_TOKEN = os.environ.get("SPOTIFY_REFRESH_TOKEN")

# Token endpoint + scope
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
NOW_PLAYING_URL = "https://api.spotify.com/v1/me/player/currently-playing"
SCOPE = "user-read-playback-state user-read-currently-playing"

# --- In-memory token storage (works during container life) ---
access_token = None
refresh_token = STATIC_REFRESH_TOKEN  # start from env if present
token_expires_at = 0  # epoch seconds

# --- Helpers ---
def exchange_code_for_token(code):
    """Exchange auth code for tokens (called once on /callback)."""
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    r = requests.post(TOKEN_URL, data=data)
    if r.status_code != 200:
        return None, r.text
    j = r.json()
    return j, None

def refresh_access_token_from_refresh_token(rtoken):
    """Use the refresh token to get a fresh access token."""
    data = {
        "grant_type": "refresh_token",
        "refresh_token": rtoken,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    r = requests.post(TOKEN_URL, data=data)
    if r.status_code != 200:
        return None, r.text
    return r.json(), None

def ensure_access_token():
    """Ensure access_token is valid: refresh if expired or missing.
       Returns (True, None) on success, (False, error_message) on failure."""
    global access_token, refresh_token, token_expires_at

    # If we have a valid in-memory access token, keep it.
    if access_token and time.time() < token_expires_at - 5:
        return True, None

    # If we have a refresh token (env or from OAuth), use it to refresh
    if refresh_token:
        j, err = refresh_access_token_from_refresh_token(refresh_token)
        if not j:
            return False, f"Refresh failed: {err}"
        access_token = j.get("access_token", access_token)
        expires_in = j.get("expires_in", 3600)
        token_expires_at = time.time() + expires_in
        # Some refresh responses include a new refresh_token (rare). When present, we should save it.
        new_refresh = j.get("refresh_token")
        if new_refresh:
            refresh_token = new_refresh
            # Important: on Render, update SPOTIFY_REFRESH_TOKEN env var manually if you want persistence.
        return True, None

    # No refresh token / no access token: not authenticated
    return False, "No refresh token available; please /login to authenticate and get a refresh token."

# --- Routes ---
@app.route("/")
def index():
    return (
        "<h3>Spotify Bridge</h3>"
        "<ul>"
        "<li><a href='/login'>Login with Spotify</a> (one-time to get refresh token)</li>"
        "<li><a href='/nowplaying'>/nowplaying — JSON output</a></li>"
        "</ul>"
        "<p>If you already set SPOTIFY_REFRESH_TOKEN in Render env vars, you don't need to /login on Render.</p>"
    )

@app.route("/login")
def login():
    # Build the authorize URL
    if not CLIENT_ID or not REDIRECT_URI:
        return "Missing CLIENT_ID or REDIRECT_URI in environment.", 500
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "scope": SCOPE,
        "redirect_uri": REDIRECT_URI
    }
    query = "&".join([f"{k}={requests.utils.quote(v)}" for k,v in params.items()])
    return redirect(f"{AUTH_URL}?{query}")

@app.route("/callback")
def callback():
    """
    After user authorizes on Spotify, Spotify redirects here with ?code=...
    We'll exchange the code and show the refresh token so you can copy it into Render env vars.
    """
    global access_token, refresh_token, token_expires_at

    code = request.args.get("code")
    error = request.args.get("error")
    if error:
        return f"Spotify returned error: {error}", 400
    if not code:
        return "No code in callback", 400

    j, err = exchange_code_for_token(code)
    if not j:
        return f"Token exchange failed: {err}", 500

    access_token = j.get("access_token")
    refresh_token = j.get("refresh_token") or refresh_token
    expires_in = j.get("expires_in", 3600)
    token_expires_at = time.time() + expires_in

    # If the app isn't using STATIC_REFRESH_TOKEN, we give the refresh token to the user to copy
    if not STATIC_REFRESH_TOKEN:
        return (
            "<h3>Authenticated — save this refresh token in your Render environment variable <code>SPOTIFY_REFRESH_TOKEN</code></h3>"
            f"<pre>{refresh_token}</pre>"
            "<p>After you paste it into Render env vars, redeploy so your service can use it permanently.</p>"
        )

    return "<h3>Authenticated.</h3><p>Static refresh token already set in env — you're good.</p>"

@app.route("/nowplaying")
def now_playing():
    ok, err = ensure_access_token()
    if not ok:
        return jsonify({"error": err}), 401

    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.get(NOW_PLAYING_URL, headers=headers)
    if r.status_code == 204:
        return jsonify({"is_playing": False, "song": None})
    if r.status_code != 200:
        # Pass through error for easier debugging
        return jsonify({"error": "spotify_api_error", "detail": r.text}), r.status_code

    data = r.json()
    item = data.get("item") or {}
    artist = ", ".join([a.get("name","") for a in item.get("artists", [])])
    track = item.get("name", "")
    prog_ms = data.get("progress_ms", 0)
    dur_ms = item.get("duration_ms", 0)

    def ms_to_mmss(ms):
        s = ms // 1000
        return f"{s//60}:{s%60:02d}"

    return jsonify({
        "is_playing": True,
        "song": f"{artist} - {track}",
        "progress": ms_to_mmss(prog_ms),
        "duration": ms_to_mmss(dur_ms)
    })

# --- Run ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
