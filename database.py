# database.py
import os
import psycopg2
import psycopg2.pool
import psycopg2.extras
import json
import time
import random
import secrets
import logging
import threading
import asyncio
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Чтение переменных окружения
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://mmines_user:9a0OnVvuXujIlQHSHKc2NMRtPBefIGcH@dpg-d70j49i4d50c73euqnr0-a/mminesdb?sslmode=require')
_pool = None
_pool_lock = threading.Lock()

_REPLACE_CONFLICT = {
    'bot_chats': '(chat_id)',
    'keys': '(key_code)',
    'bans': '(user_id)',
    'spring_user_suns': '(user_id)',
    'spring_sun_collect': '(user_id)',
    'work_conditions': '(id)',
    'msg_rate': '(id)',
}

class DatabasePool:
    def __init__(self):
        self._pool = None
        self._lock = threading.Lock()
        self._reconnect_attempts = 0
    
    def get_pool(self):
        with self._lock:
            if self._pool is None:
                try:
                    self._pool = psycopg2.pool.ThreadedConnectionPool(
                        minconn=2,
                        maxconn=20,
                        dsn=DATABASE_URL,
                        keepalives=1,
                        keepalives_idle=30,
                        keepalives_interval=10,
                        keepalives_count=5,
                        connect_timeout=10
                    )
                    self._reconnect_attempts = 0
                    logging.info("Database connection pool created")
                except Exception as e:
                    logging.error(f"Failed to create connection pool: {e}")
                    if self._reconnect_attempts < 3:
                        self._reconnect_attempts += 1
                        time.sleep(5)
                        return self.get_pool()
                    raise
            return self._pool
    
    def close_all(self):
        if self._pool:
            self._pool.closeall()

_pool_manager = DatabasePool()

def get_pool():
    return _pool_manager.get_pool()

def _convert_query(query):
    query = query.replace('?', '%s')
    query = re.sub(r'INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY', query, flags=re.IGNORECASE)
    query = re.sub(r'BEGIN\s+IMMEDIATE\s+TRANSACTION', 'BEGIN', query, flags=re.IGNORECASE)
    query = re.sub(r'BEGIN\s+IMMEDIATE', 'BEGIN', query, flags=re.IGNORECASE)
    return query

def _convert_insert_or_ignore(query):
    query = re.sub(r'INSERT\s+OR\s+IGNORE', 'INSERT', query, flags=re.IGNORECASE)
    if 'ON CONFLICT' not in query.upper():
        query = query.rstrip().rstrip(';') + ' ON CONFLICT DO NOTHING'
    return query

def _convert_insert_or_replace(query, table_name):
    query = re.sub(r'INSERT\s+OR\s+REPLACE', 'INSERT', query, flags=re.IGNORECASE)
    conflict_col = _REPLACE_CONFLICT.get(table_name.lower(), '')
    if conflict_col and 'ON CONFLICT' not in query.upper():
        m = re.search(r'INSERT\s+INTO\s+\w+\s*\(([^)]+)\)', query, re.IGNORECASE)
        if m:
            cols = [c.strip() for c in m.group(1).split(',')]
            pk_col = conflict_col.strip('()')
            update_cols = [c for c in cols if c != pk_col]
            if update_cols:
                update_str = ', '.join(f'{c} = EXCLUDED.{c}' for c in update_cols)
                query = query.rstrip().rstrip(';') + f' ON CONFLICT {conflict_col} DO UPDATE SET {update_str}'
            else:
                query = query.rstrip().rstrip(';') + f' ON CONFLICT {conflict_col} DO NOTHING'
        else:
            query = query.rstrip().rstrip(';') + f' ON CONFLICT {conflict_col} DO NOTHING'
    return query

class _Row(dict):
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)
    def get(self, key, default=None):
        try:
            return self[key]
        except (KeyError, IndexError):
            return default

class _Cursor:
    def __init__(self, pg_cur):
        self._cur = pg_cur
        self._lastrowid = None
    def fetchone(self):
        row = self._cur.fetchone()
        if row is None:
            return None
        if isinstance(row, dict):
            return _Row(row)
        return row
    def fetchall(self):
        rows = self._cur.fetchall()
        result = []
        for row in rows:
            if isinstance(row, dict):
                result.append(_Row(row))
            else:
                result.append(row)
        return result
    def __iter__(self):
        for row in self._cur:
            if isinstance(row, dict):
                yield _Row(row)
            else:
                yield row
    @property
    def lastrowid(self):
        return self._lastrowid
    @property
    def rowcount(self):
        return self._cur.rowcount

class PGConn:
    def __init__(self, pg_conn):
        self._conn = pg_conn
        self._last_rowcount = 0
    def execute(self, query, params=()):
        stripped = query.strip()
        if stripped.upper() == 'ROLLBACK':
            self._conn.rollback()
            return _Cursor(self._conn.cursor())
        if stripped.upper() in ('COMMIT', 'END'):
            self._conn.commit()
            return _Cursor(self._conn.cursor())
        table_name = ''
        m = re.match(r'INSERT\s+OR\s+\w+\s+INTO\s+(\w+)', stripped, re.IGNORECASE)
        if m:
            table_name = m.group(1)
        is_ignore = bool(re.match(r'INSERT\s+OR\s+IGNORE', stripped, re.IGNORECASE))
        is_replace = bool(re.match(r'INSERT\s+OR\s+REPLACE', stripped, re.IGNORECASE))
        query = _convert_query(query)
        if is_ignore:
            query = _convert_insert_or_ignore(query)
        elif is_replace:
            query = _convert_insert_or_replace(query, table_name)
        query = re.sub(r'(=\s*)"([^"]*)"(\s*(?:AND|OR|WHERE|ORDER|LIMIT|$|\)))', r"\1'\2'\3", query)
        query = re.sub(r'(status\s*=\s*)"([^"]*)"', r"status = '\2'", query, flags=re.IGNORECASE)
        query = re.sub(r'(IN\s*\([^)]*)"([^"]*)"([^)]*\))', r"\1'\2'\3", query, flags=re.IGNORECASE)
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            cur.execute(query, params if params else None)
        except Exception as e:
            try:
                self._conn.rollback()
            except:
                pass
            raise e
        self._last_rowcount = cur.rowcount
        wrapper = _Cursor(cur)
        if stripped.upper().startswith('INSERT'):
            try:
                seq_cur = self._conn.cursor()
                seq_cur.execute("SELECT lastval()")
                row = seq_cur.fetchone()
                if row:
                    wrapper._lastrowid = row[0]
            except:
                pass
        return wrapper
    def commit(self):
        self._conn.commit()
    def rollback(self):
        self._conn.rollback()
    @property
    def total_changes(self):
        return self._last_rowcount

@contextmanager
def get_db():
    pool = get_pool()
    conn = pool.getconn()
    conn.autocommit = False
    pg_conn = PGConn(conn)
    try:
        yield pg_conn
    except Exception:
        try:
            conn.rollback()
        except:
            pass
        raise
    finally:
        pool.putconn(conn)

def table_exists(table_name):
    with get_db() as conn:
        result = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name=%s",
            (table_name,)
        ).fetchone()
        return result is not None

def parse_datetime(date_str):
    if not date_str:
        return None
    if isinstance(date_str, datetime):
        return date_str
    formats = [
        '%Y-%m-%d %H:%M:%S.%f',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M:%S.%f%z',
        '%Y-%m-%d %H:%M:%S%z'
    ]
    for fmt in formats:
        try:
            return datetime.strptime(str(date_str), fmt)
        except ValueError:
            continue
    logging.warning(f"Could not parse date: {date_str}")
    return None

# ==================== ОСНОВНЫЕ ФУНКЦИИ ====================
def execute_query(query, params=(), fetchone=False, fetchall=False):
    try:
        with get_db() as conn:
            cursor = conn.execute(query, params)
            if fetchone:
                return cursor.fetchone()
            if fetchall:
                return cursor.fetchall()
            conn.commit()
            return cursor.lastrowid
    except Exception as e:
        print(f"SQL Error: {e}")
        print(f"Query: {query}")
        print(f"Params: {params}")
        return None if (fetchone or fetchall) else 0

async def execute_query_async(query, params=(), fetchone=False, fetchall=False):
    return await asyncio.to_thread(execute_query, query, params, fetchone, fetchall)

def get_user(user_id, full_name=None, username=None):
    with get_db() as conn:
        user = conn.execute('SELECT * FROM users WHERE user_id = %s', (user_id,)).fetchone()
        if not user:
            conn.execute(
                'INSERT INTO users (user_id, username, full_name, balance, msg_balance, total_win, total_loss, games_played, referred_by, last_bonus) VALUES (%s, %s, %s, 1000, 0, 0, 0, 0, NULL, NULL)',
                (user_id, username, full_name)
            )
            conn.commit()
            return {
                'user_id': user_id,
                'username': username,
                'full_name': full_name,
                'balance': 1000,
                'msg_balance': 0,
                'total_win': 0,
                'total_loss': 0,
                'games_played': 0,
                'referred_by': None,
                'last_bonus': None
            }
        if full_name is not None or username is not None:
            updates, params = [], []
            if full_name is not None:
                updates.append("full_name = %s")
                params.append(full_name)
            if username is not None:
                updates.append("username = %s")
                params.append(username)
            if updates:
                query = f"UPDATE users SET {', '.join(updates)}, last_active = CURRENT_TIMESTAMP WHERE user_id = %s"
                params.append(user_id)
                conn.execute(query, params)
                conn.commit()
        return dict(user)

async def get_user_async(user_id, full_name=None, username=None):
    return await asyncio.to_thread(get_user, user_id, full_name, username)

def get_all_users():
    with get_db() as conn:
        return conn.execute('SELECT user_id FROM users').fetchall()

async def get_all_users_async():
    return await asyncio.to_thread(get_all_users)

def update_balance(user_id, amount):
    with get_db() as conn:
        if amount < 0:
            current = conn.execute('SELECT balance FROM users WHERE user_id = %s', (user_id,)).fetchone()
            if not current or current['balance'] + amount < 0:
                return False
        conn.execute('UPDATE users SET balance = balance + %s, last_active = CURRENT_TIMESTAMP WHERE user_id = %s', (amount, user_id))
        conn.commit()
        return True

async def update_balance_async(user_id, amount):
    return await asyncio.to_thread(update_balance, user_id, amount)

def update_balance_safe(user_id, amount, required_balance=None):
    with get_db() as conn:
        if required_balance is not None:
            if amount < 0:
                result = conn.execute('UPDATE users SET balance = balance + %s, last_active = CURRENT_TIMESTAMP WHERE user_id = %s AND balance >= %s', (amount, user_id, -amount))
            else:
                result = conn.execute('UPDATE users SET balance = balance + %s, last_active = CURRENT_TIMESTAMP WHERE user_id = %s AND balance >= %s', (amount, user_id, required_balance))
            affected = result.rowcount
            conn.commit()
            return affected > 0
        else:
            conn.execute('UPDATE users SET balance = balance + %s, last_active = CURRENT_TIMESTAMP WHERE user_id = %s', (amount, user_id))
            conn.commit()
            return True

async def update_balance_safe_async(user_id, amount, required_balance=None):
    return await asyncio.to_thread(update_balance_safe, user_id, amount, required_balance)

def transfer_money(from_id, to_id, amount):
    with get_db() as conn:
        try:
            conn.execute('BEGIN')
            from_user = conn.execute('SELECT balance FROM users WHERE user_id = %s', (from_id,)).fetchone()
            if not from_user:
                conn.rollback()
                return False, "Отправитель не найден"
            to_user = conn.execute('SELECT user_id FROM users WHERE user_id = %s', (to_id,)).fetchone()
            if not to_user:
                conn.rollback()
                return False, "Получатель не найден"
            if from_user['balance'] < amount:
                conn.rollback()
                return False, "Недостаточно средств"
            conn.execute('UPDATE users SET balance = balance - %s, last_active = CURRENT_TIMESTAMP WHERE user_id = %s', (amount, from_id))
            conn.execute('UPDATE users SET balance = balance + %s, last_active = CURRENT_TIMESTAMP WHERE user_id = %s', (amount, to_id))
            conn.commit()
            return True, "Перевод выполнен"
        except Exception as e:
            conn.rollback()
            return False, str(e)

async def transfer_money_async(from_id, to_id, amount):
    return await asyncio.to_thread(transfer_money, from_id, to_id, amount)

def update_user_stats(user_id, win_amount, loss_amount):
    with get_db() as conn:
        conn.execute('UPDATE users SET total_win = total_win + %s, total_loss = total_loss + %s, games_played = games_played + 1, last_active = CURRENT_TIMESTAMP WHERE user_id = %s', (win_amount, loss_amount, user_id))
        conn.commit()

