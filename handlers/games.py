# handlers/games.py
import logging
import random
import time
import asyncio
import re
import secrets
import hashlib
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.error import RetryAfter
from database import *
from .common import (
    check_ban, check_subscription, send_subscription_prompt, safe_answer,
    format_amount, parse_bet_amount, parse_amount, LAST_CLICK_TIME,
    update_task_progress_for_game, MINES_SESSIONS, GOLD_SESSIONS,
    PYRAMID_SESSIONS, TOWER_SESSIONS, RR_SESSIONS, BOWLING_SESSIONS,
    KHB_GAMES, KHB_DUELS, COINFLIP_SESSIONS, DICE_SESSIONS,
    ROULETTE_SESSIONS, DARTS_SESSIONS, SPACESHIP_SESSIONS, CRASH_SESSIONS
)

# ==================== КОНСТАНТЫ ====================
FIELD_SIZE = 5
CELLS_TOTAL = FIELD_SIZE * FIELD_SIZE
COOLDOWN_SECONDS = 2
DICE_COOLDOWN_SECONDS = 2
TOWER_MAX_LEVEL = 8
DICE_MIN_BET = 1000
DICE_MAX_BET = 50000000
DICE_MAX_GAMES_PER_CHAT = 5
DICE_TIMEOUT = 30

# MINES_MULTIPLIERS
MINES_MULTIPLIERS = {
    1: [1.01, 1.05, 1.10, 1.15, 1.21, 1.27, 1.34, 1.41, 1.48, 1.56, 1.64, 1.72, 1.81, 1.90, 2.00, 2.10, 2.21, 2.32, 2.44, 2.56, 2.69, 2.82, 2.96, 3.11],
    2: [1.05, 1.15, 1.26, 1.39, 1.53, 1.68, 1.85, 2.04, 2.24, 2.46, 2.71, 2.98, 3.28, 3.61, 3.97, 4.37, 4.81, 5.29, 5.82, 6.40, 7.04, 7.74, 8.51, 9.36],
    3: [1.10, 1.26, 1.45, 1.68, 1.94, 2.24, 2.59, 3.00, 3.47, 4.01, 4.64, 5.37, 6.21, 7.19, 8.32, 9.63, 11.14, 12.89, 14.92, 17.26, 19.97, 23.11, 26.74, 30.94],
    4: [1.15, 1.39, 1.68, 2.04, 2.47, 3.00, 3.64, 4.41, 5.35, 6.49, 7.87, 9.55, 11.58, 14.05, 17.04, 20.67, 25.08, 30.42, 36.90, 44.76, 54.30, 65.86, 79.89, 96.91],
    5: [1.21, 1.53, 1.94, 2.47, 3.14, 3.99, 5.07, 6.45, 8.20, 10.43, 13.26, 16.86, 21.44, 27.26, 34.66, 44.07, 56.04, 71.25, 90.60, 115.20, 146.48, 186.25, 236.83, 301.13],
    6: [1.27, 1.68, 2.24, 3.00, 4.01, 5.37, 7.19, 9.63, 12.89, 17.26, 23.11, 30.94, 41.43, 55.47, 74.27, 99.44, 133.14, 178.25, 238.65, 319.54, 427.86, 572.90, 767.09, 1027.23],
    7: [1.34, 1.85, 2.59, 3.64, 5.07, 7.19, 10.14, 14.30, 20.16, 28.43, 40.09, 56.53, 79.71, 112.39, 158.47, 223.44, 315.05, 444.22, 626.35, 883.15, 1245.24, 1755.79, 2475.66, 3490.68],
    8: [1.41, 2.04, 3.00, 4.41, 6.45, 9.63, 14.30, 21.23, 31.53, 46.81, 69.51, 103.22, 153.28, 227.62, 338.01, 502.05, 745.54, 1107.13, 1644.09, 2441.48, 3625.60, 5384.02, 7995.27, 11875.97],
    9: [1.48, 2.24, 3.47, 5.35, 8.20, 12.89, 20.16, 31.53, 49.30, 77.09, 120.54, 188.50, 294.78, 460.96, 720.79, 1127.16, 1762.53, 2755.80, 4309.06, 6737.87, 10536.68, 16476.43, 25764.92, 40290.61],
    10: [1.56, 2.46, 4.01, 6.49, 10.43, 17.26, 28.43, 46.81, 77.09, 126.98, 209.16, 344.54, 567.58, 935.16, 1540.58, 2538.14, 4182.41, 6891.37, 11354.75, 18713.39, 30837.85, 50817.30, 83752.76, 138023.54],
    11: [1.64, 2.71, 4.64, 7.87, 13.26, 23.11, 40.09, 69.51, 120.54, 209.16, 362.96, 629.84, 1092.92, 1896.65, 3291.52, 5711.29, 9912.09, 17202.48, 29855.30, 51812.94, 89925.45, 156083.65, 270914.12, 470237.50],
    12: [1.72, 2.98, 5.37, 9.55, 16.86, 30.94, 56.53, 103.22, 188.50, 344.54, 629.84, 1151.42, 2104.74, 3848.21, 7036.92, 12866.51, 23523.78, 43010.65, 78633.93, 143760.30, 262847.19, 480602.90, 878753.30, 1606927.03],
    13: [1.81, 3.28, 6.21, 11.58, 21.44, 41.43, 79.71, 153.28, 294.78, 567.58, 1092.92, 2104.74, 4054.04, 7809.77, 15046.42, 28993.23, 55865.90, 107639.52, 207423.18, 399705.03, 770257.96, 1484327.39, 2860424.79, 5512050.09],
    14: [1.90, 3.61, 7.19, 14.05, 27.26, 55.47, 112.39, 227.62, 460.96, 935.16, 1896.65, 3848.21, 7809.77, 15853.83, 32183.27, 65359.00, 132747.77, 269624.96, 547694.09, 1112419.61, 2259659.93, 4591021.47, 9326665.43, 18951455.02],
    15: [2.00, 3.97, 8.32, 17.04, 34.66, 74.27, 158.47, 338.01, 720.79, 1540.58, 3291.52, 7036.92, 15046.42, 32183.27, 68867.00, 147375.38, 315383.31, 675118.64, 1445430.88, 3095160.06, 6629643.13, 14202577.85, 30428517.60, 65188602.66],
    16: [2.10, 4.37, 9.63, 20.67, 44.07, 99.44, 223.44, 502.05, 1127.16, 2538.14, 5711.29, 12866.51, 28993.23, 65359.00, 147375.38, 332466.48, 750041.10, 1692756.40, 3820902.92, 8625171.19, 19473471.68, 43970855.25, 99297221.48, 224289054.56],
    17: [2.21, 4.81, 11.14, 25.08, 56.04, 133.14, 315.05, 745.54, 1762.53, 4182.41, 9912.09, 23523.78, 55865.90, 132747.77, 315383.31, 750041.10, 1784225.89, 4246487.61, 10110660.51, 24075573.68, 57352079.83, 136637698.63, 325625670.90, 776236466.11],
    18: [2.32, 5.29, 12.89, 30.42, 71.25, 178.25, 444.22, 1107.13, 2755.80, 6891.37, 17202.48, 43010.65, 107639.52, 269624.96, 675118.64, 1692756.40, 4246487.61, 10656299.66, 26744415.88, 67155747.11, 168580757.63, 423458675.13, 1063573213.67, 2671994778.91],
    19: [2.44, 5.82, 14.92, 36.90, 90.60, 238.65, 626.35, 1644.09, 4309.06, 11354.75, 29855.30, 78633.93, 207423.18, 547694.09, 1445430.88, 3820902.92, 10110660.51, 26744415.88, 70821071.71, 187603603.76, 497068226.09, 1317328720.62, 3491413668.24, 9256314892.34],
    20: [2.56, 6.40, 17.26, 44.76, 115.20, 319.54, 883.15, 2441.48, 6737.87, 18713.39, 51812.94, 143760.30, 399705.03, 1112419.61, 3095160.06, 8625171.19, 24075573.68, 67155747.11, 187603603.76, 524566257.17, 1467951831.81, 4110694109.78, 11515005527.80, 32274850425.43],
    21: [2.69, 7.04, 19.97, 54.30, 146.48, 427.86, 1245.24, 3625.60, 10536.68, 30837.85, 89925.45, 262847.19, 770257.96, 2259659.93, 6629643.13, 19473471.68, 57352079.83, 168580757.63, 497068226.09, 1467951831.81, 4340857284.73, 12848341887.98, 38066713844.24, 112868252396.56],
    22: [2.82, 7.74, 23.11, 65.86, 186.25, 572.90, 1755.79, 5384.02, 16476.43, 50817.30, 156083.65, 480602.90, 1484327.39, 4591021.47, 14202577.85, 43970855.25, 136637698.63, 423458675.13, 1317328720.62, 4110694109.78, 12848341887.98, 40234197810.62, 126234672127.78, 396856782597.25],
    23: [2.96, 8.51, 26.74, 79.89, 236.83, 767.09, 2475.66, 7995.27, 25764.92, 83752.76, 270914.12, 878753.30, 2860424.79, 9326665.43, 30428517.60, 99297221.48, 325625670.90, 1063573213.67, 3491413668.24, 11515005527.80, 38066713844.24, 126234672127.78, 419897211577.99, 1401716350143.57],
    24: [3.11, 9.36, 30.94, 96.91, 301.13, 1027.23, 3490.68, 11875.97, 40290.61, 138023.54, 470237.50, 1606927.03, 5512050.09, 18951455.02, 65188602.66, 224289054.56, 776236466.11, 2671994778.91, 9256314892.34, 32274850425.43, 112868252396.56, 396856782597.25, 1401716350143.57, 4981605467192.89]
}

GOLD_MULTIPLIERS = [2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]

PYRAMID_EMOJIS = ["🚪", "🏚", "🛖", "🏠", "🏡", "🏢", "🏣", "🏤", "🏛️", "🏰", "🏯", "🕌"]
PYRAMID_MULTIPLIERS_3 = [1.31, 1.74, 2.32, 3.10, 4.13, 5.51, 7.34, 9.79, 13.05, 17.40, 23.20, 30.94]
PYRAMID_MULTIPLIERS_2 = [1.45, 2.10, 3.05, 4.42, 6.41, 9.29, 13.47, 19.53, 28.32, 41.06, 59.54, 86.33]
PYRAMID_MULTIPLIERS_1 = [1.62, 2.62, 4.24, 6.86, 11.11, 17.99, 29.14, 47.20, 76.46, 123.86, 200.65, 325.05]

TOWER_MULTIPLIERS = {
    1: [1.21, 1.52, 1.89, 2.37, 2.96, 3.70, 4.63, 5.78, 7.23],
    2: [1.62, 2.69, 4.49, 7.48, 12.47, 20.79, 34.65, 57.75, 96.25],
    3: [2.15, 4.62, 9.93, 21.35, 45.90, 98.69, 212.18, 456.19, 980.81],
    4: [2.86, 8.18, 23.39, 66.89, 191.30, 547.12, 1564.77, 4475.24, 12800.00]
}

RR_MULTIPLIERS = {1: 1.15, 2: 1.45, 3: 1.95, 4: 2.9, 5: 5.8}
RR_STEP_MULTIPLIERS = {
    1: [0, 0.7, 1.8, 3.2, 5.0, 7.5],
    2: [0, 0.6, 1.4, 2.4, 3.8, 5.8],
    3: [0, 0.5, 1.1, 1.9, 3.1],
    4: [0, 0.9, 1.9, 2.7],
    5: [0, 5.8]
}

BOWLING_MULTIPLIERS = {'strike': 3.5, 'miss': 3.2, 1: 2.9, 2: 2.9, 3: 2.9, 4: 2.9}
BOWLING_NUMBERS = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣"}
BOWLING_WORDS = {1: "кегля", 2: "кегли", 3: "кегли", 4: "кегли", 5: "кеглей"}

KHB_EMOJIS = {'камень': '🪨', 'ножницы': '✂️', 'бумага': '📃'}
KHB_WIN_MESSAGES = ["Победа! 🎉", "Вы выиграли! ✨", "Удача на вашей стороне! 🌟", "Непобедимый! 👑"]
KHB_LOSE_MESSAGES = ["В следующий раз повезёт! 🍀", "Проигрыш — тоже опыт 💪", "Попробуйте ещё раз! 🔄", "Удача отвернулась 😅"]
KHB_DRAW_MESSAGES = ["Ничья! 🤝", "Дружеская ничья! 🕊️", "В этот раз никто не уступил ⚖️"]

COINFLIP_MULTIPLIER = 1.97
COINFLIP_RESULTS = {'орел': 'орел 🦅', 'решка': 'решка 🪙'}

DARTS_MULTIPLIERS = {'miss': 4.8, 'red': 1.96, 'center': 3.8, 'white': 1.94}
DARTS_BETS = {'м': 'miss', 'мимо': 'miss', 'к': 'red', 'красное': 'red', 'ц': 'center', 'центр': 'center', 'б': 'white', 'белое': 'white'}
DARTS_RESULTS = {1: ('miss', 'мимо 😯'), 2: ('red', 'красное 🔴'), 3: ('white', 'белое ⚪'), 4: ('red', 'красное 🔴'), 5: ('white', 'белое ⚪'), 6: ('center', 'центр 🎯')}

SPACESHIP_MULTIPLIERS = {1: 1.3, 2: 1.7, 3: 2.3, 4: 2.6, 5: 3.6, 6: 4.2}

DICE_MULTIPLIERS = {'number': 5.8, 'even': 1.94, 'odd': 1.94, 'big': 1.94, 'small': 2.9, 'equal': 5.8}
DICE_NUMBERS = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣"}

FOOTBALL_WIN_QUOTES = ["Удача сегодня на вашей стороне!✨", "Оторвём частичку клевера!✨", "Удача — беспредельное счастье!✨", "Твоя удача — твое счастье!✨", "Удача – символ твоей жизни!✨", "Твоя удача — невероятна.✨"]
FOOTBALL_LOSE_QUOTES = ["Даже у королей бывает плохая раздача карт — Наполеон Б.", "Кто не рискует, тот иногда пьет дешевый коньяк — Михаил Крут", "Иногда проиграть — это просто способ сбросить лишний вес — Арнольд Шварц.", "Даже если ты проиграл, ты все равно в игре, просто теперь ты зритель — Джокер", "В этот раз фортуна просто перепутала адресата — Аноним.Г"]
BASKETBALL_WIN_QUOTES = ["Снайперская точность!🎯", "Трёхочковый в корзину!🏀", "Как Майкл Джордан в прайме!🔥", "Невозможное возможно!✨", "Чистое попадание!✅"]
BASKETBALL_LOSE_QUOTES = ["Мяч круглый, а удача квадратная — народная мудрость", "Даже Леброн иногда мажет — ничего страшного", "В следующий раз обязательно забросишь!💪", "Промах — это тоже опыт", "Фортуна сегодня взяла тайм-аут"]

ROULETTE_COLORS = {
    0: "🟢", 1: "🔴", 2: "⚫", 3: "🔴", 4: "⚫", 5: "🔴", 6: "⚫", 7: "🔴", 8: "⚫", 9: "🔴", 10: "⚫",
    11: "⚫", 12: "🔴", 13: "⚫", 14: "🔴", 15: "⚫", 16: "🔴", 17: "⚫", 18: "🔴", 19: "🔴", 20: "⚫",
    21: "🔴", 22: "⚫", 23: "🔴", 24: "⚫", 25: "🔴", 26: "⚫", 27: "🔴", 28: "⚫", 29: "⚫", 30: "🔴",
    31: "⚫", 32: "🔴", 33: "⚫", 34: "🔴", 35: "⚫", 36: "🔴"
}
ROULETTE_MULTIPLIERS = {'red': 2, 'black': 2, 'even': 2, 'odd': 2, 'high': 2, 'low': 2, '1-12': 3, '13-24': 3, '25-36': 3, 'number': 36}
ROULETTE_BETS = {
    'к': 'red', 'красное': 'red', 'ч': 'black', 'черное': 'black',
    'чет': 'even', 'четное': 'even', 'неч': 'odd', 'нечетное': 'odd',
    'бол': 'high', 'большие': 'high', 'мал': 'low', 'малые': 'low',
    '1-12': '1-12', '13-24': '13-24', '25-36': '25-36'
}

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def check_cooldown(user_id: int, last_click: dict, cooldown_seconds: int) -> float:
    current_time = time.time()
    if user_id in last_click:
        if current_time - last_click[user_id] < cooldown_seconds:
            return round(cooldown_seconds - (current_time - last_click[user_id]), 1)
    last_click[user_id] = current_time
    return 0

async def handle_session_not_found(query):
    try:
        await query.answer("⚠️ Игровая сессия не найдена. Начните новую игру.", show_alert=True)
    except:
        pass
    try:
        await query.message.edit_reply_markup(reply_markup=None)
    except:
        pass

def generate_game_hash(game_data):
    data_string = json.dumps(game_data, sort_keys=True) + str(time.time()) + secrets.token_hex(8)
    return hashlib.sha256(data_string.encode()).hexdigest()[:16]

def generate_crash_multiplier() -> float:
    r = random.random() * 100
    if r < 50:
        return round(random.uniform(1.00, 1.99), 2)
    elif r < 80:
        return round(random.uniform(2.00, 3.99), 2)
    elif r < 95:
        return round(random.uniform(4.00, 6.99), 2)
    else:
        return round(random.uniform(7.00, 20.00), 2)

