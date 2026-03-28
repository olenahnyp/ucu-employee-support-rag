CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(20) DEFAULT 'user'
);

CREATE TABLE IF NOT EXISTS access_control (
    id SERIAL PRIMARY KEY,
    role VARCHAR(20) NOT NULL,
    allowed_category VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS processed_documents (
    id SERIAL PRIMARY KEY,
    google_drive_id TEXT UNIQUE,
    file_name TEXT,
    markdown_content TEXT,
    category TEXT DEFAULT 'public',
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);