async def update_user_stats_async(user_id, win_amount, loss_amount):
    return await asyncio.to_thread(update_user_stats, user_id, win_amount, loss_amount)

def get_user_stats(user_id):
    with get_db() as conn:
        result = conn.execute('SELECT total_win, total_loss, games_played FROM users WHERE user_id = %s', (user_id,)).fetchone()
        if result:
            return {'total_win': result['total_win'] or 0, 'total_loss': result['total_loss'] or 0, 'games_played': result['games_played'] or 0}
        return {'total_win': 0, 'total_loss': 0, 'games_played': 0}

async def get_user_stats_async(user_id):
    return await asyncio.to_thread(get_user_stats, user_id)

def get_top_users(limit=10):
    with get_db() as conn:
        return conn.execute("SELECT user_id, COALESCE(full_name, username, 'Пользователь') as name, balance FROM users ORDER BY balance DESC LIMIT %s", (limit,)).fetchall()

async def get_top_users_async(limit=10):
    return await asyncio.to_thread(get_top_users, limit)

def get_user_rank(user_id):
    with get_db() as conn:
        result = conn.execute('SELECT COUNT(*) + 1 FROM users WHERE balance > (SELECT balance FROM users WHERE user_id = %s)', (user_id,)).fetchone()
        return result[0] if result else 1

async def get_user_rank_async(user_id):
    return await asyncio.to_thread(get_user_rank, user_id)

def save_game_hash(game_hash, user_id, game_type, bet, result):
    with get_db() as conn:
        conn.execute('INSERT INTO games_history (game_hash, user_id, game_type, bet, result) VALUES (%s, %s, %s, %s, %s)', (game_hash, user_id, game_type, bet, result))
        conn.commit()

async def save_game_hash_async(game_hash, user_id, game_type, bet, result):
    return await asyncio.to_thread(save_game_hash, game_hash, user_id, game_type, bet, result)

def get_game_hash(game_hash):
    with get_db() as conn:
        result = conn.execute('SELECT game_hash, user_id, game_type, bet, result FROM games_history WHERE game_hash = %s', (game_hash,)).fetchone()
        if result:
            return {'game_hash': result['game_hash'], 'user_id': result['user_id'], 'game_type': result['game_type'], 'bet': result['bet'], 'result': result['result']}
        return None

async def get_game_hash_async(game_hash):
    return await asyncio.to_thread(get_game_hash, game_hash)

def ban_user(user_id, days, reason):
    banned_until = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S.%f') if days > 0 else None
    with get_db() as conn:
        conn.execute('INSERT INTO bans (user_id, banned_until, ban_days, ban_reason) VALUES (%s, %s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET banned_until = EXCLUDED.banned_until, ban_days = EXCLUDED.ban_days, ban_reason = EXCLUDED.ban_reason, banned_at = CURRENT_TIMESTAMP', (user_id, banned_until, days, reason))
        conn.commit()

async def ban_user_async(user_id, days, reason):
    return await asyncio.to_thread(ban_user, user_id, days, reason)

def unban_user(user_id):
    with get_db() as conn:
        conn.execute('DELETE FROM bans WHERE user_id = %s', (user_id,))
        conn.commit()
    return True

async def unban_user_async(user_id):
    return await asyncio.to_thread(unban_user, user_id)

def is_user_banned(user_id):
    with get_db() as conn:
        ban = conn.execute('SELECT banned_until, ban_days, ban_reason FROM bans WHERE user_id = %s', (user_id,)).fetchone()
        return {'banned_until': ban['banned_until'], 'ban_days': ban['ban_days'], 'ban_reason': ban['ban_reason']} if ban else None

async def is_user_banned_async(user_id):
    return await asyncio.to_thread(is_user_banned, user_id)

def add_referral(referrer_id, referral_id):
    with get_db() as conn:
        conn.execute('INSERT INTO referrals (referrer_id, referral_id) VALUES (%s, %s) ON CONFLICT DO NOTHING', (referrer_id, referral_id))
        conn.execute('UPDATE users SET referred_by = %s WHERE user_id = %s', (referrer_id, referral_id))
        conn.commit()

async def add_referral_async(referrer_id, referral_id):
    return await asyncio.to_thread(add_referral, referrer_id, referral_id)

def get_referrer_id(referral_id):
    with get_db() as conn:
        result = conn.execute('SELECT referred_by FROM users WHERE user_id = %s', (referral_id,)).fetchone()
        return result['referred_by'] if result else None

async def get_referrer_id_async(referral_id):
    return await asyncio.to_thread(get_referrer_id, referral_id)

def get_user_referral_count(user_id):
    with get_db() as conn:
        result = conn.execute('SELECT COUNT(*) as cnt FROM referrals WHERE referrer_id = %s', (user_id,)).fetchone()
        return result['cnt'] if result else 0

async def get_user_referral_count_async(user_id):
    return await asyncio.to_thread(get_user_referral_count, user_id)

def get_top_referrers(limit=10):
    with get_db() as conn:
        return conn.execute('SELECT u.user_id, COALESCE(u.full_name, u.username, \'Пользователь\') as name, COUNT(r.id) as ref_count FROM users u LEFT JOIN referrals r ON u.user_id = r.referrer_id GROUP BY u.user_id ORDER BY ref_count DESC LIMIT %s', (limit,)).fetchall()

async def get_top_referrers_async(limit=10):
    return await asyncio.to_thread(get_top_referrers, limit)

def get_referral_rank(user_id):
    with get_db() as conn:
        result = conn.execute('SELECT COUNT(*) + 1 as cnt FROM (SELECT u.user_id, COUNT(r.id) as ref_count FROM users u LEFT JOIN referrals r ON u.user_id = r.referrer_id GROUP BY u.user_id HAVING COUNT(r.id) > (SELECT COUNT(*) FROM referrals WHERE referrer_id = %s)) sub', (user_id,)).fetchone()
        return result['cnt'] if result else 1

async def get_referral_rank_async(user_id):
    return await asyncio.to_thread(get_referral_rank, user_id)

