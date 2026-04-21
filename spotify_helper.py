import os
import base64
import requests
from datetime import datetime, timedelta

SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"

_token_cache = {"access_token": None, "expires_at": None}


def _get_client_token() -> str:
    """Client credentials flow — for search/recommendations (no user needed)."""
    now = datetime.utcnow()
    # Corrected comparison to handle NoneType
    if _token_cache["access_token"] and _token_cache["expires_at"]:
        if _token_cache["expires_at"] > now:
            return _token_cache["access_token"]

    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    try:
        r = requests.post(
            SPOTIFY_TOKEN_URL,
            headers={"Authorization": f"Basic {creds}"},
            data={"grant_type": "client_credentials"},
            timeout=10,
        )
        if r.status_code != 200:
            print(f"[Spotify] TOKEN ERROR: {r.status_code} - {r.text}")
            return None
        data = r.json()
        _token_cache["access_token"] = data["access_token"]
        _token_cache["expires_at"] = now + timedelta(seconds=data["expires_in"] - 60)
        return _token_cache["access_token"]
    except Exception as e:
        print(f"[Spotify] Token exception: {e}")
        return None


def get_recommendations(mood_seeds: dict, limit: int = 10) -> list:
    """
    Fetch Spotify track recommendations based on mood audio features.
    mood_seeds = {valence, energy, genres}
    """
    token = _get_client_token()
    if not token:
        print("[Spotify] Recommendations aborted: No valid token.")
        return []
    headers = {"Authorization": f"Bearer {token}"}

    genres = mood_seeds.get("genres", ["pop"])[:2]  # max 2 seed genres
    params = {
        "seed_genres": ",".join(genres),
        "target_valence": mood_seeds.get("valence", 0.5),
        "target_energy": mood_seeds.get("energy", 0.5),
        "limit": limit,
    }

    r = requests.get(f"{SPOTIFY_API_BASE}/recommendations", headers=headers, params=params, timeout=10)
    if r.status_code != 200:
        return []

    tracks = []
    for item in r.json().get("tracks", []):
        artists = ", ".join(a["name"] for a in item.get("artists", []))
        album = item.get("album", {})
        image = album.get("images", [{}])[0].get("url", "")
        tracks.append({
            "id": item["id"],
            "name": item["name"],
            "artists": artists,
            "album": album.get("name", ""),
            "image": image,
            "preview_url": item.get("preview_url"),
            "spotify_url": item["external_urls"].get("spotify", ""),
            "duration_ms": item.get("duration_ms", 0),
        })
    return tracks


def search_tracks(query: str, limit: int = 5) -> list:
    """
    Real-time Spotify track search.
    No hardcoded mappings; queries the Spotify API directly.
    """
    try:
        token = _get_client_token()
        if not token:
            print("[Spotify] Search aborted: No valid token.")
            return []
        headers = {"Authorization": f"Bearer {token}"}
        params = {"q": query, "type": "track", "limit": limit}
        r = requests.get(f"{SPOTIFY_API_BASE}/search", headers=headers, params=params, timeout=8)
        
        if r.status_code == 200:
            data = r.json()
            items = data.get("tracks", {}).get("items", [])
            print(f"[Spotify] Search for '{query}' returned {len(items)} items.")
            
            tracks = []
            for item in items:
                artists = ", ".join(a["name"] for a in item.get("artists", []))
                image = item.get("album", {}).get("images", [{}])[0].get("url", "")
                tracks.append({
                    "id": item["id"],
                    "name": item["name"],
                    "artists": artists,
                    "image": image,
                    "preview_url": item.get("preview_url"),
                    "spotify_url": item["external_urls"].get("spotify", ""),
                })
            return tracks
        else:
            print(f"[Spotify] API error status: {r.status_code}")
            print(f"[Spotify] API error response: {r.text}")
            if r.status_code == 403:
                print("[Spotify] ERROR: 403 Forbidden. Is your app in Development Mode? Make sure your email is added to the Spotify dashboard.")
    except Exception as e:
        print(f"[Spotify] Search connection error: {e}")

    return []
