from flask import Blueprint, request, jsonify
from datetime import datetime
import json
from db import get_db
from mood_model import detect_mood_from_text, detect_mood_from_image, EMOTION_SEED_MAP
from spotify_helper import get_recommendations, search_tracks
from youtube_helper import search_youtube_videos

mood_bp = Blueprint("mood", __name__)

# ── Spotify-Specific Mapping Recommendation (Fallback for 403/Empty results) ──
SPOTIFY_MAPPING = {
    "happy": [
        {"name": "Happy", "artists": "Pharrell Williams", "image": "https://i.scdn.co/image/ab67616d0000b2733b1e967a57de8426ecce7930", "spotify_url": "https://open.spotify.com/track/60nZvlP3vZ76pQkyTz9tS8"},
        {"name": "Can't Stop the Feeling!", "artists": "Justin Timberlake", "image": "https://i.scdn.co/image/ab67616d0000b27361993425b741527027d142d7", "spotify_url": "https://open.spotify.com/track/1Wj9X3B5s6X3dYaD5Y5Yf4" },
        {"name": "Walking On Sunshine", "artists": "Katrina & The Waves", "image": "https://i.scdn.co/image/ab67616d0000b273ecb83", "spotify_url": "https://open.spotify.com/track/05wIrZSwuaVWhcv5FfqeH0" },
        {"name": "Good Vibrations", "artists": "The Beach Boys", "image": "https://i.scdn.co/image/ab67616d0000b2733b1e967a57de", "spotify_url": "https://open.spotify.com/track/5t9KYeS9qYfGZ4X5zW6n7N" }
    ],
    "sad": [
        {"name": "Someone Like You", "artists": "Adele", "image": "https://i.scdn.co/image/ab67616d0000b2732115bd3a0c45169a92a54a05", "spotify_url": "https://open.spotify.com/track/4rs7A8qR199Lrk6W0G" },
        {"name": "Fix You", "artists": "Coldplay", "image": "https://i.scdn.co/image/ab67616d0000b27341993425b", "spotify_url": "https://open.spotify.com/track/7LVvBPSI9Hne6j97k7qtzP" },
        {"name": "Stay With Me", "artists": "Sam Smith", "image": "https://i.scdn.co/image/ab67616d0000b2737648347f3ae3ca58a52e9a3b", "spotify_url": "https://open.spotify.com/track/5Nm9ER99fB9CSuUiw6vYAW" },
        {"name": "Hurt", "artists": "Johnny Cash", "image": "https://i.scdn.co/image/ab67616d0000b273e92", "spotify_url": "https://open.spotify.com/track/28ou9P5f9yZp3Lc6mY99wT" }
    ],
    "angry": [
        {"name": "In the End", "artists": "Linkin Park", "image": "https://i.scdn.co/image/ab67616d0000b2736648347f3ae3ca58a52e9a3b", "spotify_url": "https://open.spotify.com/track/6RqSrxqVvY6vAnp0Dov99O" },
        {"name": "Break Stuff", "artists": "Limp Bizkit", "image": "https://i.scdn.co/image/ab67616d0000b27339247941294812", "spotify_url": "https://open.spotify.com/track/588837136w7pQkyTz9tS8" },
        {"name": "Killing In The Name", "artists": "Rage Against The Machine", "image": "https://i.scdn.co/image/ab67616d0000b2737c3", "spotify_url": "https://open.spotify.com/track/59id8Zp3Lc6mY99wT7S8" },
        {"name": "Chop Suey!", "artists": "System Of A Down", "image": "https://i.scdn.co/image/ab67616d0000b273f55", "spotify_url": "https://open.spotify.com/track/2DlHlZp3Lc6mY99wT7S8" }
    ],
    "workout": [
        {"name": "Eye of the Tiger", "artists": "Survivor", "image": "https://i.scdn.co/image/ab67616d0000b273d2a7042a98f1f516d25f540c", "spotify_url": "https://open.spotify.com/track/2KH16t" },
        {"name": "Stronger", "artists": "Kanye West", "image": "https://i.scdn.co/image/ab67616d0000b2737748347f3ae3ca58a52e9a3b", "spotify_url": "https://open.spotify.com/track/49340" },
        {"name": "Till I Collapse", "artists": "Eminem", "image": "https://i.scdn.co/image/ab67616d0000b273bb", "spotify_url": "https://open.spotify.com/track/42vw" },
        {"name": "Remember the Name", "artists": "Fort Minor", "image": "https://i.scdn.co/image/ab67616d0000b27311c", "spotify_url": "https://open.spotify.com/track/6qO" }
    ],
    "romantic": [
        {"name": "Perfect", "artists": "Ed Sheeran", "image": "https://i.scdn.co/image/ab67616d0000b273ba5db4a5157c5957d97a08e1", "spotify_url": "https://open.spotify.com/track/0tgVp" },
        {"name": "All of Me", "artists": "John Legend", "image": "https://i.scdn.co/image/ab67616d0000b273562624dc4a888c30f4a86c67", "spotify_url": "https://open.spotify.com/track/3U41" },
        {"name": "Thinking Out Loud", "artists": "Ed Sheeran", "image": "https://i.scdn.co/image/ab67616d0000b273b", "spotify_url": "https://open.spotify.com/track/34s" }
    ],
    "party": [
        {"name": "Uptown Funk", "artists": "Mark Ronson ft. Bruno Mars", "image": "https://i.scdn.co/image/ab67616d0000b273f00cd3e0c034", "spotify_url": "https://open.spotify.com/track/3294" },
        {"name": "Party Rock Anthem", "artists": "LMFAO", "image": "https://i.scdn.co/image/ab67616d0000b2732934", "spotify_url": "https://open.spotify.com/track/2349" },
        {"name": "Yeah!", "artists": "Usher", "image": "https://i.scdn.co/image/ab67616d0000b273f", "spotify_url": "https://open.spotify.com/track/45f" }
    ],
    "focus": [
        {"name": "Lofi Study", "artists": "Lofi Girl", "image": "https://i.scdn.co/image/ab67616d0000b2731113", "spotify_url": "https://open.spotify.com/track/23423" },
        {"name": "Weightless", "artists": "Marconi Union", "image": "https://i.scdn.co/image/ab67616d0000b2732223", "spotify_url": "https://open.spotify.com/track/1231" },
        {"name": "Study Vibes", "artists": "Chillhop Music", "image": "https://i.scdn.co/image/ab67616d0000b273cc", "spotify_url": "https://open.spotify.com/track/77" }
    ],
    "neutral": [
        {"name": "Chill Vibes", "artists": "MoodWave Curated", "image": "https://i.scdn.co/image/ab67616d0000b2734444", "spotify_url": "https://open.spotify.com/track/5555" },
        {"name": "After Dark", "artists": "Mr. Kitty", "image": "https://i.scdn.co/image/ab67616d0000b273dd", "spotify_url": "https://open.spotify.com/track/001" }
    ],
    "fear": [
        {"name": "Clair de Lune", "artists": "Claude Debussy", "image": "https://i.scdn.co/image/ab67616d0000b2737723", "spotify_url": "https://open.spotify.com/track/6Uyt" },
        {"name": "In the Air Tonight", "artists": "Phil Collins", "image": "https://i.scdn.co/image/ab67616d0000b273ee", "spotify_url": "https://open.spotify.com/track/02" }
    ],
    "surprise": [
        {"name": "Electric Feel", "artists": "MGMT", "image": "https://i.scdn.co/image/ab67616d0000b2739923", "spotify_url": "https://open.spotify.com/track/3034" },
        {"name": "Starboy", "artists": "The Weeknd", "image": "https://i.scdn.co/image/ab67616d0000b273ff", "spotify_url": "https://open.spotify.com/track/03" }
    ],
    "disgust": [
        {"name": "Smells Like Teen Spirit", "artists": "Nirvana", "image": "https://i.scdn.co/image/ab67616d0000b2731111", "spotify_url": "https://open.spotify.com/track/1111" },
        {"name": "Creep", "artists": "Radiohead", "image": "https://i.scdn.co/image/ab67616d0000b273gg", "spotify_url": "https://open.spotify.com/track/04" }
    ],
    "calm": [
        {"name": "Sunset Lover", "artists": "Petit Biscuit", "image": "https://i.scdn.co/image/ab67616d0000b2737b", "spotify_url": "https://open.spotify.com/track/0h" },
        {"name": "River Flows In You", "artists": "Yiruma", "image": "https://i.scdn.co/image/ab67616d0000b273b3", "spotify_url": "https://open.spotify.com/track/2g" }
    ],
    "gaming": [
        {"name": "Legends Never Die", "artists": "Against The Current", "image": "https://i.scdn.co/image/ab67616d0000b273b5", "spotify_url": "https://open.spotify.com/track/1F" },
        {"name": "Enemy", "artists": "Imagine Dragons", "image": "https://i.scdn.co/image/ab67616d0000b273d2", "spotify_url": "https://open.spotify.com/track/1q" },
        {"name": "Warriors", "artists": "Imagine Dragons", "image": "https://i.scdn.co/image/ab67616d0000b273a0", "spotify_url": "https://open.spotify.com/track/1s" }
    ],
    "telugu": [
        {"name": "Butta Bomma", "artists": "Armaan Malik", "image": "https://i.scdn.co/image/ab67616d0000b27389", "spotify_url": "https://open.spotify.com/track/4" },
        {"name": "Samajavaragamana", "artists": "Sid Sriram", "image": "https://i.scdn.co/image/ab67616d0000b27377", "spotify_url": "https://open.spotify.com/track/5" }
    ]
}