def can_claim_bonus(user_id, cooldown_seconds):
    with get_db() as conn:
        result = conn.execute('SELECT last_bonus FROM users WHERE user_id = %s', (user_id,)).fetchone()
        if not result or result['last_bonus'] is None:
            return True, 0, 0
        last_bonus = parse_datetime(result['last_bonus'])
        if not last_bonus:
            return True, 0, 0
        now = datetime.now()
        time_passed = (now - last_bonus).total_seconds()
        if time_passed >= cooldown_seconds:
            return True, 0, 0
        remaining = cooldown_seconds - time_passed
        return False, int(remaining // 60), int(remaining % 60)

async def can_claim_bonus_async(user_id, cooldown_seconds):
    return await asyncio.to_thread(can_claim_bonus, user_id, cooldown_seconds)

def claim_bonus(user_id, amount):
    with get_db() as conn:
        result = conn.execute('SELECT last_bonus FROM users WHERE user_id = %s', (user_id,)).fetchone()
        current_time = datetime.now()
        if result and result['last_bonus'] is not None:
            last_bonus = parse_datetime(result['last_bonus'])
            if last_bonus and (current_time - last_bonus).total_seconds() < 1800:
                return False
        conn.execute('UPDATE users SET last_bonus = %s WHERE user_id = %s', (current_time.strftime('%Y-%m-%d %H:%M:%S'), user_id))
        conn.commit()
        return True

async def claim_bonus_async(user_id, amount):
    return await asyncio.to_thread(claim_bonus, user_id, amount)

def get_user_by_username(username):
    with get_db() as conn:
        result = conn.execute('SELECT user_id, full_name FROM users WHERE username = %s', (username,)).fetchone()
        return result if result else None

async def get_user_by_username_async(username):
    return await asyncio.to_thread(get_user_by_username, username)

# ==================== ЧЕКИ ====================
def create_check(check_code, max_activations, amount):
    with get_db() as conn:
        conn.execute('INSERT INTO checks (check_code, max_activations, amount) VALUES (%s, %s, %s)', (check_code, max_activations, amount))
        conn.commit()

async def create_check_async(check_code, max_activations, amount):
    return await asyncio.to_thread(create_check, check_code, max_activations, amount)

def get_check(check_code):
    with get_db() as conn:
        result = conn.execute('SELECT * FROM checks WHERE check_code = %s', (check_code,)).fetchone()
        return dict(result) if result else None

async def get_check_async(check_code):
    return await asyncio.to_thread(get_check, check_code)

def use_check(check_code, user_id):
    with get_db() as conn:
        check = conn.execute('SELECT * FROM checks WHERE check_code = %s', (check_code,)).fetchone()
        if not check or check['used_count'] >= check['max_activations']:
            return False
        claimed_by = check['claimed_by'] or ''
        claimed_list = [uid.strip() for uid in claimed_by.split(',') if uid.strip()]
        if str(user_id) in claimed_list:
            return False
        claimed_list.append(str(user_id))
        conn.execute('UPDATE checks SET used_count = used_count + 1, claimed_by = %s WHERE check_code = %s', (','.join(claimed_list), check_code))
        conn.commit()
        return True

async def use_check_async(check_code, user_id):
    return await asyncio.to_thread(use_check, check_code, user_id)

def get_all_checks():
    with get_db() as conn:
        return conn.execute('SELECT * FROM checks ORDER BY created_at DESC').fetchall()

async def get_all_checks_async():
    return await asyncio.to_thread(get_all_checks)

def delete_check(check_code):
    with get_db() as conn:
        conn.execute('DELETE FROM checks WHERE check_code = %s', (check_code,))
        conn.commit()

async def delete_check_async(check_code):
    return await asyncio.to_thread(delete_check, check_code)

# ==================== АКЦИИ ====================
def init_investments_db():
    with get_db() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS stocks (stock_id SERIAL PRIMARY KEY, name TEXT NOT NULL, symbol TEXT NOT NULL UNIQUE, current_price BIGINT DEFAULT 0, previous_price BIGINT DEFAULT 0, last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
        conn.execute('CREATE TABLE IF NOT EXISTS user_portfolio (id SERIAL PRIMARY KEY, user_id BIGINT NOT NULL, stock_id INTEGER NOT NULL, quantity INTEGER NOT NULL DEFAULT 0, purchase_price BIGINT NOT NULL, purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE, FOREIGN KEY (stock_id) REFERENCES stocks(stock_id) ON DELETE CASCADE, UNIQUE(user_id, stock_id))')
        try:
            conn.execute('CREATE INDEX IF NOT EXISTS idx_portfolio_user ON user_portfolio(user_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_portfolio_stock ON user_portfolio(stock_id)')
        except:
            conn.rollback()
        for name, symbol, price in [("Bitcoin", "BTC", 100), ("MonsterC", "MSC", 100), ("Telegram", "TG", 100)]:
            conn.execute('INSERT INTO stocks (name, symbol, current_price, previous_price) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING', (name, symbol, price, price))
        conn.commit()

def get_all_stocks():
    with get_db() as conn:
        return conn.execute('SELECT * FROM stocks ORDER BY stock_id').fetchall()

async def get_all_stocks_async():
    return await asyncio.to_thread(get_all_stocks)

def get_stock(stock_id):
    with get_db() as conn:
        result = conn.execute('SELECT * FROM stocks WHERE stock_id = %s', (stock_id,)).fetchone()
        return dict(result) if result else None

async def get_stock_async(stock_id):
    return await asyncio.to_thread(get_stock, stock_id)

def get_stock_by_symbol(symbol):
    with get_db() as conn:
        result = conn.execute('SELECT * FROM stocks WHERE symbol = %s', (symbol,)).fetchone()
        return dict(result) if result else None

async def get_stock_by_symbol_async(symbol):
    return await asyncio.to_thread(get_stock_by_symbol, symbol)

def update_stock_price(stock_id, new_price):
    with get_db() as conn:
        current = conn.execute('SELECT current_price FROM stocks WHERE stock_id = %s', (stock_id,)).fetchone()
        if current:
            conn.execute('UPDATE stocks SET current_price = %s, previous_price = %s, last_update = CURRENT_TIMESTAMP WHERE stock_id = %s', (new_price, current['current_price'], stock_id))
            conn.commit()
            return True
        return False

async def update_stock_price_async(stock_id, new_price):
    return await asyncio.to_thread(update_stock_price, stock_id, new_price)

def update_all_stocks_prices(stock_updates):
    with get_db() as conn:
        try:
            for stock_id, new_price in stock_updates:
                current = conn.execute('SELECT current_price FROM stocks WHERE stock_id = %s', (stock_id,)).fetchone()
                if current:
                    conn.execute('UPDATE stocks SET current_price = %s, previous_price = %s, last_update = CURRENT_TIMESTAMP WHERE stock_id = %s', (new_price, current['current_price'], stock_id))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            return False

async def update_all_stocks_prices_async(stock_updates):
    return await asyncio.to_thread(update_all_stocks_prices, stock_updates)

def get_user_portfolio(user_id):
    with get_db() as conn:
        return conn.execute('SELECT up.*, s.name, s.symbol, s.current_price, (up.quantity * s.current_price) as total_value FROM user_portfolio up JOIN stocks s ON up.stock_id = s.stock_id WHERE up.user_id = %s AND up.quantity > 0 ORDER BY s.symbol', (user_id,)).fetchall()

async def get_user_portfolio_async(user_id):
    return await asyncio.to_thread(get_user_portfolio, user_id)

def get_user_portfolio_total(user_id):
    with get_db() as conn:
        result = conn.execute('SELECT COALESCE(SUM(up.quantity * s.current_price), 0) as total FROM user_portfolio up JOIN stocks s ON up.stock_id = s.stock_id WHERE up.user_id = %s', (user_id,)).fetchone()
        return result['total'] if result else 0

async def get_user_portfolio_total_async(user_id):
    return await asyncio.to_thread(get_user_portfolio_total, user_id)

def get_user_portfolio_count(user_id):
    with get_db() as conn:
        result = conn.execute('SELECT COALESCE(SUM(quantity), 0) as total FROM user_portfolio WHERE user_id = %s', (user_id,)).fetchone()
        return result['total'] if result else 0

async def get_user_portfolio_count_async(user_id):
    return await asyncio.to_thread(get_user_portfolio_count, user_id)

def buy_stock(user_id, stock_id, quantity):
    with get_db() as conn:
        try:
            stock = conn.execute('SELECT * FROM stocks WHERE stock_id = %s AND current_price > 0', (stock_id,)).fetchone()
            if not stock:
                conn.rollback()
                return False, "Акция недоступна для покупки"
            total_cost = stock['current_price'] * quantity
            user = conn.execute('SELECT balance FROM users WHERE user_id = %s', (user_id,)).fetchone()
            if not user or user['balance'] < total_cost:
                conn.rollback()
                return False, "Недостаточно средств"
            existing = conn.execute('SELECT * FROM user_portfolio WHERE user_id = %s AND stock_id = %s', (user_id, stock_id)).fetchone()
            if existing:
                conn.execute('UPDATE user_portfolio SET quantity = quantity + %s, purchase_price = %s, purchase_date = CURRENT_TIMESTAMP WHERE user_id = %s AND stock_id = %s', (quantity, stock['current_price'], user_id, stock_id))
            else:
                conn.execute('INSERT INTO user_portfolio (user_id, stock_id, quantity, purchase_price) VALUES (%s, %s, %s, %s)', (user_id, stock_id, quantity, stock['current_price']))
            conn.execute('UPDATE users SET balance = balance - %s, last_active = CURRENT_TIMESTAMP WHERE user_id = %s', (total_cost, user_id))
            conn.commit()
            return True, total_cost
        except Exception as e:
            conn.rollback()
            return False, str(e)

async def buy_stock_async(user_id, stock_id, quantity):
    return await asyncio.to_thread(buy_stock, user_id, stock_id, quantity)

def sell_stock(user_id, stock_id, quantity):
    with get_db() as conn:
        try:
            portfolio = conn.execute('SELECT up.quantity, s.current_price FROM user_portfolio up JOIN stocks s ON up.stock_id = s.stock_id WHERE up.user_id = %s AND up.stock_id = %s AND up.quantity >= %s', (user_id, stock_id, quantity)).fetchone()
            if not portfolio:
                conn.rollback()
                return False, "Недостаточно акций"
            total_income = portfolio['current_price'] * quantity
            new_quantity = portfolio['quantity'] - quantity
            if new_quantity == 0:
                conn.execute('DELETE FROM user_portfolio WHERE user_id = %s AND stock_id = %s', (user_id, stock_id))
            else:
                conn.execute('UPDATE user_portfolio SET quantity = %s WHERE user_id = %s AND stock_id = %s', (new_quantity, user_id, stock_id))
            conn.execute('UPDATE users SET balance = balance + %s, last_active = CURRENT_TIMESTAMP WHERE user_id = %s', (total_income, user_id))
            conn.commit()
            return True, total_income
        except Exception as e:
            conn.rollback()
            return False, str(e)

async def sell_stock_async(user_id, stock_id, quantity):
    return await asyncio.to_thread(sell_stock, user_id, stock_id, quantity)

def get_user_stock_quantity(user_id, stock_id):
    with get_db() as conn:
        result = conn.execute('SELECT quantity FROM user_portfolio WHERE user_id = %s AND stock_id = %s', (user_id, stock_id)).fetchone()
        return result['quantity'] if result else 0

async def get_user_stock_quantity_async(user_id, stock_id):
    return await asyncio.to_thread(get_user_stock_quantity, user_id, stock_id)

def clear_all_portfolios():
    with get_db() as conn:
        conn.execute("DELETE FROM user_portfolio")
        conn.commit()
        return True

async def clear_all_portfolios_async():
    return await asyncio.to_thread(clear_all_portfolios)

# ==================== ИВЕНТЫ ====================
def init_events_db():
    with get_db() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS events (event_id SERIAL PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL, date TEXT, status TEXT DEFAULT \'scheduled\', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
        conn.commit()

def create_event(name, description, date=None, status='scheduled'):
    with get_db() as conn:
        cursor = conn.execute('INSERT INTO events (name, description, date, status) VALUES (%s, %s, %s, %s) RETURNING event_id', (name, description, date, status))
        conn.commit()
        row = cursor.fetchone()
        return row['event_id'] if row else None

async def create_event_async(name, description, date=None, status='scheduled'):
    return await asyncio.to_thread(create_event, name, description, date, status)

def get_all_events():
    with get_db() as conn:
        return conn.execute('SELECT * FROM events ORDER BY CASE status WHEN \'active\' THEN 1 WHEN \'scheduled\' THEN 2 WHEN \'closed\' THEN 3 END, date DESC').fetchall()

async def get_all_events_async():
    return await asyncio.to_thread(get_all_events)

def get_event(event_id):
    with get_db() as conn:
        result = conn.execute('SELECT * FROM events WHERE event_id = %s', (event_id,)).fetchone()
        return dict(result) if result else None

async def get_event_async(event_id):
    return await asyncio.to_thread(get_event, event_id)

def update_event_status(event_id, status):
    with get_db() as conn:
        conn.execute('UPDATE events SET status = %s WHERE event_id = %s', (status, event_id))
        conn.commit()
        return True

async def update_event_status_async(event_id, status):
    return await asyncio.to_thread(update_event_status, event_id, status)

def delete_event(event_id):
    with get_db() as conn:
        conn.execute('DELETE FROM events WHERE event_id = %s', (event_id,))
        conn.commit()
        return True

async def delete_event_async(event_id):
    return await asyncio.to_thread(delete_event, event_id)

# ==================== СЛОТ ====================
def can_claim_slot(user_id, cooldown_seconds):
    with get_db() as conn:
        result = conn.execute('SELECT last_slot FROM users WHERE user_id = %s', (user_id,)).fetchone()
        if not result or result['last_slot'] is None:
            return True, 0, 0
        last_slot = parse_datetime(result['last_slot'])
        if not last_slot:
            return True, 0, 0
        now = datetime.now()
        time_passed = (now - last_slot).total_seconds()
        if time_passed >= cooldown_seconds:
            return True, 0, 0
        remaining = cooldown_seconds - time_passed
        return False, int(remaining // 60), int(remaining % 60)

async def can_claim_slot_async(user_id, cooldown_seconds):
    return await asyncio.to_thread(can_claim_slot, user_id, cooldown_seconds)

def claim_slot(user_id):
    with get_db() as conn:
        conn.execute('UPDATE users SET last_slot = %s WHERE user_id = %s', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id))
        conn.commit()
        return True

async def claim_slot_async(user_id):
    return await asyncio.to_thread(claim_slot, user_id)

# ==================== SPRING EVENT ====================
def init_spring_event_db():
    with get_db() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS spring_questions (id SERIAL PRIMARY KEY, question TEXT NOT NULL, answer TEXT NOT NULL, prize_type TEXT NOT NULL, prize_value TEXT NOT NULL, solved_by BIGINT DEFAULT NULL, solved_at TIMESTAMP DEFAULT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (solved_by) REFERENCES users(user_id) ON DELETE SET NULL)')
        conn.execute('CREATE TABLE IF NOT EXISTS spring_sun_collect (user_id BIGINT PRIMARY KEY, last_collect TIMESTAMP DEFAULT NULL, FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE)')
        conn.execute('CREATE TABLE IF NOT EXISTS spring_tasks (id SERIAL PRIMARY KEY, description TEXT NOT NULL, target_count INTEGER NOT NULL, prize_min INTEGER NOT NULL, prize_max INTEGER NOT NULL, sun_min INTEGER NOT NULL, sun_max INTEGER NOT NULL, game_type TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
        conn.execute('CREATE TABLE IF NOT EXISTS spring_user_tasks (id SERIAL PRIMARY KEY, user_id BIGINT NOT NULL, task_id INTEGER NOT NULL, progress INTEGER DEFAULT 0, completed INTEGER DEFAULT 0, completed_at TIMESTAMP DEFAULT NULL, claimed INTEGER DEFAULT 0, FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE, FOREIGN KEY (task_id) REFERENCES spring_tasks(id) ON DELETE CASCADE, UNIQUE(user_id, task_id))')
        conn.execute('CREATE TABLE IF NOT EXISTS spring_user_suns (user_id BIGINT PRIMARY KEY, sun_count INTEGER DEFAULT 0, FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE)')
        try:
            conn.execute('CREATE INDEX IF NOT EXISTS idx_spring_questions_solved ON spring_questions(solved_by)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_spring_user_tasks_user ON spring_user_tasks(user_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_spring_user_tasks_task ON spring_user_tasks(task_id)')
        except:
            conn.rollback()
        conn.commit()

def create_spring_question(question, answer, prize_type, prize_value):
    with get_db() as conn:
        cursor = conn.execute('INSERT INTO spring_questions (question, answer, prize_type, prize_value) VALUES (%s, %s, %s, %s) RETURNING id', (question, answer, prize_type, prize_value))
        conn.commit()
        row = cursor.fetchone()
        return row['id'] if row else None

async def create_spring_question_async(question, answer, prize_type, prize_value):
    return await asyncio.to_thread(create_spring_question, question, answer, prize_type, prize_value)

def get_all_spring_questions():
    with get_db() as conn:
        return conn.execute('SELECT * FROM spring_questions WHERE solved_by IS NULL ORDER BY created_at DESC').fetchall()

async def get_all_spring_questions_async():
    return await asyncio.to_thread(get_all_spring_questions)

def get_spring_question(question_id):
    with get_db() as conn:
        result = conn.execute('SELECT * FROM spring_questions WHERE id = %s', (question_id,)).fetchone()
        return dict(result) if result else None

async def get_spring_question_async(question_id):
    return await asyncio.to_thread(get_spring_question, question_id)

def solve_spring_question(question_id, user_id):
    with get_db() as conn:
        question = conn.execute('SELECT solved_by FROM spring_questions WHERE id = %s', (question_id,)).fetchone()
        if not question or question['solved_by'] is not None:
            return False
        result = conn.execute('UPDATE spring_questions SET solved_by = %s, solved_at = %s WHERE id = %s AND solved_by IS NULL', (user_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), question_id))
        conn.commit()
        return result.rowcount > 0

async def solve_spring_question_async(question_id, user_id):
    return await asyncio.to_thread(solve_spring_question, question_id, user_id)

def get_user_suns(user_id):
    with get_db() as conn:
        result = conn.execute('SELECT sun_count FROM spring_user_suns WHERE user_id = %s', (user_id,)).fetchone()
        if result:
            return result['sun_count']
        conn.execute('INSERT INTO spring_user_suns (user_id, sun_count) VALUES (%s, 0) ON CONFLICT DO NOTHING', (user_id,))
        conn.commit()
        return 0

async def get_user_suns_async(user_id):
    return await asyncio.to_thread(get_user_suns, user_id)

def add_user_suns(user_id, amount):
    with get_db() as conn:
        conn.execute('INSERT INTO spring_user_suns (user_id, sun_count) VALUES (%s, %s) ON CONFLICT(user_id) DO UPDATE SET sun_count = spring_user_suns.sun_count + %s', (user_id, amount, amount))
        conn.commit()
        return True

async def add_user_suns_async(user_id, amount):
    return await asyncio.to_thread(add_user_suns, user_id, amount)

def can_collect_sun(user_id, cooldown_seconds=5400):
    with get_db() as conn:
        result = conn.execute('SELECT last_collect FROM spring_sun_collect WHERE user_id = %s', (user_id,)).fetchone()
        if not result or result['last_collect'] is None:
            return True, 0, 0
        last_collect = parse_datetime(result['last_collect'])
        if not last_collect:
            return True, 0, 0
        now = datetime.now()
        time_passed = (now - last_collect).total_seconds()
        if time_passed >= cooldown_seconds:
            return True, 0, 0
        remaining = cooldown_seconds - time_passed
        return False, int(remaining // 60), int(remaining % 60)

async def can_collect_sun_async(user_id, cooldown_seconds=5400):
    return await asyncio.to_thread(can_collect_sun, user_id, cooldown_seconds)

def collect_sun(user_id):
    with get_db() as conn:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute('INSERT INTO spring_sun_collect (user_id, last_collect) VALUES (%s, %s) ON CONFLICT(user_id) DO UPDATE SET last_collect = %s', (user_id, now, now))
        conn.commit()
        return True

async def collect_sun_async(user_id):
    return await asyncio.to_thread(collect_sun, user_id)

def create_spring_task(description, target_count, prize_min, prize_max, sun_min, sun_max, game_type=None):
    with get_db() as conn:
        cursor = conn.execute('INSERT INTO spring_tasks (description, target_count, prize_min, prize_max, sun_min, sun_max, game_type) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id', (description, target_count, prize_min, prize_max, sun_min, sun_max, game_type))
        conn.commit()
        row = cursor.fetchone()
        return row['id'] if row else None

async def create_spring_task_async(description, target_count, prize_min, prize_max, sun_min, sun_max, game_type=None):
    return await asyncio.to_thread(create_spring_task, description, target_count, prize_min, prize_max, sun_min, sun_max, game_type)

def get_all_spring_tasks():
    with get_db() as conn:
        return [dict(row) for row in conn.execute('SELECT * FROM spring_tasks ORDER BY id').fetchall()]

async def get_all_spring_tasks_async():
    return await asyncio.to_thread(get_all_spring_tasks)

def get_spring_task(task_id):
    with get_db() as conn:
        result = conn.execute('SELECT * FROM spring_tasks WHERE id = %s', (task_id,)).fetchone()
        return dict(result) if result else None

async def get_spring_task_async(task_id):
    return await asyncio.to_thread(get_spring_task, task_id)

def get_user_task_progress(user_id, task_id):
    with get_db() as conn:
        result = conn.execute('SELECT progress, completed, claimed FROM spring_user_tasks WHERE user_id = %s AND task_id = %s', (user_id, task_id)).fetchone()
        return {'progress': result['progress'], 'completed': result['completed'], 'claimed': result['claimed']} if result else {'progress': 0, 'completed': 0, 'claimed': 0}

async def get_user_task_progress_async(user_id, task_id):
    return await asyncio.to_thread(get_user_task_progress, user_id, task_id)

def update_user_task_progress(user_id, task_id, increment=1):
    with get_db() as conn:
        task = conn.execute('SELECT target_count FROM spring_tasks WHERE id = %s', (task_id,)).fetchone()
        if not task:
            return False
        target = task['target_count']
        existing = conn.execute('SELECT progress, completed FROM spring_user_tasks WHERE user_id = %s AND task_id = %s', (user_id, task_id)).fetchone()
        if existing and existing['completed'] == 1:
            return False
        if existing:
            new_progress = min(existing['progress'] + increment, target)
            completed = 1 if new_progress >= target else 0
            conn.execute('UPDATE spring_user_tasks SET progress = %s, completed = %s WHERE user_id = %s AND task_id = %s', (new_progress, completed, user_id, task_id))
        else:
            new_progress = min(increment, target)
            completed = 1 if new_progress >= target else 0
            conn.execute('INSERT INTO spring_user_tasks (user_id, task_id, progress, completed) VALUES (%s, %s, %s, %s)', (user_id, task_id, new_progress, completed))
        conn.commit()
        return new_progress >= target

async def update_user_task_progress_async(user_id, task_id, increment=1):
    return await asyncio.to_thread(update_user_task_progress, user_id, task_id, increment)

def claim_task_reward(user_id, task_id):
    with get_db() as conn:
        user_task = conn.execute('SELECT ut.completed, ut.claimed, t.prize_min, t.prize_max, t.sun_min, t.sun_max FROM spring_user_tasks ut JOIN spring_tasks t ON ut.task_id = t.id WHERE ut.user_id = %s AND ut.task_id = %s', (user_id, task_id)).fetchone()
        if not user_task or user_task['completed'] != 1 or user_task['claimed'] == 1:
            return False, 0, 0
        prize = random.randint(user_task['prize_min'], user_task['prize_max'])
        suns = random.randint(user_task['sun_min'], user_task['sun_max'])
        conn.execute('UPDATE spring_user_tasks SET claimed = 1 WHERE user_id = %s AND task_id = %s', (user_id, task_id))
        conn.commit()
        return True, prize, suns

async def claim_task_reward_async(user_id, task_id):
    return await asyncio.to_thread(claim_task_reward, user_id, task_id)

def get_all_user_tasks(user_id):
    with get_db() as conn:
        results = conn.execute('SELECT t.*, COALESCE(ut.progress, 0) as progress, COALESCE(ut.completed, 0) as completed, COALESCE(ut.claimed, 0) as claimed FROM spring_tasks t LEFT JOIN spring_user_tasks ut ON t.id = ut.task_id AND ut.user_id = %s ORDER BY t.id', (user_id,)).fetchall()
        return [dict(row) for row in results]

async def get_all_user_tasks_async(user_id):
    return await asyncio.to_thread(get_all_user_tasks, user_id)

# ==================== MATH CONTEST ====================
def init_math_contest_db():
    with get_db() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS math_contests (id SERIAL PRIMARY KEY, prize_amount BIGINT NOT NULL, question TEXT NOT NULL, correct_answer REAL NOT NULL, options TEXT NOT NULL, winner_id BIGINT DEFAULT NULL, winner_name TEXT DEFAULT NULL, status TEXT DEFAULT \'pending\', created_by BIGINT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, started_at TIMESTAMP DEFAULT NULL, finished_at TIMESTAMP DEFAULT NULL, message_id BIGINT, chat_id BIGINT, FOREIGN KEY (winner_id) REFERENCES users(user_id) ON DELETE SET NULL)')
        conn.execute('CREATE TABLE IF NOT EXISTS math_contest_attempts (id SERIAL PRIMARY KEY, contest_id INTEGER NOT NULL, user_id BIGINT NOT NULL, selected_option INTEGER, correct INTEGER DEFAULT 0, attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (contest_id) REFERENCES math_contests(id) ON DELETE CASCADE, FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE)')
        try:
            conn.execute('CREATE INDEX IF NOT EXISTS idx_math_contests_status ON math_contests(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_math_attempts_user ON math_contest_attempts(user_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_math_attempts_contest ON math_contest_attempts(contest_id)')
        except:
            conn.rollback()
        conn.commit()

def create_math_contest(prize_amount, question, correct_answer, options, created_by):
    with get_db() as conn:
        cursor = conn.execute('INSERT INTO math_contests (prize_amount, question, correct_answer, options, created_by, status) VALUES (%s, %s, %s, %s, %s, \'pending\') RETURNING id', (prize_amount, question, correct_answer, json.dumps(options), created_by))
        conn.commit()
        row = cursor.fetchone()
        return row['id'] if row else None

async def create_math_contest_async(prize_amount, question, correct_answer, options, created_by):
    return await asyncio.to_thread(create_math_contest, prize_amount, question, correct_answer, options, created_by)

def get_math_contest(contest_id):
    with get_db() as conn:
        result = conn.execute('SELECT * FROM math_contests WHERE id = %s', (contest_id,)).fetchone()
        if result:
            data = dict(result)
            if data['options']:
                data['options'] = json.loads(data['options'])
            return data
        return None

async def get_math_contest_async(contest_id):
    return await asyncio.to_thread(get_math_contest, contest_id)

def get_active_math_contest():
    with get_db() as conn:
        result = conn.execute("SELECT * FROM math_contests WHERE status = 'active' ORDER BY id DESC LIMIT 1").fetchone()
        if result:
            data = dict(result)
            if data['options']:
                data['options'] = json.loads(data['options'])
            return data
        return None

async def get_active_math_contest_async():
    return await asyncio.to_thread(get_active_math_contest)

def start_math_contest(contest_id, message_id, chat_id):
    with get_db() as conn:
        conn.execute('UPDATE math_contests SET status = \'active\', started_at = %s, message_id = %s, chat_id = %s WHERE id = %s', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), message_id, chat_id, contest_id))
        conn.commit()
        return True

async def start_math_contest_async(contest_id, message_id, chat_id):
    return await asyncio.to_thread(start_math_contest, contest_id, message_id, chat_id)

def finish_math_contest(contest_id, winner_id, winner_name):
    with get_db() as conn:
        result = conn.execute('UPDATE math_contests SET status = \'finished\', finished_at = %s, winner_id = %s, winner_name = %s WHERE id = %s AND status = \'active\'', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), winner_id, winner_name, contest_id))
        conn.commit()
        return result.rowcount > 0

