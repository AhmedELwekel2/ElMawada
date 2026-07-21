#!/usr/bin/env python3
import sqlite3
import os
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'quality_news.db')
if not os.path.exists(DB_PATH):
    print('DB not found:', DB_PATH)
    sys.exit(1)

search = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else 'Comeback of the Physical Store'
term = f"%{search.lower()}%"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT id, title, source_name, published_at, created_at, url FROM articles WHERE lower(title) LIKE ? AND lower(source_name) LIKE ?", (term, '%harvard%'))
rows = cur.fetchall()

if not rows:
    print('No matches found for:', search)
else:
    for r in rows:
        id_, title, source, published_at, created_at, url = r
        print('ID:', id_)
        print('Title:', title)
        print('Source:', source)
        print('Published_at:', published_at)
        print('Created_at:', created_at)
        print('URL:', url)
        print('---')

conn.close()