def parse_roulette_bet(bet_str: str):
    bet_str = bet_str.lower().strip()
    if bet_str.isdigit() and 0 <= int(bet_str) <= 36:
        return ('number', int(bet_str), ROULETTE_MULTIPLIERS['number'])
    if '-' in bet_str:
        parts = bet_str.split('-')
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            range_key = f"{parts[0]}-{parts[1]}"
            if range_key in ROULETTE_MULTIPLIERS:
                return (range_key, (int(parts[0]), int(parts[1])), ROULETTE_MULTIPLIERS[range_key])
    if bet_str in ROULETTE_BETS:
        return (ROULETTE_BETS[bet_str], None, ROULETTE_MULTIPLIERS[ROULETTE_BETS[bet_str]])
    return None

# ==================== MINES ====================
async def mines_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or await check_ban(update, context):
        return
    user = update.effective_user
    if user.id not in ADMIN_IDS and not await check_subscription(update, context, user.id):
        await send_subscription_prompt(update, context)
        return
    parts = update.message.text.strip().split()
    if len(parts) < 2:
        await update.message.reply_text(
            "<blockquote>ℹ️ Мины - это игра, в которой вам нужно угадывать пустые ячейки, чем больше откроете, тем больше будет множитель!</blockquote>\n\n"
            f"🤖 {user.full_name}, чтобы начать игру используй команду:\n\n"
            "💣 /mines [*ставка] [мины (1-24)]\n\n"
            "Примеры:\n- /mines 100 6\n- Мины 100",
            parse_mode='HTML'
        )
        return
    db_user = await get_user_async(user.id)
    bet_amount = parse_bet_amount(parts[1], db_user['balance'])
    mines_count = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() and 1 <= int(parts[2]) <= 24 else 1
    if bet_amount <= 0 or bet_amount > db_user['balance']:
        await update.message.reply_text(f"❌ Неверная сумма или недостаточно средств. Баланс: {format_amount(db_user['balance'])}ms¢")
        return
    await update_balance_async(user.id, -bet_amount)
    board = [['❓' for _ in range(FIELD_SIZE)] for _ in range(FIELD_SIZE)]
    cells = [(r, c) for r in range(FIELD_SIZE) for c in range(FIELD_SIZE)]
    mine_positions = random.sample(cells, mines_count)
    game_hash = generate_game_hash({'user_id': user.id, 'game': 'mines', 'bet': bet_amount, 'mines': mines_count, 'positions': [[r, c] for r, c in mine_positions]})
    MINES_SESSIONS[user.id] = {
        'board': board, 'mines': mine_positions, 'mines_count': mines_count, 'bet': bet_amount,
        'opened': 0, 'message_id': None, 'chat_id': update.effective_chat.id,
        'message_thread_id': update.effective_message.message_thread_id, 'status': 'active',
        'start_multiplier': MINES_MULTIPLIERS[mines_count][0], 'hash': game_hash, 'start_time': time.time()
    }
    await send_mines_board(update, context, user.id)

# ==================== GOLD ====================
async def gold_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or await check_ban(update, context):
        return
    user = update.effective_user
    if user.id not in ADMIN_IDS and not await check_subscription(update, context, user.id):
        await send_subscription_prompt(update, context)
        return
    parts = update.message.text.strip().split()
    if len(parts) < 2:
        await update.message.reply_text(
            "<blockquote>ℹ️ Золото — это игра, в которой необходимо угадать, где спрятано золото. Вам нужно открыть по одной ячейке на каждом уровне.</blockquote>\n\n"
            f"🤖 {user.full_name}, чтобы начать игру, используй команду:\n\n💰 /gold [ставка]\n\nПримеры:\n— /gold 100\n— золото 100",
            parse_mode='HTML'
        )
        return
    db_user = await get_user_async(user.id)
    bet_amount = parse_bet_amount(parts[1], db_user['balance'])
    if bet_amount <= 0 or bet_amount > db_user['balance']:
        await update.message.reply_text(f"❌ Неверная сумма или недостаточно средств. Баланс: {format_amount(db_user['balance'])}ms¢")
        return
    await update_balance_async(user.id, -bet_amount)
    mine_positions = [random.choice(['left', 'right']) for _ in range(12)]
    board = [['❓', '❓'] for _ in range(12)]
    game_hash = generate_game_hash({'user_id': user.id, 'game': 'gold', 'bet': bet_amount, 'mines': mine_positions})
    GOLD_SESSIONS[user.id] = {
        'board': board, 'mines': mine_positions, 'bet': bet_amount, 'opened': 0,
        'message_id': None, 'chat_id': update.effective_chat.id,
        'message_thread_id': update.effective_message.message_thread_id, 'status': 'active',
        'hash': game_hash, 'start_time': time.time()
    }
    await send_gold_board(update, context, user.id)

# ==================== PYRAMID ====================
async def pyramid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or await check_ban(update, context):
        return
    user = update.effective_user
    if user.id not in ADMIN_IDS and not await check_subscription(update, context, user.id):
        await send_subscription_prompt(update, context)
        return
    parts = update.message.text.strip().split()
    if len(parts) < 2:
        await update.message.reply_text(
            "<blockquote>ℹ️ Пирамида - это игра, где в каждом раунде перед вами 4 двери. Ваша задача выбрать одну из них и подниматься все выше: от заброшенной развалюхи до священной вершины.</blockquote>\n"
            "Дойдите до вершины и заберите максимальный выигрыш. Чем меньше дверей, тем выше выигрыш\n\n"
            f"🤖 {user.full_name}, чтобы начать игру, используйте команду:\n\n"
            "🏝️ /pyramid [ставка] [1-3]\n\n"
            "Примеры:\n– Пирамида 100\n– /pyramid 100 1",
            parse_mode='HTML'
        )
        return
    db_user = await get_user_async(user.id)
    bet_amount = parse_bet_amount(parts[1], db_user['balance'])
    doors_count = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() and 1 <= int(parts[2]) <= 3 else 3
    if bet_amount <= 0 or bet_amount > db_user['balance']:
        await update.message.reply_text(f"❌ Неверная сумма или недостаточно средств. Баланс: {format_amount(db_user['balance'])}ms¢")
        return
    await update_balance_async(user.id, -bet_amount)
    multipliers = PYRAMID_MULTIPLIERS_1 if doors_count == 1 else PYRAMID_MULTIPLIERS_2 if doors_count == 2 else PYRAMID_MULTIPLIERS_3
    grave_positions = [random.sample(range(4), 4 - doors_count) for _ in range(12)]
    game_hash = generate_game_hash({'user_id': user.id, 'game': 'pyramid', 'bet': bet_amount, 'doors': doors_count, 'grave_positions': grave_positions})
    PYRAMID_SESSIONS[user.id] = {
        'grave_positions': grave_positions, 'doors_count': doors_count, 'multipliers': multipliers,
        'bet': bet_amount, 'current_level': 0, 'message_id': None, 'chat_id': update.effective_chat.id,
        'message_thread_id': update.effective_message.message_thread_id, 'status': 'active',
        'hash': game_hash, 'opened_doors': [], 'start_time': time.time()
    }
    await send_pyramid_board(update, context, user.id)

# ==================== TOWER ====================
async def tower_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or await check_ban(update, context):
        return
    user = update.effective_user
    if user.id not in ADMIN_IDS and not await check_subscription(update, context, user.id):
        await send_subscription_prompt(update, context)
        return
    parts = update.message.text.strip().split()
    if len(parts) < 2:
        await update.message.reply_text(
            f"<blockquote>ℹ️ Башня – это игра, в которой нужно избежать мин и добраться до вершины.</blockquote>\n\n"
            f"🤖 <b>{user.full_name}</b>, чтобы начать игру, используй команду:\n\n"
            f"🗼 <code>/tower [ставка] [мины 1-4]</code>\n\n"
            f"<b>Примеры:</b>\n• <code>/tower 100</code> (1 мина)\n• <code>башня 100 3</code> (3 мины)",
            parse_mode='HTML'
        )
        return
    db_user = await get_user_async(user.id)
    bet_amount = parse_bet_amount(parts[1], db_user['balance'])
    mines_count = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() and 1 <= int(parts[2]) <= 4 else 1
    if bet_amount <= 0 or bet_amount > db_user['balance']:
        await update.message.reply_text(f"❌ Неверная сумма или недостаточно средств. Баланс: {format_amount(db_user['balance'])}ms¢")
        return
    await update_balance_async(user.id, -bet_amount)
    mine_positions = [random.sample(range(5), mines_count) for _ in range(TOWER_MAX_LEVEL)]
    board = [['ㅤ' for _ in range(5)] for _ in range(TOWER_MAX_LEVEL)]
    game_hash = generate_game_hash({'user_id': user.id, 'game': 'tower', 'bet': bet_amount, 'mines': mines_count})
    TOWER_SESSIONS[user.id] = {
        'board': board, 'mines': mine_positions, 'mines_count': mines_count, 'bet': bet_amount,
        'current_level': 0, 'message_id': None, 'chat_id': update.effective_chat.id,
        'message_thread_id': update.effective_message.message_thread_id, 'status': 'active',
        'hash': game_hash, 'start_time': time.time(), 'last_activity': time.time()
    }
    msg = await send_tower_start(update, context, user.id)
    if msg:
        TOWER_SESSIONS[user.id]['message_id'] = msg.message_id

# ==================== RR ====================
async def rr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or await check_ban(update, context):
        return
    user = update.effective_user
    if user.id not in ADMIN_IDS and not await check_subscription(update, context, user.id):
        await send_subscription_prompt(update, context)
        return
    parts = update.message.text.strip().split()
    if len(parts) < 2:
        await update.message.reply_text(
            f"<blockquote>ℹ️ Русская рулетка – это игра, в которой игрок использует револьвер с одним или пятью патронами, помещая его в барабан и вращая его.</blockquote>\n\n"
            f"🤖 <b>{user.full_name}</b>, чтобы начать игру, используй команду:\n\n"
            f"🔫 /buckshot [ставка]\n\nПример:\n/buckshot 100\nрр 100",
            parse_mode='HTML'
        )
        return
    bet_amount = parse_amount(parts[1])
    if bet_amount < 1000:
        await update.message.reply_text("❌ Минимальная ставка: 1.000ms¢")
        return
    db_user = await get_user_async(user.id)
    if db_user['balance'] < bet_amount:
        await update.message.reply_text(f"❌ Недостаточно средств. Баланс: {format_amount(db_user['balance'])}ms¢")
        return
    await update_balance_async(user.id, -bet_amount)
    await update.message.reply_text(
        f"🔫 Рус. рулетка • начни игру!\n••••••••••••••••\n💸 Ставка: {format_amount(bet_amount)}ms¢",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("1️⃣ пуля x1.15", callback_data=f"rr_bullets_{bet_amount}_1"),
             InlineKeyboardButton("2️⃣ пули x1.45", callback_data=f"rr_bullets_{bet_amount}_2")],
            [InlineKeyboardButton("3️⃣ пули x1.95", callback_data=f"rr_bullets_{bet_amount}_3"),
             InlineKeyboardButton("4️⃣ пули x2.9", callback_data=f"rr_bullets_{bet_amount}_4")],
            [InlineKeyboardButton("5️⃣ пуль x5.8", callback_data=f"rr_bullets_{bet_amount}_5"),
             InlineKeyboardButton("❌ Отменить", callback_data="rr_cancel")]
        ])
    )

# ==================== DICE ====================
async def dice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or await check_ban(update, context):
        return
    user = update.effective_user
    if user.id not in ADMIN_IDS and not await check_subscription(update, context, user.id):
        await send_subscription_prompt(update, context)
        return
    parts = update.message.text.strip().split()
    if len(parts) == 1:
        await show_dice_games(update, context)
        return
    max_players = int(parts[1]) if len(parts) == 3 and parts[1].isdigit() and 2 <= int(parts[1]) <= 10 else 2
    bet_amount = parse_amount(parts[-1])
    if bet_amount < DICE_MIN_BET or bet_amount > DICE_MAX_BET:
        await update.message.reply_text(f"❌ Ставка должна быть от {format_amount(DICE_MIN_BET)} до {format_amount(DICE_MAX_BET)}ms¢")
        return
    db_user = await get_user_async(user.id)
    if db_user['balance'] < bet_amount:
        await update.message.reply_text(f"❌ Недостаточно средств. Баланс: {format_amount(db_user['balance'])}ms¢")
        return
    games = await get_chat_dice_games_async(update.effective_chat.id, 'waiting')
    if len(games) >= DICE_MAX_GAMES_PER_CHAT:
        await update.message.reply_text(f"❌ В чате максимум {DICE_MAX_GAMES_PER_CHAT} активных игр.")
        return
    await update_balance_async(user.id, -bet_amount)
    game_number = await get_next_game_number_async(update.effective_chat.id)
    expires_at = (datetime.now() + timedelta(minutes=DICE_TIMEOUT)).strftime('%Y-%m-%d %H:%M:%S')
    text = f"🎲 Игра в кости #{game_number}.{update.effective_chat.id % 1000:03d}\n💰 Ставка: {format_amount(bet_amount)}ms¢\n\n👥 Мест: [1/{max_players}]\n✅ Игроки:\n[{user.full_name}](tg://user?id={user.id})\n\n⚠ До автоматической отмены игры: {DICE_TIMEOUT} мин. 0 сек."
    sent_msg = await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("Играть", callback_data=f"dice_join_{game_number}"),
         InlineKeyboardButton("Отмена", callback_data=f"dice_leave_{game_number}")]
    ]), parse_mode='Markdown')
    await create_dice_game_async(update.effective_chat.id, game_number, user.id, user.full_name, max_players, bet_amount, sent_msg.message_id)

# ==================== BOWLING ====================
async def bowling_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or await check_ban(update, context):
        return
    user = update.effective_user
    if user.id not in ADMIN_IDS and not await check_subscription(update, context, user.id):
        await send_subscription_prompt(update, context)
        return
    parts = update.message.text.strip().split()
    if len(parts) < 3:
        await update.message.reply_text(
            "<blockquote>ℹ️ Боулинг – это игра, в которой вам нужно сбить кегли, чтобы получить максимальный множитель</blockquote>\n\n"
            f"🤖 {user.full_name}, чтобы начать игру, используй команду:\n\n"
            "🎳 /bowling [кегель] [ставка]\n\n"
            "📊 Коэффициенты:\n• 1-4 кегли — x2.9\n• Страйк (5 кеглей) — x3.5\n• Мимо — x3.2\n\n"
            "Примеры:\n/bowling 2 100\nбо страйк 100\nбо мимо 100\nбо 5 100 (страйк)",
            parse_mode='HTML'
        )
        return
    pins_input = parts[1].lower()
    bet_amount = parse_amount(parts[2])
    if bet_amount <= 0:
        await update.message.reply_text("❌ Неверная сумма ставки.")
        return
    pins = 5 if pins_input in ['страйк', '5'] else 0 if pins_input == 'мимо' else int(pins_input) if pins_input.isdigit() and 1 <= int(pins_input) <= 4 else None
    if pins is None:
        await update.message.reply_text("❌ Количество кеглей должно быть от 1 до 4 (или 'страйк'/'мимо').")
        return
    db_user = await get_user_async(user.id)
    if db_user['balance'] < bet_amount:
        await update.message.reply_text(f"❌ Недостаточно средств. Баланс: {format_amount(db_user['balance'])}ms¢")
        return
    await update_balance_async(user.id, -bet_amount)
    msg = await context.bot.send_dice(chat_id=update.effective_chat.id, emoji='🎳', message_thread_id=update.effective_message.message_thread_id)
    result_pins = msg.dice.value if msg.dice.value != 6 else 5
    if pins == 5:
        multiplier = BOWLING_MULTIPLIERS['strike'] if result_pins == 5 else BOWLING_MULTIPLIERS[result_pins] if result_pins > 0 else BOWLING_MULTIPLIERS['miss']
    elif pins == 0:
        multiplier = BOWLING_MULTIPLIERS['miss'] if result_pins == 0 else BOWLING_MULTIPLIERS[result_pins] if result_pins > 0 else BOWLING_MULTIPLIERS['miss']
    else:
        multiplier = BOWLING_MULTIPLIERS[pins] if result_pins == pins else BOWLING_MULTIPLIERS['strike'] if result_pins == 5 else BOWLING_MULTIPLIERS['miss'] if result_pins == 0 else BOWLING_MULTIPLIERS[result_pins]
    win_amount = int(bet_amount * multiplier)
    is_win = (pins == 5 and result_pins == 5) or (pins == 0 and result_pins == 0) or (pins == result_pins)
    await asyncio.sleep(3.5)
    choice_display = "страйк" if pins == 5 else "мимо" if pins == 0 else f"{BOWLING_NUMBERS[pins]} {BOWLING_WORDS[pins]}"
    result_display = "страйк" if result_pins == 5 else "мимо" if result_pins == 0 else f"{BOWLING_NUMBERS[result_pins]} {BOWLING_WORDS[result_pins]}"
    if is_win:
        await update_balance_async(user.id, win_amount)
        await update_user_stats_async(user.id, win_amount, 0)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"*{user.full_name}*\n🎉 Боулинг - Победа!✅\n•••••••\n💸 Ставка: {format_amount(bet_amount)}ms¢\n🎲 Выбрано: {choice_display}\n💰 Выигрыш: x{multiplier} / {format_amount(win_amount)}ms¢\n••••••••\n⚡️ Итог: {result_display}", parse_mode='Markdown', message_thread_id=update.effective_message.message_thread_id)
    else:
        await update_user_stats_async(user.id, 0, bet_amount)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f" *{user.full_name}*\n😵‍💫 Боулинг - Проигрыш!\n•••••••••••\n💸 Ставка: {format_amount(bet_amount)}ms¢\n🎲 Выбрано: {choice_display}\n••••••\n⚡️ Итог: {result_display}", parse_mode='Markdown', message_thread_id=update.effective_message.message_thread_id)