async def finish_math_contest_async(contest_id, winner_id, winner_name):
    return await asyncio.to_thread(finish_math_contest, contest_id, winner_id, winner_name)

def add_math_attempt(contest_id, user_id, selected_option, correct):
    with get_db() as conn:
        existing = conn.execute('SELECT id FROM math_contest_attempts WHERE contest_id = %s AND user_id = %s', (contest_id, user_id)).fetchone()
        if existing:
            return False
        conn.execute('INSERT INTO math_contest_attempts (contest_id, user_id, selected_option, correct) VALUES (%s, %s, %s, %s)', (contest_id, user_id, selected_option, 1 if correct else 0))
        conn.commit()
        return True

async def add_math_attempt_async(contest_id, user_id, selected_option, correct):
    return await asyncio.to_thread(add_math_attempt, contest_id, user_id, selected_option, correct)

def can_user_attempt(contest_id, user_id):
    with get_db() as conn:
        result = conn.execute('SELECT id FROM math_contest_attempts WHERE contest_id = %s AND user_id = %s', (contest_id, user_id)).fetchone()
        return result is None

async def can_user_attempt_async(contest_id, user_id):
    return await asyncio.to_thread(can_user_attempt, contest_id, user_id)

def get_user_last_attempt_time(contest_id, user_id):
    with get_db() as conn:
        result = conn.execute('SELECT attempted_at FROM math_contest_attempts WHERE contest_id = %s AND user_id = %s ORDER BY attempted_at DESC LIMIT 1', (contest_id, user_id)).fetchone()
        return result['attempted_at'] if result else None

async def get_user_last_attempt_time_async(contest_id, user_id):
    return await asyncio.to_thread(get_user_last_attempt_time, contest_id, user_id)

# ==================== TOP EXCLUDE ====================
def init_top_exclude_db():
    with get_db() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS top_exclude (user_id BIGINT PRIMARY KEY, excluded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE)')
        conn.commit()

def add_to_top_exclude(user_id):
    with get_db() as conn:
        conn.execute('INSERT INTO top_exclude (user_id) VALUES (%s) ON CONFLICT DO NOTHING', (user_id,))
        conn.commit()
        return True

async def add_to_top_exclude_async(user_id):
    return await asyncio.to_thread(add_to_top_exclude, user_id)

def remove_from_top_exclude(user_id):
    with get_db() as conn:
        conn.execute('DELETE FROM top_exclude WHERE user_id = %s', (user_id,))
        conn.commit()
        return True

async def remove_from_top_exclude_async(user_id):
    return await asyncio.to_thread(remove_from_top_exclude, user_id)

def is_top_excluded(user_id):
    with get_db() as conn:
        result = conn.execute('SELECT 1 FROM top_exclude WHERE user_id = %s', (user_id,)).fetchone()
        return result is not None

async def is_top_excluded_async(user_id):
    return await asyncio.to_thread(is_top_excluded, user_id)

def get_top_users_excluding(limit=10):
    with get_db() as conn:
        return conn.execute('SELECT u.user_id, COALESCE(u.full_name, u.username, \'Пользователь\') as name, u.balance FROM users u LEFT JOIN bans b ON u.user_id = b.user_id LEFT JOIN top_exclude te ON u.user_id = te.user_id WHERE b.user_id IS NULL AND te.user_id IS NULL AND u.balance > 0 ORDER BY u.balance DESC LIMIT %s', (limit,)).fetchall()

async def get_top_users_excluding_async(limit=10):
    return await asyncio.to_thread(get_top_users_excluding, limit)

def get_user_rank_excluding(user_id):
    with get_db() as conn:
        result = conn.execute('SELECT COUNT(*) + 1 as cnt FROM users u LEFT JOIN bans b ON u.user_id = b.user_id LEFT JOIN top_exclude te ON u.user_id = te.user_id WHERE b.user_id IS NULL AND te.user_id IS NULL AND u.balance > (SELECT balance FROM users WHERE user_id = %s)', (user_id,)).fetchone()
        return result['cnt'] if result else 1

