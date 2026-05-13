CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS urls (
    id_urls BIGSERIAL PRIMARY KEY,
    url TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id_users BIGINT PRIMARY KEY,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    id_urls BIGINT REFERENCES urls(id_urls),
    friends_count INTEGER,
    listed_count INTEGER,
    favourites_count INTEGER,
    statuses_count INTEGER,
    protected BOOLEAN,
    verified BOOLEAN,
    screen_name TEXT,
    name TEXT,
    location TEXT,
    description TEXT,
    withheld_in_countries VARCHAR(2)[]
);

CREATE TABLE IF NOT EXISTS tweets (
    id_tweets BIGINT PRIMARY KEY,
    id_users BIGINT REFERENCES users(id_users),
    created_at TIMESTAMPTZ,
    in_reply_to_status_id BIGINT,
    in_reply_to_user_id BIGINT,
    quoted_status_id BIGINT,
    retweet_count INTEGER,
    favorite_count INTEGER,
    quote_count INTEGER,
    withheld_copyright BOOLEAN,
    withheld_in_countries VARCHAR(2)[],
    source TEXT,
    text TEXT,
    country_code VARCHAR(2),
    state_code VARCHAR(2),
    lang TEXT,
    place_name TEXT,
    geo GEOMETRY
);

CREATE TABLE IF NOT EXISTS tweet_urls (
    id_tweets BIGINT REFERENCES tweets(id_tweets),
    id_urls BIGINT REFERENCES urls(id_urls),
    PRIMARY KEY (id_tweets, id_urls)
);

CREATE TABLE IF NOT EXISTS tweet_mentions (
    id_tweets BIGINT REFERENCES tweets(id_tweets),
    id_users BIGINT REFERENCES users(id_users),
    PRIMARY KEY (id_tweets, id_users)
);

CREATE TABLE IF NOT EXISTS tweet_tags (
    id_tweets BIGINT REFERENCES tweets(id_tweets),
    tag TEXT,
    PRIMARY KEY (id_tweets, tag)
);

CREATE TABLE IF NOT EXISTS tweet_media (
    id_tweets BIGINT REFERENCES tweets(id_tweets),
    id_urls BIGINT REFERENCES urls(id_urls),
    type TEXT,
    PRIMARY KEY (id_tweets, id_urls)
);

CREATE INDEX IF NOT EXISTS tweets_text_fts
    ON tweets
    USING GIN(to_tsvector('english', text));

CREATE TABLE IF NOT EXISTS app_users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    id_users BIGINT REFERENCES users(id_users),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
