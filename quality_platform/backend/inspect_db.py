#!/usr/bin/env python3
import sqlite3
import os
import datetime
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'quality_news.db')
if not os.path.exists(DB_PATH):
    print('DB not found:', DB_PATH)
    sys.exit(1)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT id, title, published_at, created_at FROM articles ORDER BY created_at DESC")
rows = cur.fetchall()
print('DB:', DB_PATH)
print('Total articles:', len(rows))

now = datetime.datetime.utcnow()

def parse_dt(dt):
    if dt is None:
        return None
    s = str(dt).strip()
    if not s:
        return None
    # Try ISO first
    try:
        return datetime.datetime.fromisoformat(s)
    except Exception:
        pass
    # Common sqlite formats
    for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.datetime.strptime(s, fmt)
        except Exception:
            pass
    # Fallback: replace space with T
    try:
        return datetime.datetime.fromisoformat(s.replace(' ', 'T'))
    except Exception:
        return None

last_day = now - datetime.timedelta(days=1)
last_week = now - datetime.timedelta(days=7)
last_month = now - datetime.timedelta(days=30)

counts = {'daily': 0, 'weekly': 0, 'monthly': 0}
samples = []

for r in rows:
    id_, title, published_at, created_at = r
    p_dt = parse_dt(published_at)
    c_dt = parse_dt(created_at)
    eff = p_dt if p_dt is not None else c_dt
    if eff is None:
        continue
    if eff >= last_day:
        counts['daily'] += 1
    if eff >= last_week:
        counts['weekly'] += 1
    if eff >= last_month:
        counts['monthly'] += 1
    if len(samples) < 20:
        samples.append((id_, title[:80], published_at, created_at, eff.isoformat()))

print('Counts (using published_at if present, else created_at):', counts)
print('\nSample rows (up to 20):')
for s in samples:
    print(s)

conn.close()
