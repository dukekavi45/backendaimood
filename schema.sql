-- ═══════════════════════════════════════════════════════════
--  MoodWave MySQL Schema
--  NOTE: DATABASE is created by Railway automatically.
--  Do NOT include CREATE DATABASE / USE here for cloud deploy.
-- ═══════════════════════════════════════════════════════════

-- ─────────────────────────────────────────────────────────
--  1. USERS
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            INT UNSIGNED    AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)     NOT NULL UNIQUE,
    email         VARCHAR(120)    NOT NULL UNIQUE,
    password      VARCHAR(256)    NOT NULL,
    full_name     VARCHAR(100)    DEFAULT NULL,
    country       VARCHAR(100)    DEFAULT NULL,
    phone_number  VARCHAR(20)     DEFAULT NULL,
    description   TEXT            DEFAULT NULL,
    date_of_birth DATE            DEFAULT NULL,
    partner       VARCHAR(100)    DEFAULT NULL,
    best_friend   VARCHAR(100)    DEFAULT NULL,
    best_person   VARCHAR(100)    DEFAULT NULL,
    avatar_url    VARCHAR(500)    DEFAULT NULL,
    is_active     TINYINT(1)      NOT NULL DEFAULT 1,
    created_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                  ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email    (email),
    INDEX idx_username (username)
) ENGINE=InnoDB;

-- ─────────────────────────────────────────────────────────
--  2. HISTORY_STORAGE
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS history_storage (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNSIGNED NOT NULL,
    source          ENUM('text','image','selfie') NOT NULL DEFAULT 'text',
    input_text      TEXT         DEFAULT NULL,
    mood            VARCHAR(30)  NOT NULL,
    confidence      DECIMAL(5,2) DEFAULT NULL,
    raw_emotions    JSON         DEFAULT NULL,
    detected_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_mood (user_id, mood),
    INDEX idx_detected  (detected_at),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ─────────────────────────────────────────────────────────
--  3. USER_SESSIONS
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_sessions (
    id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id       INT UNSIGNED NOT NULL,
    token_hash    VARCHAR(256) NOT NULL,
    expires_at    DATETIME     NOT NULL,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ─────────────────────────────────────────────────────────
--  4. SAVED_PLAYLISTS
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS saved_playlists (
    id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id       INT UNSIGNED NOT NULL,
    name          VARCHAR(150) NOT NULL,
    mood          VARCHAR(30)  NOT NULL,
    tracks        JSON         NOT NULL,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ═══════════════════════════════════════════════════════════
--  Seed: demo user
-- ═══════════════════════════════════════════════════════════
INSERT IGNORE INTO users (username, email, password, full_name) VALUES
  ('demo_user', 'demo@moodwave.app', 'demo123', 'Demo User'),
  ('kavi_45', 'kavibalan200445@gmail.com', '123456', 'kavibalan');
