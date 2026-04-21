"""
check_auth.py - Developer diagnostic for MoodWave auth system.
Run: python check_auth.py
"""
import os, sys
from dotenv import load_dotenv
load_dotenv()

SEP = "-" * 60

def section(title):
    print("\n" + SEP)
    print("  " + title)
    print(SEP)

def ok(msg):   print("  [OK]   " + msg)
def fail(msg): print("  [FAIL] " + msg)
def info(msg): print("  [INFO] " + msg)

# ---- 1. ENV VARS ------------------------------------------------
section("1. Environment Variables")
required_vars = ["DB_HOST","DB_PORT","DB_USER","DB_PASSWORD","DB_NAME","JWT_SECRET"]
all_set = True
for v in required_vars:
    val = os.getenv(v)
    if val:
        masked = val[:4] + "*" * max(0, len(val)-4)
        ok(f"{v} = {masked}")
    else:
        fail(f"{v} is NOT set")
        all_set = False

if not all_set:
    print("\n  WARNING: Fix missing .env variables before continuing.")
    sys.exit(1)

# ---- 2. MySQL Connection ----------------------------------------
section("2. MySQL Connection")
try:
    import pymysql
    conn = pymysql.connect(
        host=os.getenv("DB_HOST","127.0.0.1"),
        port=int(os.getenv("DB_PORT",3306)),
        user=os.getenv("DB_USER","root"),
        password=os.getenv("DB_PASSWORD",""),
        database=os.getenv("DB_NAME","mood_wave"),
        charset="utf8mb4",
        connect_timeout=5,
        cursorclass=pymysql.cursors.DictCursor,
    )
    ok("Connected to MySQL at %s:%s" % (os.getenv("DB_HOST"), os.getenv("DB_PORT")))
    ok("Database: " + os.getenv("DB_NAME"))
except Exception as e:
    fail("MySQL connection failed: " + str(e))
    info("Fix: check DB credentials in .env and ensure MySQL is running")
    sys.exit(1)

# ---- 3. Tables --------------------------------------------------
section("3. Database Tables")
required_tables = ["users","history_storage","user_sessions","saved_playlists"]
try:
    with conn.cursor() as cur:
        cur.execute("SHOW TABLES")
        existing = {list(r.values())[0] for r in cur.fetchall()}
    for t in required_tables:
        if t in existing:
            ok("Table '%s' exists" % t)
        else:
            fail("Table '%s' is MISSING - restart Flask to auto-apply schema" % t)
except Exception as e:
    fail("Could not check tables: " + str(e))

# ---- 4. User Count ----------------------------------------------
section("4. Users in DB")
try:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) as cnt FROM users")
        cnt = cur.fetchone()["cnt"]
    ok("users has %d user(s)" % cnt)
    if cnt > 0:
        with conn.cursor() as cur:
            cur.execute("SELECT id, username, email FROM users LIMIT 5")
            rows = cur.fetchall()
        for r in rows:
            info("  id=%s username=%s email=%s" % (r["id"], r["username"], r["email"]))
except Exception as e:
    fail("Could not query users: " + str(e))

# ---- 5. bcrypt --------------------------------------------------
section("5. bcrypt Hashing")
try:
    import bcrypt
    test_pw = b"TestPassword123"
    hashed = bcrypt.hashpw(test_pw, bcrypt.gensalt())
    if bcrypt.checkpw(test_pw, hashed):
        ok("bcrypt hash/verify working (version: %s)" % bcrypt.__version__)
    else:
        fail("bcrypt checkpw returned False")
    # Test with a stored hash style
    stored = hashed.decode("utf-8")
    if bcrypt.checkpw(test_pw, stored.encode("utf-8")):
        ok("bcrypt round-trip via str->encode works correctly")
    else:
        fail("bcrypt round-trip via str->encode failed")
except ImportError:
    fail("bcrypt NOT installed - run: pip install bcrypt==4.1.2")
except Exception as e:
    fail("bcrypt error: " + str(e))

# ---- 6. PyJWT ---------------------------------------------------
section("6. PyJWT Encode/Decode")
try:
    import jwt
    from datetime import datetime, timedelta, timezone
    secret = os.getenv("JWT_SECRET","fallback")
    payload = {
        "user_id": 999,
        "username": "diag_user",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    decoded = jwt.decode(token, secret, algorithms=["HS256"])
    assert decoded["user_id"] == 999, "user_id mismatch"
    assert isinstance(token, str), "token should be str in PyJWT>=2"
    ok("PyJWT encode/decode working (version: %s)" % jwt.__version__)
    ok("Token type: %s, sample: %s..." % (type(token).__name__, token[:40]))
except ImportError:
    fail("PyJWT NOT installed - run: pip install PyJWT==2.8.0")
except Exception as e:
    fail("JWT error: " + str(e))

# ---- 7. HTTP End-to-End -----------------------------------------
section("7. HTTP Auth Test (requires Flask on :5000)")
try:
    import requests, uuid
    BASE = "http://localhost:5000/api"

    try:
        r = requests.get(BASE + "/health", timeout=4)
        ok("Health: " + str(r.json()))
    except Exception:
        fail("Flask NOT running on port 5000")
        info("Start with: python app.py")
        raise SystemExit

    # Register
    tu = "diag_" + uuid.uuid4().hex[:6]
    te = tu + "@test.moodwave"
    tp = "DiagPass123"

    r = requests.post(BASE + "/user/register", json={
        "username": tu, "email": te, "password": tp, "full_name": "Diag User"
    }, timeout=6)
    if r.status_code == 201:
        ok("Register: 201 Created, user_id=%s" % r.json().get("user_id"))
    else:
        fail("Register failed: %d - %s" % (r.status_code, r.text))

    # Login
    r2 = requests.post(BASE + "/user/login", json={"username": tu, "password": tp}, timeout=6)
    if r2.status_code == 200 and r2.json().get("success"):
        token = r2.json()["token"]
        user  = r2.json()["user"]
        ok("Login: 200 OK, username=%s" % user["username"])
        ok("JWT: %s..." % token[:40])

        # /me
        r3 = requests.get(BASE + "/user/me",
                          headers={"Authorization": "Bearer " + token}, timeout=4)
        if r3.status_code == 200:
            ok("/me: username=%s email=%s" % (r3.json()["username"], r3.json()["email"]))
        else:
            fail("/me returned %d: %s" % (r3.status_code, r3.text))

        # verify-token
        r4 = requests.post(BASE + "/user/verify-token", json={"token": token}, timeout=4)
        if r4.json().get("valid"):
            ok("verify-token: valid for user_id=%s" % r4.json()["user_id"])
        else:
            fail("verify-token failed: " + r4.text)

        # Cleanup
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE username = %s", (tu,))
        conn.commit()
        ok("Cleanup: test user '%s' removed" % tu)
    else:
        fail("Login failed: %d - %s" % (r2.status_code, r2.text))

except SystemExit:
    info("Skipping HTTP tests")
except Exception as e:
    fail("HTTP test error: " + str(e))

conn.close()
print("\n" + SEP)
print("  Diagnostic complete!")
print(SEP + "\n")
