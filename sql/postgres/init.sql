CREATE DATABASE airflow;
CREATE DATABASE channels_data;

CREATE USER airflow WITH PASSWORD 'airflow';

GRANT ALL PRIVILEGES ON DATABASE airflow TO airflow;

\connect channels_data;
CREATE TABLE IF NOT EXISTS channels (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    total_video_visit BIGINT CHECK (total_video_visit >= 0),
    video_count INT CHECK (video_count >= 0),
    start_date_timestamp BIGINT CHECK (start_date_timestamp >= 0),
    followers_count BIGINT CHECK (followers_count >= 0),
    country TEXT,
    created_at TIMESTAMP DEFAULT '2025-01-01 00:00:00',
    update_count INT
);

\COPY channels (username, total_video_visit, video_count, start_date_timestamp, followers_count, country, update_count) FROM '/docker-entrypoint-initdb.d/raw-channel-data/channels_stripped.csv' WITH (FORMAT csv, HEADER, DELIMITER ',', QUOTE '"', ESCAPE '"');