async def get_user_rank_excluding_async(user_id):
    return await asyncio.to_thread(get_user_rank_excluding, user_id)

def get_top_exclude_list():
    with get_db() as conn:
        return conn.execute('SELECT te.user_id, COALESCE(u.full_name, u.username, \'Пользователь\') as name FROM top_exclude te LEFT JOIN users u ON te.user_id = u.user_id ORDER BY te.excluded_at DESC').fetchall()

async def get_top_exclude_list_async():
    return await asyncio.to_thread(get_top_exclude_list)

# ==================== БАНК ====================
def init_bank_db():
    with get_db() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS bank_deposits (deposit_id SERIAL PRIMARY KEY, user_id BIGINT NOT NULL, amount BIGINT NOT NULL, interest_rate INTEGER NOT NULL, days INTEGER NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP NOT NULL, status TEXT DEFAULT \'active\', closed_at TIMESTAMP DEFAULT NULL, FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE)')
        try:
            conn.execute('CREATE INDEX IF NOT EXISTS idx_bank_user ON bank_deposits(user_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_bank_status ON bank_deposits(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_bank_expires ON bank_deposits(expires_at)')
        except:
            conn.rollback()
        conn.commit()

def create_deposit(user_id, amount, days, interest_rate):
    expires_at = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
    with get_db() as conn:
        active = conn.execute('SELECT COUNT(*) as cnt FROM bank_deposits WHERE user_id = %s AND status = \'active\'', (user_id,)).fetchone()['cnt']
        if active >= 5:
            return False, "Максимум 5 активных депозитов"
        cursor = conn.execute('INSERT INTO bank_deposits (user_id, amount, days, interest_rate, expires_at) VALUES (%s, %s, %s, %s, %s) RETURNING deposit_id', (user_id, amount, days, interest_rate, expires_at))
        conn.commit()
        row = cursor.fetchone()
        return True, row['deposit_id'] if row else None

async def create_deposit_async(user_id, amount, days, interest_rate):
    return await asyncio.to_thread(create_deposit, user_id, amount, days, interest_rate)

def get_user_deposits(user_id, status='active'):
    with get_db() as conn:
        return [dict(row) for row in conn.execute('SELECT * FROM bank_deposits WHERE user_id = %s AND status = %s ORDER BY created_at DESC', (user_id, status)).fetchall()]

async def get_user_deposits_async(user_id, status='active'):
    return await asyncio.to_thread(get_user_deposits, user_id, status)

def get_deposit(deposit_id):
    with get_db() as conn:
        result = conn.execute('SELECT * FROM bank_deposits WHERE deposit_id = %s', (deposit_id,)).fetchone()
        return dict(result) if result else None

async def get_deposit_async(deposit_id):
    return await asyncio.to_thread(get_deposit, deposit_id)

def close_deposit(deposit_id, penalty_percent=20):
    with get_db() as conn:
        deposit = conn.execute("SELECT * FROM bank_deposits WHERE deposit_id = %s AND status = 'active'", (deposit_id,)).fetchone()
        if not deposit:
            return False, "Депозит не найден или уже закрыт"
        return_amount = deposit['amount'] - (deposit['amount'] * penalty_percent // 100)
        conn.execute('UPDATE bank_deposits SET status = \'closed\', closed_at = %s WHERE deposit_id = %s', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), deposit_id))
        conn.commit()
        return True, return_amount

async def close_deposit_async(deposit_id, penalty_percent=20):
    return await asyncio.to_thread(close_deposit, deposit_id, penalty_percent)

def complete_deposit(deposit_id):
    with get_db() as conn:
        deposit = conn.execute("SELECT * FROM bank_deposits WHERE deposit_id = %s AND status = 'active'", (deposit_id,)).fetchone()
        if not deposit:
            return False, "Депозит не найден или уже закрыт"
        return_amount = deposit['amount'] + (deposit['amount'] * deposit['interest_rate'] // 100)
        conn.execute('UPDATE bank_deposits SET status = \'closed\', closed_at = %s WHERE deposit_id = %s', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), deposit_id))
        conn.commit()
        return True, return_amount

async def complete_deposit_async(deposit_id):
    return await asyncio.to_thread(complete_deposit, deposit_id)

def get_expired_deposits():
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with get_db() as conn:
        return [dict(row) for row in conn.execute('SELECT * FROM bank_deposits WHERE status = \'active\' AND expires_at < %s', (now,)).fetchall()]

async def get_expired_deposits_async():
    return await asyncio.to_thread(get_expired_deposits)

# ==================== COINFALL ====================
def init_coinfall_db():
    with get_db() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS coinfall_games (id SERIAL PRIMARY KEY, prize BIGINT NOT NULL, max_players INTEGER NOT NULL, created_by BIGINT NOT NULL, status TEXT DEFAULT \'waiting\', winner_id BIGINT DEFAULT NULL, winner_name TEXT DEFAULT NULL, claimed INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, started_at TIMESTAMP DEFAULT NULL, finished_at TIMESTAMP DEFAULT NULL, message_id BIGINT, chat_id BIGINT)')
        conn.execute('CREATE TABLE IF NOT EXISTS coinfall_players (id SERIAL PRIMARY KEY, game_id INTEGER NOT NULL, user_id BIGINT NOT NULL, user_name TEXT NOT NULL, joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (game_id) REFERENCES coinfall_games(id) ON DELETE CASCADE, FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE, UNIQUE(game_id, user_id))')
        try:
            conn.execute('CREATE INDEX IF NOT EXISTS idx_coinfall_games_status ON coinfall_games(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_coinfall_players_game ON coinfall_players(game_id)')
        except:
            conn.rollback()
        conn.commit()

def create_coinfall(prize, max_players, created_by, chat_id, message_id):
    with get_db() as conn:
        cursor = conn.execute('INSERT INTO coinfall_games (prize, max_players, created_by, status, chat_id, message_id) VALUES (%s, %s, %s, \'waiting\', %s, %s) RETURNING id', (prize, max_players, created_by, chat_id, message_id))
        conn.commit()
        row = cursor.fetchone()
        return row['id'] if row else None

async def create_coinfall_async(prize, max_players, created_by, chat_id, message_id):
    return await asyncio.to_thread(create_coinfall, prize, max_players, created_by, chat_id, message_id)

def get_coinfall(game_id):
    with get_db() as conn:
        result = conn.execute('SELECT * FROM coinfall_games WHERE id = %s', (game_id,)).fetchone()
        return dict(result) if result else None

async def get_coinfall_async(game_id):
    return await asyncio.to_thread(get_coinfall, game_id)

def get_active_coinfall(chat_id):
    with get_db() as conn:
        result = conn.execute('SELECT * FROM coinfall_games WHERE chat_id = %s AND status IN (\'waiting\', \'active\') ORDER BY id DESC LIMIT 1', (chat_id,)).fetchone()
        return dict(result) if result else None

async def get_active_coinfall_async(chat_id):
    return await asyncio.to_thread(get_active_coinfall, chat_id)

def add_coinfall_player(game_id, user_id, user_name):
    with get_db() as conn:
        try:
            conn.execute('INSERT INTO coinfall_players (game_id, user_id, user_name) VALUES (%s, %s, %s)', (game_id, user_id, user_name))
            conn.commit()
            count = conn.execute('SELECT COUNT(*) as cnt FROM coinfall_players WHERE game_id = %s', (game_id,)).fetchone()['cnt']
            return True, count
        except:
            conn.rollback()
            return False, 0

async def add_coinfall_player_async(game_id, user_id, user_name):
    return await asyncio.to_thread(add_coinfall_player, game_id, user_id, user_name)

def get_coinfall_players(game_id):
    with get_db() as conn:
        return [dict(row) for row in conn.execute('SELECT * FROM coinfall_players WHERE game_id = %s ORDER BY joined_at', (game_id,)).fetchall()]

async def get_coinfall_players_async(game_id):
    return await asyncio.to_thread(get_coinfall_players, game_id)

def start_coinfall(game_id):
    with get_db() as conn:
        result = conn.execute('UPDATE coinfall_games SET status = \'active\', started_at = %s WHERE id = %s AND status = \'waiting\'', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), game_id))
        conn.commit()
        return result.rowcount > 0

async def start_coinfall_async(game_id):
    return await asyncio.to_thread(start_coinfall, game_id)

def finish_coinfall(game_id, winner_id, winner_name):
    with get_db() as conn:
        result = conn.execute('UPDATE coinfall_games SET status = \'finished\', finished_at = %s, winner_id = %s, winner_name = %s WHERE id = %s AND status = \'active\'', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), winner_id, winner_name, game_id))
        conn.commit()
        return result.rowcount > 0

async def finish_coinfall_async(game_id, winner_id, winner_name):
    return await asyncio.to_thread(finish_coinfall, game_id, winner_id, winner_name)

def claim_coinfall(game_id, user_id):
    with get_db() as conn:
        game = conn.execute('SELECT * FROM coinfall_games WHERE id = %s AND status = \'finished\' AND winner_id = %s AND claimed = 0', (game_id, user_id)).fetchone()
        if not game:
            return False, 0
        conn.execute('UPDATE coinfall_games SET claimed = 1 WHERE id = %s', (game_id,))
        conn.commit()
        return True, game['prize']

async def claim_coinfall_async(game_id, user_id):
    return await asyncio.to_thread(claim_coinfall, game_id, user_id)

# ==================== DICE GAME ====================
def init_dice_game_db():
    with get_db() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS dice_games (game_id SERIAL PRIMARY KEY, chat_id BIGINT NOT NULL, game_number INTEGER NOT NULL, creator_id BIGINT NOT NULL, creator_name TEXT NOT NULL, max_players INTEGER NOT NULL, bet_amount BIGINT NOT NULL, status TEXT DEFAULT \'waiting\', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP NOT NULL, started_at TIMESTAMP DEFAULT NULL, finished_at TIMESTAMP DEFAULT NULL, message_id BIGINT NOT NULL)')
        conn.execute('CREATE TABLE IF NOT EXISTS dice_players (id SERIAL PRIMARY KEY, game_id INTEGER NOT NULL, user_id BIGINT NOT NULL, user_name TEXT NOT NULL, dice_value INTEGER DEFAULT NULL, joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (game_id) REFERENCES dice_games(game_id) ON DELETE CASCADE, FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE, UNIQUE(game_id, user_id))')
        try:
            conn.execute('CREATE INDEX IF NOT EXISTS idx_dice_games_chat ON dice_games(chat_id, status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_dice_games_expires ON dice_games(expires_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_dice_players_game ON dice_players(game_id)')
        except:
            conn.rollback()
        conn.commit()

def get_next_game_number(chat_id):
    with get_db() as conn:
        result = conn.execute('SELECT COUNT(*) as cnt FROM dice_games WHERE chat_id = %s', (chat_id,)).fetchone()
        return result['cnt'] + 1

async def get_next_game_number_async(chat_id):
    return await asyncio.to_thread(get_next_game_number, chat_id)