@mood_bp.route("/text", methods=["POST"])
def mood_from_text():
    """POST { user_id, text } → mood + seeds"""
    data = request.get_json(force=True)
    text = data.get("text", "").strip()
    user_id = data.get("user_id")

    if not text:
        return jsonify({"error": "text is required"}), 400

    try:
        result = detect_mood_from_text(text)
        
        # Save to DB if user_id is provided
        if user_id:
            try:
                with get_db() as (conn, cur):
                    cur.execute("""
                        INSERT INTO history_storage (user_id, source, input_text, mood, confidence)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (user_id, 'text', text, result["mood"], result["confidence"]))
            except Exception as db_err:
                print(f"[MoodRoutes] DB save failed (text): {db_err}")

        return jsonify({
            "mood": result["mood"],
            "confidence": result["confidence"],
            "seeds": result["seeds"]
        })
    except Exception as e:
        print(f"[MoodRoutes] Text analysis error: {e}")
        return jsonify({"error": str(e), "mood": "neutral", "confidence": 0, "seeds": EMOTION_SEED_MAP["neutral"]}), 500


@mood_bp.route("/image", methods=["POST"])
def mood_from_image():
    """POST { user_id, image_base64 } → mood + results"""
    data = request.get_json(force=True)
    image_data = data.get("image_base64", "")
    user_id = data.get("user_id")

    if not image_data:
        return jsonify({"error": "image_base64 is required"}), 400

    try:
        result = detect_mood_from_image(image_data)
        
        # Save to MySQL if user_id present
        if user_id and result.get("mood"):
             try:
                with get_db() as (conn, cur):
                    cur.execute("""
                        INSERT INTO history_storage (user_id, source, mood, confidence, raw_emotions)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (user_id, 'selfie', result["mood"], result["confidence"], json.dumps(result.get("raw_emotions", {}))))
             except Exception as db_err:
                 print(f"[MoodRoutes] DB save failed (image): {db_err}")

        return jsonify({
            "mood": result.get("mood", "neutral"),
            "confidence": result.get("confidence", 50.0),
            "raw_emotions": result.get("raw_emotions", {}),
            "seeds": result.get("seeds", EMOTION_SEED_MAP["neutral"])
        })
    except Exception as e:
        print(f"[MoodRoutes] Image analysis error: {e}")
        return jsonify({"error": str(e), "mood": "neutral", "confidence": 0, "seeds": EMOTION_SEED_MAP["neutral"]}), 500