# ==================== KNB ====================
async def knb_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or await check_ban(update, context):
        return
    user = update.effective_user
    if user.id not in ADMIN_IDS and not await check_subscription(update, context, user.id):
        await send_subscription_prompt(update, context)
        return
    parts = update.message.text.strip().split()
    if len(parts) == 1:
        await update.message.reply_text(
            "<blockquote>ℹ️ КНБ (Камень-Ножницы-Бумага) — популярная игра в которой вы должны поставить нужный знак под другой знак. Например вы ставите ножницы, а бот ставит бумагу и т.д.</blockquote>\n\n"
            f"🤖 {user.full_name}, чтобы начать игру используйте команду:\n\n"
            "🤖 /knb [ставка] — игра с ботом\n"
            "🤝 /knb *юзернейм* [ставка] — игра с другим пользователем\n\n"
            "Пример: /knb 1к\nПример: /knb @durov 100",
            parse_mode='HTML'
        )
        return
    db_user = await get_user_async(user.id)
    if len(parts) == 2:
        bet_amount = parse_bet_amount(parts[1], db_user['balance'])
        if bet_amount <= 0 or bet_amount > db_user['balance']:
            await update.message.reply_text(f"❌ Неверная сумма или недостаточно средств")
            return
        await knb_vs_bot(update, context, user, bet_amount)
    elif len(parts) >= 3:
        target = parts[1]
        bet_amount = parse_bet_amount(parts[2], db_user['balance'])
        if bet_amount <= 0:
            await update.message.reply_text("❌ Неверная сумма ставки.")
            return
        if target.startswith('@'):
            result = await get_user_by_username_async(target[1:])
            if not result:
                await update.message.reply_text(f"❌ Пользователь {target} не найден.")
                return
            target_id, target_name = result['user_id'], result['full_name'] or target[1:]
        else:
            await update.message.reply_text("❌ Укажите корректный юзернейм (например @durov)")
            return
        if target_id == user.id:
            await update.message.reply_text("❌ Нельзя вызвать на дуэль самого себя.")
            return
        await knb_challenge(update, context, user, target_id, target_name, bet_amount)

# ==================== COINFALL ====================
async def coinfall_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user:
        return
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS and user_id != MAIN_ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав на выполнение этой команды.")
        return
    parts = update.message.text.strip().split()
    if len(parts) < 3:
        await update.message.reply_text("❌ Использование: /coinfall *участников* *сумма*")
        return
    try:
        max_players = int(parts[1])
        if max_players < 2 or max_players > 20:
            await update.message.reply_text("❌ Количество участников должно быть от 2 до 20.")
            return
    except:
        await update.message.reply_text("❌ Неверный формат количества участников.")
        return
    prize = parse_amount(parts[2])
    if prize <= 0:
        await update.message.reply_text("❌ Неверная сумма.")
        return
    text = f"🪙 Монетопад запущен!\n\n💸 Приз – {format_amount(prize)}ms¢.\n\n👥 Участники: \n\nМонетопад начнется тогда, когда достигнется максимальное количество участников и администратор запустит.\nℹ️ Чтобы вступить нажми кнопку ниже."
    sent_msg = await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🥇 Участвовать", callback_data="coinfall_join")]]))
    game_id = await create_coinfall_async(prize, max_players, user_id, update.effective_chat.id, sent_msg.message_id)
    if 'coinfall_games' not in context.chat_data:
        context.chat_data['coinfall_games'] = {}
    context.chat_data['coinfall_games'][update.effective_chat.id] = game_id

# ==================== COINFLIP ====================
async def coinflip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or await check_ban(update, context):
        return
    user = update.effective_user
    if user.id not in ADMIN_IDS and not await check_subscription(update, context, user.id):
        await send_subscription_prompt(update, context)
        return
    parts = update.message.text.strip().split()
    if parts[0].lower() not in ['монетка', '/coinflip', 'мон']:
        return
    if len(parts) < 3:
        await update.message.reply_text(
            "<blockquote>ℹ️ Монетка – это игра в которой вы должны угадать исход упавшей монетки. Что будет орел или решка.</blockquote>\n\n"
            f"🤖 <b>{user.full_name}</b>, чтобы начать игру, используй команду:\n\n"
            "🪙 /coinflip [исход] [ставка]\n\nПример:\n/coinflip орел 100\nмонетка решка все",
            parse_mode='HTML'
        )
        return
    if parts[1].lower() not in ['орел', 'решка']:
        await update.message.reply_text("❌ Неверный исход. Доступные: орел, решка")
        return
    db_user = await get_user_async(user.id)
    bet_amount = parse_bet_amount(parts[2], db_user['balance'])
    if bet_amount <= 0 or bet_amount > db_user['balance']:
        await update.message.reply_text(f"❌ Неверная сумма или недостаточно средств. Баланс: {format_amount(db_user['balance'])}ms¢")
        return
    await update_balance_async(user.id, -bet_amount)
    coinflip_sessions = context.bot_data.setdefault('COINFLIP_SESSIONS', {})
    coinflip_sessions[user.id] = {'bet': bet_amount, 'choice': parts[1].lower(), 'user_name': user.full_name, 'chat_id': update.effective_chat.id, 'thread_id': update.effective_message.message_thread_id}
    await update.message.reply_text("Подбрасываю монетку..")
    coin_msg = await context.bot.send_message(chat_id=update.effective_chat.id, text="🪙", message_thread_id=update.effective_message.message_thread_id)
    asyncio.create_task(process_coinflip_result(context, user.id, coin_msg.message_id, coinflip_sessions[user.id]))

# ==================== DARTS ====================
async def darts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or await check_ban(update, context):
        return
    user = update.effective_user
    if user.id not in ADMIN_IDS and not await check_subscription(update, context, user.id):
        await send_subscription_prompt(update, context)
        return
    parts = update.message.text.strip().split()
    if parts[0].lower() not in ['дартс', '/darts', 'дс']:
        return
    if len(parts) < 3:
        await update.message.reply_text(
            "<blockquote>ℹ️ Дартс – это игра, в которой нужно попасть в центр мишени, чтобы получить максимальный множитель</blockquote>\n\n"
            f"🤖 *{user.full_name}*, чтобы начать игру, используй команду:\n\n"
            "🎯 /darts [ставка] [исход]\n\n<b>Пример:</b>\n/darts 100 ц\nдартс 100 мимо",
            parse_mode='HTML'
        )
        return
    if parts[2].lower() not in DARTS_BETS:
        await update.message.reply_text("❌ Неверный исход. Доступные: м/мимо, к/красное, ц/центр, б/белое")
        return
    db_user = await get_user_async(user.id)
    bet_amount = parse_bet_amount(parts[1], db_user['balance'])
    if bet_amount <= 0 or bet_amount > db_user['balance']:
        await update.message.reply_text(f"❌ Неверная сумма или недостаточно средств. Баланс: {format_amount(db_user['balance'])}ms¢")
        return
    await update_balance_async(user.id, -bet_amount)
    darts_sessions = context.bot_data.setdefault('DARTS_SESSIONS', {})
    darts_sessions[user.id] = {'bet': bet_amount, 'bet_type': DARTS_BETS[parts[2].lower()], 'bet_choice': parts[2].lower(), 'user_name': user.full_name, 'chat_id': update.effective_chat.id, 'thread_id': update.effective_message.message_thread_id}
    darts_msg = await context.bot.send_dice(chat_id=update.effective_chat.id, emoji='🎯', message_thread_id=update.effective_message.message_thread_id)
    asyncio.create_task(process_darts_result(context, user.id, darts_msg.message_id, darts_msg.dice.value, darts_sessions[user.id]))

# ==================== SPACESHIP ====================
async def spaceship_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or await check_ban(update, context):
        return
    user = update.effective_user
    if user.id not in ADMIN_IDS and not await check_subscription(update, context, user.id):
        await send_subscription_prompt(update, context)
        return
    parts = update.message.text.strip().split()
    if parts[0].lower() not in ['/spaceship', 'космолёт', 'космо', '/space']:
        return
    if len(parts) < 2:
        await update.message.reply_text(
            "<blockquote>ℹ️ Космолёт – игра в которой, вы — опасный контрабандист, за вами гонятся рейнджеры космоса чтобы забрать ваш товар, ваша задача облетать базы чужаков и сбежать от рейнджеров.</blockquote>\n\n"
            f"🤖 *{user.full_name}*, чтобы начать игру, используй команду:\n\n"
            "🛸 <b><i>/space [ставка]</i></b>\n\nПример:\n/space 100\nкосмо все",
            parse_mode='HTML'
        )
        return
    db_user = await get_user_async(user.id)
    bet_amount = parse_bet_amount(parts[1], db_user['balance'])
    if bet_amount <= 0 or bet_amount > db_user['balance']:
        await update.message.reply_text(f"❌ Неверная сумма или недостаточно средств. Баланс: {format_amount(db_user['balance'])}ms¢")
        return
    await update_balance_async(user.id, -bet_amount)
    grid = []
    for level in range(6):
        row = ['ㅤ', 'ㅤ', 'ㅤ']
        row[random.randint(0, 2)] = '👮'
        grid.append(row)
    spaceship_sessions = context.bot_data.setdefault('SPACESHIP_SESSIONS', {})
    spaceship_sessions[user.id] = {'bet': bet_amount, 'level': 0, 'grid': grid, 'opened': [], 'user_name': user.full_name, 'chat_id': update.effective_chat.id, 'thread_id': update.effective_message.message_thread_id, 'message_id': None, 'status': 'active'}
    await send_spaceship_board(update, context, user.id)

# ==================== CRASH ====================
async def crash_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or await check_ban(update, context):
        return
    user = update.effective_user
    if user.id not in ADMIN_IDS and not await check_subscription(update, context, user.id):
        await send_subscription_prompt(update, context)
        return
    parts = update.message.text.strip().split()
    if parts[0].lower() not in ['краш', '/crash', 'к']:
        return
    if len(parts) < 3:
        await update.message.reply_text(
            "<blockquote>ℹ️ Краш – это игра, в которой вам нужно выбрать множитель от x1.01 до x20.00. Бот случайным образом останавливается на значении от x1 до x20</blockquote>\n\n"
            f"🤖 <b>{user.full_name}</b>, чтобы начать игру, используй команду:\n\n"
            "📈 <b><u>/crash [ставка] [1.01-20.00]</u></b>\n\nПример:\n<code>/crash 100 1.1</code>\n<code>/краш 100 1.1</code>",
            parse_mode='HTML'
        )
        return
    try:
        db_user = await get_user_async(user.id)
        bet_amount = parse_bet_amount(parts[1], db_user['balance'])
        target_multiplier = float(parts[2].replace(',', '.'))
        if bet_amount <= 0 or target_multiplier < 1.01 or target_multiplier > 20.00 or db_user['balance'] < bet_amount:
            await update.message.reply_text("❌ Неверная сумма или множитель")
            return
        await update_balance_async(user.id, -bet_amount)
        crash_multiplier = generate_crash_multiplier()
        if crash_multiplier >= target_multiplier:
            win_amount = int(bet_amount * target_multiplier)
            await update_balance_async(user.id, win_amount)
            await update_user_stats_async(user.id, win_amount, 0)
            await update.message.reply_text(f"<blockquote><b><tg-emoji emoji-id='5283080528818360566'>🚀</tg-emoji> Ракета упала на x{crash_multiplier} <tg-emoji emoji-id='5244837092042750681'>📈</tg-emoji> </b>\n\n<tg-emoji emoji-id='5427009714745517609'>✅</tg-emoji> Ты выиграл! Твой выигрыш составил {format_amount(win_amount)}ms¢</blockquote>", parse_mode='HTML')
        else:
            await update_user_stats_async(user.id, 0, bet_amount)
            await update.message.reply_text(f"<blockquote><b><tg-emoji emoji-id='5283080528818360566'>🚀</tg-emoji> Ракета упала на x{crash_multiplier} <tg-emoji emoji-id='5246762912428603768'>📉</tg-emoji> </b>\n\n<tg-emoji emoji-id='5210952531676504517'>❌</tg-emoji> Ты проиграл {format_amount(bet_amount)}ms¢</blockquote>", parse_mode='HTML')
        await save_game_hash_async(generate_game_hash({'user_id': user.id, 'game': 'crash', 'bet': bet_amount, 'target': target_multiplier, 'result': crash_multiplier, 'win': crash_multiplier >= target_multiplier}), user.id, 'crash', bet_amount, 'win' if crash_multiplier >= target_multiplier else 'lose')
    except Exception as e:
        logging.error(f"crash error: {e}")

# ==================== ROULETTE ====================
async def roulette_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or await check_ban(update, context):
        return
    user = update.effective_user
    if user.id not in ADMIN_IDS and not await check_subscription(update, context, user.id):
        await send_subscription_prompt(update, context)
        return
    parts = update.message.text.strip().split()
    if len(parts) < 3:
        await update.message.reply_text(
            "<blockquote>ℹ️ Рулетка – это популярная игра, в которой вы должны угадать итог выпавшего значения</blockquote>\n\n"
            f"🤖 *{user.full_name}*, чтобы начать игру, используй команду:\n\n"
            "🎰 <i><u>/roulette [диапазон] [ставка]</u></i>\n\n"
            "<b>Доступные ставки и множители:</b>\n• красное (к) - x2\n• черное (ч) - x2\n• четное - x2\n• нечётное - x2\n• большие (19-36) - x2\n• малые (1-18) - x2\n• 1-12 - x3\n• 13-24 - x3\n• 25-36 - x3\n• число (0-36) - x36\n\n<b>Примеры:</b>\n/roulette к 10к\nрул 13-24 100к\nрул 7 1кк",
            parse_mode='HTML'
        )
        return
    bet_info = parse_roulette_bet(parts[1])
    if not bet_info:
        await update.message.reply_text("❌ Неверный диапазон. Проверьте список доступных ставок.")
        return
    bet_type, bet_value, multiplier = bet_info
    db_user = await get_user_async(user.id)
    bet_amount = parse_bet_amount(parts[2], db_user['balance'])
    if bet_amount <= 0 or bet_amount > db_user['balance']:
        await update.message.reply_text(f"❌ Неверная сумма или недостаточно средств. Баланс: {format_amount(db_user['balance'])}ms¢")
        return
    await update_balance_async(user.id, -bet_amount)
    roulette_sessions = context.bot_data.setdefault('ROULETTE_SESSIONS', {})
    roulette_sessions[user.id] = {'bet': bet_amount, 'bet_type': bet_type, 'bet_value': bet_value, 'multiplier': multiplier, 'user_name': user.full_name, 'chat_id': update.effective_chat.id, 'thread_id': update.effective_message.message_thread_id}
    roulette_msg = await context.bot.send_message(chat_id=update.effective_chat.id, text="<tg-emoji emoji-id='5416126611214846609'>🎰</tg-emoji>", parse_mode='HTML', message_thread_id=update.effective_message.message_thread_id)
    asyncio.create_task(process_roulette_result(context, user.id, roulette_msg.message_id, roulette_sessions[user.id]))

# ==================== CUBIC ====================
async def cubic_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or await check_ban(update, context):
        return
    user = update.effective_user
    if user.id not in ADMIN_IDS and not await check_subscription(update, context, user.id):
        await send_subscription_prompt(update, context)
        return
    parts = update.message.text.strip().split()
    if len(parts) < 2:
        await update.message.reply_text(
            "<blockquote>ℹ️ Кубик – это игра, в которой нужно угадать число на кубике или сделать ставку на то, будет ли оно чётным или нечетным, а также больше 3 или меньше 3.</blockquote>\n\n"
            f"🤖 <b>{user.full_name}</b>, чтобы начать игру, используй команду:\n\n"
            "<tg-emoji emoji-id='5350314303352223876'>🎲</tg-emoji> /dice [ставка]\n\nПример:\nКуб 100\n/dice 100",
            parse_mode='HTML'
        )
        return
    db_user = await get_user_async(user.id)
    bet_amount = parse_bet_amount(parts[1], db_user['balance'])
    if bet_amount <= 0 or bet_amount > db_user['balance']:
        await update.message.reply_text(f"❌ Неверная сумма или недостаточно средств. Баланс: {format_amount(db_user['balance'])}ms¢")
        return
    await update_balance_async(user.id, -bet_amount)
    dice_sessions = context.bot_data.setdefault('DICE_SESSIONS', {})
    dice_sessions[user.id] = {'bet': bet_amount, 'status': 'waiting', 'choice': None, 'choice_type': None, 'choice_display': None, 'multiplier': None, 'message_id': None, 'chat_id': update.effective_chat.id, 'thread_id': update.effective_message.message_thread_id, 'user_name': user.full_name}
    await send_dice_choice(update, context, user.id, user.full_name, bet_amount)

