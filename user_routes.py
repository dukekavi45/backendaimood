from flask import Blueprint, request, jsonify
import bcrypt
import jwt
import os
from datetime import datetime, timedelta, timezone
from db import get_db

user_bp = Blueprint("user", __name__)

JWT_SECRET = os.getenv("JWT_SECRET", "fallback-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXP_DAYS = 7


def make_token(user_id: int, username: str) -> str:
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXP_DAYS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str):
    """Decode a JWT. Returns payload dict or raises jwt.exceptions.*"""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def get_current_user():
    """
    Extract and validate the Bearer token from Authorization header.
    Returns (user_id, username) or raises ValueError with a message.
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise ValueError("Missing or invalid Authorization header")
    token = auth.split(" ", 1)[1]
    try:
        payload = decode_token(token)
        return payload["user_id"], payload["username"]
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {e}")


# ──────────────────────────────────────────────────────────────
# POST /api/user/register
# ──────────────────────────────────────────────────────────────
@user_bp.route("/register", methods=["POST", "OPTIONS"])
def register():
    print(f"[DEBUG] /register — method={request.method}")
    if request.method == "OPTIONS":
        return "", 200

    data = request.get_json(force=True, silent=True) or {}
    username  = (data.get("username")  or "").strip()
    email     = (data.get("email")     or "").strip()
    password  = (data.get("password")  or "").strip()
    full_name = (data.get("full_name") or "").strip()

    if not username or not email or not password:
        return jsonify({"error": "Username, email, and password are required"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    # NO HASHING as requested by user
    plain_password = password

    try:
        with get_db() as (conn, cur):
            # Check for existing user
            cur.execute(
                "SELECT id FROM users WHERE email = %s OR username = %s",
                (email, username)
            )
            existing = cur.fetchone()
            if existing:
                return jsonify({"error": "A user with that email or username already exists"}), 409

            # Insert new user
            cur.execute(
                "INSERT INTO users (username, email, password, full_name) "
                "VALUES (%s, %s, %s, %s)",
                (username, email, plain_password, full_name or None)
            )
            user_id = cur.lastrowid
            # commit happens automatically when `with` block exits cleanly

        print(f"[DEBUG] Registered user_id={user_id} username={username}")
        return jsonify({
            "success": True,
            "message": "Account created successfully",
            "user_id": user_id
        }), 201

    except Exception as e:
        print(f"[ERROR] register: {e}")
        return jsonify({"error": "Registration failed. Please try again."}), 500


# ──────────────────────────────────────────────────────────────
# POST /api/user/login
# ──────────────────────────────────────────────────────────────
@user_bp.route("/login", methods=["POST", "OPTIONS"])
def login():
    print(f"[DEBUG] /login — method={request.method}")
    if request.method == "OPTIONS":
        return "", 200

    data = request.get_json(force=True, silent=True) or {}
    identifier = (data.get("username") or data.get("email") or "").strip()
    password   = (data.get("password") or "").strip()

    if not identifier or not password:
        return jsonify({"error": "Email/username and password are required"}), 400

    try:
        user = None
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT id, username, email, full_name, password "
                "FROM users "
                "WHERE username = %s OR email = %s",
                (identifier, identifier)
            )
            user = cur.fetchone()

        if user is None:
            print(f"[DEBUG] Login: user not found for identifier={identifier}")
            return jsonify({"error": "Invalid email/username or password"}), 401

        # NO HASHING: direct string comparison
        if password != user["password"]:
            print(f"[DEBUG] Login: wrong password for identifier={identifier}")
            return jsonify({"error": "Invalid email/username or password"}), 401

        token = make_token(user["id"], user["username"])
        print(f"[DEBUG] Login success for user_id={user['id']}")
        return jsonify({
            "success": True,
            "token": token,
            "user": {
                "id":        user["id"],
                "username":  user["username"],
                "email":     user["email"],
                "full_name": user.get("full_name") or "",
            }
        }), 200

    except Exception as e:
        print(f"[ERROR] login: {e}")
        return jsonify({"error": "Login failed. Please try again."}), 500


# ──────────────────────────────────────────────────────────────
# GET /api/user/me  — JWT-protected, returns current user info
# ──────────────────────────────────────────────────────────────
@user_bp.route("/me", methods=["GET"])
def me():
    try:
        user_id, username = get_current_user()
    except ValueError as e:
        return jsonify({"error": str(e)}), 401

    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT id, username, email, full_name, country, phone_number, description, "
                "date_of_birth, partner, best_friend, best_person, avatar_url, created_at "
                "FROM users WHERE id = %s",
                (user_id,)
            )
            profile = cur.fetchone()

        if not profile:
            return jsonify({"error": "User not found"}), 404

        # Important: convert any potential tuples to dict if we ever move off DictCursor
        # but DictCursor is currently set in db.py. 
        # Making sure the frontend gets a clean object.
        return jsonify(profile), 200

    except Exception as e:
        print(f"[ERROR] /me: {e}")
        return jsonify({"error": "Could not fetch profile"}), 500


# ──────────────────────────────────────────────────────────────
# GET /api/user/profile/<user_id>
# ──────────────────────────────────────────────────────────────
@user_bp.route("/profile/<int:user_id>", methods=["GET"])
def get_profile(user_id):
    try:
        with get_db() as (conn, cur):
            cur.execute(
                "SELECT username, email, full_name, country, phone_number, description, "
                "date_of_birth, partner, best_friend, best_person, avatar_url "
                "FROM users WHERE id = %s",
                (user_id,)
            )
            profile = cur.fetchone()

        if profile:
            # If for some reason the database is not using DictCursor, 
            # we want to ensure the JSON is an object for the frontend.
            if isinstance(profile, (list, tuple)):
                return jsonify({
                    "username": profile[0],
                    "email": profile[1],
                    "full_name": profile[2],
                    "country": profile[3] if len(profile) > 3 else "",
                }), 200
            return jsonify(profile), 200
        return jsonify({"error": "User not found"}), 404

    except Exception as e:
        print(f"[ERROR] get_profile: {e}")
        return jsonify({"error": "Could not fetch profile"}), 500


@user_bp.route("/profile", methods=["PUT"])
def update_profile():
    """Update current user's profile info."""
    try:
        user_id, _ = get_current_user()
    except ValueError as e:
        return jsonify({"error": str(e)}), 401

    data = request.get_json(force=True, silent=True) or {}
    full_name      = data.get("full_name")
    country        = data.get("country")
    phone_number   = data.get("phone_number")
    description    = data.get("description")
    date_of_birth  = data.get("date_of_birth")
    partner        = data.get("partner")
    best_friend    = data.get("best_friend")
    best_person    = data.get("best_person")
    avatar_url     = data.get("avatar_url")

    try:
        with get_db() as (conn, cur):
            cur.execute(
                "UPDATE users SET "
                "full_name = %s, country = %s, phone_number = %s, description = %s, "
                "date_of_birth = %s, partner = %s, best_friend = %s, best_person = %s, avatar_url = %s "
                "WHERE id = %s",
                (full_name, country, phone_number, description, date_of_birth, partner, best_friend, best_person, avatar_url, user_id)
            )
        return jsonify({"success": True, "message": "Profile updated"}), 200
    except Exception as e:
        print(f"[ERROR] update_profile: {e}")
        return jsonify({"error": str(e)}), 500


# ──────────────────────────────────────────────────────────────
# POST /api/user/verify-token  — Check if a JWT is still valid
# ──────────────────────────────────────────────────────────────
@user_bp.route("/verify-token", methods=["POST"])
def verify_token():
    data = request.get_json(force=True, silent=True) or {}
    token = data.get("token", "")
    if not token:
        return jsonify({"valid": False, "error": "No token provided"}), 400
    try:
        payload = decode_token(token)
        return jsonify({"valid": True, "user_id": payload["user_id"], "username": payload["username"]}), 200
    except jwt.ExpiredSignatureError:
        return jsonify({"valid": False, "error": "Token expired"}), 401
    except jwt.InvalidTokenError as e:
        return jsonify({"valid": False, "error": str(e)}), 401