@mood_bp.route("/recommendations", methods=["POST"])
def get_mood_recommendations():
    """POST { mood, language } → spotify + youtube results"""
    data = request.get_json(force=True)
    mood = data.get("mood", "neutral")
    language = data.get("language", "English").strip()
    
    # Query Spotify/YouTube with dynamic search queries
    if mood == "workout":
        search_query = f"{language} Workout Gym Motivation High Energy songs"
    elif mood == "romantic":
        search_query = f"{language} Romantic Love Ballads and Sweetest Songs"
    elif mood == "party":
        search_query = f"{language} Party Dance Club Anthems"
    elif mood == "focus":
        search_query = f"{language} Deep Focus Lo-fi Study Beats"
    elif mood == "happy":
        search_query = f"{language} Feel Good Upbeat Happy Hits"
    else:
        search_query = f"{language} {mood} music"

    # ── Spotify Recommendation Logic ──
    # User requested to avoid static mapping and use base emotion search
    seeds = EMOTION_SEED_MAP.get(mood, EMOTION_SEED_MAP["neutral"])
    spotify_tracks = search_tracks(search_query, limit=12)
    
    if not spotify_tracks:
        print(f"[MoodRoutes] API Search empty. Trying Recommendation Engine via seeds...")
        spotify_tracks = get_recommendations(seeds, limit=10)
    
    # Final Fallback to hardcoded mapping only if all API calls fail
    if not spotify_tracks:
        print(f"[MoodRoutes] Spotify API failed (possible 403/Quota). Using hardcoded mapping.")
        # Ensure we only use the primary emotion to avoid "sad" bias if mapping is needed
        spotify_tracks = SPOTIFY_MAPPING.get(mood, SPOTIFY_MAPPING["neutral"])

    # ── YouTube Logic (Stay with Search) ──
    # Explicitly include the detected mood in the YouTube search to ensure accuracy
    youtube_videos = search_youtube_videos(search_query, max_results=8)
    
    return jsonify({
        "mood": mood,
        "language": language,
        "spotify": spotify_tracks,
        "youtube": youtube_videos
    })