# ==================== FOOTBALL ====================
async def football_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or await check_ban(update, context):
        return
    user = update.effective_user
    if user.id not in ADMIN_IDS and not await check_subscription(update, context, user.id):
        await send_subscription_prompt(update, context)
        return
    parts = update.message.text.strip().split()
    if len(parts) < 3:
        await update.message.reply_text(
            "<blockquote>ℹ️ Футбол – игра в которой вы должны попасть в ворота!</blockquote>\n\n"
            f"🤖 {user.full_name}, используйте команду:\n\nПример: фб 10000 гол\nПример: фб 10000 мимо\n\nКоэффициенты:\n• Гол ✅ — x1.7\n• Мимо ❌ — x0.3",
            parse_mode='HTML'
        )
        return
    if parts[2].lower() not in ['гол', 'мимо']:
        await update.message.reply_text("❌ Итог должен быть 'гол' или 'мимо'")
        return
    db_user = await get_user_async(user.id)
    bet_amount = parse_bet_amount(parts[1], db_user['balance'])
    if bet_amount <= 0 or bet_amount > db_user['balance']:
        await update.message.reply_text(f"❌ Неверная сумма или недостаточно средств. Баланс: {format_amount(db_user['balance'])}ms¢")
        return
    await update_balance_async(user.id, -bet_amount)
    await update.message.reply_text("⚽ Пинаю мяч....")
    asyncio.create_task(process_football_game(update, context, user.id, bet_amount, parts[2].lower()))

# ==================== BASKETBALL ====================
async def basketball_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or await check_ban(update, context):
        return
    user = update.effective_user
    if user.id not in ADMIN_IDS and not await check_subscription(update, context, user.id):
        await send_subscription_prompt(update, context)
        return
    parts = update.message.text.strip().split()
    if len(parts) < 3:
        await update.message.reply_text(
            "<blockquote>ℹ️ Баскетбол – игра в которой вы должны забросить мяч в корзину!</blockquote>\n\n"
            f"🤖 {user.full_name}, используйте команду:\n\nПример: бк 10000 гол\nПример: бк 10000 мимо\n\nКоэффициенты:\n• Гол ✅ — x1.7\n• Мимо ❌ — x0.3",
            parse_mode='HTML'
        )
        return
    if parts[2].lower() not in ['гол', 'мимо']:
        await update.message.reply_text("❌ Итог должен быть 'гол' или 'мимо'")
        return
    db_user = await get_user_async(user.id)
    bet_amount = parse_bet_amount(parts[1], db_user['balance'])
    if bet_amount <= 0 or bet_amount > db_user['balance']:
        await update.message.reply_text(f"❌ Неверная сумма или недостаточно средств. Баланс: {format_amount(db_user['balance'])}ms¢")
        return
    await update_balance_async(user.id, -bet_amount)
    await update.message.reply_text("🏀 Бросаю мяч....")
    asyncio.create_task(process_basketball_game(update, context, user.id, bet_amount, parts[2].lower()))

# ==================== ОТПРАВКА ДОСОК ====================
async def send_mines_board(update, context, user_id):
    session = MINES_SESSIONS.get(user_id)
    if not session:
        return
    opened, mines_count = session['opened'], session['mines_count']
    max_opened = len(MINES_MULTIPLIERS[mines_count]) - 1
    current_multiplier = MINES_MULTIPLIERS[mines_count][min(opened, max_opened)]
    next_multiplier = MINES_MULTIPLIERS[mines_count][min(opened + 1, max_opened)]
    board_text = "\n".join(''.join(row) for row in session['board'])
    keyboard = [[InlineKeyboardButton("❓" if cell == '❓' else "💎" if cell == '💎' else cell, callback_data=f"mines_cell_{user_id}_{r}_{c}") for c, cell in enumerate(row)] for r, row in enumerate(session['board'])]
    if opened > 0:
        keyboard.append([InlineKeyboardButton("✔️ Забрать", callback_data=f"mines_take_{user_id}")])
    else:
        keyboard.append([InlineKeyboardButton("✔️ Забрать", callback_data=f"mines_take_{user_id}"), InlineKeyboardButton("❌ Отменить", callback_data=f"mines_cancel_{user_id}")])
    if session.get('message_id'):
        try:
            await context.bot.edit_message_text(
                f"☘️ Мины — начни игру!\n•••••••\n💣 Мин: {mines_count}\n💸 Ставка: {format_amount(session['bet'])}ms¢\n\nТекущий множитель: x{current_multiplier:.2f}.\n📈 Следующий множитель: x{next_multiplier:.2f}.\n{board_text}",
                chat_id=session['chat_id'], message_id=session['message_id'], reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except:
            msg = await context.bot.send_message(chat_id=session['chat_id'], text=f"☘️ Мины — начни игру!\n•••••••\n💣 Мин: {mines_count}\n💸 Ставка: {format_amount(session['bet'])}ms¢\n\nТекущий множитель: x{current_multiplier:.2f}.\n📈 Следующий множитель: x{next_multiplier:.2f}.\n{board_text}", reply_markup=InlineKeyboardMarkup(keyboard), message_thread_id=session['message_thread_id'])
            session['message_id'] = msg.message_id
    else:
        msg = await context.bot.send_message(chat_id=session['chat_id'], text=f"☘️ Мины — начни игру!\n•••••••\n💣 Мин: {mines_count}\n💸 Ставка: {format_amount(session['bet'])}ms¢\n\nТекущий множитель: x{current_multiplier:.2f}.\n📈 Следующий множитель: x{next_multiplier:.2f}.\n{board_text}", reply_markup=InlineKeyboardMarkup(keyboard), message_thread_id=session['message_thread_id'])
        session['message_id'] = msg.message_id

async def send_gold_board(update, context, user_id):
    session = GOLD_SESSIONS.get(user_id)
    if not session:
        return
    board_lines = [f"| {session['board'][i][0]} | {session['board'][i][1]} | {format_amount(int(session['bet'] * GOLD_MULTIPLIERS[i]))}ms¢ ({GOLD_MULTIPLIERS[i]}x)" for i in range(11, -1, -1)]
    if session['opened'] == 0:
        text = f"🌻 Золото - начни игру!\n••••••••••••••\n💸 Ставка: {format_amount(session['bet'])}ms¢\n\n{chr(10).join(board_lines)}"
    else:
        text = f"⚜️ Золото • игра идёт!\n••••••••••\n💸 Ставка: {format_amount(session['bet'])}ms¢\n\n💰 Выигрыш: x{GOLD_MULTIPLIERS[session['opened'] - 1]} / {format_amount(int(session['bet'] * GOLD_MULTIPLIERS[session['opened'] - 1]))}ms¢\n\n{chr(10).join(board_lines)}"
    keyboard = [[InlineKeyboardButton("❓", callback_data=f"gold_left_{user_id}"), InlineKeyboardButton("❓", callback_data=f"gold_right_{user_id}")]]
    if session['opened'] > 0:
        keyboard.append([InlineKeyboardButton("✅ Забрать выигрыш", callback_data=f"gold_take_{user_id}")])
    if session.get('message_id'):
        try:
            await context.bot.edit_message_text(text, chat_id=session['chat_id'], message_id=session['message_id'], reply_markup=InlineKeyboardMarkup(keyboard))
        except:
            msg = await context.bot.send_message(chat_id=session['chat_id'], text=text, reply_markup=InlineKeyboardMarkup(keyboard), message_thread_id=session['message_thread_id'])
            session['message_id'] = msg.message_id
    else:
        msg = await context.bot.send_message(chat_id=session['chat_id'], text=text, reply_markup=InlineKeyboardMarkup(keyboard), message_thread_id=session['message_thread_id'])
        session['message_id'] = msg.message_id

async def send_pyramid_board(update, context, user_id):
    session = PYRAMID_SESSIONS.get(user_id)
    if not session:
        return
    level, doors_count, multipliers, bet = session['current_level'], session['doors_count'], session['multipliers'], session['bet']
    current_emoji = PYRAMID_EMOJIS[level]
    current_multiplier, current_win = multipliers[level], int(bet * multipliers[level])
    if level == 0:
        text = f"🏃‍♂ Пирамида • начни путь!\n•••••••\n🚪 Двери: {doors_count}\n💸 Ставка: {format_amount(bet)}ms¢\n💰 Текущий множитель: x{current_multiplier:.2f} / {current_win}ms¢\n"
    else:
        text = f"🏃‍♂ Пирамида • игра идёт • уровень {level + 1}\n•••••••\n🚪 Двери: {doors_count}\n💸 Ставка: {format_amount(bet)}ms¢\n\n💰 Текущий множитель: x{current_multiplier:.2f} / {current_win}ms¢\n"
    suffix = random.randint(1000, 9999)
    keyboard = [
        [InlineKeyboardButton(current_emoji, callback_data=f"pyr_{user_id}_{level}_0_{suffix}"), InlineKeyboardButton(current_emoji, callback_data=f"pyr_{user_id}_{level}_1_{suffix}")],
        [InlineKeyboardButton(current_emoji, callback_data=f"pyr_{user_id}_{level}_2_{suffix}"), InlineKeyboardButton(current_emoji, callback_data=f"pyr_{user_id}_{level}_3_{suffix}")],
        [InlineKeyboardButton("✅ Забрать выигрыш" if level > 0 else "❌ Отменить", callback_data=f"take_{user_id}_{suffix}" if level > 0 else f"cancel_{user_id}_{suffix}")]
    ]
    if session.get('message_id'):
        try:
            await context.bot.edit_message_text(text, chat_id=session['chat_id'], message_id=session['message_id'], reply_markup=InlineKeyboardMarkup(keyboard))
        except:
            msg = await context.bot.send_message(chat_id=session['chat_id'], text=text, reply_markup=InlineKeyboardMarkup(keyboard), message_thread_id=session['message_thread_id'])
            session['message_id'] = msg.message_id
    else:
        msg = await context.bot.send_message(chat_id=session['chat_id'], text=text, reply_markup=InlineKeyboardMarkup(keyboard), message_thread_id=session['message_thread_id'])
        session['message_id'] = msg.message_id

async def send_tower_start(update, context, user_id):
    session = TOWER_SESSIONS.get(user_id)
    if not session:
        return None
    return await context.bot.send_message(
        chat_id=session['chat_id'],
        text=f"🍀 Башня • начни игру!\n•••••••••••••••\n💣 Мин: {session['mines_count']}\n💸 Ставка: {format_amount(session['bet'])}ms¢\n\nСледующий уровень: x{TOWER_MULTIPLIERS[session['mines_count']][1]:.2f}.\n",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ㅤ", callback_data=f"tower_cell_{user_id}_0_{col}") for col in range(5)] + [[InlineKeyboardButton("❌ Отменить", callback_data=f"tower_cancel_{user_id}")]]]),
        message_thread_id=session['message_thread_id']
    )

async def send_dice_choice(update, context, user_id, user_name, bet_amount):
    text = f"🎲 <b>{user_name}*</b>, выберите исход:\n\n<tg-emoji emoji-id='5472030678633684592'>💸</tg-emoji> Ставка: {format_amount(bet_amount)}ms¢"
    keyboard = [
        [InlineKeyboardButton("1️⃣", callback_data=f"dice_num_{user_id}_1"), InlineKeyboardButton("2️⃣", callback_data=f"dice_num_{user_id}_2"), InlineKeyboardButton("3️⃣", callback_data=f"dice_num_{user_id}_3")],
        [InlineKeyboardButton("4️⃣", callback_data=f"dice_num_{user_id}_4"), InlineKeyboardButton("5️⃣", callback_data=f"dice_num_{user_id}_5"), InlineKeyboardButton("6️⃣", callback_data=f"dice_num_{user_id}_6")],
        [InlineKeyboardButton("Большие", callback_data=f"dice_big_{user_id}"), InlineKeyboardButton("Равно (3)", callback_data=f"dice_equal_{user_id}"), InlineKeyboardButton("Малые", callback_data=f"dice_small_{user_id}")],
        [InlineKeyboardButton("Чётное", callback_data=f"dice_even_{user_id}"), InlineKeyboardButton("Нечётное", callback_data=f"dice_odd_{user_id}")],
        [InlineKeyboardButton("❌ Отменить", callback_data=f"dice_cancel_{user_id}")]
    ]
    msg = await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    dice_sessions = context.bot_data.get('DICE_SESSIONS', {})
    if user_id in dice_sessions:
        dice_sessions[user_id]['message_id'] = msg.message_id

async def send_spaceship_board(update, context, user_id):
    session = context.bot_data.get('SPACESHIP_SESSIONS', {}).get(user_id)
    if not session:
        return
    text = f"🛸 {session['user_name']}, вы начали погоню!\n💸 Ставка: {format_amount(session['bet'])}ms¢\n📊 Выигрыш: x0.0 / 0"
    keyboard = [[InlineKeyboardButton("ㅤ", callback_data=f"spaceship_cell_{user_id}_0_0"), InlineKeyboardButton("ㅤ", callback_data=f"spaceship_cell_{user_id}_0_1"), InlineKeyboardButton("ㅤ", callback_data=f"spaceship_cell_{user_id}_0_2")]]
    if session.get('message_id'):
        try:
            await context.bot.edit_message_text(text, chat_id=session['chat_id'], message_id=session['message_id'], reply_markup=InlineKeyboardMarkup(keyboard))
        except:
            msg = await context.bot.send_message(chat_id=session['chat_id'], text=text, reply_markup=InlineKeyboardMarkup(keyboard), message_thread_id=session['thread_id'])
            session['message_id'] = msg.message_id
    else:
        msg = await context.bot.send_message(chat_id=session['chat_id'], text=text, reply_markup=InlineKeyboardMarkup(keyboard), message_thread_id=session['thread_id'])
        session['message_id'] = msg.message_id

# ==================== ОБРАБОТКА РЕЗУЛЬТАТОВ ====================
async def process_coinflip_result(context, user_id, msg_id, session):
    await asyncio.sleep(2)
    result = random.choice(['орел', 'решка'])
    if result == session['choice']:
        win_amount = int(session['bet'] * COINFLIP_MULTIPLIER)
        await update_balance_async(user_id, win_amount)
        await update_user_stats_async(user_id, win_amount, 0)
        await context.bot.send_message(chat_id=session['chat_id'], text=f"🎊<b>Монета • Победа!<tg-emoji emoji-id='5427009714745517609'>✅</tg-emoji></b>\n•••••••••\n<tg-emoji emoji-id='5472030678633684592'>💸</tg-emoji>Ставка: {format_amount(session['bet'])}ms¢\n🎲 Выбрано: {COINFLIP_RESULTS[session['choice']]}\n📊 Выигрыш: x{COINFLIP_MULTIPLIER} / {format_amount(win_amount)}ms¢\n•••••••••\n<blockquote><tg-emoji emoji-id='5258203794772085854'>⚡️</tg-emoji>Выпало: {COINFLIP_RESULTS[result]}</blockquote>", parse_mode='HTML', message_thread_id=session.get('thread_id'), reply_to_message_id=msg_id)
    else:
        await update_user_stats_async(user_id, 0, session['bet'])
        await context.bot.send_message(chat_id=session['chat_id'], text=f"😣<b> Монета • Проигрыш!</b>\n••••••••••\n<tg-emoji emoji-id='5472030678633684592'>💸</tg-emoji>Ставка: {format_amount(session['bet'])}ms¢\n🎲 Выбрано: {COINFLIP_RESULTS[session['choice']]}\n•••••••••\n<blockquote><tg-emoji emoji-id='5258203794772085854'>⚡️</tg-emoji>Выпало: {COINFLIP_RESULTS[result]}</blockquote>", parse_mode='HTML', message_thread_id=session.get('thread_id'), reply_to_message_id=msg_id)
    del context.bot_data['COINFLIP_SESSIONS'][user_id]

async def process_darts_result(context, user_id, msg_id, dice_value, session):
    await asyncio.sleep(4.5)
    result_type, result_display = DARTS_RESULTS.get(dice_value, ('miss', 'мимо 😯'))
    is_win = (result_type == session['bet_type'])
    bet_amount, multiplier = session['bet'], DARTS_MULTIPLIERS.get(session['bet_type'], 1.0)
    choice_display = "центр 🎯" if session['bet_type'] == 'center' else "красное 🔴" if session['bet_type'] == 'red' else "белое ⚪" if session['bet_type'] == 'white' else "мимо 😯"
    if is_win:
        win_amount = int(bet_amount * multiplier)
        await update_balance_async(user_id, win_amount)
        await update_user_stats_async(user_id, win_amount, 0)
        await context.bot.send_message(chat_id=session['chat_id'], text=f"🎊 <b>Дартс • Победа! <tg-emoji emoji-id='5427009714745517609'>✅</tg-emoji></b>\n•••••••••••\n<tg-emoji emoji-id='5472030678633684592'>💸</tg-emoji> Ставка: {format_amount(bet_amount)}ms¢\n🎲 Выбрано: {choice_display}\n💰 Выигрыш: x{multiplier} / {format_amount(win_amount)}ms¢\n••••••••\n<blockquote><b><tg-emoji emoji-id='5258203794772085854'>⚡️</tg-emoji> Выпало:</b> {result_display}</blockquote>", parse_mode='HTML', message_thread_id=session.get('thread_id'), reply_to_message_id=msg_id)
    else:
        await update_user_stats_async(user_id, 0, bet_amount)
        await context.bot.send_message(chat_id=session['chat_id'], text=f"😣<b> Дартс • Проигрыш!</b>\n••••••••••••\n<tg-emoji emoji-id='5472030678633684592'>💸</tg-emoji> Ставка: {format_amount(bet_amount)}ms¢\n🎲 Выбрано: {choice_display}\n•••••••••\n<blockquote><b><tg-emoji emoji-id='5258203794772085854'>⚡️</tg-emoji> Выпало:</b> {result_display}</blockquote>", parse_mode='HTML', message_thread_id=session.get('thread_id'), reply_to_message_id=msg_id)
    del context.bot_data['DARTS_SESSIONS'][user_id]

async def process_roulette_result(context, user_id, msg_id, session):
    await asyncio.sleep(3)
    result = random.randint(0, 36)
    color = ROULETTE_COLORS.get(result, "⚫")
    bet_type, bet_value, multiplier, bet_amount = session['bet_type'], session['bet_value'], session['multiplier'], session['bet']
    win = (bet_type == 'red' and color == "🔴") or (bet_type == 'black' and color == "⚫") or (bet_type == 'even' and result != 0 and result % 2 == 0) or (bet_type == 'odd' and result != 0 and result % 2 == 1) or (bet_type == 'high' and 19 <= result <= 36) or (bet_type == 'low' and 1 <= result <= 18) or (bet_type == '1-12' and 1 <= result <= 12) or (bet_type == '13-24' and 13 <= result <= 24) or (bet_type == '25-36' and 25 <= result <= 36) or (bet_type == 'number' and result == bet_value)
    if win:
        win_amount = int(bet_amount * multiplier)
        await update_balance_async(user_id, win_amount)
        await update_user_stats_async(user_id, win_amount, 0)
        await context.bot.send_message(chat_id=session['chat_id'], text=f"<blockquote><tg-emoji emoji-id='5235989279024373566'>🎰</tg-emoji> Итоги игры «Рулетка»</blockquote>\n\n<b><tg-emoji emoji-id='5415683280395585071'>🎰</tg-emoji> Выпало: {result} {color}</b>\n\n<tg-emoji emoji-id='5415594207068822547'>🤑</tg-emoji> Выигрыш: x{multiplier} / {format_amount(win_amount)}ms¢", parse_mode='HTML', message_thread_id=session.get('thread_id'), reply_to_message_id=msg_id)
    else:
        await update_user_stats_async(user_id, 0, bet_amount)
        await context.bot.send_message(chat_id=session['chat_id'], text=f"<blockquote><tg-emoji emoji-id='5235989279024373566'>🎰</tg-emoji> Итоги игры «Рулетка»</blockquote>\n\n<b><tg-emoji emoji-id='5415683280395585071'>🎰</tg-emoji> Выпало: {result} {color}</b>\n\n<tg-emoji emoji-id='5373272140499918095'>😕</tg-emoji> Вы проиграли {format_amount(bet_amount)}ms¢!", parse_mode='HTML', message_thread_id=session.get('thread_id'), reply_to_message_id=msg_id)
    del context.bot_data['ROULETTE_SESSIONS'][user_id]

async def process_dice_result(context, user_id, msg_id, session, dice_value):
    await asyncio.sleep(4.5)
    win = (session['choice_type'] == 'number' and dice_value == session['choice']) or (session['choice_type'] == 'even' and dice_value % 2 == 0) or (session['choice_type'] == 'odd' and dice_value % 2 == 1) or (session['choice_type'] == 'big' and dice_value > 3) or (session['choice_type'] == 'small' and dice_value <= 3) or (session['choice_type'] == 'equal' and dice_value == 3)
    if win:
        win_amount = int(session['bet'] * session['multiplier'])
        await update_balance_async(user_id, win_amount)
        await update_user_stats_async(user_id, win_amount, 0)
        await context.bot.send_message(chat_id=session['chat_id'], text=f"🎉 <b>Кубик • Победа!</b><tg-emoji emoji-id='5427009714745517609'>✅</tg-emoji>\n•••••••••••••••\n<tg-emoji emoji-id='5472030678633684592'>💸</tg-emoji>Ставка: {format_amount(session['bet'])}ms¢\n<tg-emoji emoji-id='5350314303352223876'>🎲</tg-emoji>Выбрано: {session['choice_display']}\n💰 Выигрыш: x{session['multiplier']} / {format_amount(win_amount)}ms¢\n•••••••••\n<blockquote><tg-emoji emoji-id='5258203794772085854'>⚡️</tg-emoji> Выпало: {DICE_NUMBERS[dice_value]}</blockquote>", parse_mode='HTML', message_thread_id=session.get('thread_id'), reply_to_message_id=msg_id)
    else:
        await update_user_stats_async(user_id, 0, session['bet'])
        await context.bot.send_message(chat_id=session['chat_id'], text=f"🛑<b> Кубик • Проигрыш!</b>\n•••••••••••\n<tg-emoji emoji-id='5472030678633684592'>💸</tg-emoji>Ставка: {format_amount(session['bet'])}ms¢\n<tg-emoji emoji-id='5350314303352223876'>🎲</tg-emoji>Выбрано: {session['choice_display']}\n•••••••\n<blockquote><tg-emoji emoji-id='5258203794772085854'>⚡️</tg-emoji> Выпало: {DICE_NUMBERS[dice_value]}</blockquote>", parse_mode='HTML', message_thread_id=session.get('thread_id'), reply_to_message_id=msg_id)
    del context.bot_data['DICE_SESSIONS'][user_id]

async def process_football_game(update, context, user_id, bet_amount, user_choice):
    try:
        dice_msg = await update.message.reply_dice(emoji="⚽")
        await asyncio.sleep(4)
        actual_result = "гол" if dice_msg.dice.value in [3, 4, 5] else "мимо"
        if user_choice == actual_result:
            win_amount = int(bet_amount * 1.7)
            await update_balance_async(user_id, win_amount)
            await update_user_stats_async(user_id, win_amount, 0)
            await update_task_progress_for_game(user_id, 'football', 1)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"⚽ Игра \"Футбол\" окончена!\n\n☑ Итог — {'гол ✅' if actual_result == 'гол' else 'мимо ❌'}\n\n💸 Ставка: {format_amount(bet_amount)}ms¢\n💰 Выигрыш: {format_amount(win_amount)}ms¢\n\n{random.choice(FOOTBALL_WIN_QUOTES)}", reply_to_message_id=dice_msg.message_id)
        else:
            await update_user_stats_async(user_id, 0, bet_amount)
            await update_task_progress_for_game(user_id, 'football', 1)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"⚽ Игра \"Футбол\" окончена!\n\n☑ Итог — {'гол ✅' if actual_result == 'гол' else 'мимо ❌'}\n\n💸 Ставка: {format_amount(bet_amount)}ms¢\n\n{random.choice(FOOTBALL_LOSE_QUOTES)}", reply_to_message_id=dice_msg.message_id)
    except Exception as e:
        logging.error(f"football error: {e}")