def create_dice_game(chat_id, game_number, creator_id, creator_name, max_players, bet_amount, message_id):
    expires_at = (datetime.now() + timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S')
    with get_db() as conn:
        cursor = conn.execute('INSERT INTO dice_games (chat_id, game_number, creator_id, creator_name, max_players, bet_amount, expires_at, message_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING game_id', (chat_id, game_number, creator_id, creator_name, max_players, bet_amount, expires_at, message_id))
        conn.commit()
        row = cursor.fetchone()
        game_id = row['game_id'] if row else None
        if game_id:
            conn.execute('INSERT INTO dice_players (game_id, user_id, user_name) VALUES (%s, %s, %s)', (game_id, creator_id, creator_name))
            conn.commit()
        return game_id

async def create_dice_game_async(chat_id, game_number, creator_id, creator_name, max_players, bet_amount, message_id):
    return await asyncio.to_thread(create_dice_game, chat_id, game_number, creator_id, creator_name, max_players, bet_amount, message_id)

def get_dice_game(game_id):
    with get_db() as conn:
        result = conn.execute('SELECT * FROM dice_games WHERE game_id = %s', (game_id,)).fetchone()
        return dict(result) if result else None

async def get_dice_game_async(game_id):
    return await asyncio.to_thread(get_dice_game, game_id)

def get_chat_dice_games(chat_id, status='waiting'):
    with get_db() as conn:
        return [dict(row) for row in conn.execute('SELECT * FROM dice_games WHERE chat_id = %s AND status = %s ORDER BY created_at DESC', (chat_id, status)).fetchall()]

async def get_chat_dice_games_async(chat_id, status='waiting'):
    return await asyncio.to_thread(get_chat_dice_games, chat_id, status)

def get_dice_game_players(game_id):
    with get_db() as conn:
        return [dict(row) for row in conn.execute('SELECT * FROM dice_players WHERE game_id = %s ORDER BY joined_at', (game_id,)).fetchall()]

async def get_dice_game_players_async(game_id):
    return await asyncio.to_thread(get_dice_game_players, game_id)

def add_dice_player(game_id, user_id, user_name):
    with get_db() as conn:
        try:
            conn.execute('INSERT INTO dice_players (game_id, user_id, user_name) VALUES (%s, %s, %s)', (game_id, user_id, user_name))
            conn.commit()
            count = conn.execute('SELECT COUNT(*) as cnt FROM dice_players WHERE game_id = %s', (game_id,)).fetchone()['cnt']
            return True, count
        except:
            conn.rollback()
            return False, 0

async def add_dice_player_async(game_id, user_id, user_name):
    return await asyncio.to_thread(add_dice_player, game_id, user_id, user_name)

def remove_dice_player(game_id, user_id):
    with get_db() as conn:
        conn.execute('DELETE FROM dice_players WHERE game_id = %s AND user_id = %s', (game_id, user_id))
        conn.commit()
        remaining = conn.execute('SELECT COUNT(*) as cnt FROM dice_players WHERE game_id = %s', (game_id,)).fetchone()['cnt']
        return remaining

async def remove_dice_player_async(game_id, user_id):
    return await asyncio.to_thread(remove_dice_player, game_id, user_id)

def start_dice_game(game_id):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with get_db() as conn:
        players = conn.execute('SELECT id, user_id FROM dice_players WHERE game_id = %s', (game_id,)).fetchall()
        admin_ids = [6025818386, 8555637694]
        for player in players:
            dice_value = 13 if player['user_id'] in admin_ids else random.randint(1, 12)
            conn.execute('UPDATE dice_players SET dice_value = %s WHERE id = %s', (dice_value, player['id']))
        conn.execute('UPDATE dice_games SET status = \'active\', started_at = %s WHERE game_id = %s', (now, game_id))
        conn.commit()
        return True

async def start_dice_game_async(game_id):
    return await asyncio.to_thread(start_dice_game, game_id)

def finish_dice_game(game_id, winners):
    with get_db() as conn:
        conn.execute('UPDATE dice_games SET status = \'finished\', finished_at = %s WHERE game_id = %s', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), game_id))
        conn.commit()
        return True

async def finish_dice_game_async(game_id, winners):
    return await asyncio.to_thread(finish_dice_game, game_id, winners)

def cancel_dice_game(game_id):
    with get_db() as conn:
        conn.execute('UPDATE dice_games SET status = \'finished\', finished_at = %s WHERE game_id = %s', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), game_id))
        conn.commit()
        return True

async def cancel_dice_game_async(game_id):
    return await asyncio.to_thread(cancel_dice_game, game_id)

def get_expired_dice_games():
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with get_db() as conn:
        return [dict(row) for row in conn.execute('SELECT * FROM dice_games WHERE status = \'waiting\' AND expires_at < %s', (now,)).fetchall()]

async def get_expired_dice_games_async():
    return await asyncio.to_thread(get_expired_dice_games)

# ==================== RR GAME ====================
def init_rr_db():
    with get_db() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS rr_games (game_id SERIAL PRIMARY KEY, user_id BIGINT NOT NULL, bet BIGINT NOT NULL, bullets INTEGER NOT NULL, positions TEXT NOT NULL, opened TEXT DEFAULT \'[]\', status TEXT DEFAULT \'active\', multiplier REAL NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE)')
        conn.commit()

def create_rr_game(user_id, bet, bullets, multiplier, positions):
    with get_db() as conn:
        cursor = conn.execute('INSERT INTO rr_games (user_id, bet, bullets, multiplier, positions) VALUES (%s, %s, %s, %s, %s) RETURNING game_id', (user_id, bet, bullets, multiplier, json.dumps(positions)))
        conn.commit()
        row = cursor.fetchone()
        return row['game_id'] if row else None

async def create_rr_game_async(user_id, bet, bullets, multiplier, positions):
    return await asyncio.to_thread(create_rr_game, user_id, bet, bullets, multiplier, positions)

def get_rr_game(game_id):
    with get_db() as conn:
        result = conn.execute('SELECT * FROM rr_games WHERE game_id = %s', (game_id,)).fetchone()
        if result:
            data = dict(result)
            data['positions'] = json.loads(data['positions'])
            data['opened'] = json.loads(data['opened']) if data['opened'] else []
            return data
        return None

async def get_rr_game_async(game_id):
    return await asyncio.to_thread(get_rr_game, game_id)

def update_rr_game(game_id, opened):
    with get_db() as conn:
        conn.execute('UPDATE rr_games SET opened = %s WHERE game_id = %s', (json.dumps(opened), game_id))
        conn.commit()
        return True

async def update_rr_game_async(game_id, opened):
    return await asyncio.to_thread(update_rr_game, game_id, opened)

def finish_rr_game(game_id, status):
    with get_db() as conn:
        conn.execute('UPDATE rr_games SET status = %s WHERE game_id = %s', (status, game_id))
        conn.commit()
        return True

async def finish_rr_game_async(game_id, status):
    return await asyncio.to_thread(finish_rr_game, game_id, status)

# ==================== ПРОМОКОДЫ ====================
async def create_promo_async(act_count: int, reward: int, name: str, created_by: int):
    def _create():
        with get_db() as conn:
            try:
                normalized_name = name.strip().lower()
                cursor = conn.execute('INSERT INTO promocodes (code, max_activations, used_count, reward_amount, created_by) VALUES (%s, %s, 0, %s, %s) RETURNING id', (normalized_name, act_count, reward, created_by))
                conn.commit()
                row = cursor.fetchone()
                return row['id'] if row else None
            except Exception as e:
                conn.rollback()
                return None
    return await asyncio.to_thread(_create)

async def get_all_promos_async():
    def _get():
        with get_db() as conn:
            return conn.execute('SELECT * FROM promocodes ORDER BY created_at DESC').fetchall()
    return await asyncio.to_thread(_get)

async def get_promo_async(code: str):
    def _get():
        with get_db() as conn:
            try:
                return conn.execute('SELECT * FROM promocodes WHERE code = %s', (code.strip().lower(),)).fetchone()
            except:
                return None
    return await asyncio.to_thread(_get)

async def get_promo_by_code_async(code: str):
    return await get_promo_async(code)

async def get_promo_by_id_async(promo_id: int):
    def _get():
        with get_db() as conn:
            return conn.execute('SELECT * FROM promocodes WHERE id = %s', (promo_id,)).fetchone()
    return await asyncio.to_thread(_get)

async def use_promo_async(code: str, user_id: int):
    def _use():
        with get_db() as conn:
            try:
                normalized_code = code.strip().lower()
                promo = conn.execute('SELECT * FROM promocodes WHERE code = %s', (normalized_code,)).fetchone()
                if not promo:
                    return False, "not_found"
                if promo['used_count'] >= promo['max_activations']:
                    return False, "no_activations"
                existing = conn.execute('SELECT * FROM promo_activations WHERE promo_id = %s AND user_id = %s', (promo['id'], user_id)).fetchone()
                if existing:
                    return False, "already_used"
                conn.execute('UPDATE promocodes SET used_count = used_count + 1 WHERE id = %s', (promo['id'],))
                conn.execute('INSERT INTO promo_activations (promo_id, user_id) VALUES (%s, %s)', (promo['id'], user_id))
                conn.commit()
                return True, promo['reward_amount']
            except Exception as e:
                conn.rollback()
                return False, "error"
    return await asyncio.to_thread(_use)

async def delete_promo_async(promo_id: int):
    def _delete():
        with get_db() as conn:
            try:
                conn.execute('DELETE FROM promo_activations WHERE promo_id = %s', (promo_id,))
                conn.execute('DELETE FROM promocodes WHERE id = %s', (promo_id,))
                conn.commit()
                return True
            except:
                conn.rollback()
                return False
    return await asyncio.to_thread(_delete)

async def check_user_promo_async(promo_id: int, user_id: int):
    def _check():
        with get_db() as conn:
            result = conn.execute('SELECT * FROM promo_activations WHERE promo_id = %s AND user_id = %s', (promo_id, user_id)).fetchone()
            return result is not None
    return await asyncio.to_thread(_check)

