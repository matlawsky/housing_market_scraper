"""Local ETL: archived JSON or bounded Selenium collection -> validated SQLite."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
import os
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parent
DB = Path(os.environ.get('HOUSING_DB', ROOT / 'data' / 'housing.sqlite3'))


def canonical_url(value):
    p = urlsplit(str(value))
    host = (p.hostname or '').lower().removeprefix('www.')
    if p.scheme not in ('http', 'https') or host not in ('olx.pl', 'otodom.pl'):
        raise ValueError('unsupported URL')
    return urlunsplit(('https', 'www.' + host, p.path.rstrip('/'), '', ''))


def number(value):
    if value is None or isinstance(value, bool):
        return None
    text = re.sub(r'\s+', '', str(value)).lower()
    text = re.sub(r'(zł|pln|m²|m2|pokoje|pokoi|pokój)$', '', text)
    if not re.fullmatch(r'\d+(?:[.,]\d+)?', text):
        return None
    try:
        result = Decimal(text.replace(',', '.'))
        return result if result.is_finite() and result > 0 else None
    except InvalidOperation:
        return None


def clean_text(value):
    text = str(value or '').strip()
    if not text or any(x in text.lower() for x in ('unknown', 'not found', 'no data', 'no id found')):
        return None
    return text


def normalize(url, raw):
    url = canonical_url(url)
    tags = str(raw.get('tags') or '')
    area_match = re.search(r'Powierzchnia\s*:?\s*([\d ,.\u00a0]+)\s*m[²2]', tags, re.I)
    rooms_match = re.search(r'Liczba pokoi\s*:?\s*(\d+)', tags, re.I)
    price = number(raw.get('price'))
    area = number(raw.get('area_m2')) if raw.get('area_m2') is not None else number(area_match[1] if area_match else None)
    rooms = number(raw.get('rooms')) if raw.get('rooms') is not None else number(rooms_match[1] if rooms_match else None)
    if rooms is not None and (rooms != int(rooms) or rooms > 50):
        rooms = None
    title, location = clean_text(raw.get('offer_title')), clean_text(raw.get('location'))
    active = {'yes': 1, 'true': 1, '1': 1, 'no': 0, 'false': 0, '0': 0}.get(str(raw.get('active')).lower())
    issues = []
    for key, value in [('price', price), ('area_m2', area), ('rooms', rooms), ('title', title), ('location', location)]:
        if value is None:
            issues.append('missing_or_invalid_' + key)
    if area is not None and area > 2000:
        issues.append('area_outlier')
    return dict(url=url, website=urlsplit(url).hostname.removeprefix('www.'),
                title=title, location=location,
                price_grosz=int((price * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP)) if price else None,
                area_m2=float(area) if area else None, rooms=int(rooms) if rooms else None,
                active=active, issues=json.dumps(issues),
                valid=int(price is not None and area is not None and area <= 2000))


def connect(db=DB):
    db = Path(db)
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS offers (
      url TEXT PRIMARY KEY, website TEXT NOT NULL, title TEXT, location TEXT,
      price_grosz INTEGER CHECK(price_grosz > 0), area_m2 REAL CHECK(area_m2 > 0),
      rooms INTEGER CHECK(rooms > 0), active INTEGER CHECK(active IN (0,1)),
      issues TEXT NOT NULL, valid INTEGER NOT NULL, source TEXT NOT NULL,
      observed_at TEXT NOT NULL, imported_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS runs (
      id INTEGER PRIMARY KEY, started_at TEXT, source TEXT, accepted INTEGER, rejected INTEGER, valid INTEGER);
    CREATE TABLE IF NOT EXISTS rejected (
      id INTEGER PRIMARY KEY, run_id INTEGER, url TEXT, reason TEXT);
    CREATE INDEX IF NOT EXISTS offers_source ON offers(source, valid);
    CREATE VIEW IF NOT EXISTS analysis_offers AS
      SELECT *, price_grosz/100.0 AS price_pln,
      price_grosz/100.0/area_m2 AS price_per_m2 FROM offers WHERE valid=1;
    ''')
    return conn


def ingest(records, source, observed_at, db=DB):
    # Explicit observation date: importing old data never turns it into today's market.
    observed = datetime.fromisoformat(observed_at)
    observed_at = observed.replace(tzinfo=observed.tzinfo or timezone.utc).astimezone(timezone.utc).isoformat()
    accepted = rejected = valid = 0
    now = datetime.now(timezone.utc).isoformat()
    with closing(connect(db)) as conn, conn:
        run_id = conn.execute('INSERT INTO runs(started_at, source) VALUES (?,?)', (now, source)).lastrowid
        for url, raw in records.items():
            try:
                if not isinstance(raw, dict):
                    raise ValueError('record must be an object')
                row = normalize(url, raw)
            except (ValueError, TypeError) as exc:
                rejected += 1
                conn.execute('INSERT INTO rejected(run_id,url,reason) VALUES (?,?,?)', (run_id, str(url), str(exc)))
                continue
            row.update(source=source, observed_at=observed_at, imported_at=now)
            columns = list(row)
            updates = ','.join(f'{k}=excluded.{k}' for k in columns if k != 'url')
            conn.execute(f"INSERT INTO offers ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)}) "
                         f'ON CONFLICT(url) DO UPDATE SET {updates} WHERE excluded.observed_at >= offers.observed_at', tuple(row.values()))
            accepted += 1
            valid += row['valid']
        conn.execute('UPDATE runs SET accepted=?,rejected=?,valid=? WHERE id=?', (accepted, rejected, valid, run_id))
    return dict(accepted=accepted, rejected=rejected, valid=valid)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db', type=Path, default=DB)
    sub = p.add_subparsers(dest='command', required=True)
    imp = sub.add_parser('import-json')
    imp.add_argument('path', type=Path)
    imp.add_argument('--observed-at', required=True, help='ISO date of original collection')
    live = sub.add_parser('scrape')
    live.add_argument('--search-url', required=True)
    live.add_argument('--max-pages', type=int, default=1)
    live.add_argument('--max-offers', type=int, default=5)
    args = p.parse_args()
    if args.command == 'import-json':
        records = json.loads(args.path.read_text(encoding='utf-8'))
        if not isinstance(records, dict):
            p.error('Expected JSON mapping URL -> record')
        source = 'archive:' + args.path.name
        observed_at = datetime.fromisoformat(args.observed_at).isoformat()
    else:
        if not 1 <= args.max_pages <= 50 or not 1 <= args.max_offers <= 500:
            p.error('Use 1–50 pages and 1–500 offers')
        from scrape_offers import collect
        records, errors = collect(args.search_url, args.max_pages, args.max_offers)
        observed_at = datetime.now(timezone.utc).isoformat()
        source = 'selenium'
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
        raw_path = ROOT / 'data' / 'raw' / f'{stamp}.json'
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(json.dumps(records, ensure_ascii=False), encoding='utf-8')
        raw_path.with_suffix('.errors.json').write_text(json.dumps(errors, ensure_ascii=False), encoding='utf-8')
        if not records:
            raise SystemExit('No offers collected; inspect selectors, consent or access restrictions. No database changes.')
    print(json.dumps(ingest(records, source, observed_at, args.db), ensure_ascii=False))


if __name__ == '__main__':
    main()