async def process_basketball_game(update, context, user_id, bet_amount, user_choice):
    try:
        dice_msg = await update.message.reply_dice(emoji="🏀")
        await asyncio.sleep(3)
        actual_result = "гол" if dice_msg.dice.value >= 4 else "мимо"
        if user_choice == actual_result:
            win_amount = int(bet_amount * 1.7)
            await update_balance_async(user_id, win_amount)
            await update_user_stats_async(user_id, win_amount, 0)
            await update_task_progress_for_game(user_id, 'basketball', 1)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"🏀 Игра \"Баскетбол\" окончена!\n\n✔️ Итог – {'гол ✅' if actual_result == 'гол' else 'мимо ❌'}\n\n💸 Ставка: {format_amount(bet_amount)}ms¢\n💰 Выигрыш: {format_amount(win_amount)}ms¢ (x1.7)\n\n{random.choice(BASKETBALL_WIN_QUOTES)}", reply_to_message_id=dice_msg.message_id)
        else:
            win_amount = int(bet_amount * 0.3)
            await update_balance_async(user_id, win_amount)
            await update_user_stats_async(user_id, win_amount, 0)
            await update_task_progress_for_game(user_id, 'basketball', 1)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"🏀 Игра \"Баскетбол\" окончена!\n\n✔️ Итог – {'гол ✅' if actual_result == 'гол' else 'мимо ❌'}\n\n💸 Ставка: {format_amount(bet_amount)}ms¢\n💰 Выигрыш: {format_amount(win_amount)}ms¢ (x0.3)\n\n{random.choice(BASKETBALL_LOSE_QUOTES)}", reply_to_message_id=dice_msg.message_id)
    except Exception as e:
        logging.error(f"basketball error: {e}")

# ==================== KNB ВСПОМОГАТЕЛЬНЫЕ ====================
async def knb_vs_bot(update, context, user, bet_amount):
    await update_balance_async(user.id, -bet_amount)
    game_msg = await update.message.reply_text(f"🗿 {user.full_name}, игра начата! • Камень-Ножницы-Бумага\n•••••••••••\n🤖 Бот — *ждёт хода*\n👤 {user.full_name} — *ждёт хода*\n\n💸 Ставка: {format_amount(bet_amount)}ms¢.", parse_mode='Markdown')
    game_id = f"{user.id}_{int(time.time() * 1000)}"
    KHB_GAMES[game_id] = {'type': 'bot', 'user1_id': user.id, 'user1_name': user.full_name, 'user2_id': None, 'user2_name': 'Бот', 'bet': bet_amount, 'message_id': game_msg.message_id, 'chat_id': update.effective_chat.id, 'status': 'waiting_bot', 'user1_choice': None, 'user2_choice': None, 'bot_move_time': time.time() + 4.2, 'turn': None}
    keyboard = [[InlineKeyboardButton(f"Камень {KHB_EMOJIS['камень']}", callback_data=f"knb:choice:{game_id}:камень"), InlineKeyboardButton(f"Ножницы {KHB_EMOJIS['ножницы']}", callback_data=f"knb:choice:{game_id}:ножницы"), InlineKeyboardButton(f"Бумага {KHB_EMOJIS['бумага']}", callback_data=f"knb:choice:{game_id}:бумага")]]
    await context.bot.edit_message_text(chat_id=game_msg.chat_id, message_id=game_msg.message_id, text=f"🗿 {user.full_name}, игра начата! • Камень-Ножницы-Бумага\n•••••••••••\n🤖 Бот — *ждёт хода*\n👤 {user.full_name} — *ждёт хода*\n\n💸 Ставка: {format_amount(bet_amount)}ms¢.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    asyncio.create_task(knb_bot_move(context, game_id))

async def knb_bot_move(context, game_id):
    await asyncio.sleep(4.2)
    game = KHB_GAMES.get(game_id)
    if not game or game['status'] != 'waiting_bot':
        return
    game['user2_choice'] = random.choice(['камень', 'ножницы', 'бумага'])
    game['status'] = 'waiting_user'
    game['turn'] = game['user1_id']
    keyboard = [[InlineKeyboardButton(f"Камень {KHB_EMOJIS['камень']}", callback_data=f"knb:choice:{game_id}:камень"), InlineKeyboardButton(f"Ножницы {KHB_EMOJIS['ножницы']}", callback_data=f"knb:choice:{game_id}:ножницы"), InlineKeyboardButton(f"Бумага {KHB_EMOJIS['бумага']}", callback_data=f"knb:choice:{game_id}:бумага")]]
    try:
        await context.bot.edit_message_text(chat_id=game['chat_id'], message_id=game['message_id'], text=f"🗿 {game['user1_name']}, игра начата! • Камень-Ножницы-Бумага\n•••••••••••\n🤖 Бот — ♟️ Ход сделан\n👤 {game['user1_name']} — *ваш ход*\n\n💸 Ставка: {format_amount(game['bet'])}ms¢.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    except:
        pass

async def knb_challenge(update, context, user, target_id, target_name, bet_amount):
    if (await get_user_async(user.id))['balance'] < bet_amount:
        await update.message.reply_text(f"❌ Недостаточно средств.")
        return
    await update_balance_async(user.id, -bet_amount)
    for duel_id, duel in list(KHB_DUELS.items()):
        if duel['status'] == 'active' and (duel['challenger_id'] == user.id or duel['opponent_id'] == user.id):
            await update_balance_async(duel['challenger_id'], duel['bet'])
            del KHB_DUELS[duel_id]
    duel_id = f"{user.id}_{target_id}_{int(time.time())}"
    expire_time = time.time() + 300
    msg = await update.message.reply_text(f"🔫 {target_name}, вас вызвали на дуэль \"КНБ\"\nВызов от {user.full_name}\n\n🙈 Вызов - активен\n\n💸 Ставка: {format_amount(bet_amount)}ms¢.\n\n⏱ Вызов будет автоматически отозван через 5 минут.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Принять вызов", callback_data=f"knb_accept_{duel_id}")], [InlineKeyboardButton("❌ Отменить вызов", callback_data=f"knb_cancel_{duel_id}")]]))
    KHB_DUELS[duel_id] = {'challenger_id': user.id, 'challenger_name': user.full_name, 'opponent_id': target_id, 'opponent_name': target_name, 'bet': bet_amount, 'message_id': msg.message_id, 'chat_id': update.effective_chat.id, 'status': 'active', 'expire_time': expire_time}
    asyncio.create_task(knb_duel_expire(context, duel_id))

async def knb_duel_expire(context, duel_id):
    await asyncio.sleep(300)
    duel = KHB_DUELS.get(duel_id)
    if not duel or duel['status'] != 'active':
        return
    await update_balance_async(duel['challenger_id'], duel['bet'])
    duel['status'] = 'expired'
    try:
        await context.bot.edit_message_text(chat_id=duel['chat_id'], message_id=duel['message_id'], text=f"🔫 {duel['opponent_name']}, вас вызвали на дуэль \"КНБ\"\nВызов от {duel['challenger_name']}\n\n🙈 Вызов - неактивен\n\n💸 Ставка: {format_amount(duel['bet'])}ms¢.\n\n⏱ Вызов был автоматически отозван. Средства возвращены.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏱ Вызов отозван", callback_data="noop")]]))
    except:
        pass

# ==================== DICE GAME CALLBACKS ====================
async def show_dice_games(update, context):
    games = await get_chat_dice_games_async(update.effective_chat.id, 'waiting')
    if not games:
        await update.message.reply_text("🎲 Сейчас нет ставок.")
        return
    for game in games:
        players = await get_dice_game_players_async(game['game_id'])
        expires = datetime.strptime(game['expires_at'], '%Y-%m-%d %H:%M:%S')
        delta = expires - datetime.now()
        minutes, seconds = max(0, delta.seconds // 60), max(0, delta.seconds % 60)
        players_text = "\n".join(f"[{p['user_name']}](tg://user?id={p['user_id']})" for p in players)
        await update.message.reply_text(f"🎲 Игра в кости #{game['game_number']}.{update.effective_chat.id % 1000:03d}\n💰 Ставка: {format_amount(game['bet_amount'])}ms¢\n\n👥 Мест: [{len(players)}/{game['max_players']}]\n✅ Игроки:\n{players_text}\n\n⚠ До автоматической отмены игры: {minutes} мин. {seconds} сек.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Играть", callback_data=f"dice_join_{game['game_number']}"), InlineKeyboardButton("Отмена", callback_data=f"dice_leave_{game['game_number']}")]]), parse_mode='Markdown')

# ==================== CALLBACK HANDLERS ====================
async def handle_mines_callbacks(update, context, data, user_id):
    query = update.callback_query
    if data.startswith("mines_cell_"):
        parts = data.split('_')
        if len(parts) >= 5 and query.from_user.id == int(parts[2]):
            await mines_cell_click(update, context, int(parts[2]), int(parts[3]), int(parts[4]))
    elif data.startswith("mines_take_"):
        parts = data.split('_')
        if len(parts) >= 3 and query.from_user.id == int(parts[2]):
            await mines_take_win(update, context, int(parts[2]))
    elif data.startswith("mines_cancel_"):
        parts = data.split('_')
        if len(parts) >= 3 and query.from_user.id == int(parts[2]):
            await mines_cancel_game(update, context, int(parts[2]))

async def handle_gold_callbacks(update, context, data, user_id):
    query = update.callback_query
    if data.startswith("gold_left_"):
        parts = data.split('_')
        if len(parts) >= 3 and query.from_user.id == int(parts[2]):
            await gold_choice(update, context, int(parts[2]), 'left')
    elif data.startswith("gold_right_"):
        parts = data.split('_')
        if len(parts) >= 3 and query.from_user.id == int(parts[2]):
            await gold_choice(update, context, int(parts[2]), 'right')
    elif data.startswith("gold_take_"):
        parts = data.split('_')
        if len(parts) >= 3 and query.from_user.id == int(parts[2]):
            await gold_take_win(update, context, int(parts[2]))

async def handle_pyramid_callbacks(update, context, data, user_id):
    query = update.callback_query
    if data.startswith("pyr_"):
        parts = data.split('_')
        if len(parts) >= 5 and query.from_user.id == int(parts[1]):
            await pyramid_cell_click(update, context, int(parts[1]), int(parts[2]), int(parts[3]))
    elif data.startswith("take_"):
        parts = data.split('_')
        if len(parts) >= 2 and query.from_user.id == int(parts[1]):
            await pyramid_take_win(update, context, int(parts[1]))
    elif data.startswith("cancel_"):
        parts = data.split('_')
        if len(parts) >= 2 and query.from_user.id == int(parts[1]):
            await pyramid_cancel_game(update, context, int(parts[1]))

async def handle_tower_callbacks(update, context, data, user_id):
    query = update.callback_query
    if data.startswith("tower_cell_"):
        parts = data.split('_')
        if len(parts) >= 5 and query.from_user.id == int(parts[2]):
            await tower_cell_click(update, context, int(parts[2]), int(parts[3]), int(parts[4]))
    elif data.startswith("tower_take_"):
        parts = data.split('_')
        if len(parts) >= 3 and query.from_user.id == int(parts[2]):
            await tower_take_win(update, context, int(parts[2]))
    elif data.startswith("tower_cancel_"):
        parts = data.split('_')
        if len(parts) >= 3 and query.from_user.id == int(parts[2]):
            await tower_cancel_game(update, context, int(parts[2]))

