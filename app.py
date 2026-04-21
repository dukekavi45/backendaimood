from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os

# ── Load .env FIRST before any other imports ──────────────────
load_dotenv()

app = Flask(__name__)

# ── CORS — allow all origins in development ───────────────────
CORS(app, resources={r"/*": {"origins": "*"}},
     supports_credentials=False,
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

app.config["SECRET_KEY"]  = os.getenv("SECRET_KEY",  "moodwave_fallback_key")
app.config["JWT_SECRET"]  = os.getenv("JWT_SECRET",  "moodwave_fallback_jwt_secret")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024 

# ── Register blueprints ───────────────────────────────────────
from user_routes     import user_bp
from mood_routes     import mood_bp
from spotify_routes  import spotify_bp
from analytics_routes import analytics_bp

app.register_blueprint(user_bp,      url_prefix="/api/user")
app.register_blueprint(mood_bp,      url_prefix="/api/mood")
app.register_blueprint(spotify_bp,   url_prefix="/api/spotify")
app.register_blueprint(analytics_bp, url_prefix="/api/analytics")

# ── Root / Health Check ───────────────────────────────────────
@app.route("/")
def index():
    return jsonify({
        "name": "MoodWave API Server",
        "status": "Online 🎵",
        "message": "Welcome to MoodWave Backend. Frontend is usually on Port 5173.",
        "endpoints": ["/api/user", "/api/mood", "/api/spotify", "/api/analytics"]
    }), 200

@app.route("/api/health")
def health():
    from datetime import datetime
    now = datetime.now()
    return jsonify({
        "status": "MoodWave API running 🎵", 
        "version": "2.0.0",
        "server_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "day": now.strftime("%A"),
        "tomorrow": (datetime.fromtimestamp(now.timestamp() + 86400)).strftime("%A")
    }), 200

# ── Global Error Handler ──────────────────────────────────────
@app.errorhandler(Exception)
def handle_exception(e):
    # Pass through HTTP errors
    if hasattr(e, 'code'):
        return jsonify({"error": str(e)}), e.code
    # Handle non-HTTP exceptions
    print(f"[CRITICAL ERROR] {e}")
    return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500

# ── DB init (run after blueprints so errors don't block startup) ─
from db import init_db
with app.app_context():
    init_db()

if __name__ == "__main__":
    print("Starting MoodWave API on http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
