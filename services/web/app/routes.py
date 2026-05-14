import psycopg2
import os
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

main = Blueprint("main", __name__)

def get_db():
    conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
    return conn

@main.route("/")
def home():
    page = request.args.get("page", 1, type=int)
    offset = (page - 1) * 20
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT users.screen_name, tweets.text, tweets.created_at
        FROM tweets
        JOIN users ON tweets.id_users = users.id_users
        ORDER BY tweets.created_at DESC
        LIMIT 20 OFFSET %s;
    """, (offset,))
    messages = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("home.html", messages=messages, page=page)

@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, password_hash FROM app_users WHERE username = %s;", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        if user and check_password_hash(user[1], password):
            session["user_id"] = user[0]
            session["username"] = username
            return redirect(url_for("main.home"))
        flash("Invalid credentials")
    return render_template("login.html")

@main.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.home"))

@main.route("/create_user", methods=["GET", "POST"])
def create_user():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm  = request.form["confirm"]
        if password != confirm:
            flash("Passwords do not match")
            return render_template("create_user.html")
        password_hash = generate_password_hash(password)
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO app_users (username, password_hash) VALUES (%s, %s);", (username, password_hash))
            conn.commit()
        except Exception:
            conn.rollback()
            flash("Username already exists")
            return render_template("create_user.html")
        cur.close()
        conn.close()
        return redirect(url_for("main.login"))
    return render_template("create_user.html")

@main.route("/create_message", methods=["GET", "POST"])
def create_message():
    if "user_id" not in session:
        return redirect(url_for("main.login"))
    if request.method == "POST":
        text = request.form["text"]
        conn = get_db()
        cur = conn.cursor()
        # ensure app user has a corresponding twitter user row
        cur.execute("""
            INSERT INTO users (id_users, screen_name)
            VALUES (%s, %s)
            ON CONFLICT (id_users) DO NOTHING;
        """, (session["user_id"], session["username"]))
        cur.execute("""
            INSERT INTO tweets (id_tweets, id_users, created_at, text)
            VALUES (
                (SELECT COALESCE(MAX(id_tweets), 0) + 1 FROM tweets),
                %s,
                NOW(),
                %s
            );
        """, (session["user_id"], text))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for("main.home"))
    return render_template("create_message.html")

@main.route("/search")
def search():
    query = request.args.get("q", "")
    page = request.args.get("page", 1, type=int)
    offset = (page - 1) * 20
    messages = []
    suggestion = None
    if query:
        conn = get_db()
        cur = conn.cursor()

        # main FTS search
        cur.execute("""
            SELECT
                users.screen_name,
                TS_HEADLINE(
                    'english',
                    tweets.text,
                    plainto_tsquery('english', %s),
                    'StartSel=<mark>, StopSel=</mark>, MaxFragments=2, MinWords=5, MaxWords=15'
                ),
                tweets.created_at
            FROM tweets
            JOIN users ON tweets.id_users = users.id_users
            WHERE to_tsvector('english', tweets.text) @@ plainto_tsquery('english', %s)
            ORDER BY TS_RANK(to_tsvector('english', tweets.text), plainto_tsquery('english', %s)) DESC,
                     tweets.created_at DESC
            LIMIT 20 OFFSET %s;
        """, (query, query, query, offset))
        messages = cur.fetchall()

        # spelling suggestion using pg_trgm if no results found
        if not messages:
            words = query.split()
            suggested_words = []
            for word in words:
                cur.execute("""
                    SELECT word
                    FROM ts_stat('SELECT to_tsvector(''simple'', text) FROM tweets')
                    WHERE word %% %s
                    ORDER BY similarity(word, %s) DESC
                    LIMIT 1;
                """, (word, word))
                result = cur.fetchone()
                if result and result[0].lower() != word.lower():
                    suggested_words.append(result[0].strip('.,!?'))
                else:
                    suggested_words.append(word)
            suggestion = ' '.join(suggested_words)
            if suggestion.lower() == query.lower():
                suggestion = None

        cur.close()
        conn.close()
    return render_template("search.html", messages=messages, query=query, page=page, suggestion=suggestion)
