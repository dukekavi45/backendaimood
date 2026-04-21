from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from collections import Counter
from db import get_db

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/weekly/<int:user_id>", methods=["GET"])
def weekly_report(user_id):
    """Weekly mood summary for a user."""
    since = datetime.utcnow() - timedelta(days=7)
    
    with get_db() as (conn, cur):
        cur.execute("""
            SELECT mood, detected_at
            FROM history_storage
            WHERE user_id = %s AND detected_at >= %s
        """, (user_id, since))
        entries = cur.fetchall()

    mood_counts = Counter(e["mood"] for e in entries)
    dominant = mood_counts.most_common(1)[0][0] if mood_counts else "neutral"

    daily = {}
    for e in entries:
        day = e["detected_at"].strftime("%a")
        daily.setdefault(day, []).append(e["mood"])

    daily_summary = {day: Counter(moods).most_common(1)[0][0] for day, moods in daily.items()}

    return jsonify({
        "total_entries": len(entries),
        "mood_distribution": dict(mood_counts),
        "dominant_mood": dominant,
        "daily_summary": daily_summary,
        "period": "last 7 days",
    })

@analytics_bp.route("/summary/<int:user_id>", methods=["GET"])
def get_summary(user_id):
    """General mood summary across all time."""
    with get_db() as (conn, cur):
        cur.execute("SELECT COUNT(*) as total FROM history_storage WHERE user_id = %s", (user_id,))
        total = cur.fetchone()['total']
        
        cur.execute("SELECT mood, COUNT(*) as count FROM history_storage WHERE user_id = %s GROUP BY mood ORDER BY count DESC", (user_id,))
        mood_distribution = {row['mood']: row['count'] for row in cur.fetchall()}
        
    return jsonify({
        "total_sessions": total,
        "mood_distribution": mood_distribution
    })
