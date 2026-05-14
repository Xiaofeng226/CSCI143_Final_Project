#!/bin/sh
DB=${1:-postgresql://twitter:twitter@localhost:9876/twitter_dev}
echo "========================================"
echo "Loading tweets into $DB..."
echo "========================================"
time python3 load_tweets.py \
    --db=$DB \
    --inputs data/sample_small.json