@mood_bp.route("/history/<int:user_id>", methods=["GET"])
def get_history(user_id):
    """GET mood history for a user (last 50 entries)"""
    with get_db() as (conn, cur):
        cur.execute("""
            SELECT mood, source, confidence, detected_at, raw_emotions
            FROM history_storage
            WHERE user_id = %s
            ORDER BY detected_at DESC
            LIMIT 50
        """, (user_id,))
        entries = cur.fetchall()
        
    for e in entries:
        if e.get("detected_at"):
            e["detected_at"] = e["detected_at"].isoformat()
        if e.get("raw_emotions"):
            try:
                e["raw_emotions"] = json.loads(e["raw_emotions"])
            except:
                pass
                
    return jsonify(entries)


@mood_bp.route("/singer-search", methods=["GET"])
def singer_search():
    """GET /api/mood/singer-search?q=Harris+Jayaraj&lang=Tamil"""
    query = request.args.get("q", "").strip()
    language = request.args.get("lang", "English").strip()
    
    if not query:
        return jsonify({"error": "artist query is required"}), 400
        
    # Build a specific query for the artist in that language
    full_query = f"{query} {language} songs playlist"
    print(f"[MoodRoutes] Artist Search: {full_query}")
    
    youtube_videos = search_youtube_videos(full_query, max_results=8)
    return jsonify({"youtube": youtube_videos})


@mood_bp.route("/top-hits", methods=["GET"])
def top_hits():
    """GET /api/mood/top-hits?lang=Tamil"""
    language = request.args.get("lang", "English").strip()
    
    # Query for the literal top hits of the current year
    full_query = f"Top {language} songs 2026 hits playlist"
    print(f"[MoodRoutes] Top Hits Request: {full_query}")
    
    youtube_videos = search_youtube_videos(full_query, max_results=12)
    return jsonify({"youtube": youtube_videos})