async def handle_rr_callbacks(update, context, data, user_id):
    if data.startswith("rr_bullets_"):
        await rr_bullets_callback(update, context)
    elif data == "rr_cancel":
        await rr_cancel_callback(update, context)
    elif data.startswith("rr_cell_"):
        await rr_cell_callback(update, context)

async def handle_dice_callbacks(update, context, data, user_id):
    if data.startswith("dice_join_"):
        await dice_join_callback(update, context)
    elif data.startswith("dice_leave_"):
        await dice_leave_callback(update, context)

async def handle_coinfall_callbacks(update, context, data, user_id):
    if data == "coinfall_join":
        await coinfall_join_callback(update, context)
    elif data == "coinfall_start":
        await coinfall_start_callback(update, context)
    elif data.startswith("coinfall_claim_"):
        await coinfall_claim_callback(update, context)

async def handle_knb_callbacks(update, context, data, user_id):
    if data.startswith("knb:choice:"):
        parts = data.split(':')
        if len(parts) >= 4:
            await knb_choice_handler(update, context, parts[2], parts[3])
    elif data.startswith("knb:pvp:"):
        parts = data.split(':')
        if len(parts) >= 4:
            await knb_pvp_choice_handler(update, context, parts[2], parts[3])
    elif data.startswith("knb_accept_"):
        await knb_accept_duel(update, context, data.replace("knb_accept_", ""))
    elif data.startswith("knb_cancel_"):
        await knb_cancel_duel(update, context, data.replace("knb_cancel_", ""))

async def handle_dice_game_callbacks(update, context, data, user_id):
    if data.startswith("dice_num_"):
        parts = data.split('_')
        if len(parts) >= 4:
            await dice_choice_callback(update, context, int(parts[2]), 'num', parts[3])
    elif data.startswith("dice_even_"):
        await dice_choice_callback(update, context, int(data.split('_')[2]), 'even')
    elif data.startswith("dice_odd_"):
        await dice_choice_callback(update, context, int(data.split('_')[2]), 'odd')
    elif data.startswith("dice_big_"):
        await dice_choice_callback(update, context, int(data.split('_')[2]), 'big')
    elif data.startswith("dice_small_"):
        await dice_choice_callback(update, context, int(data.split('_')[2]), 'small')
    elif data.startswith("dice_equal_"):
        await dice_choice_callback(update, context, int(data.split('_')[2]), 'equal')
    elif data.startswith("dice_cancel_"):
        await dice_cancel_callback(update, context, int(data.split('_')[2]))

# ==================== MINES ВНУТРЕННИЕ ====================
async def mines_cell_click(update, context, user_id, r, c):
    query = update.callback_query
    if query.from_user.id != user_id:
        await safe_answer(query, "🙈 Это не ваша игра!")
        return
    cooldown = check_cooldown(user_id, LAST_CLICK_TIME, COOLDOWN_SECONDS)
    if cooldown > 0:
        await safe_answer(query, f"⏳ Подождите {cooldown} сек.")
        return
    session = MINES_SESSIONS.get(user_id)
    if not session or session['status'] != 'active':
        await handle_session_not_found(query)
        return
    if session['board'][r][c] != '❓':
        await safe_answer(query, "🧐 Уже открыто.")
        return
    if (r, c) in session['mines']:
        session['status'] = 'lost'
        session['board'][r][c] = '💥'
        for mr, mc in session['mines']:
            if session['board'][mr][mc] == '❓':
                session['board'][mr][mc] = '💥'
        opened = session['opened']
        current_multiplier = MINES_MULTIPLIERS[session['mines_count']][min(opened, len(MINES_MULTIPLIERS[session['mines_count']]) - 1)]
        await save_game_hash_async(session['hash'], user_id, 'mines', session['bet'], 'lose')
        await update_user_stats_async(user_id, 0, session['bet'])
        await update_task_progress_for_game(user_id, 'mines', 1)
        keyboard = [[InlineKeyboardButton('ㅤ' if cell == '❓' else cell, callback_data=f"mines_dead_{user_id}_{r}_{c}") for c, cell in enumerate(row)] for r, row in enumerate(session['board'])]
        await context.bot.edit_message_text(f"💥 Мины — проигрыш!\n••••••••••\n💣 Мин: {session['mines_count']}\n💸 Ставка: {format_amount(session['bet'])}ms¢\n\n💎 Открыто: {opened} из {CELLS_TOTAL - session['mines_count']}\n\n✔️ Ты мог забрать {int(session['bet'] * current_multiplier)}ms¢, но ничего страшного, повезет в следующий раз.\n\n👩‍💻 Hash: {session['hash']}", chat_id=session['chat_id'], message_id=session['message_id'], reply_markup=InlineKeyboardMarkup(keyboard))
        del MINES_SESSIONS[user_id]
        await safe_answer(query, "💥 Бомба!")
        return
    session['board'][r][c] = '💎'
    session['opened'] += 1
    await send_mines_board(update, context, user_id)
    await safe_answer(query, f"💎 +{MINES_MULTIPLIERS[session['mines_count']][min(session['opened'], len(MINES_MULTIPLIERS[session['mines_count']]) - 1)]:.2f}x")

async def mines_take_win(update, context, user_id):
    query = update.callback_query
    if query.from_user.id != user_id:
        await safe_answer(query, "🙈 Это не ваша игра!")
        return
    cooldown = check_cooldown(user_id, LAST_CLICK_TIME, COOLDOWN_SECONDS)
    if cooldown > 0:
        await safe_answer(query, f"⏳ Подождите {cooldown} сек.")
        return
    session = MINES_SESSIONS.get(user_id)
    if not session or session['status'] != 'active':
        await handle_session_not_found(query)
        return
    if session['opened'] == 0:
        await safe_answer(query, "⚠️ Сначала откройте хотя бы одну ячейку.")
        return
    session['status'] = 'won'
    opened = min(session['opened'], len(MINES_MULTIPLIERS[session['mines_count']]) - 1)
    win_amount = int(session['bet'] * MINES_MULTIPLIERS[session['mines_count']][opened])
    await update_balance_async(user_id, win_amount)
    for mr, mc in session['mines']:
        if session['board'][mr][mc] == '❓':
            session['board'][mr][mc] = '💣'
    await save_game_hash_async(session['hash'], user_id, 'mines', session['bet'], 'win')
    await update_user_stats_async(user_id, win_amount, 0)
    await update_task_progress_for_game(user_id, 'mines', 1)
    keyboard = [[InlineKeyboardButton('ㅤ' if cell == '❓' else cell, callback_data=f"mines_dead_{user_id}_{r}_{c}") for c, cell in enumerate(row)] for r, row in enumerate(session['board'])]
    await context.bot.edit_message_text(f"🎉 Мины — Победа! ✅\n💣 Мин: {session['mines_count']}\n💸 Ставка: {format_amount(session['bet'])}ms¢\n\n💎 Открыто: {session['opened']} из {CELLS_TOTAL - session['mines_count']}\n\nЗабранный выигрыш {win_amount}ms¢ успешно пополнен на баланс.\n\n👩‍💻 Hash: {session['hash']}", chat_id=session['chat_id'], message_id=session['message_id'], reply_markup=InlineKeyboardMarkup(keyboard))
    del MINES_SESSIONS[user_id]
    await safe_answer(query, f"Выигрыш {win_amount}ms¢")

async def mines_cancel_game(update, context, user_id):
    query = update.callback_query
    if query.from_user.id != user_id:
        await safe_answer(query, "🙈 Это не ваша игра!")
        return
    cooldown = check_cooldown(user_id, LAST_CLICK_TIME, COOLDOWN_SECONDS)
    if cooldown > 0:
        await safe_answer(query, f"⏳ Подождите {cooldown} сек.")
        return
    session = MINES_SESSIONS.get(user_id)
    if not session:
        await handle_session_not_found(query)
        return
    if session['opened'] > 0:
        await safe_answer(query, "⚠️ Нельзя отменить игру после первого хода.")
        return
    await update_balance_async(user_id, session['bet'])
    try:
        await context.bot.delete_message(chat_id=session['chat_id'], message_id=session['message_id'])
    except:
        pass
    del MINES_SESSIONS[user_id]
    await safe_answer(query, "Игра отменена, средства возвращены")

# ==================== GOLD ВНУТРЕННИЕ ====================
async def gold_choice(update, context, user_id, side):
    query = update.callback_query
    if query.from_user.id != user_id:
        await safe_answer(query, "🙈 Это не ваша игра!")
        return
    cooldown = check_cooldown(user_id, LAST_CLICK_TIME, COOLDOWN_SECONDS)
    if cooldown > 0:
        await safe_answer(query, f"⏳ Подождите {cooldown} сек.")
        return
    session = GOLD_SESSIONS.get(user_id)
    if not session or session['status'] != 'active':
        await handle_session_not_found(query)
        return
    current_level = session['opened']
    if current_level >= 12:
        await safe_answer(query, "⚠️ Вы уже прошли все уровни!")
        return
    if session['board'][current_level][0] != '❓' or session['board'][current_level][1] != '❓':
        await safe_answer(query, "🧐 Этот уровень уже открыт!")
        return
    if side == session['mines'][current_level]:
        session['board'][current_level][0 if side == 'left' else 1] = '💰'
        session['board'][current_level][1 if side == 'left' else 0] = '🧨'
        session['opened'] += 1
        await send_gold_board(update, context, user_id)
        if session['opened'] >= 12:
            await gold_take_win(update, context, user_id)
        else:
            await safe_answer(query, "💰 +1 уровень!")
    else:
        session['status'] = 'lost'
        session['board'][current_level][0 if side == 'left' else 1] = '💥'
        for level in range(12):
            if session['board'][level][0] == '❓' and session['board'][level][1] == '❓':
                correct = session['mines'][level]
                session['board'][level][0] = '💸' if correct == 'right' else '🧨'
                session['board'][level][1] = '💸' if correct == 'left' else '🧨'
        await save_game_hash_async(session['hash'], user_id, 'gold', session['bet'], 'lose')
        await update_user_stats_async(user_id, 0, session['bet'])
        await update_task_progress_for_game(user_id, 'gold', 1)
        await context.bot.edit_message_text(f"💥 Золото • Проигрыш!\n••••••••\n💸 Ставка: {format_amount(session['bet'])}ms¢\n\n⚜️ Пройдено: {session['opened']} из 12\n\n👩‍💻 Hash: {session['hash']}", chat_id=session['chat_id'], message_id=session['message_id'], reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🧨", callback_data=f"gold_dead_{user_id}"), InlineKeyboardButton("🧨", callback_data=f"gold_dead_{user_id}")]]))
        del GOLD_SESSIONS[user_id]
        await safe_answer(query, "💥 Бомба!")

async def gold_take_win(update, context, user_id):
    query = update.callback_query
    if query.from_user.id != user_id:
        await safe_answer(query, "🙈 Это не ваша игра!")
        return
    cooldown = check_cooldown(user_id, LAST_CLICK_TIME, COOLDOWN_SECONDS)
    if cooldown > 0:
        await safe_answer(query, f"⏳ Подождите {cooldown} сек.")
        return
    session = GOLD_SESSIONS.get(user_id)
    if not session or session['status'] != 'active':
        await handle_session_not_found(query)
        return
    if session['opened'] == 0:
        await safe_answer(query, "⚠️ Сначала откройте хотя бы один уровень.")
        return
    session['status'] = 'won'
    win_amount = int(session['bet'] * GOLD_MULTIPLIERS[session['opened'] - 1])
    await update_balance_async(user_id, win_amount)
    for level in range(12):
        if session['board'][level][0] == '❓' and session['board'][level][1] == '❓':
            correct = session['mines'][level]
            session['board'][level][0] = '💸' if correct == 'right' else '🧨'
            session['board'][level][1] = '💸' if correct == 'left' else '🧨'
    await save_game_hash_async(session['hash'], user_id, 'gold', session['bet'], 'win')
    await update_user_stats_async(user_id, win_amount, 0)
    await update_task_progress_for_game(user_id, 'gold', 1)
    await context.bot.edit_message_text(f"🎉 Золото • Победа!\n••••••••\n💸 Ставка: {format_amount(session['bet'])}ms¢\n\n💰 Выигрыш: {format_amount(win_amount)}ms¢\n\n👩‍💻 Hash: {session['hash']}", chat_id=session['chat_id'], message_id=session['message_id'], reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💰", callback_data=f"gold_dead_{user_id}"), InlineKeyboardButton("💰", callback_data=f"gold_dead_{user_id}")]]))
    del GOLD_SESSIONS[user_id]
    await safe_answer(query, f"✅ Выигрыш {format_amount(win_amount)}ms¢")

# ==================== PYRAMID ВНУТРЕННИЕ ====================
async def pyramid_cell_click(update, context, user_id, level, door):
    query = update.callback_query
    if query.from_user.id != user_id:
        await safe_answer(query, "🙈 Это не ваша игра!")
        return
    cooldown = check_cooldown(user_id, LAST_CLICK_TIME, COOLDOWN_SECONDS)
    if cooldown > 0:
        await safe_answer(query, f"⏳ Подождите {cooldown} сек.")
        return
    session = PYRAMID_SESSIONS.get(user_id)
    if not session or session['status'] != 'active':
        await handle_session_not_found(query)
        return
    if session['current_level'] != level:
        await safe_answer(query, "🧐 Не тот уровень!")
        return
    if session['current_level'] >= 12:
        await safe_answer(query, "⚠️ Вы уже прошли все уровни!")
        return
    if (level, door) in session.get('opened_doors', []):
        await safe_answer(query, "🧐 Эта дверь уже открыта!")
        return
    if door in session['grave_positions'][level]:
        session['status'] = 'lost'
        final_board = ['🪦' if i in session['grave_positions'][level] else '⭐' for i in range(4)]
        message_text = f"😱 Пирамида • Проигрыш!\n•••••••••••\n🚪 Двери: {session['doors_count']}\n💸 Ставка: {format_amount(session['bet'])}ms¢\n🔝 Пройдено: {level} из 12\n\n"
        if level > 0:
            message_text += f"✔️ Мог забрать x{session['multipliers'][level - 1]:.2f} / {int(session['bet'] * session['multipliers'][level - 1])}ms¢\n\n"
        message_text += f"{final_board[0]}{final_board[1]}\n{final_board[2]}{final_board[3]}\n\n👩‍💻 Hash: {session['hash']}"
        await save_game_hash_async(session['hash'], user_id, 'pyramid', session['bet'], 'lose')
        await update_user_stats_async(user_id, 0, session['bet'])
        await update_task_progress_for_game(user_id, 'pyramid', 1)
        await context.bot.edit_message_text(message_text, chat_id=session['chat_id'], message_id=session['message_id'], reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(final_board[0], callback_data=f"dead_{user_id}"), InlineKeyboardButton(final_board[1], callback_data=f"dead_{user_id}")], [InlineKeyboardButton(final_board[2], callback_data=f"dead_{user_id}"), InlineKeyboardButton(final_board[3], callback_data=f"dead_{user_id}")]]))
        del PYRAMID_SESSIONS[user_id]
        await safe_answer(query, "💥 Могила!")
        return
    session.setdefault('opened_doors', []).append((level, door))
    session['current_level'] += 1
    if session['current_level'] >= 12:
        await pyramid_take_win(update, context, user_id)
    else:
        await send_pyramid_board(update, context, user_id)
    await safe_answer(query, f"✅ Уровень {level + 1} пройден!")

async def pyramid_take_win(update, context, user_id):
    query = update.callback_query
    if query.from_user.id != user_id:
        await safe_answer(query, "🙈 Это не ваша игра!")
        return
    cooldown = check_cooldown(user_id, LAST_CLICK_TIME, COOLDOWN_SECONDS)
    if cooldown > 0:
        await safe_answer(query, f"⏳ Подождите {cooldown} сек.")
        return
    session = PYRAMID_SESSIONS.get(user_id)
    if not session or session['status'] != 'active':
        await handle_session_not_found(query)
        return
    if session['current_level'] == 0:
        await safe_answer(query, "⚠️ Сначала откройте хотя бы один уровень.")
        return
    session['status'] = 'won'
    level = session['current_level'] - 1
    win_amount = int(session['bet'] * session['multipliers'][level])
    await update_balance_async(user_id, win_amount)
    final_board = ['🪦' if i in session['grave_positions'][level] else '⭐' for i in range(4)]
    await save_game_hash_async(session['hash'], user_id, 'pyramid', session['bet'], 'win')
    await update_user_stats_async(user_id, win_amount, 0)
    await update_task_progress_for_game(user_id, 'pyramid', 1)
    await context.bot.edit_message_text(f"🥳 Пирамида • Победа!✅\n•••••••••••\n🚪 Двери: {session['doors_count']}\n💸 Ставка: {format_amount(session['bet'])}ms¢\n🔝 Пройдено: {session['current_level']} из 12\n\n💰 Выигрыш x{session['multipliers'][level]:.2f} / {win_amount}ms¢\n\n{final_board[0]}{final_board[1]}\n{final_board[2]}{final_board[3]}\n\n👩‍💻 Hash: {session['hash']}", chat_id=session['chat_id'], message_id=session['message_id'], reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(final_board[0], callback_data=f"dead_{user_id}"), InlineKeyboardButton(final_board[1], callback_data=f"dead_{user_id}")], [InlineKeyboardButton(final_board[2], callback_data=f"dead_{user_id}"), InlineKeyboardButton(final_board[3], callback_data=f"dead_{user_id}")]]))
    del PYRAMID_SESSIONS[user_id]
    await safe_answer(query, f"✅ Выигрыш {win_amount}ms¢")