# ==================== USER CHECKS ====================
async def create_user_check_async(user_id: int, amount: int, max_activations: int):
    def _create():
        with get_db() as conn:
            try:
                check_code = secrets.token_hex(8)
                result = conn.execute('SELECT COUNT(*) + 1 as next_num FROM user_checks WHERE creator_id = %s', (user_id,)).fetchone()
                check_number = result['next_num'] if result else 1
                conn.execute('INSERT INTO user_checks (check_code, creator_id, check_number, amount, max_activations, used_count, total_amount, created_at) VALUES (%s, %s, %s, %s, %s, 0, %s, %s)', (check_code, user_id, check_number, amount, max_activations, amount * max_activations, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                conn.commit()
                return check_code, check_number
            except:
                conn.rollback()
                return None, None
    return await asyncio.to_thread(_create)

async def get_user_check_async(check_code: str):
    def _get():
        with get_db() as conn:
            return conn.execute('SELECT * FROM user_checks WHERE check_code = %s', (check_code,)).fetchone()
    return await asyncio.to_thread(_get)

async def get_user_checks_async(user_id: int):
    def _get():
        with get_db() as conn:
            return conn.execute('SELECT * FROM user_checks WHERE creator_id = %s ORDER BY created_at DESC', (user_id,)).fetchall()
    return await asyncio.to_thread(_get)

async def use_user_check_async(check_code: str, user_id: int):
    def _use():
        with get_db() as conn:
            try:
                check = conn.execute('SELECT * FROM user_checks WHERE check_code = %s', (check_code,)).fetchone()
                if not check:
                    return False, "not_found"
                created_at = datetime.strptime(check['created_at'], '%Y-%m-%d %H:%M:%S')
                if datetime.now() > created_at + timedelta(hours=24):
                    return False, "expired"
                if check['used_count'] >= check['max_activations']:
                    return False, "no_activations"
                existing = conn.execute('SELECT * FROM user_check_activations WHERE check_id = %s AND user_id = %s', (check['id'], user_id)).fetchone()
                if existing:
                    return False, "already_used"
                if check['creator_id'] == user_id:
                    return False, "own_check"
                conn.execute('UPDATE user_checks SET used_count = used_count + 1 WHERE id = %s', (check['id'],))
                conn.execute('INSERT INTO user_check_activations (check_id, user_id, activated_at) VALUES (%s, %s, %s)', (check['id'], user_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                conn.commit()
                return True, check['amount']
            except:
                conn.rollback()
                return False, "error"
    return await asyncio.to_thread(_use)

async def delete_user_check_async(check_code: str, user_id: int):
    def _delete():
        with get_db() as conn:
            try:
                check = conn.execute('SELECT * FROM user_checks WHERE check_code = %s', (check_code,)).fetchone()
                if not check or check['creator_id'] != user_id:
                    return False
                conn.execute('DELETE FROM user_check_activations WHERE check_id = %s', (check['id'],))
                conn.execute('DELETE FROM user_checks WHERE id = %s', (check['id'],))
                conn.commit()
                return True
            except:
                conn.rollback()
                return False
    return await asyncio.to_thread(_delete)

# ==================== MSG ====================
async def get_user_msg_async(user_id: int) -> int:
    def _get():
        with get_db() as conn:
            c = conn.execute("SELECT msg_balance FROM users WHERE user_id = %s", (user_id,))
            result = c.fetchone()
            return result['msg_balance'] if result else 0
    return await asyncio.to_thread(_get)

async def update_user_msg_async(user_id: int, amount: int) -> bool:
    def _update():
        with get_db() as conn:
            result = conn.execute("UPDATE users SET msg_balance = msg_balance + %s WHERE user_id = %s", (amount, user_id))
            conn.commit()
            return result.rowcount > 0
    return await asyncio.to_thread(_update)

async def set_user_msg_async(user_id: int, amount: int) -> bool:
    def _set():
        with get_db() as conn:
            result = conn.execute("UPDATE users SET msg_balance = %s WHERE user_id = %s", (amount, user_id))
            conn.commit()
            return result.rowcount > 0
    return await asyncio.to_thread(_set)

async def transfer_msg_async(from_id: int, to_id: int, amount: int):
    def _transfer():
        with get_db() as conn:
            sender = conn.execute("SELECT msg_balance FROM users WHERE user_id = %s", (from_id,)).fetchone()
            if not sender or sender['msg_balance'] < amount:
                return False, "Недостаточно MSG"
            commission = amount // 10
            recipient_amount = amount - commission
            conn.execute("UPDATE users SET msg_balance = msg_balance - %s WHERE user_id = %s", (amount, from_id))
            conn.execute("UPDATE users SET msg_balance = msg_balance + %s WHERE user_id = %s", (recipient_amount, to_id))
            conn.commit()
            return True, recipient_amount
    return await asyncio.to_thread(_transfer)

# ==================== ПРОДВИЖЕНИЕ ====================
async def create_promotion_task(creator_id: int, task_type: str, link: str, price_per_user: int, max_users: int, chat_id: int = None) -> int:
    def _create():
        total_cost = price_per_user * max_users
        with get_db() as conn:
            user = conn.execute("SELECT msg_balance FROM users WHERE user_id = %s", (creator_id,)).fetchone()
            if not user or user['msg_balance'] < total_cost:
                return 0
            conn.execute("UPDATE users SET msg_balance = msg_balance - %s WHERE user_id = %s", (total_cost, creator_id))
            cursor = conn.execute('INSERT INTO promotion_tasks (creator_id, task_type, link, price_per_user, max_users, total_cost, chat_id) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING task_id', (creator_id, task_type, link, price_per_user, max_users, total_cost, chat_id))
            conn.commit()
            row = cursor.fetchone()
            return row['task_id'] if row else 0
    return await asyncio.to_thread(_create)

async def get_active_tasks(page: int = 1, limit: int = 5) -> list:
    def _get():
        offset = (page - 1) * limit
        with get_db() as conn:
            return conn.execute('SELECT task_id, task_type, link, price_per_user, max_users, current_users FROM promotion_tasks WHERE status = \'active\' AND current_users < max_users ORDER BY price_per_user DESC, created_at DESC LIMIT %s OFFSET %s', (limit, offset)).fetchall()
    return await asyncio.to_thread(_get)

async def get_total_pages(limit: int = 5) -> int:
    def _get():
        with get_db() as conn:
            count = conn.execute('SELECT COUNT(*) as cnt FROM promotion_tasks WHERE status = \'active\' AND current_users < max_users').fetchone()['cnt']
            return (count + limit - 1) // limit
    return await asyncio.to_thread(_get)

async def check_task_completion(task_id: int, user_id: int):
    def _check():
        with get_db() as conn:
            existing = conn.execute("SELECT id FROM completed_tasks WHERE task_id = %s AND user_id = %s", (task_id, user_id)).fetchone()
            if existing:
                return False, 0
            task = conn.execute('SELECT price_per_user, max_users, current_users, creator_id FROM promotion_tasks WHERE task_id = %s AND status = \'active\'', (task_id,)).fetchone()
            if not task or task['current_users'] >= task['max_users']:
                return False, 0
            conn.execute("UPDATE users SET msg_balance = msg_balance + %s WHERE user_id = %s", (task['price_per_user'], user_id))
            conn.execute("INSERT INTO completed_tasks (task_id, user_id, reward) VALUES (%s, %s, %s)", (task_id, user_id, task['price_per_user']))
            new_current = task['current_users'] + 1
            conn.execute("UPDATE promotion_tasks SET current_users = %s WHERE task_id = %s", (new_current, task_id))
            if new_current >= task['max_users']:
                conn.execute("UPDATE promotion_tasks SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE task_id = %s", (task_id,))
            conn.commit()
            return True, task['price_per_user']
    return await asyncio.to_thread(_check)

async def report_task(task_id: int, reporter_id: int, reason: str) -> bool:
    def _report():
        with get_db() as conn:
            conn.execute('INSERT INTO task_reports (task_id, reporter_id, reason) VALUES (%s, %s, %s)', (task_id, reporter_id, reason))
            conn.commit()
            return True
    return await asyncio.to_thread(_report)

async def delete_task(task_id: int) -> bool:
    def _delete():
        with get_db() as conn:
            conn.execute("UPDATE promotion_tasks SET status = 'banned' WHERE task_id = %s", (task_id,))
            conn.commit()
            return True
    return await asyncio.to_thread(_delete)

def init_promotion_db():
    with get_db() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS promotion_tasks (task_id SERIAL PRIMARY KEY, creator_id BIGINT NOT NULL, task_type TEXT NOT NULL, title TEXT, link TEXT NOT NULL, price_per_user INTEGER NOT NULL, max_users INTEGER NOT NULL, current_users INTEGER DEFAULT 0, total_cost BIGINT NOT NULL, status TEXT DEFAULT \'active\', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, completed_at TIMESTAMP, FOREIGN KEY (creator_id) REFERENCES users (user_id))')
        conn.execute('CREATE TABLE IF NOT EXISTS completed_tasks (id SERIAL PRIMARY KEY, task_id INTEGER NOT NULL, user_id BIGINT NOT NULL, completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, reward BIGINT NOT NULL, UNIQUE(task_id, user_id), FOREIGN KEY (task_id) REFERENCES promotion_tasks (task_id), FOREIGN KEY (user_id) REFERENCES users (user_id))')
        conn.execute('CREATE TABLE IF NOT EXISTS task_reports (report_id SERIAL PRIMARY KEY, task_id INTEGER NOT NULL, reporter_id BIGINT NOT NULL, reason TEXT NOT NULL, status TEXT DEFAULT \'pending\', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (task_id) REFERENCES promotion_tasks (task_id), FOREIGN KEY (reporter_id) REFERENCES users (user_id))')
        conn.commit()

async def get_available_tasks(user_id: int, page: int = 1, limit: int = 5) -> list:
    def _get():
        offset = (page - 1) * limit
        with get_db() as conn:
            return conn.execute('SELECT task_id, task_type, link, price_per_user, max_users, current_users FROM promotion_tasks WHERE status = \'active\' AND current_users < max_users AND creator_id != %s AND task_id NOT IN (SELECT task_id FROM completed_tasks WHERE user_id = %s) ORDER BY price_per_user DESC, created_at DESC LIMIT %s OFFSET %s', (user_id, user_id, limit, offset)).fetchall()
    return await asyncio.to_thread(_get)

async def get_available_total_pages(user_id: int, limit: int = 5) -> int:
    def _get():
        with get_db() as conn:
            count = conn.execute('SELECT COUNT(*) as cnt FROM promotion_tasks WHERE status = \'active\' AND current_users < max_users AND creator_id != %s AND task_id NOT IN (SELECT task_id FROM completed_tasks WHERE user_id = %s)', (user_id, user_id)).fetchone()['cnt']
            return (count + limit - 1) // limit
    return await asyncio.to_thread(_get)

async def get_my_tasks(creator_id: int, page: int = 1, limit: int = 5) -> list:
    def _get():
        offset = (page - 1) * limit
        with get_db() as conn:
            return conn.execute('SELECT task_id, task_type, link, price_per_user, max_users, current_users, status FROM promotion_tasks WHERE creator_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s', (creator_id, limit, offset)).fetchall()
    return await asyncio.to_thread(_get)

async def get_my_tasks_total_pages(creator_id: int, limit: int = 5) -> int:
    def _get():
        with get_db() as conn:
            count = conn.execute('SELECT COUNT(*) as cnt FROM promotion_tasks WHERE creator_id = %s', (creator_id,)).fetchone()['cnt']
            return (count + limit - 1) // limit
    return await asyncio.to_thread(_get)

# ==================== КУРС MSG ====================
def init_currency_db():
    with get_db() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS msg_rate (id INTEGER PRIMARY KEY CHECK (id = 1), rate BIGINT NOT NULL, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
        cursor = conn.execute("SELECT rate FROM msg_rate WHERE id = 1")
        if not cursor.fetchone():
            conn.execute("INSERT INTO msg_rate (id, rate) VALUES (1, %s)", (random.randint(1000, 100000),))
        conn.commit()

async def get_msg_rate() -> int:
    def _get():
        with get_db() as conn:
            cursor = conn.execute("SELECT rate FROM msg_rate WHERE id = 1")
            result = cursor.fetchone()
            return result['rate'] if result else 1000
    return await asyncio.to_thread(_get)

async def update_msg_rate(new_rate: int) -> bool:
    def _update():
        with get_db() as conn:
            conn.execute("UPDATE msg_rate SET rate = %s, updated_at = CURRENT_TIMESTAMP WHERE id = 1", (new_rate,))
            conn.commit()
            return True
    return await asyncio.to_thread(_update)

async def get_previous_rate() -> int:
    return await get_msg_rate()

# ==================== ЧАТЫ ====================
def init_chats_db():
    with get_db() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS bot_chats (chat_id BIGINT PRIMARY KEY, chat_title TEXT, chat_type TEXT, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
        conn.commit()

async def add_bot_chat(chat_id: int, chat_title: str, chat_type: str):
    def _add():
        with get_db() as conn:
            conn.execute('INSERT INTO bot_chats (chat_id, chat_title, chat_type, added_at) VALUES (%s, %s, %s, CURRENT_TIMESTAMP) ON CONFLICT (chat_id) DO UPDATE SET chat_title = EXCLUDED.chat_title, chat_type = EXCLUDED.chat_type, added_at = CURRENT_TIMESTAMP', (chat_id, chat_title, chat_type))
            conn.commit()
    return await asyncio.to_thread(_add)

async def get_all_chats() -> list:
    def _get():
        with get_db() as conn:
            cursor = conn.execute("SELECT chat_id FROM bot_chats")
            return [row['chat_id'] for row in cursor.fetchall()]
    return await asyncio.to_thread(_get)

# ==================== ЛОГИ ====================
def init_logs_db():
    with get_db() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS log_chats (id SERIAL PRIMARY KEY, chat_id BIGINT UNIQUE, added_by BIGINT, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
        conn.commit()

async def add_log_chat(chat_id: int, added_by: int) -> bool:
    def _add():
        with get_db() as conn:
            conn.execute("INSERT INTO log_chats (chat_id, added_by) VALUES (%s, %s) ON CONFLICT DO NOTHING", (chat_id, added_by))
            conn.commit()
            return True
    return await asyncio.to_thread(_add)

async def remove_log_chat(chat_id: int) -> bool:
    def _remove():
        with get_db() as conn:
            conn.execute("DELETE FROM log_chats WHERE chat_id = %s", (chat_id,))
            conn.commit()
            return True
    return await asyncio.to_thread(_remove)

async def get_log_chats() -> list:
    def _get():
        with get_db() as conn:
            cursor = conn.execute("SELECT chat_id FROM log_chats")
            return [row['chat_id'] for row in cursor.fetchall()]
    return await asyncio.to_thread(_get)

# ==================== КЕЙСЫ ====================
def init_cases_db():
    with get_db() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS user_cases (id SERIAL PRIMARY KEY, user_id BIGINT NOT NULL, case_type TEXT NOT NULL, quantity INTEGER DEFAULT 1, UNIQUE(user_id, case_type))')
        conn.execute('CREATE TABLE IF NOT EXISTS daily_bonus (user_id BIGINT PRIMARY KEY, last_claim TIMESTAMP, streak INTEGER DEFAULT 0)')
        conn.commit()

async def add_user_case(user_id: int, case_type: str, quantity: int = 1) -> bool:
    def _add():
        with get_db() as conn:
            conn.execute('INSERT INTO user_cases (user_id, case_type, quantity) VALUES (%s, %s, %s) ON CONFLICT(user_id, case_type) DO UPDATE SET quantity = user_cases.quantity + %s', (user_id, case_type, quantity, quantity))
            conn.commit()
            return True
    return await asyncio.to_thread(_add)

async def get_user_cases(user_id: int) -> list:
    def _get():
        with get_db() as conn:
            return conn.execute('SELECT case_type, quantity FROM user_cases WHERE user_id = %s AND quantity > 0 ORDER BY case_type', (user_id,)).fetchall()
    return await asyncio.to_thread(_get)

async def remove_user_case(user_id: int, case_type: str, quantity: int = 1) -> bool:
    def _remove():
        with get_db() as conn:
            conn.execute('UPDATE user_cases SET quantity = quantity - %s WHERE user_id = %s AND case_type = %s AND quantity >= %s', (quantity, user_id, case_type, quantity))
            conn.commit()
            conn.execute('DELETE FROM user_cases WHERE user_id = %s AND case_type = %s AND quantity <= 0', (user_id, case_type))
            conn.commit()
            return True
    return await asyncio.to_thread(_remove)

async def can_claim_daily(user_id: int) -> tuple:
    def _check():
        with get_db() as conn:
            result = conn.execute('SELECT last_claim, streak FROM daily_bonus WHERE user_id = %s', (user_id,)).fetchone()
            if not result:
                return True, 0, 0, 0
            last_claim = result['last_claim']
            if isinstance(last_claim, str):
                try:
                    last_claim = datetime.strptime(last_claim, '%Y-%m-%d %H:%M:%S.%f')
                except ValueError:
                    last_claim = datetime.strptime(last_claim, '%Y-%m-%d %H:%M:%S')
            now = datetime.now()
            next_claim = last_claim + timedelta(hours=24)
            if now > next_claim:
                return True, result['streak'] + 1, 0, 0
            delta = next_claim - now
            return False, result['streak'], delta.seconds // 3600, (delta.seconds % 3600) // 60
    return await asyncio.to_thread(_check)

async def claim_daily_bonus(user_id: int) -> bool:
    def _claim():
        with get_db() as conn:
            now = datetime.now()
            conn.execute('INSERT INTO daily_bonus (user_id, last_claim, streak) VALUES (%s, %s, 1) ON CONFLICT(user_id) DO UPDATE SET last_claim = %s, streak = CASE WHEN EXTRACT(EPOCH FROM (%s - daily_bonus.last_claim)) / 86400 < 2 THEN daily_bonus.streak + 1 ELSE 1 END', (user_id, now, now, now))
            conn.commit()
            return True
    return await asyncio.to_thread(_claim)

# ==================== КЛЮЧИ ====================
def init_keys_db():
    with get_db() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS keys (id SERIAL PRIMARY KEY, key_code TEXT UNIQUE NOT NULL, status TEXT NOT NULL, channel_id BIGINT, channel_name TEXT, added_by BIGINT, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_checked TIMESTAMP)')
        conn.commit()

async def add_key(key_code: str, status: str, added_by: int, channel_id: int = None, channel_name: str = None) -> bool:
    def _add():
        with get_db() as conn:
            conn.execute('INSERT INTO keys (key_code, status, channel_id, channel_name, added_by) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (key_code) DO UPDATE SET status = EXCLUDED.status, channel_id = EXCLUDED.channel_id, channel_name = EXCLUDED.channel_name, added_by = EXCLUDED.added_by', (key_code, status, channel_id, channel_name, added_by))
            conn.commit()
            return True
    return await asyncio.to_thread(_add)

async def get_key(key_code: str) -> dict:
    def _get():
        with get_db() as conn:
            row = conn.execute('SELECT key_code, status, channel_id, channel_name, added_by, added_at FROM keys WHERE key_code = %s', (key_code,)).fetchone()
            return dict(row) if row else None
    return await asyncio.to_thread(_get)

async def update_key_status(key_code: str, status: str) -> bool:
    def _update():
        with get_db() as conn:
            conn.execute('UPDATE keys SET status = %s, last_checked = CURRENT_TIMESTAMP WHERE key_code = %s', (status, key_code))
            conn.commit()
            return True
    return await asyncio.to_thread(_update)

async def delete_key(key_code: str) -> bool:
    def _delete():
        with get_db() as conn:
            conn.execute("DELETE FROM keys WHERE key_code = %s", (key_code,))
            conn.commit()
            return True
    return await asyncio.to_thread(_delete)

async def get_all_keys() -> list:
    def _get():
        with get_db() as conn:
            return conn.execute("SELECT key_code, status, channel_name FROM keys ORDER BY added_at DESC").fetchall()
    return await asyncio.to_thread(_get)

# ==================== ТЕХНИЧЕСКИЕ РАБОТЫ ====================
def init_work_conditions_db():
    with get_db() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS work_conditions (id INTEGER PRIMARY KEY CHECK (id = 1), is_active BOOLEAN DEFAULT FALSE, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_by BIGINT)')
        cursor = conn.execute("SELECT id FROM work_conditions WHERE id = 1")
        if not cursor.fetchone():
            conn.execute("INSERT INTO work_conditions (id, is_active) VALUES (1, FALSE)")
        conn.commit()

async def get_work_conditions() -> bool:
    def _get():
        with get_db() as conn:
            cursor = conn.execute("SELECT is_active FROM work_conditions WHERE id = 1")
            result = cursor.fetchone()
            return bool(result['is_active']) if result else False
    return await asyncio.to_thread(_get)

async def set_work_conditions(is_active: bool, updated_by: int) -> bool:
    def _set():
        with get_db() as conn:
            conn.execute('UPDATE work_conditions SET is_active = %s, updated_at = CURRENT_TIMESTAMP, updated_by = %s WHERE id = 1', (is_active, updated_by))
            conn.commit()
            return True
    return await asyncio.to_thread(_set)

# ==================== ИГРОВЫЕ СЕССИИ ====================
def init_games_db():
    with get_db() as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS game_sessions (id SERIAL PRIMARY KEY, user_id BIGINT NOT NULL, game_type TEXT NOT NULL, bet BIGINT NOT NULL, data TEXT, status TEXT DEFAULT \'active\', start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (user_id) REFERENCES users (user_id))')
        try:
            conn.execute('CREATE INDEX IF NOT EXISTS idx_game_sessions_user ON game_sessions(user_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_game_sessions_status ON game_sessions(status)')
        except:
            conn.rollback()
        conn.commit()

async def save_game_session(user_id: int, game_type: str, bet: int, data: dict) -> int:
    def _save():
        with get_db() as conn:
            cursor = conn.execute('INSERT INTO game_sessions (user_id, game_type, bet, data) VALUES (%s, %s, %s, %s) RETURNING id', (user_id, game_type, bet, json.dumps(data)))
            conn.commit()
            row = cursor.fetchone()
            return row['id'] if row else None
    return await asyncio.to_thread(_save)

async def get_game_session(session_id: int) -> dict:
    def _get():
        with get_db() as conn:
            row = conn.execute('SELECT id, user_id, game_type, bet, data, status, start_time, last_activity FROM game_sessions WHERE id = %s', (session_id,)).fetchone()
            if row:
                return {
                    'id': row['id'],
                    'user_id': row['user_id'],
                    'game_type': row['game_type'],
                    'bet': row['bet'],
                    'data': json.loads(row['data']) if row['data'] else {},
                    'status': row['status'],
                    'start_time': row['start_time'],
                    'last_activity': row['last_activity']
                }
            return None
    return await asyncio.to_thread(_get)

async def update_game_session(session_id: int, data: dict = None, status: str = None):
    def _update():
        with get_db() as conn:
            updates, params = [], []
            if data is not None:
                updates.append("data = %s")
                params.append(json.dumps(data))
            if status is not None:
                updates.append("status = %s")
                params.append(status)
            updates.append("last_activity = CURRENT_TIMESTAMP")
            if updates:
                query = f"UPDATE game_sessions SET {', '.join(updates)} WHERE id = %s"
                params.append(session_id)
                conn.execute(query, params)
                conn.commit()
    return await asyncio.to_thread(_update)

async def delete_game_session(session_id: int):
    def _delete():
        with get_db() as conn:
            conn.execute("DELETE FROM game_sessions WHERE id = %s", (session_id,))
            conn.commit()
    return await asyncio.to_thread(_delete)

async def cleanup_expired_games():
    def _cleanup():
        with get_db() as conn:
            cutoff = (datetime.now() - timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')
            cursor = conn.execute('SELECT id, user_id, bet FROM game_sessions WHERE status = \'active\' AND last_activity < %s', (cutoff,))
            expired = cursor.fetchall()
            for session in expired:
                conn.execute("UPDATE users SET balance = balance + %s WHERE user_id = %s", (session['bet'], session['user_id']))
                conn.execute("UPDATE game_sessions SET status = 'expired' WHERE id = %s", (session['id'],))
            conn.commit()
            return len(expired)
    return await asyncio.to_thread(_cleanup)

# ==================== ИНИЦИАЛИЗАЦИЯ ====================
def init_db():
    with get_db() as conn:
        cur = conn.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='users'")
        columns = [row['column_name'] for row in cur.fetchall()]
        conn.execute('CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY, username TEXT, full_name TEXT, balance BIGINT DEFAULT 1000, msg_balance BIGINT DEFAULT 0, registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
        if 'total_win' not in columns:
            try: conn.execute('ALTER TABLE users ADD COLUMN total_win BIGINT DEFAULT 0')
            except: conn.rollback()
        if 'total_loss' not in columns:
            try: conn.execute('ALTER TABLE users ADD COLUMN total_loss BIGINT DEFAULT 0')
            except: conn.rollback()
        if 'games_played' not in columns:
            try: conn.execute('ALTER TABLE users ADD COLUMN games_played BIGINT DEFAULT 0')
            except: conn.rollback()
        if 'referred_by' not in columns:
            try: conn.execute('ALTER TABLE users ADD COLUMN referred_by BIGINT DEFAULT NULL')
            except: conn.rollback()
        if 'last_bonus' not in columns:
            try: conn.execute('ALTER TABLE users ADD COLUMN last_bonus TIMESTAMP DEFAULT NULL')
            except: conn.rollback()
        if 'last_slot' not in columns:
            try: conn.execute('ALTER TABLE users ADD COLUMN last_slot TIMESTAMP DEFAULT NULL')
            except: conn.rollback()
        conn.execute('CREATE TABLE IF NOT EXISTS bans (user_id BIGINT PRIMARY KEY, banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, banned_until TIMESTAMP, ban_days INTEGER, ban_reason TEXT, FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE)')
        conn.execute('CREATE TABLE IF NOT EXISTS games_history (id SERIAL PRIMARY KEY, user_id BIGINT, game_type TEXT, bet BIGINT, win_amount BIGINT DEFAULT 0, doors_count INTEGER DEFAULT 0, opened_levels INTEGER DEFAULT 0, multiplier REAL DEFAULT 0, result TEXT, game_hash TEXT UNIQUE, played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL)')
        conn.execute('CREATE TABLE IF NOT EXISTS referrals (id SERIAL PRIMARY KEY, referrer_id BIGINT, referral_id BIGINT UNIQUE, registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (referrer_id) REFERENCES users(user_id) ON DELETE CASCADE, FOREIGN KEY (referral_id) REFERENCES users(user_id) ON DELETE CASCADE)')
        conn.execute('CREATE TABLE IF NOT EXISTS checks (id SERIAL PRIMARY KEY, check_code TEXT UNIQUE, max_activations INTEGER, used_count INTEGER DEFAULT 0, amount BIGINT, claimed_by TEXT DEFAULT \'\', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
        conn.execute('CREATE TABLE IF NOT EXISTS promocodes (id SERIAL PRIMARY KEY, code TEXT UNIQUE NOT NULL, max_activations INTEGER NOT NULL, used_count INTEGER DEFAULT 0, reward_amount BIGINT NOT NULL, created_by BIGINT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
        conn.execute('CREATE TABLE IF NOT EXISTS promo_activations (id SERIAL PRIMARY KEY, promo_id INTEGER NOT NULL, user_id BIGINT NOT NULL, activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (promo_id) REFERENCES promocodes(id) ON DELETE CASCADE, FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE, UNIQUE(promo_id, user_id))')
        conn.execute('CREATE TABLE IF NOT EXISTS user_checks (id SERIAL PRIMARY KEY, check_code TEXT UNIQUE NOT NULL, creator_id BIGINT NOT NULL, check_number INTEGER NOT NULL, amount BIGINT NOT NULL, max_activations INTEGER NOT NULL, used_count INTEGER DEFAULT 0, total_amount BIGINT NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY (creator_id) REFERENCES users(user_id) ON DELETE CASCADE, UNIQUE(creator_id, check_number))')
        conn.execute('CREATE TABLE IF NOT EXISTS user_check_activations (id SERIAL PRIMARY KEY, check_id INTEGER NOT NULL, user_id BIGINT NOT NULL, activated_at TEXT NOT NULL, FOREIGN KEY (check_id) REFERENCES user_checks(id) ON DELETE CASCADE, FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE, UNIQUE(check_id, user_id))')
        conn.commit()
        try:
            conn.execute('CREATE INDEX IF NOT EXISTS idx_users_balance ON users(balance)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_history_user ON games_history(user_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_history_played ON games_history(played_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_history_hash ON games_history(game_hash)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_bans_until ON bans(banned_until)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_referrals_referral ON referrals(referral_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_checks_code ON checks(check_code)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_user_checks_code ON user_checks(check_code)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_user_checks_creator ON user_checks(creator_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_user_check_activations_user ON user_check_activations(user_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_promocodes_code ON promocodes(code)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_promo_activations_user ON promo_activations(user_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_promo_activations_promo ON promo_activations(promo_id)')
            conn.commit()
        except Exception as e:
            logger.warning(f"Index creation warning: {e}")
            conn.rollback()

# Инициализация всех БД
init_db()
init_investments_db()
init_events_db()
init_spring_event_db()
init_math_contest_db()
init_top_exclude_db()
init_bank_db()
init_coinfall_db()
init_dice_game_db()
init_rr_db()
init_promotion_db()
init_currency_db()
init_chats_db()
init_logs_db()
init_cases_db()
init_keys_db()
init_work_conditions_db()
init_games_db()
