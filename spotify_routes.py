from flask import Blueprint, request, jsonify
from spotify_helper import search_tracks, get_recommendations

spotify_bp = Blueprint("spotify", __name__)


@spotify_bp.route("/search", methods=["GET"])
def search():
    query = request.args.get("q", "")
    if not query:
        return jsonify({"error": "q param required"}), 400
    tracks = search_tracks(query, limit=8)
    return jsonify({"tracks": tracks})


@spotify_bp.route("/recommend", methods=["POST"])
def recommend():
    data = request.get_json(force=True)
    seeds = data.get("seeds", {})
    limit = int(data.get("limit", 10))
    tracks = get_recommendations(seeds, limit=limit)
    return jsonify({"tracks": tracks})