async def pyramid_cancel_game(update, context, user_id):
    query = update.callback_query
    if query.from_user.id != user_id:
        await safe_answer(query, "🙈 Это не ваша игра!")
        return
    cooldown = check_cooldown(user_id, LAST_CLICK_TIME, COOLDOWN_SECONDS)
    if cooldown > 0:
        await safe_answer(query, f"⏳ Подождите {cooldown} сек.")
        return
    session = PYRAMID_SESSIONS.get(user_id)
    if not session:
        await handle_session_not_found(query)
        return
    if session['current_level'] > 0:
        await safe_answer(query, "⚠️ Нельзя отменить игру после первого хода.")
        return
    await update_balance_async(user_id, session['bet'])
    try:
        await context.bot.delete_message(chat_id=session['chat_id'], message_id=session['message_id'])
    except:
        pass
    del PYRAMID_SESSIONS[user_id]
    await safe_answer(query, "✅ Игра отменена, средства возвращены")

# ==================== TOWER ВНУТРЕННИЕ ====================
async def tower_cell_click(update, context, user_id, level, col):
    query = update.callback_query
    if query.from_user.id != user_id:
        await safe_answer(query, "🙈 Это не ваша игра!")
        return
    cooldown = check_cooldown(user_id, LAST_CLICK_TIME, COOLDOWN_SECONDS)
    if cooldown > 0:
        await safe_answer(query, f"⏳ Подождите {cooldown} сек.")
        return
    session = TOWER_SESSIONS.get(user_id)
    if not session or not session.get('message_id'):
        await handle_session_not_found(query)
        return
    if session['status'] != 'active':
        await safe_answer(query, "🙈 Игра уже завершена")
        return
    if level != session['current_level']:
        await safe_answer(query, "🧐 Не тот уровень!")
        return
    session['last_activity'] = time.time()
    if session['board'][level][col] != 'ㅤ':
        await safe_answer(query, "🧐 Эта клетка уже открыта!")
        return
    if col in session['mines'][level]:
        session['board'][level][col] = '💥'
        session['status'] = 'lost'
        keyboard = []
        for lvl in range(level, -1, -1):
            row = []
            for c in range(5):
                cell = session['board'][lvl][c]
                row.append(InlineKeyboardButton('💎' if cell == '💎' else '💥' if cell == '💥' else '💣' if c in session['mines'][lvl] else '💼', callback_data=f"tower_dead_{user_id}"))
            keyboard.append(row)
        await save_game_hash_async(session['hash'], user_id, 'tower', session['bet'], 'lose')
        await update_user_stats_async(user_id, 0, session['bet'])
        await context.bot.edit_message_text(f"💥 Башня • проигрыш!\n•••••••••••\n💣 Мин: {session['mines_count']}\n💸 Ставка: {format_amount(session['bet'])}ms¢\n💼 Пройдено: {level} из {TOWER_MAX_LEVEL}\n\n👩‍💻 Hash: {session['hash']}", chat_id=session['chat_id'], message_id=session['message_id'], reply_markup=InlineKeyboardMarkup(keyboard))
        del TOWER_SESSIONS[user_id]
        await safe_answer(query, "💥 Бомба!")
        return
    session['board'][level][col] = '💎'
    if level + 1 >= TOWER_MAX_LEVEL:
        session['status'] = 'won'
        win_amount = int(session['bet'] * TOWER_MULTIPLIERS[session['mines_count']][level])
        await update_balance_async(user_id, win_amount)
        await save_game_hash_async(session['hash'], user_id, 'tower', session['bet'], 'win')
        await update_user_stats_async(user_id, win_amount, 0)
        keyboard = []
        for lvl in range(level, -1, -1):
            row = []
            for c in range(5):
                cell = session['board'][lvl][c]
                row.append(InlineKeyboardButton('💎' if cell == '💎' else '💣' if c in session['mines'][lvl] else '💼', callback_data=f"tower_dead_{user_id}"))
            keyboard.append(row)
        await context.bot.edit_message_text(f"🎉 Башня – победа!✅\n••••••••••••••\n💣 Мин: {session['mines_count']}\n💸 Ставка: {format_amount(session['bet'])}ms¢\n> Вы прошли до конца!\n\n👩‍💻 Hash: {session['hash']}", chat_id=session['chat_id'], message_id=session['message_id'], reply_markup=InlineKeyboardMarkup(keyboard))
        del TOWER_SESSIONS[user_id]
        await safe_answer(query, f"🎉 Победа! +{format_amount(win_amount)}ms¢")
        return
    session['current_level'] += 1
    await update_tower_board(update, context, user_id)
    await safe_answer(query, f"Мины не оказалось.")

async def tower_take_win(update, context, user_id):
    query = update.callback_query
    if query.from_user.id != user_id:
        await safe_answer(query, "🙈 Это не ваша игра!")
        return
    cooldown = check_cooldown(user_id, LAST_CLICK_TIME, COOLDOWN_SECONDS)
    if cooldown > 0:
        await safe_answer(query, f"⏳ Подождите {cooldown} сек.")
        return
    session = TOWER_SESSIONS.get(user_id)
    if not session or not session.get('message_id'):
        await handle_session_not_found(query)
        return
    if session['status'] != 'active':
        await safe_answer(query, "🙈 Игра уже завершена")
        return
    if session['current_level'] == 0:
        await safe_answer(query, "⚠️ Сначала откройте хотя бы один уровень.")
        return
    session['status'] = 'won'
    win_amount = int(session['bet'] * TOWER_MULTIPLIERS[session['mines_count']][session['current_level'] - 1])
    await update_balance_async(user_id, win_amount)
    await save_game_hash_async(session['hash'], user_id, 'tower', session['bet'], 'win')
    await update_user_stats_async(user_id, win_amount, 0)
    keyboard = []
    for lvl in range(session['current_level'] - 1, -1, -1):
        row = []
        for c in range(5):
            cell = session['board'][lvl][c]
            row.append(InlineKeyboardButton('💎' if cell == '💎' else '💣' if c in session['mines'][lvl] else '💼', callback_data=f"tower_dead_{user_id}"))
        keyboard.append(row)
    await context.bot.edit_message_text(f"🎉 Башня – победа!✅\n••••••••••••••\n💣 Мин: {session['mines_count']}\n💸 Ставка: {format_amount(session['bet'])}ms¢\n> Вы забрали выигрыш!\n\n👩‍💻 Hash: {session['hash']}", chat_id=session['chat_id'], message_id=session['message_id'], reply_markup=InlineKeyboardMarkup(keyboard))
    del TOWER_SESSIONS[user_id]
    await safe_answer(query, f"Выигрыш {format_amount(win_amount)}ms¢")

async def tower_cancel_game(update, context, user_id):
    query = update.callback_query
    if query.from_user.id != user_id:
        await safe_answer(query, "🙈 Это не ваша игра!")
        return
    cooldown = check_cooldown(user_id, LAST_CLICK_TIME, COOLDOWN_SECONDS)
    if cooldown > 0:
        await safe_answer(query, f"⏳ Подождите {cooldown} сек.")
        return
    session = TOWER_SESSIONS.get(user_id)
    if not session or not session.get('message_id'):
        await handle_session_not_found(query)
        return
    if session['current_level'] > 0:
        await safe_answer(query, "⚠️ Нельзя отменить игру после первого хода.")
        return
    await update_balance_async(user_id, session['bet'])
    try:
        await context.bot.delete_message(chat_id=session['chat_id'], message_id=session['message_id'])
    except:
        pass
    del TOWER_SESSIONS[user_id]
    await safe_answer(query, " Игра отменена, средства возвращены")

