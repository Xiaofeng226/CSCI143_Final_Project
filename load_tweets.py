import sqlalchemy
import os
import datetime
import zipfile
import io
import json

def remove_nulls(s):
    if s is None:
        return None
    return s.replace('\x00', '')

def get_id_urls(url, connection):
    sql = sqlalchemy.text('''
        INSERT INTO urls (url) VALUES (:url)
        ON CONFLICT DO NOTHING
        RETURNING id_urls;
    ''')
    res = connection.execute(sql, {'url': url}).first()
    if res is None:
        sql = sqlalchemy.text('SELECT id_urls FROM urls WHERE url = :url')
        res = connection.execute(sql, {'url': url}).first()
    return res[0]

def insert_tweet(connection, tweet):
    sql = sqlalchemy.text('SELECT id_tweets FROM tweets WHERE id_tweets = :id_tweets')
    res = connection.execute(sql, {'id_tweets': tweet['id']})
    if res.first() is not None:
        return

    if tweet['user']['url'] is None:
        user_id_urls = None
    else:
        user_id_urls = get_id_urls(tweet['user']['url'], connection)

    sql = sqlalchemy.text('''
        INSERT INTO users
        (id_users, created_at, updated_at, id_urls, friends_count, listed_count, favourites_count, statuses_count, protected, verified, screen_name, name, location, description, withheld_in_countries)
        VALUES
        (:id_users, :created_at, :updated_at, :id_urls, :friends_count, :listed_count, :favourites_count, :statuses_count, :protected, :verified, :screen_name, :name, :location, :description, :withheld_in_countries)
        ON CONFLICT (id_users) DO UPDATE SET
        updated_at = EXCLUDED.updated_at,
        screen_name = EXCLUDED.screen_name,
        name = EXCLUDED.name;
    ''')
    connection.execute(sql, {
        'id_users': tweet['user']['id'],
        'created_at': tweet['user']['created_at'],
        'updated_at': tweet['created_at'],
        'id_urls': user_id_urls,
        'friends_count': tweet['user']['friends_count'],
        'listed_count': tweet['user']['listed_count'],
        'favourites_count': tweet['user']['favourites_count'],
        'statuses_count': tweet['user']['statuses_count'],
        'protected': tweet['user']['protected'],
        'verified': tweet['user']['verified'],
        'screen_name': remove_nulls(tweet['user']['screen_name']),
        'name': remove_nulls(tweet['user']['name']),
        'location': remove_nulls(tweet['user']['location']),
        'description': remove_nulls(tweet['user']['description']),
        'withheld_in_countries': tweet['user'].get('withheld_in_countries', None),
    })

    try:
        geo_coords = tweet['geo']['coordinates']
        geo_coords = str(geo_coords[0]) + ' ' + str(geo_coords[1])
        geo_str = 'POINT'
    except TypeError:
        try:
            geo_coords = '('
            for i, poly in enumerate(tweet['place']['bounding_box']['coordinates']):
                if i > 0:
                    geo_coords += ','
                geo_coords += '('
                for j, point in enumerate(poly):
                    geo_coords += str(point[0]) + ' ' + str(point[1]) + ','
                geo_coords += str(poly[0][0]) + ' ' + str(poly[0][1])
                geo_coords += ')'
            geo_coords += ')'
            geo_str = 'MULTIPOLYGON'
        except (KeyError, TypeError):
            geo_str = None
            geo_coords = None

    try:
        text = tweet['extended_tweet']['full_text']
    except (KeyError, TypeError):
        text = tweet['text']

    try:
        country_code = tweet['place']['country_code'].lower()
    except (TypeError, AttributeError):
        country_code = None

    if country_code == 'us':
        state_code = tweet['place']['full_name'].split(',')[-1].strip().lower()
        if len(state_code) > 2:
            state_code = None
    else:
        state_code = None

    try:
        place_name = tweet['place']['full_name']
    except TypeError:
        place_name = None

    if tweet.get('in_reply_to_user_id') is not None:
        sql = sqlalchemy.text('''
            INSERT INTO users (id_users) VALUES (:id_users)
            ON CONFLICT DO NOTHING;
        ''')
        connection.execute(sql, {'id_users': tweet['in_reply_to_user_id']})

    sql = sqlalchemy.text(f'''
        INSERT INTO tweets
        (id_tweets, id_users, created_at, in_reply_to_status_id, in_reply_to_user_id, quoted_status_id, retweet_count, favorite_count, quote_count, withheld_copyright, withheld_in_countries, source, text, country_code, state_code, lang, place_name, geo)
        VALUES
        (:id_tweets, :id_users, :created_at, :in_reply_to_status_id, :in_reply_to_user_id, :quoted_status_id, :retweet_count, :favorite_count, :quote_count, :withheld_copyright, :withheld_in_countries, :source, :text, :country_code, :state_code, :lang, :place_name, ST_GeomFromText(:geo))
        ON CONFLICT DO NOTHING;
    ''')
    connection.execute(sql, {
        'id_tweets': tweet['id'],
        'id_users': tweet['user']['id'],
        'created_at': tweet['created_at'],
        'in_reply_to_status_id': tweet.get('in_reply_to_status_id'),
        'in_reply_to_user_id': tweet.get('in_reply_to_user_id'),
        'quoted_status_id': tweet.get('quoted_status_id'),
        'retweet_count': tweet.get('retweet_count'),
        'favorite_count': tweet.get('favorite_count'),
        'quote_count': tweet.get('quote_count'),
        'withheld_copyright': tweet.get('withheld_copyright'),
        'withheld_in_countries': tweet.get('withheld_in_countries'),
        'source': remove_nulls(tweet.get('source')),
        'text': remove_nulls(text),
        'country_code': country_code,
        'state_code': state_code,
        'lang': tweet.get('lang'),
        'place_name': remove_nulls(place_name),
        'geo': None if geo_str is None else f'{geo_str}({geo_coords})',
    })

    try:
        urls = tweet['extended_tweet']['entities']['urls']
    except (KeyError, TypeError):
        urls = tweet['entities']['urls']
    for url in urls:
        id_urls = get_id_urls(url['expanded_url'], connection)
        sql = sqlalchemy.text('''
            INSERT INTO tweet_urls (id_tweets, id_urls) VALUES (:id_tweets, :id_urls)
            ON CONFLICT DO NOTHING;
        ''')
        connection.execute(sql, {'id_tweets': tweet['id'], 'id_urls': id_urls})

    try:
        mentions = tweet['extended_tweet']['entities']['user_mentions']
    except (KeyError, TypeError):
        mentions = tweet['entities']['user_mentions']
    for mention in mentions:
        sql = sqlalchemy.text('''
            INSERT INTO users (id_users, screen_name, name) VALUES (:id_users, :screen_name, :name)
            ON CONFLICT DO NOTHING;
        ''')
        connection.execute(sql, {
            'id_users': mention['id'],
            'screen_name': remove_nulls(mention['screen_name']),
            'name': remove_nulls(mention['name']),
        })
        sql = sqlalchemy.text('''
            INSERT INTO tweet_mentions (id_tweets, id_users) VALUES (:id_tweets, :id_users)
            ON CONFLICT DO NOTHING;
        ''')
        connection.execute(sql, {'id_tweets': tweet['id'], 'id_users': mention['id']})

    try:
        hashtags = tweet['extended_tweet']['entities']['hashtags']
        cashtags = tweet['extended_tweet']['entities']['symbols']
    except (KeyError, TypeError):
        hashtags = tweet['entities']['hashtags']
        cashtags = tweet['entities']['symbols']
    tags = ['#' + h['text'] for h in hashtags] + ['$' + c['text'] for c in cashtags]
    for tag in tags:
        sql = sqlalchemy.text('''
            INSERT INTO tweet_tags (id_tweets, tag) VALUES (:id_tweets, :tag)
            ON CONFLICT DO NOTHING;
        ''')
        connection.execute(sql, {'id_tweets': tweet['id'], 'tag': remove_nulls(tag)})

    try:
        media = tweet['extended_tweet']['extended_entities']['media']
    except (KeyError, TypeError):
        try:
            media = tweet['extended_entities']['media']
        except (KeyError, TypeError):
            media = []
    for medium in media:
        id_urls = get_id_urls(medium['media_url'], connection)
        sql = sqlalchemy.text('''
            INSERT INTO tweet_media (id_tweets, id_urls, type) VALUES (:id_tweets, :id_urls, :type)
            ON CONFLICT DO NOTHING;
        ''')
        connection.execute(sql, {'id_tweets': tweet['id'], 'id_urls': id_urls, 'type': medium['type']})

    connection.commit()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', required=True)
    parser.add_argument('--inputs', nargs='+', required=True)
    parser.add_argument('--print_every', type=int, default=1000)
    args = parser.parse_args()

    engine = sqlalchemy.create_engine(args.db, connect_args={'application_name': 'load_tweets.py'})

    with engine.connect() as connection:
        for filename in sorted(args.inputs, reverse=True):
            with zipfile.ZipFile(filename, 'r') as archive:
                print(datetime.datetime.now(), filename)
                for subfilename in sorted(archive.namelist(), reverse=True):
                    with io.TextIOWrapper(archive.open(subfilename)) as f:
                        for i, line in enumerate(f):
                            tweet = json.loads(line)
                            insert_tweet(connection, tweet)
                            if i % args.print_every == 0:
                                print(datetime.datetime.now(), filename, subfilename, 'i=', i, 'id=', tweet['id'])
