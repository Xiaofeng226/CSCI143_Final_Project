#!/bin/sh
echo "========================================"
echo "Loading tweets..."
echo "========================================"
time python3 load_tweets.py \
    --db=postgresql://twitter:twitter@localhost:9876/twitter_dev \
    --inputs /data/Twitter\ dataset/geoTwitter20-01-01.zip