async def update_tower_board(update, context, user_id):
    session = TOWER_SESSIONS.get(user_id)
    if not session:
        return
    level, mines_count, bet = session['current_level'], session['mines_count'], session['bet']
    multipliers = TOWER_MULTIPLIERS[mines_count]
    current_multiplier = multipliers[level - 1]
    next_multiplier = multipliers[level] if level < TOWER_MAX_LEVEL else current_multiplier
    keyboard = [[InlineKeyboardButton("ㅤ", callback_data=f"tower_cell_{user_id}_{level}_{col}") for col in range(5)]]
    for lvl in range(level - 1, -1, -1):
        row = []
        for col in range(5):
            cell = session['board'][lvl][col]
            row.append(InlineKeyboardButton('💎' if cell == '💎' else '💣' if cell in ['💣', '💥'] else "ㅤ", callback_data=f"tower_dead_{user_id}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("✅ Забрать награду", callback_data=f"tower_take_{user_id}")])
    await context.bot.edit_message_text(f"🗼 Башня • игра идёт.\n•••••••••••••••\n💣 Мин: {mines_count}\n💸 Ставка: {format_amount(bet)}ms¢\n📊 Выигрыш: x{current_multiplier:.2f} / {format_amount(int(bet * current_multiplier))}ms¢\n\nСледующий уровень: x{next_multiplier:.2f}.\n\n", chat_id=session['chat_id'], message_id=session['message_id'], reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== RR ВНУТРЕННИЕ ====================
async def rr_bullets_callback(update, context):
    query = update.callback_query
    parts = query.data.split('_')
    bet_amount = int(parts[2])
    bullets = int(parts[3])
    positions = [0] * 6
    for idx in random.sample(range(6), bullets):
        positions[idx] = 1
    game_id = await create_rr_game_async(query.from_user.id, bet_amount, bullets, RR_MULTIPLIERS[bullets], positions)
    keyboard = [[InlineKeyboardButton("ㅤ", callback_data=f"rr_cell_{game_id}_{i}"), InlineKeyboardButton("ㅤ", callback_data=f"rr_cell_{game_id}_{i+1}")] for i in range(0, 6, 2)]
    bullet_emoji = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"][bullets-1]
    sent_msg = await query.edit_message_text(f"🔫 Рус. рулетка • игра начата!\n••••••••••••••••\n💸 Ставка: {format_amount(bet_amount)}ms¢\n🔫 Пули: {bullet_emoji}\n📈 Коэффициент: x0", reply_markup=InlineKeyboardMarkup(keyboard))
    RR_SESSIONS[query.from_user.id] = {'game_id': game_id, 'message_id': sent_msg.message_id, 'chat_id': update.effective_chat.id, 'start_time': time.time()}

async def rr_cancel_callback(update, context):
    query = update.callback_query
    match = re.search(r'rr_bullets_(\d+)_', query.message.text)
    if match:
        await update_balance_async(query.from_user.id, int(match.group(1)))
    await query.message.delete()
    await safe_answer(query, "❌ Игра отменена")

async def rr_cell_callback(update, context):
    query = update.callback_query
    parts = query.data.split('_')
    if len(parts) < 4:
        return
    game_id = int(parts[2])
    cell_idx = int(parts[3])
    game = await get_rr_game_async(game_id)
    if not game or game['user_id'] != query.from_user.id or game['status'] != 'active' or cell_idx in game['opened']:
        await safe_answer(query, "❌ Игра не найдена или уже завершена", show_alert=True)
        return
    opened = game['opened'] + [cell_idx]
    await update_rr_game_async(game_id, opened)
    game = await get_rr_game_async(game_id)
    is_bullet = game['positions'][cell_idx] == 1
    bullets, opened_count = game['bullets'], len(game['opened'])
    current_multiplier = RR_STEP_MULTIPLIERS[bullets][opened_count]
    bullet_emoji = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"][bullets-1]
    keyboard = []
    for i in range(0, 6, 2):
        row = []
        for j in range(2):
            idx = i + j
            if idx in game['opened']:
                row.append(InlineKeyboardButton("💥" if game['positions'][idx] == 1 else "✅", callback_data="rr_dead"))
            else:
                row.append(InlineKeyboardButton("⬜", callback_data=f"rr_cell_{game_id}_{idx}"))
        keyboard.append(row)
    if is_bullet:
        await finish_rr_game_async(game_id, 'lost')
        await update_user_stats_async(query.from_user.id, 0, game['bet'])
        await query.edit_message_text(f"🔫 Русская рулетка • ПРОИГРЫШ! 💥\n••••••••••••••••\n💸 Ставка: {format_amount(game['bet'])}ms¢\n🔫 Пули: {bullet_emoji}\n📈 Открыто ячеек: {opened_count - 1}\n💔 Вы проиграли {format_amount(game['bet'])}ms¢", reply_markup=InlineKeyboardMarkup(keyboard))
        if query.from_user.id in RR_SESSIONS:
            del RR_SESSIONS[query.from_user.id]
    else:
        total_cells, bullets_count = 6, game['bullets']
        opened_safe = len([i for i in game['opened'] if game['positions'][i] == 0])
        if opened_safe == total_cells - bullets_count:
            await finish_rr_game_async(game_id, 'won')
            win_amount = int(game['bet'] * RR_STEP_MULTIPLIERS[bullets][opened_count])
            await update_balance_async(query.from_user.id, win_amount)
            await update_user_stats_async(query.from_user.id, win_amount, 0)
            dead_keyboard = [[InlineKeyboardButton("⬜", callback_data="rr_finished") for _ in range(2)] for __ in range(3)]
            await query.edit_message_text(f"🔫 Русская рулетка • ПОБЕДА! ✅\n••••••••••••••••\n💸 Ставка: {format_amount(game['bet'])}ms¢\n🔫 Пули: {bullet_emoji}\n📈 Коэффициент: x{RR_STEP_MULTIPLIERS[bullets][opened_count]:.2f}\n💰 Выигрыш: {format_amount(win_amount)}ms¢", reply_markup=InlineKeyboardMarkup(dead_keyboard))
            if query.from_user.id in RR_SESSIONS:
                del RR_SESSIONS[query.from_user.id]
        else:
            await query.edit_message_text(f"🔫 Русская рулетка • игра продолжается!\n••••••••••••••••\n💸 Ставка: {format_amount(game['bet'])}ms¢\n🔫 Пули: {bullet_emoji}\n📈 Текущий коэффициент: x{current_multiplier:.2f}\n✅ Безопасных ячеек осталось: {(total_cells - bullets_count) - opened_safe}", reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== DICE (кости) ВНУТРЕННИЕ ====================
async def dice_join_callback(update, context):
    query = update.callback_query
    user = query.from_user
    game_number = int(query.data.replace('dice_join_', ''))
    games = await get_chat_dice_games_async(update.effective_chat.id, 'waiting')
    game = next((g for g in games if g['game_number'] == game_number), None)
    if not game:
        await safe_answer(query, "❌ Игра не найдена", show_alert=True)
        return
    players = await get_dice_game_players_async(game['game_id'])
    if any(p['user_id'] == user.id for p in players):
        await safe_answer(query, "🎲 Вы уже играете.", show_alert=True)
        return
    if len(players) >= game['max_players']:
        await safe_answer(query, "❌ Мест больше нет", show_alert=True)
        return
    db_user = await get_user_async(user.id)
    if db_user['balance'] < game['bet_amount']:
        await safe_answer(query, f"❌ Недостаточно средств. Нужно {format_amount(game['bet_amount'])}ms¢", show_alert=True)
        return
    dice_cooldown[user.id] = time.time()
    await update_balance_async(user.id, -game['bet_amount'])
    await add_dice_player_async(game['game_id'], user.id, user.full_name)
    players = await get_dice_game_players_async(game['game_id'])
    expires = datetime.strptime(game['expires_at'], '%Y-%m-%d %H:%M:%S')
    delta = expires - datetime.now()
    minutes, seconds = max(0, delta.seconds // 60), max(0, delta.seconds % 60)
    players_text = "\n".join(f"[{p['user_name']}](tg://user?id={p['user_id']})" for p in players)
    text = f"🎲 Игра в кости #{game['game_number']}.{update.effective_chat.id % 1000:03d}\n💰 Ставка: {format_amount(game['bet_amount'])}ms¢\n\n👥 Мест: [{len(players)}/{game['max_players']}]\n✅ Игроки:\n{players_text}\n\n⚠ До автоматической отмены игры: {minutes} мин. {seconds} сек."
    if len(players) >= game['max_players']:
        await query.edit_message_text(text, parse_mode='Markdown')
        await start_dice_game(update, context, game['game_id'], update.effective_chat.id)
    else:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎲 Играть", callback_data=f"dice_join_{game_number}"), InlineKeyboardButton("❌ Отмена", callback_data=f"dice_leave_{game_number}")]]), parse_mode='Markdown')
    await safe_answer(query, "✅ Вы зашли в игру!")

async def dice_leave_callback(update, context):
    query = update.callback_query
    user = query.from_user
    game_number = int(query.data.replace('dice_leave_', ''))
    games = await get_chat_dice_games_async(update.effective_chat.id, 'waiting')
    game = next((g for g in games if g['game_number'] == game_number), None)
    if not game:
        await safe_answer(query, "❌ Игра не найдена", show_alert=True)
        return
    players = await get_dice_game_players_async(game['game_id'])
    if not any(p['user_id'] == user.id for p in players):
        await safe_answer(query, "🗿 Это не ваша игра!", show_alert=True)
        return
    dice_cooldown[user.id] = time.time()
    await update_balance_async(user.id, game['bet_amount'])
    remaining = await remove_dice_player_async(game['game_id'], user.id)
    if remaining == 0:
        await cancel_dice_game_async(game['game_id'])
        try:
            await query.message.delete()
        except:
            pass
        await safe_answer(query, "🎲 Вы успешно вышли из игры.")
        return
    players = await get_dice_game_players_async(game['game_id'])
    expires = datetime.strptime(game['expires_at'], '%Y-%m-%d %H:%M:%S')
    delta = expires - datetime.now()
    minutes, seconds = max(0, delta.seconds // 60), max(0, delta.seconds % 60)
    players_text = "\n".join(f"[{p['user_name']}](tg://user?id={p['user_id']})" for p in players)
    text = f"🎲 Игра в кости #{game['game_number']}.{update.effective_chat.id % 1000:03d}\n💰 Ставка: {format_amount(game['bet_amount'])}ms¢\n\n👥 Мест: [{remaining}/{game['max_players']}]\n✅ Игроки:\n{players_text}\n\n⚠ До автоматической отмены игры: {minutes} мин. {seconds} сек."
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Играть", callback_data=f"dice_join_{game_number}"), InlineKeyboardButton("Отмена", callback_data=f"dice_leave_{game_number}")]]), parse_mode='Markdown')
    await safe_answer(query, "🎲 Вы успешно вышли из игры.")

async def start_dice_game(update, context, game_id, chat_id):
    await start_dice_game_async(game_id)
    game = await get_dice_game_async(game_id)
    players = await get_dice_game_players_async(game_id)
    sorted_players = sorted(players, key=lambda x: x['dice_value'], reverse=True)
    top_value = sorted_players[0]['dice_value']
    winners = [p for p in sorted_players if p['dice_value'] == top_value]
    total_pot = game['bet_amount'] * len(players)
    if len(winners) == 1:
        win_amount = total_pot
        await update_balance_async(winners[0]['user_id'], win_amount)
        result_text = f"💰 Победитель: [{winners[0]['user_name']}](tg://user?id={winners[0]['user_id']}), он забирает весь банк {format_amount(win_amount)}ms¢."
    else:
        win_amount = total_pot // len(winners)
        for w in winners:
            await update_balance_async(w['user_id'], win_amount)
        result_text = f"💰 {', '.join(f'[{w['user_name']}](tg://user?id={w['user_id']})' for w in winners)} делят между собой весь банк. Каждый получает: {format_amount(win_amount)}ms¢"
    players_text = "\n".join(f"[{p['user_name']}](tg://user?id={p['user_id']}): {p['dice_value']}" for p in sorted_players)
    await context.bot.edit_message_text(f"🎲 Игра в кости #{game['game_number']}.{chat_id % 1000:03d}\n\n{players_text}\n{result_text}", chat_id=chat_id, message_id=game['message_id'], parse_mode='Markdown')
    await finish_dice_game_async(game_id, [w['user_id'] for w in winners])

# ==================== COINFALL ВНУТРЕННИЕ ====================
async def coinfall_join_callback(update, context):
    query = update.callback_query
    user = query.from_user
    game = await get_active_coinfall_async(update.effective_chat.id)
    if not game or game['status'] != 'waiting':
        await safe_answer(query, "❌ Монетопад не найден или уже начался", show_alert=True)
        return
    success, count = await add_coinfall_player_async(game['id'], user.id, user.full_name)
    if not success:
        await safe_answer(query, "❌ Вы уже участвуете", show_alert=True)
        return
    players = await get_coinfall_players_async(game['id'])
    players_text = "👥 Участники: " + ", ".join(p['user_name'] for p in players)
    text = f"🪙 Монетопад запущен!\n\n💸 Приз – {format_amount(game['prize'])}ms¢.\n\n{players_text}\n\n"
    if count >= game['max_players']:
        text += "✅ Набрано максимальное количество участников! Админ может запустить монетопад."
        keyboard = [[InlineKeyboardButton("🥇 Участвовать", callback_data="coinfall_join_disabled")], [InlineKeyboardButton("🪙 Запустить", callback_data="coinfall_start")]]
    else:
        text += "Монетопад начнется тогда, когда достигнется максимальное количество участников и администратор запустит.\nℹ️ Чтобы вступить нажми кнопку ниже."
        keyboard = [[InlineKeyboardButton("🥇 Участвовать", callback_data="coinfall_join")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    await safe_answer(query, f"✅ Вы стали участником монетопада!")

async def coinfall_start_callback(update, context):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS and query.from_user.id != MAIN_ADMIN_ID:
        await safe_answer(query, "❌ Вы не администратор.", show_alert=True)
        return
    game = await get_active_coinfall_async(update.effective_chat.id)
    if not game or game['status'] != 'waiting':
        await safe_answer(query, "❌ Монетопад не найден или уже начат", show_alert=True)
        return
    players = await get_coinfall_players_async(game['id'])
    if len(players) < game['max_players']:
        await safe_answer(query, f"❌ Нужно еще {game['max_players'] - len(players)} участников", show_alert=True)
        return
    await start_coinfall_async(game['id'])
    await query.edit_message_text("🎉 Разыгрываем....")
    await context.bot.send_message(chat_id=update.effective_chat.id, text="🪙")
    await asyncio.sleep(4)
    winner = random.choice(players)
    await finish_coinfall_async(game['id'], winner['user_id'], winner['user_name'])
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"🪙 Монетопад окончен!\n\nПобедитель — {winner['user_name']}.\n\nℹ️ {winner['user_name']}, чтобы забрать выигрыш нажми кнопку ниже.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"✅ Забрать {format_amount(game['prize'])}ms¢", callback_data=f"coinfall_claim_{game['id']}")]]))

async def coinfall_claim_callback(update, context):
    query = update.callback_query
    game_id = int(query.data.replace('coinfall_claim_', ''))
    game = await get_coinfall_async(game_id)
    if not game or game['status'] != 'finished' or game['claimed'] == 1 or game['winner_id'] != query.from_user.id:
        await safe_answer(query, "❌ Награда недоступна", show_alert=True)
        return
    success, prize = await claim_coinfall_async(game_id, query.from_user.id)
    if success:
        await update_balance_async(query.from_user.id, prize)
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f"✅ Получено", callback_data="coinfall_claimed")]]))
        await safe_answer(query, f"✅ Вы получили {format_amount(prize)}ms¢!", show_alert=True)

# ==================== KNB ВНУТРЕННИЕ ====================
async def knb_choice_handler(update, context, game_id, choice):
    query = update.callback_query
    game = KHB_GAMES.get(game_id)
    if not game or game['type'] != 'bot' or query.from_user.id != game['user1_id']:
        await safe_answer(query, "❌ Игра не найдена.", show_alert=True)
        return
    if game['status'] != 'waiting_user' or game['user1_choice'] is not None:
        await safe_answer(query, "❌ Игра уже завершена или не ваш ход.", show_alert=True)
        return
    game['user1_choice'] = choice
    if choice == game['user2_choice']:
        await update_balance_async(game['user1_id'], game['bet'])
        winner_text = "Ничья! 🤝"
        quote = random.choice(KHB_DRAW_MESSAGES)
    elif (choice == 'камень' and game['user2_choice'] == 'ножницы') or (choice == 'ножницы' and game['user2_choice'] == 'бумага') or (choice == 'бумага' and game['user2_choice'] == 'камень'):
        await update_balance_async(game['user1_id'], game['bet'] * 2)
        await update_user_stats_async(game['user1_id'], game['bet'] * 2, 0)
        winner_text = f"{game['user1_name']} победил! 🎉"
        quote = random.choice(KHB_WIN_MESSAGES)
    else:
        await update_user_stats_async(game['user1_id'], 0, game['bet'])
        winner_text = "Бот победил! 🤖"
        quote = random.choice(KHB_LOSE_MESSAGES)
    game['status'] = 'finished'
    await query.edit_message_text(f"⏱ {game['user1_name']}, игра окончена! • Камень-Ножницы-Бумага\n•••••••••••\n🤖 Бот — {KHB_EMOJIS[game['user2_choice']]}\n👤 {game['user1_name']} — {KHB_EMOJIS[choice]}\n\n🏦 Банк в размере {format_amount(game['bet'] * 2)}ms¢ забирает {winner_text}\n\n{quote}")

async def knb_pvp_choice_handler(update, context, game_id, choice):
    query = update.callback_query
    game = KHB_GAMES.get(game_id)
    if not game or game['type'] != 'pvp':
        await safe_answer(query, "❌ Игра не найдена.", show_alert=True)
        return
    if query.from_user.id not in [game['user1_id'], game['user2_id']]:
        await safe_answer(query, "🗿 Это не ваша игра!", show_alert=True)
        return
    if game['turn'] != query.from_user.id:
        await safe_answer(query, "⏱ Сейчас не ваш ход.", show_alert=True)
        return
    if query.from_user.id == game['user1_id']:
        if game['user1_choice'] is not None:
            await safe_answer(query, "❌ Вы уже сделали ход.", show_alert=True)
            return
        game['user1_choice'] = choice
        game['turn'] = game['user2_id']
        keyboard = [[InlineKeyboardButton(f"Камень {KHB_EMOJIS['камень']}", callback_data=f"knb:pvp:{game_id}:камень"), InlineKeyboardButton(f"Ножницы {KHB_EMOJIS['ножницы']}", callback_data=f"knb:pvp:{game_id}:ножницы"), InlineKeyboardButton(f"Бумага {KHB_EMOJIS['бумага']}", callback_data=f"knb:pvp:{game_id}:бумага")]]
        await query.edit_message_text(f"🪨 {game['user2_name']}, игра начата! • Камень-Ножницы-Бумага\n•••••••••••\nСейчас ходит — {game['user2_name']}. Ожидаем ход..\n\n👤 {game['user1_name']} — ♟️ Ход сделан\n👤 {game['user2_name']} — *ваш ход*\n\n💸 Ставка: {format_amount(game['bet'])}ms¢.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        await safe_answer(query, "✅ Ход принят!")
    else:
        if game['user2_choice'] is not None:
            await safe_answer(query, "❌ Вы уже сделали ход.", show_alert=True)
            return
        if game['user1_choice'] is None:
            await safe_answer(query, "⏱ Ожидаем ход первого игрока.", show_alert=True)
            return
        game['user2_choice'] = choice
        if game['user1_choice'] == game['user2_choice']:
            await update_balance_async(game['user1_id'], game['bet'])
            await update_balance_async(game['user2_id'], game['bet'])
            winner_text = "Ничья! 🤝"
            quote = random.choice(KHB_DRAW_MESSAGES)
        elif (game['user1_choice'] == 'камень' and game['user2_choice'] == 'ножницы') or (game['user1_choice'] == 'ножницы' and game['user2_choice'] == 'бумага') or (game['user1_choice'] == 'бумага' and game['user2_choice'] == 'камень'):
            await update_balance_async(game['user1_id'], game['bet'] * 2)
            await update_user_stats_async(game['user1_id'], game['bet'] * 2, 0)
            await update_user_stats_async(game['user2_id'], 0, game['bet'])
            winner_text = f"{game['user1_name']} победил! 🎉"
            quote = random.choice(KHB_WIN_MESSAGES)
        else:
            await update_balance_async(game['user2_id'], game['bet'] * 2)
            await update_user_stats_async(game['user2_id'], game['bet'] * 2, 0)
            await update_user_stats_async(game['user1_id'], 0, game['bet'])
            winner_text = f"{game['user2_name']} победил! 🎉"
            quote = random.choice(KHB_LOSE_MESSAGES)
        game['status'] = 'finished'
        await query.edit_message_text(f"⏱ {game['user1_name']} и {game['user2_name']}, игра окончена! • Камень-Ножницы-Бумага\n•••••••••••\n👤 {game['user1_name']} — {KHB_EMOJIS.get(game['user1_choice'], '❓')}\n👤 {game['user2_name']} — {KHB_EMOJIS.get(game['user2_choice'], '❓')}\n\n🏦 Банк в размере {format_amount(game['bet'] * 2)}ms¢ забирает {winner_text}\n\n{quote}")

async def knb_accept_duel(update, context, duel_id):
    query = update.callback_query
    duel = KHB_DUELS.get(duel_id)
    if not duel or duel['status'] != 'active' or query.from_user.id != duel['opponent_id']:
        await safe_answer(query, "❌ Вызов уже неактивен.", show_alert=True)
        return
    opponent = await get_user_async(duel['opponent_id'])
    if opponent['balance'] < duel['bet']:
        await safe_answer(query, f"❌ Недостаточно средств. Баланс: {format_amount(opponent['balance'])}ms¢", show_alert=True)
        return
    await update_balance_async(duel['opponent_id'], -duel['bet'])
    duel['status'] = 'accepted'
    game_id = f"{duel['challenger_id']}_{duel['opponent_id']}_{int(time.time())}"
    KHB_GAMES[game_id] = {'type': 'pvp', 'user1_id': duel['challenger_id'], 'user1_name': duel['challenger_name'], 'user2_id': duel['opponent_id'], 'user2_name': duel['opponent_name'], 'bet': duel['bet'], 'message_id': None, 'chat_id': update.effective_chat.id, 'status': 'waiting_user1', 'user1_choice': None, 'user2_choice': None, 'turn': duel['challenger_id']}
    keyboard = [[InlineKeyboardButton(f"Камень {KHB_EMOJIS['камень']}", callback_data=f"knb:pvp:{game_id}:камень"), InlineKeyboardButton(f"Ножницы {KHB_EMOJIS['ножницы']}", callback_data=f"knb:pvp:{game_id}:ножницы"), InlineKeyboardButton(f"Бумага {KHB_EMOJIS['бумага']}", callback_data=f"knb:pvp:{game_id}:бумага")]]
    del KHB_DUELS[duel_id]
    await query.edit_message_text(f"🪨 {duel['challenger_name']}, игра начата! • Камень-Ножницы-Бумага\n•••••••••••\nСейчас ходит — {duel['challenger_name']}. Ожидаем ход..\n\n👤 {duel['challenger_name']} — *ваш ход*\n👤 {duel['opponent_name']} — *ждёт хода*\n\n💸 Ставка: {format_amount(duel['bet'])}ms¢.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    await safe_answer(query, "✅ Вызов принят! Ожидаем ход создателя.")

async def knb_cancel_duel(update, context, duel_id):
    query = update.callback_query
    duel = KHB_DUELS.get(duel_id)
    if not duel or duel['status'] != 'active' or query.from_user.id != duel['challenger_id']:
        await safe_answer(query, "❌ Вызов уже неактивен.", show_alert=True)
        return
    await update_balance_async(duel['challenger_id'], duel['bet'])
    duel['status'] = 'cancelled'
    await query.edit_message_text(text=f"🔫 {duel['opponent_name']}, вызов на дуэль \"КНБ\" отменён\nВызов от {duel['challenger_name']}\n\n🙈 Вызов - отменён\n\n💸 Ставка: {format_amount(duel['bet'])}ms¢.\n\n❌ Вызов отменён создателем. Средства возвращены.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Вызов отменён", callback_data="noop")]]))
    await safe_answer(query, "✅ Вызов отменён, средства возвращены")

# ==================== DICE (кубик) ВНУТРЕННИЕ ====================
async def dice_choice_callback(update, context, user_id, choice_type, value=None):
    query = update.callback_query
    if query.from_user.id != user_id:
        await safe_answer(query, "🙈 Это не ваша игра!", show_alert=True)
        return
    session = DICE_SESSIONS.get(user_id)
    if not session or session['status'] != 'waiting':
        await handle_session_not_found(query)
        return
    if choice_type == 'num':
        session['choice'] = int(value)
        session['choice_type'] = 'number'
        session['choice_display'] = DICE_NUMBERS[int(value)]
        multiplier = DICE_MULTIPLIERS['number']
    elif choice_type == 'even':
        session['choice_type'] = 'even'
        session['choice_display'] = "Чётное"
        multiplier = DICE_MULTIPLIERS['even']
    elif choice_type == 'odd':
        session['choice_type'] = 'odd'
        session['choice_display'] = "Нечётное"
        multiplier = DICE_MULTIPLIERS['odd']
    elif choice_type == 'big':
        session['choice_type'] = 'big'
        session['choice_display'] = "Большие (4-6)"
        multiplier = DICE_MULTIPLIERS['big']
    elif choice_type == 'small':
        session['choice_type'] = 'small'
        session['choice_display'] = "Малые (1-3)"
        multiplier = DICE_MULTIPLIERS['small']
    elif choice_type == 'equal':
        session['choice_type'] = 'equal'
        session['choice_display'] = "Равно 3"
        multiplier = DICE_MULTIPLIERS['equal']
    else:
        await safe_answer(query, "❌ Неизвестный выбор", show_alert=True)
        return
    session['status'] = 'rolling'
    session['multiplier'] = multiplier
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except:
        pass
    await safe_answer(query, "🎲 Бросаем кубик...")
    dice_msg = await context.bot.send_dice(chat_id=session['chat_id'], emoji='🎲', message_thread_id=session.get('thread_id'), reply_to_message_id=session['message_id'])
    asyncio.create_task(process_dice_result(context, user_id, dice_msg.message_id, session, dice_msg.dice.value))

async def dice_cancel_callback(update, context, user_id):
    query = update.callback_query
    if query.from_user.id != user_id:
        await safe_answer(query, "🙈 Это не ваша кнопка!", show_alert=True)
        return
    session = DICE_SESSIONS.get(user_id)
    if not session:
        await handle_session_not_found(query)
        return
    await update_balance_async(user_id, session['bet'])
    try:
        await query.message.delete()
    except:
        pass
    del DICE_SESSIONS[user_id]
    await safe_answer(query, "❌ Игра отменена, средства возвращены")
