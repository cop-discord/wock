CREATE TABLE IF NOT EXISTS tts_preferences (
    user_id BIGINT PRIMARY KEY,
    accent VARCHAR(10) DEFAULT 'us',
    language VARCHAR(5) DEFAULT 'en'
);

CREATE TABLE IF NOT EXISTS blacklist (
    target_id BIGINT PRIMARY KEY,
    reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);