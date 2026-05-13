# Twitter Clone

[![tests](https://github.com/Xiaofeng226/CSCI143_Final_Project/actions/workflows/tests.yml/badge.svg)](https://github.com/Xiaofeng226/CSCI143_Final_Project/actions/workflows/tests.yml)

## Overview

A CRUD web application inspired by Twitter, built using the Instagram tech stack.

## Tech Stack

- Python
- Flask
- PostgreSQL + PostGIS
- Docker
- Nginx
- Gunicorn

## Features

**Home** - Displays all tweets in the system, 20 per page with pagination.

**Login** - Cookie-based login system using Flask sessions.

**Logout** - Clears session to log the user out.

**Create User** - Register a new account. Password must be entered twice to confirm.

**Create Message** - Post a tweet. Requires the user to be logged in.

**Search** - Full-text search over all tweets using PostgreSQL GIN index and plainto_tsquery.

## How to Use

### Development

    docker compose up -d --build

### Production

    docker compose -f docker-compose.prod.yml up -d --build

### Load Tweet Data

    bash load_tweets_parallel.sh

### Load into Production

    bash load_tweets_parallel.sh postgresql://twitter:twitter@localhost:9877/twitter_prod

### Bring Down Containers

    docker compose down

To also delete data:

    docker compose down -v
