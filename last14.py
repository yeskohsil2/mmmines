# last14.py - ЧАСТЬ 1/7 (импорты и константы)
import logging
import os
import re
import random
import math
import time
import hashlib
import json
import asyncio
import secrets
from functools import wraps
from decimal import Decimal, getcontext
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple, Union
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions, InlineQueryResultArticle, InputTextMessageContent, KeyboardButtonRequestChat, ReplyKeyboardMarkup
from telegram.error import RetryAfter
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, InlineQueryHandler

from database import *
from handlers import button_handler
from handlers.games import (
    crash_command, cubic_command, handle_dice_game_callbacks,
    mines_command, gold_command, pyramid_command, tower_command,
    rr_command, dice_command, bowling_command, knb_command,
    coinflip_command, darts_command, spaceship_command, roulette_command,
    football_command, basketball_command,
    handle_mines_callbacks, handle_gold_callbacks, handle_pyramid_callbacks,
    handle_tower_callbacks, handle_rr_callbacks, handle_dice_callbacks,
    handle_coinfall_callbacks, handle_knb_callbacks
)
from handlers.common import (
    format_amount, safe_answer, check_ban, check_subscription, send_subscription_prompt,
    parse_amount, parse_bet_amount, generate_check_code, generate_math_problem,
    show_global_top, show_chat_top, get_user_async, update_task_progress_for_game,
    MINES_SESSIONS, GOLD_SESSIONS, PYRAMID_SESSIONS, TOWER_SESSIONS, RR_SESSIONS,
    BOWLING_SESSIONS, KHB_GAMES, KHB_DUELS, COINFLIP_SESSIONS, CASES_SESSIONS,
    SPACESHIP_SESSIONS, CRASH_SESSIONS, DICE_SESSIONS, ROULETTE_SESSIONS, DARTS_SESSIONS,
    pending_transfers, transfer_confirmations, pending_msg_transfers, mailing_data,
    math_contest_pending, LAST_CLICK_TIME, dice_cooldown
)

import sys
print("=" * 50)
print("БОТ НАЧИНАЕТ ЗАПУСК")
print("=" * 50)
sys.stdout.flush()
getcontext().prec = 28

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=os.getenv('LOG_LEVEL', 'INFO')
)

BOT_TOKEN = '8510598502:AAFW6wxiPIEJ_eHL2RDsukOtguuk5utdacI'
ADMIN_IDS = "6025818386,8555637694,7019856389,6219530066"
MAIN_ADMIN_ID = 6025818386
CHANNEL_USERNAME = "@monstrbotnewss"
CHANNEL2_USERNAME = "@kursmsgmonstr"
KURS_CHANNEL = "@kursmsgmonstr"
INVESTMENT_ADMIN_IDS = []
ITEMS_PER_PAGE = 3
COOLDOWN_SECONDS = 2
SESSION_TIMEOUT = 150
CACHE_TTL = 300
application = None
TRANSFER_TTL = 120
BONUS_COOLDOWN = 1800
ACTIVE_GAMES = {}
SPAM_PROTECTION = {}
MAX_CONCURRENT_GAMES = 3
SPAM_WARNING_LIMIT = 5
SPAM_BLOCK_TIME = 300
SPAM_BAN_DAYS = 10
COINFLIP_MULTIPLIER = 1.97
COINFLIP_RESULTS = {'орел': 'орел 🦅', 'решка': 'решка 🪙'}
SLOT_SESSIONS = {}
subscription_cache = {}
user_cache = {}

# ROULETTE константы
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

checklist_pages = {}
FIELD_SIZE = 5
CELLS_TOTAL = FIELD_SIZE * FIELD_SIZE
RR_MULTIPLIERS = {1: 1.15, 2: 1.45, 3: 1.95, 4: 2.9, 5: 5.8}
RR_STEP_MULTIPLIERS = {
    1: [0, 0.7, 1.8, 3.2, 5.0, 7.5], 2: [0, 0.6, 1.4, 2.4, 3.8, 5.8],
    3: [0, 0.5, 1.1, 1.9, 3.1], 4: [0, 0.9, 1.9, 2.7], 5: [0, 5.8]
}
MUTE_COMMANDS = ['мут', 'глуш']
KICK_COMMANDS = ['кик']
GOLD_MULTIPLIERS = [2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]
DARTS_MULTIPLIERS = {'miss': 4.8, 'red': 1.96, 'center': 3.8, 'white': 1.94}
DARTS_BETS = {'м': 'miss', 'мимо': 'miss', 'к': 'red', 'красное': 'red', 'ц': 'center', 'центр': 'center', 'б': 'white', 'белое': 'white'}
DARTS_RESULTS = {1: ('miss', 'мимо 😯'), 2: ('red', 'красное 🔴'), 3: ('white', 'белое ⚪'), 4: ('red', 'красное 🔴'), 5: ('white', 'белое ⚪'), 6: ('center', 'центр 🎯')}
SPACESHIP_MULTIPLIERS = {1: 1.3, 2: 1.7, 3: 2.3, 4: 2.6, 5: 3.6, 6: 4.2}
SPACESHIP_POLICE_CHANCE = 30
PYRAMID_EMOJIS = ["🚪", "🏚", "🛖", "🏠", "🏡", "🏢", "🏣", "🏤", "🏛️", "🏰", "🏯", "🕌"]
PYRAMID_MULTIPLIERS_3 = [1.31, 1.74, 2.32, 3.10, 4.13, 5.51, 7.34, 9.79, 13.05, 17.40, 23.20, 30.94]
PYRAMID_MULTIPLIERS_2 = [1.45, 2.10, 3.05, 4.42, 6.41, 9.29, 13.47, 19.53, 28.32, 41.06, 59.54, 86.33]
PYRAMID_MULTIPLIERS_1 = [1.62, 2.62, 4.24, 6.86, 11.11, 17.99, 29.14, 47.20, 76.46, 123.86, 200.65, 325.05]

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

SLOT_EMOJIS = ["🟢", "🔵", "🟣", "🟡", "🔴", "⚫"]
SLOT_NAMES = ["Rare", "Super Rare", "Epic", "Legendary", "Mythic", "Mystical"]
SLOT_RANGES = [(10, 50), (100, 200), (500, 700), (800, 1200), (1500, 2500), (10000, 25000)]
SLOT_WEIGHTS = [50, 25, 15, 6, 3, 1]

FOOTBALL_WIN_QUOTES = [
    "Удача сегодня на вашей стороне!✨", "Оторвём частичку клевера!✨",
    "Удача — беспредельное счастье!✨", "Твоя удача — твое счастье!✨",
    "Удача – символ твоей жизни!✨", "Твоя удача — невероятна.✨"
]
FOOTBALL_LOSE_QUOTES = [
    "Даже у королей бывает плохая раздача карт — Наполеон Б.",
    "Кто не рискует, тот иногда пьет дешевый коньяк — Михаил Крут",
    "Иногда проиграть — это просто способ сбросить лишний вес — Арнольд Шварц.",
    "Даже если ты проиграл, ты все равно в игре, просто теперь ты зритель — Джокер",
    "В этот раз фортуна просто перепутала адресата — Аноним.Г"
]
BASKETBALL_WIN_QUOTES = [
    "Снайперская точность!🎯", "Трёхочковый в корзину!🏀",
    "Как Майкл Джордан в прайме!🔥", "Невозможное возможно!✨",
    "Чистое попадание!✅"
]
BASKETBALL_LOSE_QUOTES = [
    "Мяч круглый, а удача квадратная — народная мудрость",
    "Даже Леброн иногда мажет — ничего страшного",
    "В следующий раз обязательно забросишь!💪", "Промах — это тоже опыт",
    "Фортуна сегодня взяла тайм-аут"
]

BOT_START_TIME = time.time()
FOOTBALL_EMOJI = "⚽"
BASKETBALL_EMOJI = "🏀"

KHB_EMOJIS = {'камень': '🪨', 'ножницы': '✂️', 'бумага': '📃'}
KHB_WIN_MESSAGES = ["Победа! 🎉", "Вы выиграли! ✨", "Удача на вашей стороне! 🌟", "Непобедимый! 👑"]
KHB_LOSE_MESSAGES = ["В следующий раз повезёт! 🍀", "Проигрыш — тоже опыт 💪", "Попробуйте ещё раз! 🔄", "Удача отвернулась 😅"]
KHB_DRAW_MESSAGES = ["Ничья! 🤝", "Дружеская ничья! 🕊️", "В этот раз никто не уступил ⚖️"]

BOWLING_MULTIPLIERS = {'strike': 3.5, 'miss': 3.2, 1: 2.9, 2: 2.9, 3: 2.9, 4: 2.9}
BOWLING_NUMBERS = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣"}
BOWLING_WORDS = {1: "кегля", 2: "кегли", 3: "кегли", 4: "кегли", 5: "кеглей"}

SPRING_EVENT_START = datetime(2026, 3, 7)
SPRING_EVENT_END = datetime(2026, 6, 1)
SPRING_CHANNEL = "https://t.me/monstrbotnews"
spring_question_creation = {}
math_contest_cooldown = {}
MATH_CONTEST_COOLDOWN = 0.9
BANK_INTEREST_RATES = {1: 3, 3: 7, 5: 11, 12: 12, 30: 21}
BANK_PRESET_AMOUNTS = [500000, 1000000, 5000000, 10000000, 50000000]
BANK_MAX_AMOUNT = 50000000
BANK_PENALTY_PERCENT = 20
bank_creation_data = {}
DICE_MIN_BET = 1000
DICE_MAX_BET = 50000000
DICE_MAX_GAMES_PER_CHAT = 5
DICE_TIMEOUT = 30
EVENT_COUNTER = 0
CASES_DATA = {
    'daily': {'name': '🎊 Daily', 'emoji': '🎊', 'min_reward': 5000, 'max_reward': 25000, 'empty_chance': 20, 'cells': 9, 'opens': 3},
    'empty': {'name': '😑 Пустышка', 'emoji': '😑', 'min_reward': 2000, 'max_reward': 7000, 'empty_chance': 40, 'cells': 9, 'opens': 3}
}
CASES_NAMES_RU = {'daily': 'Дэйли', 'empty': 'Пустышка'}
TOWER_FIELD_SIZE = 5
TOWER_MAX_LEVEL = 8
TOWER_MULTIPLIERS = {
    1: [1.21, 1.52, 1.89, 2.37, 2.96, 3.70, 4.63, 5.78, 7.23],
    2: [1.62, 2.69, 4.49, 7.48, 12.47, 20.79, 34.65, 57.75, 96.25],
    3: [2.15, 4.62, 9.93, 21.35, 45.90, 98.69, 212.18, 456.19, 980.81],
    4: [2.86, 8.18, 23.39, 66.89, 191.30, 547.12, 1564.77, 4475.24, 12800.00]
}
DICE_MULTIPLIERS = {'number': 5.8, 'even': 1.94, 'odd': 1.94, 'big': 1.94, 'small': 2.9, 'equal': 5.8}
DICE_NUMBERS = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣"}

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def is_recent(update: Update) -> bool:
    if update.message: return update.message.date.timestamp() >= BOT_START_TIME
    elif update.callback_query and update.callback_query.message: return update.callback_query.message.date.timestamp() >= BOT_START_TIME
    elif update.inline_query: return update.inline_query.date.timestamp() >= BOT_START_TIME
    return True

def generate_game_hash(game_data: dict) -> str:
    data_string = json.dumps(game_data, sort_keys=True) + str(time.time()) + secrets.token_hex(8)
    return hashlib.sha256(data_string.encode()).hexdigest()[:16]

def generate_transfer_hash() -> str: return secrets.token_hex(8)

def parse_roulette_bet(bet_str: str) -> Optional[Tuple[str, Optional[Any], int]]:
    bet_str = bet_str.lower().strip()
    if bet_str.isdigit() and 0 <= int(bet_str) <= 36: return ('number', int(bet_str), ROULETTE_MULTIPLIERS['number'])
    if '-' in bet_str:
        parts = bet_str.split('-')
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            range_key = f"{parts[0]}-{parts[1]}"
            if range_key in ROULETTE_MULTIPLIERS: return (range_key, (int(parts[0]), int(parts[1])), ROULETTE_MULTIPLIERS[range_key])
    if bet_str in ROULETTE_BETS: return (ROULETTE_BETS[bet_str], None, ROULETTE_MULTIPLIERS[ROULETTE_BETS[bet_str]])
    return None

def simple_parse_bet(amount_str: str, user_balance: Optional[int] = None) -> int:
    if not amount_str: return 0
    amount_str = str(amount_str).lower().strip()
    if amount_str in ['всё', 'все', 'all']: return user_balance if user_balance is not None else 0
    amount_str = amount_str.replace(',', '.')
    for suffix, mult in {'кккк': 1000000000000, 'ккк': 1000000000, 'кк': 1000000, 'к': 1000, 'м': 1000000}.items():
        if amount_str.endswith(suffix):
            try: return int(float(amount_str[:-len(suffix)]) * mult)
            except: pass
    try: return int(float(amount_str.replace('.', '') if amount_str.count('.') > 1 else amount_str))
    except: return 0

def check_cooldown(user_id: int) -> float:
    current_time = time.time()
    if user_id in LAST_CLICK_TIME:
        if current_time - LAST_CLICK_TIME[user_id] < COOLDOWN_SECONDS:
            return round(COOLDOWN_SECONDS - (current_time - LAST_CLICK_TIME[user_id]), 1)
    LAST_CLICK_TIME[user_id] = current_time
    return 0

async def check_spam_protection(user_id: int, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    current_time = time.time()
    if await check_ban(update, context): return False
    if user_id in SPAM_PROTECTION:
        spam_info = SPAM_PROTECTION[user_id]
        if current_time < spam_info['blocked_until']:
            await update.message.reply_text(f"⚠ Вы временно заблокированы на {int(spam_info['blocked_until'] - current_time)} секунд.\nПожалуйста, подождите.")
            return False
        else: del SPAM_PROTECTION[user_id]
    if user_id in ACTIVE_GAMES:
        if ACTIVE_GAMES[user_id].get('count', 0) >= MAX_CONCURRENT_GAMES:
            await update.message.reply_text(f"⚠ У вас уже {ACTIVE_GAMES[user_id]['count']} активных игр. Подождите завершения.")
            return False
        games = [t for t in ACTIVE_GAMES[user_id].get('games_in_window', []) if current_time - t < 60]
        ACTIVE_GAMES[user_id]['games_in_window'] = games
        if len(games) >= SPAM_WARNING_LIMIT:
            warnings = SPAM_PROTECTION.get(user_id, {}).get('warnings', 0) + 1
            SPAM_PROTECTION[user_id] = {'warnings': warnings, 'blocked_until': current_time + SPAM_BLOCK_TIME, 'banned': False}
            await update.message.reply_text(f"⚠ Вы делаете слишком много запросов!\nПредупреждение {warnings}/3. При 3-х предупреждениях - бан на 10 дней.")
            if warnings >= 3: await ban_spammer(user_id, update, context)
            return False
    return True

async def ban_spammer(user_id: int, update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await ban_user_async(user_id, 10, "Чрезмерный спам в играх (автоматический бан)")
        SPAM_PROTECTION[user_id] = {'warnings': 3, 'blocked_until': time.time() + SPAM_BLOCK_TIME, 'banned': True}
        username = f"@{update.effective_user.username}" if update.effective_user.username else f"ID: {user_id}"
        for aid in ADMIN_IDS:
            try: await context.bot.send_message(chat_id=aid, text=f"🚫 **АВТОМАТИЧЕСКИЙ БАН**\n\nПользователь: {username}\nИмя: {update.effective_user.full_name}\nID: `{user_id}`\nПричина: Чрезмерный спам\nСрок: 10 дней\nВремя: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", parse_mode='Markdown')
            except: pass
        try: await context.bot.send_message(chat_id=user_id, text=f"🚨 Вы были заблокированы в боте на 10 дней по причине: Чрезмерный спам\n\n❓ Не согласны? Нажмите кнопку ниже", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🧐 Не согласен", url="https://t.me/kleymorf")]]))
        except: pass
        await update.message.reply_text(f"Вы забанены на 10 дней за чрезмерный спам!\nОбратитесь к администратору.")
    except Exception as e: logging.error(f"Ошибка при бане спамера {user_id}: {e}")

async def handle_flood(update: Update, context: ContextTypes.DEFAULT_TYPE, error: RetryAfter):
    retry_after = error.retry_after
    if update.callback_query: await safe_answer(update.callback_query, f"⏳ Flood Control, ожидай {retry_after} сек.", show_alert=True)
    elif update.message: await update.message.reply_text(f"⏳ Слишком много запросов. Подождите {retry_after} секунд.")
    logging.warning(f"Flood control for user {update.effective_user.id}: wait {retry_after}s")
    await asyncio.sleep(retry_after)

def generate_crash_multiplier() -> float:
    r = random.random() * 100
    if r < 50: return round(random.uniform(1.00, 1.99), 2)
    elif r < 80: return round(random.uniform(2.00, 3.99), 2)
    elif r < 95: return round(random.uniform(4.00, 6.99), 2)
    else: return round(random.uniform(7.00, 20.00), 2)

async def update_stock_prices(context: ContextTypes.DEFAULT_TYPE):
    stocks = await get_all_stocks_async()
    updates, stock_updates = [], []
    stock_trends = context.bot_data.get('stock_trends', {})
    for stock in stocks:
        sid, name, prev = stock['stock_id'], stock['name'], stock['current_price']
        if sid not in stock_trends: stock_trends[sid] = {'trend': random.choice(['up', 'down', 'side']), 'strength': random.uniform(0.5, 1.5), 'duration': random.randint(3, 8), 'counter': 0}
        trend = stock_trends[sid]
        trend['counter'] += 1
        if trend['counter'] >= trend['duration']:
            if trend['trend'] == 'up': new_trend = random.choices(['down', 'side'], weights=[60, 40])[0]
            elif trend['trend'] == 'down': new_trend = random.choices(['up', 'side'], weights=[70, 30])[0]
            else: new_trend = random.choices(['up', 'down', 'side'], weights=[40, 40, 20])[0]
            stock_trends[sid] = {'trend': new_trend, 'strength': random.uniform(0.8, 2.0), 'duration': random.randint(4, 12), 'counter': 0}
            trend = stock_trends[sid]
        if trend['trend'] == 'up': change_percent = (random.uniform(0.01, 0.08) if random.random() < 0.8 else random.uniform(-0.03, -0.01)) * trend['strength']
        elif trend['trend'] == 'down': change_percent = (random.uniform(-0.08, -0.01) if random.random() < 0.8 else random.uniform(0.01, 0.03)) * trend['strength']
        else: change_percent = random.uniform(-0.03, 0.03)
        if random.random() < 0.05:
            change_percent = random.uniform(0.10, 0.25) if random.random() < 0.5 else random.uniform(-0.25, -0.10)
            stock_trends[sid]['trend'], stock_trends[sid]['counter'], stock_trends[sid]['duration'] = ('up' if change_percent > 0 else 'down'), 0, random.randint(5, 10)
        change = int(prev * change_percent) or random.choice([-1, 1]) * random.randint(1, 3)
        new_price = max(1, prev + change)
        stock_updates.append((sid, new_price))
        pct = ((new_price - prev) / prev) * 100
        emoji = "🚀" if pct > 5 else "📈" if pct > 1 else "↗️" if pct > 0 else "💥" if pct < -5 else "📉" if pct < -1 else "↘️" if pct < 0 else "➡️"
        updates.append(f"🆔 {sid} — {name} {new_price}ms¢ ({emoji}{pct:+.2f}%) {'📈' if trend['trend'] == 'up' else '📉' if trend['trend'] == 'down' else '➡️'}")
    context.bot_data['stock_trends'] = stock_trends
    if stock_updates: await update_all_stocks_prices_async(stock_updates)
    if updates and KURS_CHANNEL:
        try: await context.bot.send_message(chat_id=KURS_CHANNEL, text="📊 Ежеминутный отчёт.\n\n" + "\n".join(updates))
        except: pass

# ==================== ОЧИСТКА СЕССИЙ ====================
async def cleanup_old_sessions(app: Application):
    while True:
        try:
            await asyncio.sleep(60)
            current_time, bot = time.time(), app.bot
            for uid in list(LAST_CLICK_TIME.keys()):
                if current_time - LAST_CLICK_TIME[uid] > 3600: del LAST_CLICK_TIME[uid]
            for uid in list(user_cache.keys()):
                if current_time - user_cache[uid]['time'] > CACHE_TTL: del user_cache[uid]
            for uid in list(subscription_cache.keys()):
                if current_time - subscription_cache[uid][0] > CACHE_TTL: del subscription_cache[uid]
            await cleanup_expired_games()
            bd = app.bot_data
            for sdict in [bd.get('MINES_SESSIONS', {}), bd.get('GOLD_SESSIONS', {}), bd.get('PYRAMID_SESSIONS', {})]:
                for uid in list(sdict.keys()):
                    try:
                        s = sdict[uid]
                        if s.get('status') == 'active':
                            if 'last_activity' in s and current_time - s['last_activity'] > 600:
                                if s.get('bet', 0) > 0: await update_balance_async(uid, s['bet'])
                                del sdict[uid]
                                try: await bot.send_message(chat_id=uid, text="⏰ Игра автоматически завершена по таймауту. Средства возвращены.")
                                except: pass
                            elif 'start_time' in s and current_time - s['start_time'] > 600:
                                if s.get('bet', 0) > 0: await update_balance_async(uid, s['bet'])
                                del sdict[uid]
                        elif s.get('status') in ['lost', 'won']:
                            if 'end_time' not in s: s['end_time'] = current_time
                            elif current_time - s['end_time'] > 120: del sdict[uid]
                        elif 'start_time' in s and current_time - s['start_time'] > 300:
                            if s.get('bet', 0) > 0: await update_balance_async(uid, s['bet'])
                            del sdict[uid]
                    except: pass
            for uid in list(bd.get('RR_SESSIONS', {}).keys()):
                try:
                    s = bd['RR_SESSIONS'][uid]
                    g = await get_rr_game_async(s['game_id'])
                    if not g: del bd['RR_SESSIONS'][uid]
                    elif 'start_time' in s and current_time - s['start_time'] > 300 and g['status'] == 'active':
                        await update_balance_async(uid, g['bet'])
                        await finish_rr_game_async(s['game_id'], 'timeout')
                        del bd['RR_SESSIONS'][uid]
                except: pass
            for uid in list(bd.get('BOWLING_SESSIONS', {}).keys()):
                try:
                    s = bd['BOWLING_SESSIONS'][uid]
                    if s.get('status') in ['won', 'lost']:
                        if 'end_time' not in s: s['end_time'] = current_time
                        elif current_time - s['end_time'] > 120: del bd['BOWLING_SESSIONS'][uid]
                    elif s.get('status') == 'waiting' and 'start_time' in s and current_time - s['start_time'] > 300:
                        if s.get('bet', 0) > 0: await update_balance_async(uid, s['bet'])
                        del bd['BOWLING_SESSIONS'][uid]
                except: pass
            for uid in list(bd.get('TOWER_SESSIONS', {}).keys()):
                try:
                    s = bd['TOWER_SESSIONS'][uid]
                    if s.get('status') == 'active':
                        if 'last_activity' in s and current_time - s['last_activity'] > 120:
                            if s.get('bet', 0) > 0: await update_balance_async(uid, s['bet'])
                            del bd['TOWER_SESSIONS'][uid]
                        elif 'start_time' in s and current_time - s['start_time'] > 120:
                            if s.get('bet', 0) > 0: await update_balance_async(uid, s['bet'])
                            del bd['TOWER_SESSIONS'][uid]
                    elif s.get('status') in ['lost', 'won']:
                        if 'end_time' not in s: s['end_time'] = current_time
                        elif current_time - s['end_time'] > 120: del bd['TOWER_SESSIONS'][uid]
                except: pass
            for did in list(bd.get('KHB_DUELS', {}).keys()):
                try:
                    d = bd['KHB_DUELS'][did]
                    if d['status'] == 'active' and current_time > d['expire_time']:
                        await update_balance_async(d['challenger_id'], d['bet'])
                        try: await bot.edit_message_text(chat_id=d['chat_id'], message_id=d['message_id'], text=f"🔫 {d['opponent_name']}, вас вызвали на дуэль \"КНБ\"\nВызов от {d['challenger_name']}\n\n🙈 Вызов - неактивен\n\n💸 Ставка: {format_amount(d['bet'])}ms¢.\n\n⏱ Вызов был автоматически отозван. Средства возвращены.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏱ Вызов отозван", callback_data="noop")]]))
                        except: pass
                        del bd['KHB_DUELS'][did]
                    elif d['status'] in ['accepted', 'cancelled', 'expired']:
                        if 'cleanup_time' not in d: d['cleanup_time'] = current_time
                        elif current_time - d['cleanup_time'] > 3600: del bd['KHB_DUELS'][did]
                except: pass
            for gid in list(bd.get('KHB_GAMES', {}).keys()):
                try:
                    g = bd['KHB_GAMES'][gid]
                    if g.get('status') in ['finished']:
                        if 'cleanup_time' not in g: g['cleanup_time'] = current_time
                        elif current_time - g['cleanup_time'] > 3600: del bd['KHB_GAMES'][gid]
                    elif 'start_time' in g and current_time - g['start_time'] > 1800:
                        if g['type'] == 'pvp':
                            if g['user1_choice'] is None: await update_balance_async(g['user1_id'], g['bet'])
                            if g['user2_choice'] is None: await update_balance_async(g['user2_id'], g['bet'])
                        del bd['KHB_GAMES'][gid]
                except: pass
            for tid in list(pending_transfers.keys()):
                if current_time - pending_transfers[tid]['time'] > TRANSFER_TTL: del pending_transfers[tid]
            for tid in list(transfer_confirmations.keys()):
                if current_time - transfer_confirmations[tid]['time'] > TRANSFER_TTL: del transfer_confirmations[tid]
            for uid in list(mailing_data.keys()):
                if current_time - mailing_data[uid].get('time', 0) > 3600: del mailing_data[uid]
            for uid in list(checklist_pages.keys()):
                if current_time - checklist_pages[uid].get('time', 0) > 600: del checklist_pages[uid]
        except Exception as e: logging.error(f"Error in cleanup task: {e}")

# last14.py - ЧАСТЬ 2/7 (основные команды)

# ==================== КОМАНДЫ START, HELP, GAMES ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or await check_ban(update, context): return
    user, args = update.effective_user, context.args
    referrer_id = check_code = user_check_code = None
    if args:
        arg = args[0]
        if arg == 'bank': await bank_private_command(update, context); return
        elif arg.startswith('userchk_'): await handle_user_check(update, context, arg.replace('userchk_', '')); return
        elif arg.startswith('ref_'): referrer_id = int(arg.replace('ref_', ''))
        elif arg.startswith('chk_'): check_code = arg.replace('chk_', '')
        elif arg.startswith('listcheck_') and user.id == MAIN_ADMIN_ID: await show_checklist(update, context, 1); return
        elif arg.startswith('listcheck_'): await update.message.reply_text("❌ Эта ссылка не для вас."); return
    db_user = await get_user_async(user.id, user.full_name, user.username)
    if check_code:
        check = await get_check_async(check_code)
        if not check or check['used_count'] >= check['max_activations'] or str(user.id) in (check['claimed_by'] or '').split(','):
            await update.message.reply_text("❌ Чек не найден или уже использован.")
            return
        if await check_subscription(update, context, user.id):
            await use_check_async(check_code, user.id)
            await update_balance_async(user.id, check['amount'])
            await update.message.reply_text(f"☑ {user.full_name}, активирован чек на {check['amount']}ms¢.")
            await send_welcome(update, context)
        else: await send_subscription_prompt(update, context)
        return
    if referrer_id and referrer_id != user.id and db_user.get('registered_at') is None:
        referrer = await get_user_async(referrer_id)
        if referrer:
            await add_referral_async(referrer_id, user.id)
            reward = random.randint(100, 50000)
            await update_balance_async(user.id, reward)
            await update_balance_async(referrer_id, reward)
            await update.message.reply_text(f"🦣 За переход по реферальной ссылке вы получили {reward}ms¢")
            try: await context.bot.send_message(chat_id=referrer_id, text=f"🦣 ЗАСКАМЛЕНО! Вы получили за реферала {reward}ms¢ от {user.full_name}")
            except: pass
    await send_welcome(update, context)

async def send_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user: return
    try:
        await update.message.reply_text(
            "👋*Привет*! Я – Монстр бот💣\n\n"
            "📲 Проведи свое время с удовольствием играя в нашего бота! Тут ты сможешь насладиться множественным функционалом и реально годными играми\n\n"
            "🧐 Во что будем играть? Пиши /game для получения список игр.\n\n"
            "❓ Думаю все понятно, если остались вопросы просто напиши /help.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Добавить бота в чат", url="https://t.me/monstrminesbot?startgroup=true")],
                [InlineKeyboardButton("📰 Новости [1]", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
                [InlineKeyboardButton("📰 Новости [2]", url=f"https://t.me/{CHANNEL2_USERNAME[1:]}")],
                [InlineKeyboardButton("💬 Официальный чат", url="https://t.me/gamemonstroff")]
            ]), parse_mode='Markdown')
    except Exception as e:
        if "Forbidden" not in str(e): logging.error(f"Error in send_welcome: {e}")

async def games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or await check_ban(update, context): return
    if update.effective_user.id not in ADMIN_IDS and not await check_subscription(update, context, update.effective_user.id):
        await send_subscription_prompt(update, context)
        return
    await update.message.reply_text(
        "🎮 Список доступных игр:\n"
        "💣 Мины — /mines *мин* *ставка*\n"
        "💰 Золото — /gold *ставка*\n"
        "🎳 Боулинг – /bowling *ставка* *мимо,страйк*\n"
        "🏝️ Пирамида — /pyramid *ставка* *дверей (1-3)*\n"
        "🚀 Краш – /crash *ставка* *коэф*\n"
        "🎲 Дайс – /cubic *ставка*\n"
        "🎰 Рулетка – /roulette *диапазон* *ставка*\n"
        "🗼 Башня – /tower *ставка* *мин*\n"
        "🪨 КНБ - /knb *ставка*\n"
        "🎲 Кости - кости *ставка*\n"
        "🎰 Барабан — /slot\n"
        "⚽ Футбол — /fb *ставка* *гол/мимо*\n"
        "🏀 Баскетбол — /bk *ставка* *гол/мимо*\n"
        "• Пример: /mines 5 1к\n"
        "• Пример: /gold 100\n"
        "• Пример: /pyramid 100 2"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or await check_ban(update, context): return
    if update.effective_user.id not in ADMIN_IDS and not await check_subscription(update, context, update.effective_user.id):
        await send_subscription_prompt(update, context)
        return
    await update.message.reply_text(
        "🗂 Помощь по боту:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💡 Основные", callback_data="help_basic"), InlineKeyboardButton("🎮 Игры", callback_data="help_games")],
            [InlineKeyboardButton("🔘 Другое", callback_data="help_other"), InlineKeyboardButton("📕 Правила", callback_data="help_rules")]
        ])
    )

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or await check_ban(update, context): return
    if update.effective_user.id not in ADMIN_IDS and not await check_subscription(update, context, update.effective_user.id):
        await send_subscription_prompt(update, context)
        return
    await update.message.reply_text(
        "🛡️ Мы всегда на страже помощи!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🆘 Помощь", url="https://t.me/kleymorf")],
            [InlineKeyboardButton("🧐 Др. вопросы", url="https://t.me/kleymorf")]
        ])
    )

# ==================== БАЛАНС, ПРОФИЛЬ, ТОПЫ ====================
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or await check_ban(update, context): return
    if update.effective_user.id not in ADMIN_IDS and not await check_subscription(update, context, update.effective_user.id):
        await send_subscription_prompt(update, context)
        return
    db_user = await get_user_async(update.effective_user.id, update.effective_user.full_name, update.effective_user.username)
    await update.message.reply_text(
        text=f"💎 {update.effective_user.full_name}, ваш баланс: {format_amount(db_user['balance'])}ms¢\n"
             f"<tg-emoji emoji-id='5402418909557053333'>🍯</tg-emoji> MSG: {format_amount(db_user.get('msg_balance', 0))}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 Бонус", callback_data=f"bonus_{update.effective_user.id}"),
             InlineKeyboardButton("🎰 Барабан", callback_data=f"slot_{update.effective_user.id}")]
        ]), parse_mode='HTML'
    )

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or await check_ban(update, context): return
    if update.effective_user.id not in ADMIN_IDS and not await check_subscription(update, context, update.effective_user.id):
        await send_subscription_prompt(update, context)
        return
    stats = await get_user_stats_async(update.effective_user.id)
    db_user = await get_user_async(update.effective_user.id, update.effective_user.full_name, update.effective_user.username)
    await update.message.reply_text(
        text=f"👤 {update.effective_user.full_name}, ваш профиль:\n\n"
             f"🆔 {update.effective_user.id}\n\n"
             f"💰 Общая сумма выигрышей: {format_amount(stats['total_win'])}ms¢\n\n"
             f"💸 Общая сумма проигрышей: {format_amount(stats['total_loss'])}ms¢\n\n"
             f"<tg-emoji emoji-id='5402418909557053333'>🍯</tg-emoji> MSG: {format_amount(db_user.get('msg_balance', 0))}\n\n"
             f"Ваш баланс: {format_amount(db_user['balance'])}ms¢\n\n"
             f"За все время вы сыграли в {stats['games_played']} игр.\n\n"
             f"🦣 Приглашено мамонтов: {await get_user_referral_count_async(update.effective_user.id)}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 Бонус", callback_data=f"bonus_{update.effective_user.id}"),
             InlineKeyboardButton("🎰 Барабан", callback_data=f"slot_{update.effective_user.id}")]
        ]), parse_mode='HTML'
    )

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or await check_ban(update, context): return
    if update.effective_user.id not in ADMIN_IDS and not await check_subscription(update, context, update.effective_user.id):
        await send_subscription_prompt(update, context)
        return
    await show_global_top(update.message, context, update.effective_user)

async def chat_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or await check_ban(update, context): return
    if update.effective_user.id not in ADMIN_IDS and not await check_subscription(update, context, update.effective_user.id):
        await send_subscription_prompt(update, context)
        return
    await show_chat_top(update.message, context, update.effective_user)

async def ref_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or await check_ban(update, context): return
    if update.effective_user.id not in ADMIN_IDS and not await check_subscription(update, context, update.effective_user.id):
        await send_subscription_prompt(update, context)
        return
    await update.message.reply_text(
        f"🦣 {update.effective_user.full_name}, система для мамонтов:\n\n"
        f"🔗 Ваша реферальная ссылка: https://t.me/{context.bot.username}?start=ref_{update.effective_user.id}\n\n"
        f"Краткая информация - вы приглашаете пользователя и получаете 100-50.000ms¢\n"
        f"❕ Важная информация, реферал зачисляется только после того, как подпишется на новостные каналы.\n\n"
        f"📊 Приглашено мамонтов: {await get_user_referral_count_async(update.effective_user.id)}"
    )

async def top_ref_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or await check_ban(update, context): return
    if update.effective_user.id not in ADMIN_IDS and not await check_subscription(update, context, update.effective_user.id):
        await send_subscription_prompt(update, context)
        return
    top_refs = await get_top_referrers_async(10)
    if not top_refs:
        await update.message.reply_text("🦣 Мамонтоводов пока нет.")
        return
    msg = f"🦣 {update.effective_user.full_name}, топ мамонтоводов:\n\n"
    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for i, (_, name, cnt) in enumerate(top_refs):
        msg += f"{emojis[i]} {name} — заскамил {cnt} чел.\n"
    rank = await get_referral_rank_async(update.effective_user.id)
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🙈 Вы на {rank} месте." if rank <= 10 else f"🥲 Вы не в топе.", callback_data="noop")]
    ]))

async def get_user_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS and update.effective_user.id != MAIN_ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
        target_name = update.message.reply_to_message.from_user.full_name
    else:
        if len(context.args) < 1:
            await update.message.reply_text("❌ Использование: /гет *@username* или /гет *id*")
            return
        target = context.args[0]
        if target.startswith('@'):
            ud = await get_user_by_username_async(target[1:])
            if not ud:
                await update.message.reply_text(f"❌ Пользователь {target} не найден.")
                return
            target_id, target_name = ud['user_id'], ud['full_name'] or target[1:]
        else:
            try:
                target_id = int(target)
                ud = await get_user_async(target_id)
                target_name = ud.get('full_name') or f"ID: {target_id}"
            except:
                await update.message.reply_text("❌ Неверный формат ID.")
                return
    db_user = await get_user_async(target_id)
    msg_balance = db_user.get('msg_balance', 0)
    text = f"👤 Профиль пользователя {target_name}:\n\n"
    text += f"💸 Баланс – {format_amount(db_user['balance'])}ms¢\n"
    text += f"🍯 MSG – {format_amount(msg_balance)}\n\n"
    text += f"🏦 Депозиты:\n"
    deposits = await get_user_deposits_async(target_id, 'active')
    if deposits:
        now = datetime.now()
        for dep in deposits:
            try:
                expires = datetime.strptime(dep['expires_at'], '%Y-%m-%d %H:%M:%S')
            except:
                continue
            delta = expires - now
            text += f"🆔 {dep['deposit_id']} — {format_amount(dep['amount'])}ms¢ — закончится через {delta.days} дн. {delta.seconds//3600} ч. {(delta.seconds%3600)//60} мин.\n"
    else:
        text += "Нет активных депозитов\n"
    portfolio = await get_user_portfolio_async(target_id)
    text += f"\n📊 Акции:\n"
    if portfolio:
        for item in portfolio:
            text += f"• {item['name']} — {item['quantity']} шт. x {item['current_price']}ms¢\n"
        total_val = await get_user_portfolio_total_async(target_id)
        total_cnt = await get_user_portfolio_count_async(target_id)
        text += f"\n💰 Общая сумма акций: {format_amount(total_val)}ms¢ ({total_cnt} шт.)"
    else:
        text += "Нет акций"
    await update.message.reply_text(text)

# ==================== ПЕРЕВОДЫ ====================
async def transfer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or await check_ban(update, context): return
    if update.effective_user.id not in ADMIN_IDS and not await check_subscription(update, context, update.effective_user.id):
        await send_subscription_prompt(update, context)
        return
    target_user = None
    amount = 0
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        if context.args:
            amount = parse_amount(context.args[0])
    else:
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: п *юзернейм* *сумма* или ответьте на сообщение: п *сумма*")
            return
        target_identifier = context.args[0]
        amount = parse_amount(' '.join(context.args[1:]))
        if target_identifier.startswith('@'):
            await update.message.reply_text("❌ Поиск по юзернейму временно недоступен.")
            return
        try:
            target_user = type('User', (), {'id': int(target_identifier), 'full_name': f"User {target_identifier}"})()
        except:
            await update.message.reply_text("❌ Неверный формат ID.")
            return
    if amount <= 0:
        await update.message.reply_text("❌ Неверная сумма.")
        return
    if target_user.id == update.effective_user.id:
        await update.message.reply_text("❌ Нельзя перевести средства самому себе.")
        return
    db_user = await get_user_async(update.effective_user.id)
    if db_user['balance'] < amount:
        await update.message.reply_text(f"❌ Недостаточно средств. Ваш баланс: {format_amount(db_user['balance'])}ms¢")
        return
    transfer_id = generate_transfer_hash()
    pending = context.bot_data.get('pending_transfers', {})
    pending[transfer_id] = {
        'from_id': update.effective_user.id,
        'from_name': update.effective_user.full_name,
        'to_id': target_user.id,
        'to_name': target_user.full_name,
        'amount': amount,
        'time': time.time(),
        'message_id': update.message.message_id,
        'chat_id': update.effective_chat.id
    }
    context.bot_data['pending_transfers'] = pending
    await update.message.reply_text(
        f"❓ {update.effective_user.full_name}, вы хотите перевести {amount}ms¢ пользователю <a href='tg://user?id={target_user.id}'>{target_user.full_name}</a>.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("☑ Подтверждаю", callback_data=f"confirm_transfer_{transfer_id}")]]),
        parse_mode='HTML'
    )

async def confirm_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE, transfer_id: str):
    query = update.callback_query
    pending = context.bot_data.get('pending_transfers', {})
    if transfer_id not in pending or query.from_user.id != pending[transfer_id]['from_id']:
        await safe_answer(query, "❌ Перевод не найден или не ваша кнопка.")
        return
    transfer = pending[transfer_id]
    try:
        await query.delete_message()
    except:
        pass
    confirmation_id = generate_transfer_hash()
    confirm = context.bot_data.get('transfer_confirmations', {})
    confirm[confirmation_id] = {
        'from_id': transfer['from_id'],
        'from_name': transfer['from_name'],
        'to_id': transfer['to_id'],
        'to_name': transfer['to_name'],
        'amount': transfer['amount'],
        'time': time.time(),
        'original_message_id': transfer['message_id'],
        'original_chat_id': transfer['chat_id']
    }
    context.bot_data['transfer_confirmations'] = confirm
    await context.bot.send_message(
        chat_id=transfer['chat_id'],
        text="✔ Почти готово! Подтвердите в личные сообщения с ботом.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Перейти в ЛС", url=f"https://t.me/{context.bot.username}")]])
    )
    try:
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=f"☑ Последний шаг для перевода\n\nℹ️ Информация для перевода:\n\n"
                 f"Вы хотите перевести {transfer['amount']}ms¢ пользователю <a href='tg://user?id={transfer['to_id']}'>{transfer['to_name']}</a>.\n\n"
                 f"Hash перевода: {confirmation_id}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❗ ПОДТВЕРЖДАЮ", callback_data=f"final_confirm_{confirmation_id}")]]),
            parse_mode='HTML'
        )
    except Exception as e:
        if "Forbidden" in str(e):
            await context.bot.send_message(chat_id=transfer['chat_id'], text="❌ Вы заблокировали бота. Разблокируйте для продолжения.")
        else:
            await context.bot.send_message(chat_id=transfer['chat_id'], text="❌ Не удалось отправить сообщение в ЛС. Возможно, вы не начинали диалог с ботом.")
    del pending[transfer_id]
    context.bot_data['pending_transfers'] = pending
    await safe_answer(query, "✅ Перейдите в ЛС для подтверждения")

async def final_confirm_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE, confirmation_id: str):
    query = update.callback_query
    confirm = context.bot_data.get('transfer_confirmations', {})
    if confirmation_id not in confirm or query.from_user.id != confirm[confirmation_id]['from_id']:
        await safe_answer(query, "❌ Перевод не найден или не ваша кнопка.")
        return
    transfer = confirm[confirmation_id]
    success, msg = await transfer_money_async(transfer['from_id'], transfer['to_id'], transfer['amount'])
    if not success:
        await safe_answer(query, f"❌ {msg}")
        return
    await update_user_stats_async(transfer['from_id'], 0, 0)
    await update_user_stats_async(transfer['to_id'], 0, 0)
    try:
        await query.edit_message_text(f"💸 Вы успешно перевели {transfer['amount']}ms¢ пользователю {transfer['to_name']}.")
    except:
        pass
    try:
        new_balance = await get_user_async(transfer['to_id'])
        await context.bot.send_message(
            chat_id=transfer['to_id'],
            text=f"💰 {transfer['from_name']} перевёл вам {transfer['amount']}ms¢.\nВаш новый баланс: {new_balance['balance']}ms¢"
        )
    except:
        pass
    try:
        await context.bot.edit_message_text(
            chat_id=transfer['original_chat_id'],
            message_id=transfer['original_message_id'],
            text=f"💸 Перевод {transfer['amount']}ms¢ пользователю {transfer['to_name']} успешно завершен!"
        )
    except:
        pass
    try:
        await send_transfer_log(context, {'user_id': transfer['from_id'], 'full_name': transfer['from_name']},
                                {'user_id': transfer['to_id'], 'full_name': transfer['to_name']},
                                transfer['amount'], confirmation_id, False)
    except:
        pass
    del confirm[confirmation_id]
    context.bot_data['transfer_confirmations'] = confirm
    await safe_answer(query, "✅ Перевод выполнен!")

async def send_transfer_log(context, from_user, to_user, amount, transfer_hash, is_msg=False):
    try:
        log_chats = await get_log_chats()
        if not log_chats:
            return
        from_name = from_user.get('full_name') or from_user.get('username') or f"ID: {from_user['user_id']}"
        to_name = to_user.get('full_name') or to_user.get('username') or f"ID: {to_user['user_id']}"
        currency = "MSG" if is_msg else "ms¢"
        text = f"<tg-emoji emoji-id='5472030678633684592'>💸</tg-emoji> Совершен новый перевод\n" \
               f"Кто переводил: {from_name}\nКому: {to_name}\nСумма: {format_amount(amount)} {currency}\n" \
               f"<tg-emoji emoji-id='5258203794772085854'>⚡️</tg-emoji> Хэш перевода: <code>{transfer_hash}</code>"
        for chat_id in log_chats:
            try:
                await context.bot.send_message(chat_id=chat_id, text=text, parse_mode='HTML')
            except Exception as e:
                if "chat not found" in str(e).lower() or "forbidden" in str(e).lower():
                    await remove_log_chat(chat_id)
    except Exception as e:
        logging.error(f"Error in send_transfer_log: {e}")

async def setlogs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS and update.effective_user.id != MAIN_ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    if await add_log_chat(update.effective_chat.id, update.effective_user.id):
        await update.message.reply_text(f"✅ Чат «{update.effective_chat.title or 'Личный чат'}» добавлен в список логов переводов!")
    else:
        await update.message.reply_text("❌ Ошибка при добавлении чата.")

async def removelogs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS and update.effective_user.id != MAIN_ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    if await remove_log_chat(update.effective_chat.id):
        await update.message.reply_text("✅ Чат удален из списка логов переводов!")
    else:
        await update.message.reply_text("❌ Ошибка при удалении чата.")

async def track_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.chat:
        await add_bot_chat(update.message.chat.id, update.message.chat.title or "Личный чат", update.message.chat.type)

async def allchats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS and update.effective_user.id != MAIN_ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    parts = update.message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await update.message.reply_text(
            "❌ Использование: /allchats *текст*\n\n"
            "Для добавления кнопок:\n"
            "• inl|текст - обычная кнопка\n"
            "• inl|текст\"ссылка\" - кнопка с ссылкой\n\n"
            "Пример:\n/allchats Привет! inl|Нажми\"https://t.me/durov\""
        )
        return
    raw = parts[1]
    keyboard, final_text_lines = [], []
    for line in raw.split('\n'):
        if line.startswith('inl|'):
            button = line.replace('inl|', '').strip()
            match = re.search(r'(.+?)"([^"]+)"', button)
            if match:
                btn_text = match.group(1).strip()
                btn_url = match.group(2)
                if not btn_url.startswith(('http://', 'https://')):
                    btn_url = 'https://' + btn_url
                keyboard.append([InlineKeyboardButton(btn_text, url=btn_url)])
            else:
                keyboard.append([InlineKeyboardButton(button, callback_data="noop")])
        else:
            final_text_lines.append(line)
    text = '\n'.join(final_text_lines)
    progress = await update.message.reply_text("⏳ Начинаю рассылку по всем чатам...")
    chats = await get_all_chats()
    if not chats:
        await progress.edit_text("❌ Бот не добавлен ни в один чат.")
        return
    success, total = 0, len(chats)
    for chat_id in chats:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
            )
            success += 1
        except Exception as e:
            if "chat not found" in str(e).lower() or "forbidden" in str(e).lower():
                def _remove():
                    with get_db() as conn:
                        conn.execute("DELETE FROM bot_chats WHERE chat_id = %s", (chat_id,))
                        conn.commit()
                await asyncio.to_thread(_remove)
        await asyncio.sleep(0.1)
    await progress.edit_text(f"✅ Рассылка завершена!\n📊 Всего чатов: {total}\n✅ Успешно: {success}\n❌ Ошибок: {total - success}")

# ==================== ЧЕКИ ====================
async def newcheck_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("❌ Использование: /newcheck *активаций* *сумма*")
        return
    try:
        activations = int(context.args[0])
        amount = parse_amount(context.args[1])
        if activations <= 0 or amount <= 0:
            await update.message.reply_text("❌ Неверные значения.")
            return
    except:
        await update.message.reply_text("❌ Неверный формат.")
        return
    check_code = generate_check_code()
    await create_check_async(check_code, activations, amount)
    await update.message.reply_text(
        f"🧾 {update.effective_user.full_name}, вы успешно создали чек на {activations} активаций суммой {amount}ms¢\n\n"
        f"🔗 Ссылка для чека: https://t.me/{context.bot.username}?start=chk_{check_code}"
    )

async def checklist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    await update.message.reply_text(
        "☑ Нажмите ниже для просмотра чеков",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Просмотреть чеки", url=f"https://t.me/{context.bot.username}?start=listcheck_{update.effective_user.id}")]
        ])
    )

async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.inline_query
    if not q.query.strip().lower().startswith('чек '):
        return
    parts = q.query.strip().split()
    if len(parts) != 3:
        await q.answer([
            InlineQueryResultArticle(
                id='1',
                title='❌ Неправильный формат',
                description='Используй: чек [активаций] [сумма]',
                input_message_content=InputTextMessageContent(
                    '❌ Формат: чек *активаций* *сумма*\nПример: чек 5 100к',
                    parse_mode='Markdown'
                )
            )
        ], cache_time=1)
        return
    try:
        activations = int(parts[1])
        amount = parse_amount(parts[2])
        if activations <= 0 or activations > 100 or amount <= 0 or amount > 10000000:
            raise ValueError
    except:
        await q.answer([
            InlineQueryResultArticle(
                id='1',
                title='❌ Ошибка',
                description='Проверь формат',
                input_message_content=InputTextMessageContent(
                    '❌ Неверный формат. Используй: чек 5 100к'
                )
            )
        ], cache_time=1)
        return
    db_user = await get_user_async(q.from_user.id)
    total = amount * activations
    if db_user['balance'] < total:
        await q.answer([
            InlineQueryResultArticle(
                id='1',
                title='❌ Недостаточно средств',
                description=f'Нужно {format_amount(total)}ms¢',
                input_message_content=InputTextMessageContent(
                    f'❌ Недостаточно средств. Нужно {format_amount(total)}ms¢'
                )
            )
        ], cache_time=1)
        return
    await q.answer([
        InlineQueryResultArticle(
            id='1',
            title=f'🧾 Создать чек на {format_amount(amount)}ms¢',
            description=f'{activations} активаций • всего {format_amount(total)}ms¢',
            input_message_content=InputTextMessageContent(
                f"🧾 Вы хотите создать чек:\n"
                f"• Сумма: {format_amount(amount)}ms¢ за активацию\n"
                f"• Активаций: {activations}\n"
                f"• Всего списано: {format_amount(total)}ms¢\n\n"
                f"Подтверди создание 👇",
                parse_mode='HTML'
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Подтвердить создание", callback_data=f"confirm_user_check_{q.from_user.id}_{activations}_{amount}")]
            ])
        )
    ], cache_time=1)

async def handle_user_check(update: Update, context: ContextTypes.DEFAULT_TYPE, check_code: str):
    user = update.effective_user
    check = await get_user_check_async(check_code)
    if not check:
        await update.message.reply_text(f"❌ {user.full_name}, данного чека не существует.")
        return
    created_at = datetime.strptime(check['created_at'], '%Y-%m-%d %H:%M:%S')
    if datetime.now() > created_at + timedelta(hours=24):
        await update.message.reply_text(f"❌ {user.full_name}, срок действия чека истёк.")
        return
    if check['used_count'] >= check['max_activations']:
        await update.message.reply_text(f"❌ {user.full_name}, активации закончились.")
        return
    if check['creator_id'] == user.id:
        await update.message.reply_text(f"❌ {user.full_name}, нельзя активировать свой чек.")
        return
    creator = await get_user_async(check['creator_id'])
    creator_name = creator['full_name'] if creator else "Неизвестно"
    await update.message.reply_text(
        f"🧾 Информация о чеке:\n\n"
        f"👤 Создатель: {creator_name}\n"
        f"💰 Сумма: {format_amount(check['amount'])}ms¢\n"
        f"📊 Осталось активаций: {check['max_activations'] - check['used_count']}\n\n"
        f"Хотите активировать?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Активировать чек", callback_data=f"activate_user_check_{check_code}")]
        ])
    )

async def user_check_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not context.args or not context.args[0].startswith('userchk_'):
        return
    await handle_user_check(update, context, context.args[0].replace('userchk_', ''))


# last14.py - ЧАСТЬ 3/7 (MSG переводы, промокоды, продвижение, работа)

# ==================== MSG ПЕРЕВОДЫ ====================
async def msg_transfer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or await check_ban(update, context): return
    if update.effective_user.id not in ADMIN_IDS and not await check_subscription(update, context, update.effective_user.id):
        await send_subscription_prompt(update, context)
        return
    user = update.effective_user
    target_user = None
    amount = 0
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
        if context.args:
            amount = int(context.args[0]) if context.args[0].isdigit() else 0
    else:
        if len(context.args) < 2:
            await update.message.reply_text(
                "<blockquote>ℹ️ Для перевода MSG, следуй инструкции:</blockquote>\n\n"
                f"<b><u>msg *username* *кол-во*</u></b>\n\n"
                f"Пример: msg @durov 10",
                parse_mode='HTML'
            )
            return
        target_identifier = context.args[0]
        amount = int(context.args[1]) if context.args[1].isdigit() else 0
        if target_identifier.startswith('@'):
            ud = await get_user_by_username_async(target_identifier[1:])
            if not ud:
                await update.message.reply_text(f"❌ Пользователь {target_identifier} не найден.")
                return
            target_user = type('User', (), {'id': ud['user_id'], 'full_name': ud['full_name'] or target_identifier[1:]})()
        else:
            try:
                target_user = type('User', (), {'id': int(target_identifier), 'full_name': f"ID: {target_identifier}"})()
            except:
                await update.message.reply_text("❌ Неверный формат ID.")
                return
    if amount < 10:
        await update.message.reply_text("❌ Минимальная сумма перевода: 10 MSG")
        return
    if target_user.id == user.id:
        await update.message.reply_text("❌ Нельзя перевести MSG самому себе.")
        return
    db_user = await get_user_async(user.id)
    msg_balance = db_user.get('msg_balance', 0)
    if msg_balance < amount:
        await update.message.reply_text(f"❌ Недостаточно MSG. Ваш баланс: {format_amount(msg_balance)} MSG")
        return
    commission = amount // 10
    recipient_amount = amount - commission
    transfer_id = generate_transfer_hash()
    pending = context.bot_data.get('pending_msg_transfers', {})
    pending[transfer_id] = {
        'from_id': user.id,
        'from_name': user.full_name,
        'to_id': target_user.id,
        'to_name': target_user.full_name,
        'amount': amount,
        'commission': commission,
        'recipient_amount': recipient_amount,
        'time': time.time()
    }
    context.bot_data['pending_msg_transfers'] = pending
    await update.message.reply_text(
        f"<tg-emoji emoji-id='5402418909557053333'>🍯</tg-emoji> {user.full_name}, вы хотите перевести {amount} MSG пользователю <a href='tg://user?id={target_user.id}'>{target_user.full_name}</a>\n\n"
        f"🧾 Комиссия 10% ({commission} MSG)",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("☑ Подтверждаю", callback_data=f"confirm_msg_{transfer_id}")]]),
        parse_mode='HTML'
    )

async def confirm_msg_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE, transfer_id: str):
    query = update.callback_query
    pending = context.bot_data.get('pending_msg_transfers', {})
    if transfer_id not in pending or query.from_user.id != pending[transfer_id]['from_id']:
        await safe_answer(query, "❌ Перевод не найден или не ваша кнопка.")
        return
    t = pending[transfer_id]
    db_user = await get_user_async(t['from_id'])
    if db_user.get('msg_balance', 0) < t['amount']:
        await safe_answer(query, "❌ Недостаточно MSG.", show_alert=True)
        return
    success, _ = await transfer_msg_async(t['from_id'], t['to_id'], t['amount'])
    if not success:
        await safe_answer(query, "❌ Ошибка перевода", show_alert=True)
        return
    await query.edit_message_text(
        f"<tg-emoji emoji-id='5427009714745517609'>✅</tg-emoji> {t['from_name']}, вы успешно перевели {t['recipient_amount']} MSG пользователю {t['to_name']}\n"
        f"🧾 Комиссия съела {t['commission']} MSG\n"
        f"👨‍💻 Hash: {transfer_id}",
        parse_mode='HTML'
    )
    try:
        await context.bot.send_message(
            chat_id=t['to_id'],
            text=f"<tg-emoji emoji-id='5402418909557053333'>🍯</tg-emoji> {t['from_name']} перевел вам {t['recipient_amount']} MSG.",
            parse_mode='HTML'
        )
    except:
        pass
    try:
        await send_transfer_log(
            context,
            {'user_id': t['from_id'], 'full_name': t['from_name']},
            {'user_id': t['to_id'], 'full_name': t['to_name']},
            t['amount'], transfer_id, True
        )
    except:
        pass
    del pending[transfer_id]
    context.bot_data['pending_msg_transfers'] = pending
    await safe_answer(query, "✅ Перевод выполнен!")

async def give_msg_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS and update.effective_user.id != MAIN_ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    target_id = None
    amount = 0
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
        if context.args:
            amount = int(context.args[0]) if context.args[0].isdigit() else 0
    else:
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: !gmsg *@username* *кол-во*")
            return
        target = context.args[0]
        amount = int(context.args[1]) if context.args[1].isdigit() else 0
        if target.startswith('@'):
            ud = await get_user_by_username_async(target[1:])
            if not ud:
                await update.message.reply_text(f"❌ Пользователь {target} не найден.")
                return
            target_id = ud['user_id']
        else:
            try:
                target_id = int(target)
            except:
                await update.message.reply_text("❌ Неверный формат ID.")
                return
    if amount <= 0:
        await update.message.reply_text("❌ Неверная сумма.")
        return
    if await update_user_msg_async(target_id, amount):
        await update.message.reply_text(f"<tg-emoji emoji-id='5427009714745517609'>✅</tg-emoji> Успешно выдано {amount} MSG.", parse_mode='HTML')
    else:
        await update.message.reply_text("❌ Ошибка при выдаче MSG.")

async def take_msg_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS and update.effective_user.id != MAIN_ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    target_id = None
    amount = 0
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
        if context.args:
            amount = int(context.args[0]) if context.args[0].isdigit() else 0
    else:
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: !tmsg *@username* *кол-во*")
            return
        target = context.args[0]
        amount = int(context.args[1]) if context.args[1].isdigit() else 0
        if target.startswith('@'):
            ud = await get_user_by_username_async(target[1:])
            if not ud:
                await update.message.reply_text(f"❌ Пользователь {target} не найден.")
                return
            target_id = ud['user_id']
        else:
            try:
                target_id = int(target)
            except:
                await update.message.reply_text("❌ Неверный формат ID.")
                return
    if amount <= 0:
        await update.message.reply_text("❌ Неверная сумма.")
        return
    if await update_user_msg_async(target_id, -amount):
        await update.message.reply_text(f"<tg-emoji emoji-id='5427009714745517609'>✅</tg-emoji> Успешно списано {amount} MSG.", parse_mode='HTML')
    else:
        await update.message.reply_text("❌ Ошибка при списании MSG (возможно недостаточно средств).")

# ==================== ПРОМОКОДЫ ====================
async def setpromo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS and update.effective_user.id != MAIN_ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    if len(context.args) < 3:
        await update.message.reply_text("❌ Использование: /setpromo *активаций* *награда* *название*\nПример: /setpromo 100 10к пятница")
        return
    try:
        activations = int(context.args[0])
        reward = parse_amount(context.args[1])
        name = ' '.join(context.args[2:]).strip().lower()
        if activations <= 0 or reward <= 0 or not name:
            await update.message.reply_text("❌ Неверные значения.")
            return
    except:
        await update.message.reply_text("❌ Неверный формат.")
        return
    promo_id = await create_promo_async(activations, reward, name, update.effective_user.id)
    if promo_id:
        await update.message.reply_text(
            f"📃 Промокод «<b>{name}</b>» на <b>{activations}</b> активаций был создан!\n"
            f"💰 Награда: {format_amount(reward)}ms¢\n"
            f"🔍 Для активации используйте: промо {name}",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text("❌ Ошибка при создании промокода.")

async def checkprom_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS and update.effective_user.id != MAIN_ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    promos = await get_all_promos_async()
    if not promos:
        await update.message.reply_text("📃 Промокодов пока нет.")
        return
    text = "📃 <b>Список промокодов:</b>\n\n"
    for p in promos:
        text += f"🆔 <b>{p['id']}</b>: <code>{p['code']}</code> - {p['used_count']}/{p['max_activations']} акт. | {format_amount(p['reward_amount'])}ms¢\n"
    await update.message.reply_text(text, parse_mode='HTML')

async def delpromo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS and update.effective_user.id != MAIN_ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    if len(context.args) < 1:
        await update.message.reply_text("Использование: /delpromo *id*")
        return
    try:
        promo_id = int(context.args[0])
        promo = await get_promo_by_id_async(promo_id)
        if not promo:
            await update.message.reply_text("Промокод с таким ID не найден.")
            return
        if await delete_promo_async(promo_id):
            await update.message.reply_text(f"✅ Промокод «<b>{promo['code']}</b>» (ID: {promo_id}) удалён.", parse_mode='HTML')
        else:
            await update.message.reply_text("Ошибка при удалении промокода.")
    except:
        await update.message.reply_text("Неверный ID.")

async def promo_activate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user:
        return
    if update.effective_user.id not in ADMIN_IDS and not await check_subscription(update, context, update.effective_user.id):
        await send_subscription_prompt(update, context)
        return
    if not context.args:
        await update.message.reply_text("Использование: промо *название*")
        return
    code = ' '.join(context.args).strip().lower()
    promo = await get_promo_async(code)
    if not promo:
        await update.message.reply_text(f"{update.effective_user.full_name}, данного промокода не существует.")
        return
    if await check_user_promo_async(promo['id'], update.effective_user.id):
        await update.message.reply_text(f"{update.effective_user.full_name}, ты уже активировал этот промокод ☑")
        return
    if promo['used_count'] >= promo['max_activations']:
        await update.message.reply_text(f"{update.effective_user.full_name}, активации закончились.")
        return
    success, reward = await use_promo_async(code, update.effective_user.id)
    if success:
        await update_balance_async(update.effective_user.id, reward)
        await update.message.reply_text(
            f"{update.effective_user.full_name},<i> ты успешно активировал промокод «<b>{code}</b>» и получил {format_amount(reward)}ms¢!</i>",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(f"{update.effective_user.full_name}, ошибка при активации.")

# ==================== ПРОДВИЖЕНИЕ ====================
async def promotion_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user:
        return
    if update.effective_chat.type in ["group", "supergroup"]:
        await update.message.reply_text(
            f"⚙️ {update.effective_user.full_name}, продвижение доступно только в ЛС!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📱 Перейти в ЛС", url=f"https://t.me/{context.bot.username}?start=promotion")]])
        )
        return
    msg_balance = (await get_user_async(update.effective_user.id)).get('msg_balance', 0)
    await update.message.reply_text(
        f"⚙️ {update.effective_user.full_name}, что ты хочешь рекламировать?\n\n"
        f"⚠️ Продвигая канал/группу или же чат вы автоматически принимаете правила продвижения!\n\n"
        f"🍯 Баланс: {format_amount(msg_balance)} MSG",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Продвигать канал", callback_data="promo_channel")],
            [InlineKeyboardButton("💬 Продвигать чат/группу", callback_data="promo_chat")],
            [InlineKeyboardButton("🎯 Активные задания", callback_data="promo_my_tasks")],
            [InlineKeyboardButton("📕 Правила", callback_data="promo_rules")]
        ])
    )

async def promo_rules_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    text = (
        f"👨‍⚖️ *{query.from_user.full_name}*, общие положения*\n\n"
        "1. Нажимая /promotion в боте @monstrminesbot, вы соглашаетесь с этими правилами и правилами Telegram.\n\n"
        "2. Незнание правил не освобождает от ответственности.\n\n"
        "3. Вы несёте личную ответственность за контент своих каналов и чатов.\n\n"
        "❓ *Что запрещено продвигать*\n"
        "Если ваш канал или чат содержит что-либо из списка ниже он не будет принят, и вы можете лишиться доступа к продвижению:\n\n"
        "1. Порнография и эротика\n"
        "2. Политика и войны\n"
        "3. Запрещённая торговля\n"
        "4. Насилие, травля, жестокость\n"
        "5. Дезинформация и фейки\n"
        "6. Хакерство и доступы\n"
        "7. Спам и навязчивая реклама\n"
        "8. Нарушение приватности\n\n"
        "✅ *Что разрешено продвигать?*\n"
        "Почти всё кроме указано выше\n\n"
        "⚖️ *Наказание за нарушение*\n"
        "Ваше задание будет удалено без возвращения MSG. Продвижение для вас может стать недоступным навсегда. При грубых нарушениях — бан аккаунта.\n\n"
        "⚠️ *Важно*\n"
        "• Не пытайтесь обходить правила через звёздочки цензуру, временные замены контента\n"
        "• Если ваш канал выглядит нормально, но позже контент меняется на запрещённый — это также считается нарушением\n"
        "• Жалобы обрабатываются в течении 24-72 часов после жалобы. Пожаловаться на канал/чат можно используя кнопку пожаловаться в выполнении задания"
    )
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀ Назад", callback_data="promo_back_to_menu")]]), parse_mode='Markdown')

async def promo_price_input(update: Update, context: ContextTypes.DEFAULT_TYPE, promo_type: str):
    query = update.callback_query
    context.user_data.update({'promo_type': promo_type, 'promo_step': 'price'})
    await query.edit_message_text(
        f"👤 {query.from_user.full_name}, напишите цену за 1 подписчика!\n\n"
        f"⚠️ Минимальная цена за 1 подписчика — 1 MSG!\n"
        f"<blockquote>🔝 Чем выше цена за подписчика – тем выше будет в списке твое задание!</blockquote>",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("1 MSG", callback_data="promo_price_1"),
             InlineKeyboardButton("3 MSG", callback_data="promo_price_3"),
             InlineKeyboardButton("5 MSG", callback_data="promo_price_5")],
            [InlineKeyboardButton("◀ Назад", callback_data="promo_back_to_menu")]
        ]), parse_mode='HTML'
    )

async def promo_users_count(update: Update, context: ContextTypes.DEFAULT_TYPE, price: int):
    query = update.callback_query
    msg_balance = (await get_user_async(query.from_user.id)).get('msg_balance', 0)
    max_users = msg_balance // price
    context.user_data.update({'promo_price': price, 'promo_step': 'users', 'promo_max_users': max_users})
    await query.edit_message_text(
        f"🔶 {query.from_user.full_name}, введите количество подписчиков:\n\n🔘 Максимум: {max_users} чел.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("1 чел.", callback_data="promo_users_1"),
             InlineKeyboardButton("5 чел.", callback_data="promo_users_5"),
             InlineKeyboardButton("10 чел.", callback_data="promo_users_10")],
            [InlineKeyboardButton(f"Макс • {max_users} чел.", callback_data="promo_users_max")],
            [InlineKeyboardButton("◀ Назад", callback_data="promo_back_to_price")]
        ])
    )

async def promo_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, users_count: int):
    query = update.callback_query
    price = context.user_data.get('promo_price')
    promo_type = context.user_data.get('promo_type')
    total = price * users_count
    context.user_data.update({'promo_users': users_count, 'promo_total': total, 'promo_step': 'waiting_chat'})
    await query.edit_message_text(
        "❗ *Важно:*\n"
        "Канал должен быть публичным и без заявок на вступление\n"
        "Канал не должен содержать список нарушений указанных в правилах\n"
        "Соблюдайте правила! Мы не несём ответственность за ваш канал! В ином случае вы будете забанены навсегда!\n\n"
        "📝 *Инструкция по добавлению:*\n\n"
        "⬇️ Нажмите кнопку ниже и выберите канал/чат",
        parse_mode='Markdown'
    )
    from telegram import KeyboardButton, ReplyKeyboardMarkup, KeyboardButtonRequestChat, ChatAdministratorRights
    bot_rights = ChatAdministratorRights(
        is_anonymous=False, can_post_messages=False, can_edit_messages=False,
        can_delete_messages=False, can_invite_users=True, can_restrict_members=False,
        can_pin_messages=False, can_promote_members=True, can_change_info=False,
        can_manage_chat=False, can_manage_video_chats=False, can_post_stories=False,
        can_edit_stories=False, can_delete_stories=False
    )
    user_rights = ChatAdministratorRights(
        is_anonymous=False, can_change_info=True, can_post_messages=True,
        can_edit_messages=True, can_delete_messages=True, can_invite_users=True,
        can_restrict_members=True, can_pin_messages=True, can_promote_members=True,
        can_manage_chat=True, can_manage_video_chats=True, can_post_stories=True,
        can_edit_stories=True, can_delete_stories=True
    )
    if promo_type == 'channel':
        button = KeyboardButton("📢 Выбрать канал", request_chat=KeyboardButtonRequestChat(
            request_id=1, chat_is_channel=True, bot_administrator_rights=bot_rights, user_administrator_rights=user_rights
        ))
    else:
        button = KeyboardButton("💬 Выбрать чат/группу", request_chat=KeyboardButtonRequestChat(
            request_id=1, chat_is_channel=False, bot_administrator_rights=bot_rights, user_administrator_rights=user_rights
        ))
    await context.bot.send_message(
        chat_id=query.from_user.id,
        text="Выберите канал/чат для продвижения:",
        reply_markup=ReplyKeyboardMarkup([[button], [KeyboardButton("❌ Отменить")]], one_time_keyboard=True, resize_keyboard=True)
    )

async def promo_handle_chat_shared(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('promo_step') != 'waiting_chat':
        return
    cs = update.message.chat_shared
    if not cs or cs.request_id != 1:
        return
    chat_id = cs.chat_id
    promo_type = context.user_data.get('promo_type')
    price = context.user_data.get('promo_price')
    users = context.user_data.get('promo_users')
    total = context.user_data.get('promo_total')
    if not all([promo_type, price, users, total]):
        await update.message.reply_text("❌ Ошибка: данные не найдены. Начните заново.")
        context.user_data.clear()
        return
    if (await get_user_async(update.effective_user.id)).get('msg_balance', 0) < total:
        await update.message.reply_text("❌ Недостаточно средств.", reply_markup=ReplyKeyboardMarkup([]))
        context.user_data.clear()
        return
    try:
        link = (await context.bot.create_chat_invite_link(
            chat_id=chat_id, member_limit=users, creates_join_request=False
        )).invite_link
        task_id = await create_promotion_task(
            creator_id=update.effective_user.id,
            task_type='channel' if promo_type == 'channel' else 'chat',
            link=link,
            price_per_user=price,
            max_users=users,
            chat_id=chat_id
        )
        if task_id:
            await update.message.reply_text(
                f"✅ {update.effective_user.full_name}, твой {'канал' if promo_type == 'channel' else 'чат/группа'} успешно добавлен!\n🆔 ID задания: {task_id}",
                reply_markup=ReplyKeyboardMarkup([])
            )
            context.user_data.clear()
        else:
            await update.message.reply_text("❌ Ошибка при создании задания.", reply_markup=ReplyKeyboardMarkup([]))
    except Exception as e:
        await update.message.reply_text("❌ Не удалось создать пригласительную ссылку. Убедитесь, что бот имеет права.", reply_markup=ReplyKeyboardMarkup([]))
        context.user_data.clear()

# ==================== WORK (ЗАРАБОТАТЬ) ====================
async def work_command(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1):
    if not update.effective_user:
        return
    if update.effective_chat.type in ["group", "supergroup"]:
        await update.message.reply_text(
            f"⚙️ {update.effective_user.full_name}, заработок доступен только в ЛС!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📱 Перейти в ЛС", url=f"https://t.me/{context.bot.username}?start=work")]])
        )
        return
    if update.callback_query:
        query = update.callback_query
        user = query.from_user
        message = query.message
    else:
        user = update.effective_user
        message = update.message
    if user.id not in ADMIN_IDS and not await check_subscription(update, context, user.id):
        await send_subscription_prompt(update, context)
        return
    tasks = await get_available_tasks(user.id, page)
    total_pages = await get_available_total_pages(user.id)
    if not tasks:
        text = f"📝 {user.full_name}, сейчас нет доступных заданий!"
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Обновить", callback_data="work_refresh")]])
        if update.callback_query:
            await query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await message.reply_text(text, reply_markup=reply_markup)
        return
    text = f"📝 {user.full_name}, доступные задания:\n\n"
    for task in tasks:
        task_id, task_type, link, price, max_users, current = task
        text += f"🆔 {task_id} — {'Вступить в группу' if task_type == 'chat' else 'Подписаться на канал'} | +{price} MSG\n"
    keyboard = []
    row = []
    for i, task in enumerate(tasks[:3]):
        row.append(InlineKeyboardButton(f"🆔 {task[0]}", callback_data=f"work_task_{task[0]}"))
    if row:
        keyboard.append(row)
    row = []
    for i, task in enumerate(tasks[3:5]):
        row.append(InlineKeyboardButton(f"🆔 {task[0]}", callback_data=f"work_task_{task[0]}"))
    if row:
        keyboard.append(row)
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"work_page_{page-1}"))
    nav.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"work_page_{page+1}"))
    keyboard.append(nav)
    if update.callback_query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def work_task_view(update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int):
    query = update.callback_query
    def _get_task():
        with get_db() as conn:
            return conn.execute('SELECT task_type, link, price_per_user, creator_id FROM promotion_tasks WHERE task_id = %s AND status = %s', (task_id, 'active')).fetchone()
    task = await asyncio.to_thread(_get_task)
    if not task:
        await safe_answer(query, "❌ Задание не найдено или уже завершено", show_alert=True)
        return
    task_type, link, price, creator_id = task
    if creator_id == query.from_user.id:
        await safe_answer(query, "❌ Нельзя выполнять свое задание!", show_alert=True)
        return
    def _check_completed():
        with get_db() as conn:
            return conn.execute('SELECT id FROM completed_tasks WHERE task_id = %s AND user_id = %s', (task_id, query.from_user.id)).fetchone()
    if await asyncio.to_thread(_check_completed):
        await safe_answer(query, "❌ Вы уже выполнили это задание", show_alert=True)
        return
    action = "вступить в группу" if task_type == 'chat' else "подписаться на канал"
    await query.edit_message_text(
        f"🎯 Задание №{task_id} — {action}\n💰 Награда: {price} MSG\n\n⬇️ Выберите действие:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Перейти", url=link), InlineKeyboardButton("🔄 Проверить", callback_data=f"work_check_{task_id}")],
            [InlineKeyboardButton("⚠️ Пожаловаться", callback_data=f"work_report_{task_id}")],
            [InlineKeyboardButton("◀ Назад", callback_data="work_refresh")]
        ])
    )

async def work_check_task(update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int):
    query = update.callback_query
    await safe_answer(query, "⏳ Проверяю...")
    def _get_task():
        with get_db() as conn:
            return conn.execute('SELECT task_type, chat_id, price_per_user, creator_id FROM promotion_tasks WHERE task_id = %s AND status = %s', (task_id, 'active')).fetchone()
    task = await asyncio.to_thread(_get_task)
    if not task:
        await query.edit_message_text("❌ Задание не найдено или уже завершено")
        return
    task_type, chat_id, price, creator_id = task
    if creator_id == query.from_user.id:
        await query.edit_message_text("❌ Нельзя выполнять свое задание!")
        return
    if not chat_id:
        await query.edit_message_text("❌ Ошибка: ID чата не найден")
        return
    try:
        chat_member = await context.bot.get_chat_member(chat_id=chat_id, user_id=query.from_user.id)
        if chat_member.status in ['member', 'administrator', 'creator']:
            success, reward = await check_task_completion(task_id, query.from_user.id)
            if success:
                await query.edit_message_text(f"✅ {query.from_user.full_name}, вы выполнили задание! Получено {reward} MSG.")
                def _check_completion():
                    with get_db() as conn:
                        return conn.execute('SELECT current_users, max_users, creator_id FROM promotion_tasks WHERE task_id = %s', (task_id,)).fetchone()
                completed = await asyncio.to_thread(_check_completion)
                if completed and completed[0] >= completed[1]:
                    try:
                        await context.bot.send_message(chat_id=completed[2], text=f"✅ Ваше задание №{task_id} выполнено!")
                    except:
                        pass
            else:
                await query.edit_message_text("❌ Ошибка при начислении награды")
        else:
            await query.edit_message_text(f"❌ {query.from_user.full_name}, вы не подписались. Подпишитесь и нажмите кнопку еще раз.")
    except Exception as e:
        await query.edit_message_text("❌ Не удалось проверить подписку. Возможно, бот не является администратором.")

async def work_report_task(update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int):
    query = update.callback_query
    await query.edit_message_text(
        "Выберите причину:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔞 Онанизм", callback_data=f"work_report_reason_{task_id}_porn"),
             InlineKeyboardButton("💀 Расчленение", callback_data=f"work_report_reason_{task_id}_violence"),
             InlineKeyboardButton("📝 Другое", callback_data=f"work_report_reason_{task_id}_other")],
            [InlineKeyboardButton("◀ Назад", callback_data=f"work_task_{task_id}")]
        ])
    )

async def work_report_submit(update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int, reason: str):
    query = update.callback_query
    await report_task(task_id, query.from_user.id, reason)
    await query.edit_message_text("✅ Жалоба отправлена!")
    def _get_task_creator():
        with get_db() as conn:
            return conn.execute('SELECT creator_id, link FROM promotion_tasks WHERE task_id = %s', (task_id,)).fetchone()
    info = await asyncio.to_thread(_get_task_creator)
    if info:
        creator_id, link = info
        creator = await get_user_async(creator_id)
        creator_username = creator.get('username') or f"ID: {creator_id}"
        admin_text = f"✔ Жалоба на №{task_id}\nСоздатель: @{creator_username}\nКанал/чат: {link}\nПожаловался: {query.from_user.full_name} (ID: {query.from_user.id})\nПричина: {reason}"
        for aid in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=aid,
                    text=admin_text,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Удалить задание", callback_data=f"promo_admin_delete_{task_id}"),
                         InlineKeyboardButton("Оставить задание", callback_data=f"promo_admin_keep_{task_id}")]
                    ])
                )
            except:
                pass

async def my_tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1):
    query = update.callback_query
    tasks = await get_my_tasks(query.from_user.id, page)
    total_pages = await get_my_tasks_total_pages(query.from_user.id)
    if not tasks:
        await query.edit_message_text(
            f"📝 {query.from_user.full_name}, у вас пока нет созданных заданий!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀ Назад", callback_data="promo_back_to_menu")]])
        )
        return
    text = f"📝 {query.from_user.full_name}, ваши активные задания:\n\n"
    for task in tasks:
        task_id, task_type, link, price, max_users, current, status = task
        status_emoji = "✅" if status == 'completed' else "🔄" if current >= max_users else "⏳"
        text += f"{status_emoji} 🆔 {task_id} — {'Группа' if task_type == 'chat' else 'Канал'} | {current}/{max_users} | {price} MSG\n"
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"my_tasks_page_{page-1}"))
    nav.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"my_tasks_page_{page+1}"))
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([nav, [InlineKeyboardButton("◀ В меню", callback_data="promo_back_to_menu")]]))

async def promo_tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1):
    if update.callback_query:
        query = update.callback_query
        user_name = query.from_user.full_name
        message = query.message
    else:
        user_name = update.effective_user.full_name
        message = update.message
    tasks = await get_active_tasks(page)
    total_pages = await get_total_pages()
    if not tasks:
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("◀ Назад", callback_data="promo_back_to_menu")]])
        if update.callback_query:
            await query.edit_message_text(f"📝 {user_name}, активных заданий пока нет!", reply_markup=reply_markup)
        else:
            await message.reply_text(f"📝 {user_name}, активных заданий пока нет!", reply_markup=reply_markup)
        return
    text = f"📝 {user_name}, активные задания:\n\n"
    for task in tasks:
        task_id, task_type, link, price, max_users, current = task
        text += f"🆔 {task_id} — {'Вступить в группу' if task_type == 'chat' else 'Подписаться на канал'}\n"
    keyboard = []
    row = []
    for i, task in enumerate(tasks[:3]):
        row.append(InlineKeyboardButton(f"🆔 {task[0]}", callback_data=f"promo_task_{task[0]}"))
    keyboard.append(row)
    row = []
    for i, task in enumerate(tasks[3:5]):
        row.append(InlineKeyboardButton(f"🆔 {task[0]}", callback_data=f"promo_task_{task[0]}"))
    keyboard.append(row)
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"promo_tasks_page_{page-1}"))
    nav.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"promo_tasks_page_{page+1}"))
    keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("◀ В меню", callback_data="promo_back_to_menu")])
    if update.callback_query:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def promo_task_view(update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int):
    query = update.callback_query
    def _get_task():
        with get_db() as conn:
            return conn.execute('SELECT task_type, link, price_per_user FROM promotion_tasks WHERE task_id = %s AND status = %s', (task_id, 'active')).fetchone()
    task = await asyncio.to_thread(_get_task)
    if not task:
        await safe_answer(query, "❌ Задание не найдено или уже завершено", show_alert=True)
        return
    task_type, link, price = task
    action = "вступить в группу" if task_type == 'chat' else "подписаться на канал"
    await query.edit_message_text(
        f"🎯 Задание №{task_id} — {action}\n\n⬇️ Выберите действие:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Подписаться", url=link), InlineKeyboardButton("🔄 Проверить", callback_data=f"promo_check_{task_id}")],
            [InlineKeyboardButton("⚠️ Пожаловаться", callback_data=f"promo_report_{task_id}")],
            [InlineKeyboardButton("◀ Назад", callback_data="promo_tasks")]
        ])
    )

async def promo_check_task(update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int):
    query = update.callback_query
    await safe_answer(query, "⏳ Проверяю подписку...")
    def _get_task():
        with get_db() as conn:
            return conn.execute('SELECT task_type, link, price_per_user, creator_id FROM promotion_tasks WHERE task_id = %s AND status = %s', (task_id, 'active')).fetchone()
    task = await asyncio.to_thread(_get_task)
    if not task:
        await query.edit_message_text("❌ Задание не найдено или уже завершено")
        return
    task_type, link, price, creator_id = task
    if '/joinchat/' in link:
        invite_hash = link.split('/joinchat/')[-1]
    elif '/+' in link:
        invite_hash = link.split('/+')[-1]
    else:
        invite_hash = link.split('/')[-1]
    try:
        chat_id = None
        if invite_hash.startswith('+'):
            try:
                chat_info = await context.bot.get_chat(f"@{invite_hash[1:]}")
                chat_id = chat_info.id
            except:
                chat_id = invite_hash
        else:
            chat_id = invite_hash
        try:
            chat_member = await context.bot.get_chat_member(chat_id=chat_id, user_id=query.from_user.id)
            is_member = chat_member.status in ['member', 'administrator', 'creator']
        except:
            try:
                chat_member = await context.bot.get_chat_member(chat_id=f"@{invite_hash}", user_id=query.from_user.id)
                is_member = chat_member.status in ['member', 'administrator', 'creator']
            except:
                is_member = False
        if is_member:
            success, reward = await check_task_completion(task_id, query.from_user.id)
            if success:
                await query.edit_message_text(f"✅ {query.from_user.full_name}, ваша подписка найдена! Вам начислено {reward} MSG.")
                def _check_completion():
                    with get_db() as conn:
                        return conn.execute('SELECT current_users, max_users FROM promotion_tasks WHERE task_id = %s', (task_id,)).fetchone()
                completed = await asyncio.to_thread(_check_completion)
                if completed and completed[0] >= completed[1]:
                    try:
                        await context.bot.send_message(chat_id=creator_id, text=f"✅ Ваше задание №{task_id} выполнено!")
                    except:
                        pass
            else:
                await query.edit_message_text("❌ Ошибка при начислении награды")
        else:
            await query.edit_message_text(f"❌ {query.from_user.full_name}, вы не подписаны. Подпишитесь и нажмите кнопку еще раз.")
    except Exception as e:
        await query.edit_message_text("❌ Не удалось проверить подписку. Возможно, бот не является администратором.")

async def promo_report_task(update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int):
    query = update.callback_query
    await query.edit_message_text(
        "Выберите причину:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔞 Запрещенный контент", callback_data=f"promo_report_reason_{task_id}_forbidden"),
             InlineKeyboardButton("💀 Насилие", callback_data=f"promo_report_reason_{task_id}_violence"),
             InlineKeyboardButton("📝 Другое", callback_data=f"promo_report_reason_{task_id}_other")],
            [InlineKeyboardButton("◀ Назад", callback_data=f"promo_task_{task_id}")]
        ])
    )

async def promo_report_submit(update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int, reason: str):
    query = update.callback_query
    await report_task(task_id, query.from_user.id, reason)
    await query.edit_message_text("✅ Жалоба отправлена!")
    def _get_task_creator():
        with get_db() as conn:
            return conn.execute('SELECT creator_id, link FROM promotion_tasks WHERE task_id = %s', (task_id,)).fetchone()
    info = await asyncio.to_thread(_get_task_creator)
    if info:
        creator_id, link = info
        creator = await get_user_async(creator_id)
        creator_username = creator.get('username') or f"ID: {creator_id}"
        admin_text = f"✔ Жалоба на №{task_id}\nСоздатель: @{creator_username}\nКанал/чат: {link}\nПожаловался: {query.from_user.full_name} (ID: {query.from_user.id})\nПричина: {reason}"
        for aid in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=aid,
                    text=admin_text,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Удалить задание", callback_data=f"promo_admin_delete_{task_id}"),
                         InlineKeyboardButton("Оставить задание", callback_data=f"promo_admin_keep_{task_id}")]
                    ])
                )
            except:
                pass

# last14.py - ЧАСТЬ 4/7 (донат, бонус, кейсы, банк, акции, ключи, спринг)

# ==================== ДОНАТ ====================
async def donat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user: return
    if update.effective_chat.type in ["group", "supergroup"]:
        await update.message.reply_text(
            f"⚙️ {update.effective_user.full_name}, донат доступен только в ЛС!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📱 Перейти в ЛС", url=f"https://t.me/{context.bot.username}?start=donat")]])
        )
        return
    db_user = await get_user_async(update.effective_user.id)
    rate = await get_msg_rate()
    await update.message.reply_text(
        f"<tg-emoji emoji-id='5373351094883719887'>🍩</tg-emoji> {update.effective_user.full_name}, донат:\n\n"
        f"<tg-emoji emoji-id='5402418909557053333'>🍯</tg-emoji> Ваш баланс: {format_amount(db_user.get('msg_balance', 0))} MSG\n"
        f"<tg-emoji emoji-id='5402186569006210455'>💱</tg-emoji> Текущий курс: 1 MSG = {format_amount(rate)} ms¢",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💱 MSG to ms¢", callback_data="donat_exchange")],
            [InlineKeyboardButton("🛒 Донат", url="https://t.me/kleymorf")]
        ]), parse_mode='HTML'
    )

async def donat_exchange_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    db_user = await get_user_async(query.from_user.id)
    rate = await get_msg_rate()
    context.user_data['donat_step'] = 'waiting_amount'
    await query.edit_message_text(
        f"<tg-emoji emoji-id='5402186569006210455'>💱</tg-emoji> {query.from_user.full_name}, текущий курс за 1 MSG = {format_amount(rate)} ms¢\n"
        f"<tg-emoji emoji-id='5402418909557053333'>🍯</tg-emoji> У вас {format_amount(db_user.get('msg_balance', 0))} MSG, введите количество которое вы хотите обменять.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🍯 10 MSG", callback_data="donat_amount_10"),
             InlineKeyboardButton("🍯 50 MSG", callback_data="donat_amount_50"),
             InlineKeyboardButton("🍯 100 MSG", callback_data="donat_amount_100")],
            [InlineKeyboardButton(f"🍯 Макс: {format_amount(db_user.get('msg_balance', 0))} MSG", callback_data="donat_amount_max")],
            [InlineKeyboardButton("◀️ Назад", callback_data="donat_back")]
        ]), parse_mode='HTML'
    )

async def donat_amount_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, amount: int):
    query = update.callback_query
    db_user = await get_user_async(query.from_user.id)
    rate = await get_msg_rate()
    if amount > db_user.get('msg_balance', 0):
        await safe_answer(query, f"❌ У вас только {format_amount(db_user.get('msg_balance', 0))} MSG", show_alert=True)
        return
    msc = amount * rate
    context.user_data.update({'donat_amount': amount, 'donat_msc': msc})
    if 'donat_step' in context.user_data: del context.user_data['donat_step']
    await query.edit_message_text(
        f"<tg-emoji emoji-id='5258203794772085854'>⚡️</tg-emoji> {query.from_user.full_name}, вы уверены что хотите обменять {format_amount(amount)} MSG на {format_amount(msc)} ms¢?",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Подтверждаю", callback_data="donat_confirm")]]), parse_mode='HTML'
    )

async def donat_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    amount = context.user_data.get('donat_amount')
    msc = context.user_data.get('donat_msc')
    if not amount or not msc:
        await safe_answer(query, "❌ Ошибка: данные не найдены", show_alert=True)
        return
    db_user = await get_user_async(query.from_user.id)
    if db_user.get('msg_balance', 0) < amount:
        await safe_answer(query, f"❌ Недостаточно MSG. Баланс: {format_amount(db_user.get('msg_balance', 0))}", show_alert=True)
        context.user_data.clear()
        return
    await update_user_msg_async(query.from_user.id, -amount)
    await update_balance_async(query.from_user.id, msc)
    await query.edit_message_text(
        f"<tg-emoji emoji-id='5427009714745517609'>✅</tg-emoji> Вы успешно обменяли {format_amount(amount)} MSG на {format_amount(msc)} ms¢.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ В меню доната", callback_data="donat_back")]]), parse_mode='HTML'
    )
    context.user_data.clear()

async def donat_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    db_user = await get_user_async(query.from_user.id)
    rate = await get_msg_rate()
    await query.edit_message_text(
        f"<tg-emoji emoji-id='5373351094883719887'>🍩</tg-emoji> {query.from_user.full_name}, донат:\n\n"
        f"<tg-emoji emoji-id='5402418909557053333'>🍯</tg-emoji> Ваш баланс: {format_amount(db_user.get('msg_balance', 0))} MSG\n"
        f"<tg-emoji emoji-id='5402186569006210455'>💱</tg-emoji> Текущий курс: 1 MSG = {format_amount(rate)} ms¢",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💱 MSG to ms¢", callback_data="donat_exchange")],
            [InlineKeyboardButton("🛒 Донат", url="https://t.me/kleymorf")]
        ]), parse_mode='HTML'
    )

async def donat_handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('donat_step') != 'waiting_amount': return
    try:
        amount = int(update.message.text.strip())
    except:
        await update.message.reply_text("❌ Пожалуйста, введите число")
        return
    db_user = await get_user_async(update.effective_user.id)
    rate = await get_msg_rate()
    if amount <= 0:
        await update.message.reply_text("❌ Сумма должна быть больше 0")
        return
    if amount > db_user.get('msg_balance', 0):
        await update.message.reply_text(f"❌ У вас только {format_amount(db_user.get('msg_balance', 0))} MSG")
        return
    msc = amount * rate
    context.user_data.update({'donat_amount': amount, 'donat_msc': msc, 'donat_step': 'confirm'})
    await update.message.reply_text(
        f"<tg-emoji emoji-id='5258203794772085854'>⚡️</tg-emoji> {update.effective_user.full_name}, вы уверены что хотите обменять {format_amount(amount)} MSG на {format_amount(msc)} ms¢?",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Подтверждаю", callback_data="donat_confirm")]]), parse_mode='HTML'
    )

# ==================== ЕЖЕДНЕВНЫЙ БОНУС ====================
async def daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user: return
    can, _, hours, mins = await can_claim_daily(update.effective_user.id)
    if not can:
        await update.message.reply_text(f"😯 {update.effective_user.full_name}, вы уже забирали сегодня бонус! Приходите через {hours} ч. {mins} мин.", parse_mode='HTML')
        return
    await update.message.reply_text(
        f"🎁 {update.effective_user.full_name}, чтобы получить ежедневный бонус, следуйте инструкции:\n\n"
        f"1️⃣ — Добавьте юзер @monstrminesbot в описании профиля (раздел \"О себе\")\n"
        f"••••••••••••••••\n"
        f"2️⃣ — Написать любую команду бота @monstrminesbot\n"
        f"••••••••••••••••\n"
        f"3️⃣ — Забрать бонус.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Сделано", callback_data="daily_claim")]])
    )

async def daily_claim_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query, "⏳ Проверяю...")
    try:
        bio = (await context.bot.get_chat(query.from_user.id)).bio or ''
        if '@monstrminesbot' not in bio:
            await query.edit_message_text("❌ Вы не выполнили все условия! Добавьте @monstrminesbot в описание профиля.")
            return
    except:
        await query.edit_message_text("❌ Не удалось проверить профиль. Убедитесь, что у вас есть описание.")
        return
    can, streak, hours, mins = await can_claim_daily(query.from_user.id)
    if not can:
        await query.edit_message_text(f"😯 {query.from_user.full_name}, вы уже забирали сегодня бонус! Приходите через {hours} ч. {mins} мин.")
        return
    prize_type = random.choices(['money', 'case_daily', 'case_empty'], weights=[70, 15, 15])[0]
    if prize_type == 'money':
        amount = random.randint(10000, 100000)
        await update_balance_async(query.from_user.id, amount)
        await query.edit_message_text(f"✅ Вы получили {format_amount(amount)}ms¢!")
    elif prize_type == 'case_daily':
        await add_user_case(query.from_user.id, 'daily', 1)
        await query.edit_message_text(f"✅ Вы получили 🎊 Кейс «Daily»!")
    else:
        await add_user_case(query.from_user.id, 'empty', 1)
        await query.edit_message_text(f"✅ Вы получили 😑 Кейс «Пустышка»!")
    await claim_daily_bonus(query.from_user.id)

# ==================== КЕЙСЫ ====================
async def cases_command(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 1):
    if not update.effective_user: return
    user_cases = await get_user_cases(update.effective_user.id)
    if not user_cases:
        text = f"😯 {update.effective_user.full_name}, похоже у тебя нет кейсов!"
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Обновить", callback_data="cases_refresh")]])
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
        return
    user_cases.sort()
    items_per_page = 6
    total_pages = (len(user_cases) + items_per_page - 1) // items_per_page
    start_idx = (page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, len(user_cases))
    text = f"💼 {update.effective_user.full_name}, вот твои кейсы:\n\n"
    for i in range(start_idx, end_idx):
        case_type, quantity = user_cases[i]
        case_info = CASES_DATA.get(case_type, {'name': case_type, 'emoji': '📦'})
        text += f"{case_info['emoji']} {case_info['name']} — {quantity}шт.\n•••••••••••••\n"
    keyboard = []
    row = []
    for i in range(start_idx, end_idx):
        case_type, quantity = user_cases[i]
        case_info = CASES_DATA.get(case_type, {'name': case_type, 'emoji': '📦'})
        row.append(InlineKeyboardButton(f"{case_info['emoji']} {case_info['name']}", callback_data=f"case_open_{case_type}"))
        if len(row) == 3 or i == end_idx - 1:
            keyboard.append(row)
            row = []
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"cases_page_{page-1}"))
    nav.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"cases_page_{page+1}"))
    keyboard.append(nav)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def case_open_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, case_type: str):
    query = update.callback_query
    user_cases = await get_user_cases(query.from_user.id)
    if not any(ct == case_type and qty > 0 for ct, qty in user_cases):
        await safe_answer(query, "❌ У вас нет такого кейса!", show_alert=True)
        return
    cd = CASES_DATA.get(case_type, CASES_DATA['empty'])
    grid = []
    for _ in range(9):
        if random.randint(1, 100) <= cd['empty_chance']:
            grid.append({'type': 'empty', 'value': 0})
        else:
            grid.append({'type': 'money', 'value': random.randint(cd['min_reward'], cd['max_reward'])})
    sessions = context.bot_data.get('CASES_SESSIONS', {})
    sessions[query.from_user.id] = {
        'case_type': case_type,
        'grid': grid,
        'opened': [],
        'opens_left': cd['opens'],
        'total_reward': sum(g['value'] for g in grid if g['type'] == 'money'),
        'message_id': None,
        'chat_id': update.effective_chat.id,
        'thread_id': update.effective_message.message_thread_id,
        'status': 'active'
    }
    context.bot_data['CASES_SESSIONS'] = sessions
    keyboard = [[InlineKeyboardButton("ㅤ", callback_data=f"case_cell_{query.from_user.id}_{i+j}") for j in range(3)] for i in range(0, 9, 3)]
    await query.edit_message_text(f"🔑 {query.from_user.full_name}, открывай ячейки!\n\n", reply_markup=InlineKeyboardMarkup(keyboard))

async def case_cell_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, cell_idx: int):
    query = update.callback_query
    if query.from_user.id != user_id:
        await safe_answer(query, "🙈 Это не ваш кейс!", show_alert=True)
        return
    sessions = context.bot_data.get('CASES_SESSIONS', {})
    s = sessions.get(user_id)
    if not s or s['status'] != 'active':
        await safe_answer(query, "❌ Сессия открытия кейса не найдена", show_alert=True)
        return
    if cell_idx in s['opened']:
        await safe_answer(query, "❌ Эта ячейка уже открыта", show_alert=True)
        return
    if s['opens_left'] <= 0:
        await safe_answer(query, "❌ У вас больше нет попыток", show_alert=True)
        return
    s['opened'].append(cell_idx)
    s['opens_left'] -= 1
    text = f"🔑 {query.from_user.full_name}, открывай ячейки!\n\n"
    for i, idx in enumerate(s['opened'], 1):
        cell = s['grid'][idx]
        text += f"{i}️⃣ — {format_amount(cell['value'])}ms¢\n" if cell['type'] == 'money' else f"{i}️⃣ — пусто.\n"
    keyboard = []
    for i in range(0, 9, 3):
        row = []
        for j in range(3):
            idx = i + j
            if idx in s['opened']:
                row.append(InlineKeyboardButton("☑️" if s['grid'][idx]['type'] == 'money' else "⚪", callback_data=f"case_dead_{user_id}"))
            else:
                row.append(InlineKeyboardButton("ㅤ", callback_data=f"case_cell_{user_id}_{idx}"))
        keyboard.append(row)
    if s['opens_left'] == 0:
        s['status'] = 'finished'
        total_win = sum(s['grid'][idx]['value'] for idx in s['opened'] if s['grid'][idx]['type'] == 'money')
        await remove_user_case(user_id, s['case_type'], 1)
        if total_win > 0:
            await update_balance_async(user_id, total_win)
            text = f"🎊 {query.from_user.full_name}, кейс открыт!\n\n"
            for i, idx in enumerate(s['opened'], 1):
                cell = s['grid'][idx]
                text += f"{i}️⃣ — {format_amount(cell['value'])}ms¢\n" if cell['type'] == 'money' else f"{i}️⃣ — пусто.\n"
            text += f"\n💸 Общая сумма выигрыша {format_amount(total_win)}ms¢"
        else:
            text = f"😯 {query.from_user.full_name}, открытые ячейки были пусты."
        for i in range(0, 9, 3):
            for j in range(3):
                idx = i + j
                keyboard[i//3][j] = InlineKeyboardButton("☑️" if s['grid'][idx]['type'] == 'money' else "⚪", callback_data=f"case_finished_{user_id}")
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    if s['opens_left'] == 0:
        del sessions[user_id]
        context.bot_data['CASES_SESSIONS'] = sessions
    else:
        context.bot_data['CASES_SESSIONS'] = sessions

# ==================== БАНК ====================
async def bank_private_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user: return
    await update.message.reply_text(
        f"🏦 *{update.effective_user.full_name}*, добро пожаловать в \"Monst Bank\"\n\n"
        f"Здесь ты можешь создать депозит и обменять валюту (временно недоступно)\n\n"
        f"Выбери действие:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Создать депозит", callback_data="bank_create")],
            [InlineKeyboardButton("🏧 Список депозитов", callback_data="bank_list")],
            [InlineKeyboardButton("⏳ Конвертация", callback_data="bank_convert")]
        ]), parse_mode='Markdown'
    )

async def bank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user: return
    if update.effective_chat.type == "private":
        await bank_private_command(update, context)
    else:
        await update.message.reply_text(
            f"🏦 *{update.effective_user.full_name}*, банк доступен только в ЛС!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📱 Перейти в ЛС", url=f"https://t.me/{context.bot.username}?start=bank")]]), parse_mode='Markdown'
        )

async def bank_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user: return
    user_id = update.effective_user.id
    if user_id not in bank_creation_data or bank_creation_data[user_id].get('step') != 'custom_amount':
        return
    amount = parse_amount(update.message.text.strip())
    if amount <= 0 or amount > BANK_MAX_AMOUNT:
        await update.message.reply_text("❌ Неверная сумма.")
        return
    user = await get_user_async(user_id)
    if user['balance'] < amount:
        await update.message.reply_text(f"❌ Недостаточно средств. Баланс: {format_amount(user['balance'])}ms¢")
        return
    d = bank_creation_data[user_id]
    d['amount'] = amount
    d['step'] = 'confirm'
    success, deposit_id = await create_deposit_async(user_id, amount, d['days'], d['rate'])
    if not success:
        await update.message.reply_text(f"❌ {deposit_id}")
        del bank_creation_data[user_id]
        return
    d['deposit_id'] = deposit_id
    await update.message.reply_text(
        f"🏦 Вы хотите создать депозит 🆔 {deposit_id}.\n\n"
        f"💸 Сумма – {format_amount(amount)}ms¢.\n"
        f"Процентная ставка: {d['rate']}%\n\n"
        f"Подтвердите создание:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Создать", callback_data=f"bank_final_confirm_{deposit_id}")]])
    )

async def bank_create_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    bank_creation_data[user_id] = {'step': 'days'}
    await query.edit_message_text(
        f"ℹ️ Для создания депозита выберите количество дней для депозита.\n\nВыбери:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("1 день (3%)", callback_data="bank_days_1"),
             InlineKeyboardButton("3 дня (7%)", callback_data="bank_days_3"),
             InlineKeyboardButton("5 дней (11%)", callback_data="bank_days_5")],
            [InlineKeyboardButton("12 дней (12%)", callback_data="bank_days_12"),
             InlineKeyboardButton("30 дней (21%)", callback_data="bank_days_30")],
            [InlineKeyboardButton("🔙 Назад", callback_data="bank_back_to_menu")]
        ]), parse_mode='Markdown'
    )

async def bank_days_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    days = int(query.data.replace('bank_days_', ''))
    if user_id not in bank_creation_data:
        bank_creation_data[user_id] = {}
    bank_creation_data[user_id]['days'] = days
    bank_creation_data[user_id]['rate'] = BANK_INTEREST_RATES[days]
    bank_creation_data[user_id]['step'] = 'amount'
    await query.edit_message_text(
        f"🏦 Теперь выберите сумму депозита:\n\n"
        f"📅 Вы выбрали {days} дней ({BANK_INTEREST_RATES[days]}%)\n"
        f"⚠ Максимальная сумма депозита – {format_amount(BANK_MAX_AMOUNT)}ms¢.\n\n"
        f"Выберите:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(format_amount(BANK_PRESET_AMOUNTS[0]), callback_data=f"bank_amount_{BANK_PRESET_AMOUNTS[0]}"),
             InlineKeyboardButton(format_amount(BANK_PRESET_AMOUNTS[1]), callback_data=f"bank_amount_{BANK_PRESET_AMOUNTS[1]}")],
            [InlineKeyboardButton(format_amount(BANK_PRESET_AMOUNTS[2]), callback_data=f"bank_amount_{BANK_PRESET_AMOUNTS[2]}"),
             InlineKeyboardButton(format_amount(BANK_PRESET_AMOUNTS[3]), callback_data=f"bank_amount_{BANK_PRESET_AMOUNTS[3]}")],
            [InlineKeyboardButton(format_amount(BANK_PRESET_AMOUNTS[4]), callback_data=f"bank_amount_{BANK_PRESET_AMOUNTS[4]}")],
            [InlineKeyboardButton("💳 Другое", callback_data="bank_amount_custom")],
            [InlineKeyboardButton("🔙 Назад", callback_data="bank_create")]
        ]), parse_mode='Markdown'
    )

async def bank_amount_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    amount = int(query.data.replace('bank_amount_', ''))
    if user_id not in bank_creation_data or bank_creation_data[user_id].get('step') != 'amount':
        await safe_answer(query, "❌ Сессия создания депозита устарела", show_alert=True)
        return
    bank_creation_data[user_id]['amount'] = amount
    await bank_confirm_deposit(query, context, user_id)

async def bank_amount_custom_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if user_id not in bank_creation_data or bank_creation_data[user_id].get('step') != 'amount':
        await safe_answer(query, "❌ Сессия создания депозита устарела", show_alert=True)
        return
    bank_creation_data[user_id]['step'] = 'custom_amount'
    await query.edit_message_text(
        f"⚠ Введите сумму:\nМожно использовать к, кк\nМаксимум: {format_amount(BANK_MAX_AMOUNT)}ms¢"
    )

async def bank_confirm_deposit(query, context, user_id):
    d = bank_creation_data[user_id]
    amount, days, rate = d['amount'], d['days'], d['rate']
    user = await get_user_async(user_id)
    if user['balance'] < amount:
        await query.edit_message_text(f"❌ Недостаточно средств. Баланс: {format_amount(user['balance'])}ms¢")
        del bank_creation_data[user_id]
        return
    success, deposit_id = await create_deposit_async(user_id, amount, days, rate)
    if not success:
        await query.edit_message_text(f"❌ {deposit_id}")
        del bank_creation_data[user_id]
        return
    await update_balance_async(user_id, -amount)
    await query.edit_message_text(
        f"🏦 Вы хотите создать депозит 🆔 {deposit_id}.\n\n"
        f"💸 Сумма – {format_amount(amount)}ms¢.\n"
        f"Процентная ставка: {rate}%\n\n"
        f"Подтвердите создание:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Создать", callback_data=f"bank_final_confirm_{deposit_id}")]])
    )
    bank_creation_data[user_id]['step'] = 'final'

async def bank_final_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    deposit_id = int(query.data.replace('bank_final_confirm_', ''))
    deposit = await get_deposit_async(deposit_id)
    if not deposit or deposit['user_id'] != user_id or deposit['status'] != 'active':
        await safe_answer(query, "❌ Депозит не найден или уже неактивен", show_alert=True)
        return
    await query.edit_message_text(
        f"✅ Вы успешно создали депозит 🆔 {deposit_id}!\n\n"
        f"💸 Сумма: {format_amount(deposit['amount'])}ms¢\n"
        f"📅 Дней: {deposit['days']}\n"
        f"📊 Процент: {deposit['interest_rate']}%"
    )
    if user_id in bank_creation_data:
        del bank_creation_data[user_id]

async def bank_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    deposits = await get_user_deposits_async(user_id, 'active')
    if not deposits:
        await query.edit_message_text(
            f"🏧 *{query.from_user.full_name}*, у вас пока нет депозитов!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="bank_back_to_menu")]]), parse_mode='Markdown'
        )
        return
    text = f"🏧 *{query.from_user.full_name}*, список ваших депозитов:\n\n"
    now = datetime.now()
    for dep in deposits:
        try:
            expires = datetime.strptime(dep['expires_at'], '%Y-%m-%d %H:%M:%S')
        except:
            continue
        delta = expires - now
        text += f"🆔 {dep['deposit_id']} — {format_amount(dep['amount'])}ms¢ | {dep['interest_rate']}% — депозит снимется через {delta.days} дн. {delta.seconds//3600} ч. {(delta.seconds%3600)//60} мин. {delta.seconds%60} сек.\n\n"
    keyboard = []
    row = []
    for i, dep in enumerate(deposits):
        row.append(InlineKeyboardButton(f"🆔 {dep['deposit_id']}", callback_data=f"bank_view_{dep['deposit_id']}"))
        if len(row) == 3 or i == len(deposits) - 1:
            keyboard.append(row)
            row = []
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="bank_back_to_menu")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def bank_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    deposit_id = int(query.data.replace('bank_view_', ''))
    deposit = await get_deposit_async(deposit_id)
    if not deposit or deposit['user_id'] != query.from_user.id:
        await safe_answer(query, "❌ Депозит не найден", show_alert=True)
        return
    try:
        created = datetime.strptime(deposit['created_at'], '%Y-%m-%d %H:%M:%S')
        expires = datetime.strptime(deposit['expires_at'], '%Y-%m-%d %H:%M:%S')
    except:
        created = expires = datetime.now()
    delta = expires - datetime.now()
    final_amount = deposit['amount'] + (deposit['amount'] * deposit['interest_rate'] // 100)
    await query.edit_message_text(
        f"Депозит 🆔 {deposit_id}:\n\n"
        f"Депозит был создан: {created.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"💸 Сумма депозита – {format_amount(deposit['amount'])}ms¢\n"
        f"После истечения {delta.days} дн. {delta.seconds//3600} ч. вы получите {format_amount(final_amount)}ms¢.\n\n"
        f"Хотите снять депозит прямо сейчас?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Снять 💸", callback_data=f"bank_withdraw_{deposit_id}"),
             InlineKeyboardButton("Назад 🔙", callback_data="bank_list")]
        ]), parse_mode='Markdown'
    )

async def bank_withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    deposit_id = int(query.data.replace('bank_withdraw_', ''))
    deposit = await get_deposit_async(deposit_id)
    if not deposit or deposit['user_id'] != query.from_user.id:
        await safe_answer(query, "❌ Депозит не найден", show_alert=True)
        return
    penalty = deposit['amount'] * BANK_PENALTY_PERCENT // 100
    return_amount = deposit['amount'] - penalty
    await query.edit_message_text(
        f"Вы точно хотите снять депозит 🆔 {deposit_id}?\n\nВы получите {format_amount(return_amount)}ms¢",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Подтверждаю ✅", callback_data=f"bank_confirm_withdraw_{deposit_id}"),
             InlineKeyboardButton("Назад 🔙", callback_data=f"bank_view_{deposit_id}")]
        ]), parse_mode='Markdown'
    )

async def bank_confirm_withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    deposit_id = int(query.data.replace('bank_confirm_withdraw_', ''))
    deposit = await get_deposit_async(deposit_id)
    if not deposit or deposit['user_id'] != query.from_user.id:
        await safe_answer(query, "❌ Депозит не найден", show_alert=True)
        return
    success, return_amount = await close_deposit_async(deposit_id, BANK_PENALTY_PERCENT)
    if success:
        await update_balance_async(query.from_user.id, return_amount)
        await query.edit_message_text(f"✅ Вы успешно сняли депозит 🆔 {deposit_id}.\n💸 Получено: {format_amount(return_amount)}ms¢")
    else:
        await query.edit_message_text("❌ Ошибка при снятии депозита")

async def bank_convert_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query, "👨‍💻 Конвертация на доработках.", show_alert=True)

async def bank_back_to_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if user_id in bank_creation_data:
        del bank_creation_data[user_id]
    await query.edit_message_text(
        f"🏦 *{query.from_user.full_name}*, добро пожаловать в \"Monst Bank\"\n\n"
        f"Здесь ты можешь создать депозит и обменять валюту (временно недоступно)\n\n"
        f"Выбери действие:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Создать депозит", callback_data="bank_create")],
            [InlineKeyboardButton("🏧 Список депозитов", callback_data="bank_list")],
            [InlineKeyboardButton("⏳ Конвертация", callback_data="bank_convert")]
        ]), parse_mode='Markdown'
    )

# ==================== АКЦИИ ====================
async def stocks_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user: return
    await update.message.reply_text(
        "<tg-emoji emoji-id='5231200819986047254'>📊</tg-emoji>Акции – инвестируй и зарабатывай!*\n\n"
        "<tg-emoji emoji-id='5224257782013769471'>💰</tg-emoji>Покупай акции, следи за курсом и продавай, когда цена растёт.\n"
        "📈 Каждую минуту курсы меняются от -30% до +30%.\n"
        "💎 Доступные акции: Bitcoin (BTC), MonsterC (MSC), Telegram (TG).\n\n"
        "📌 *Команды:*\n"
        "• <code>мои акции</code> — твой портфель\n"
        "• <code>магазин или /shop</code> — купить акции\n"
        "• <code>/buyact ID количество</code> — быстрая покупка\n"
        "• <code>/sellact ID количество</code> — продажа",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📉 Курс-канал", url="https://t.me/monstraction")]]), parse_mode='HTML'
    )

async def buyact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or len(context.args) < 2:
        await update.message.reply_text("❌ Использование: buyact *id* *количество*")
        return
    try:
        stock_id = int(context.args[0])
        qty = int(context.args[1])
        if qty <= 0: raise ValueError
    except:
        await update.message.reply_text("❌ Неверный формат.")
        return
    stock = await get_stock_async(stock_id)
    if not stock:
        await update.message.reply_text("❌ Акция не найдена.")
        return
    if stock['current_price'] == 0:
        await update.message.reply_text("❌ Эта акция пока недоступна.")
        return
    success, res = await buy_stock_async(update.effective_user.id, stock_id, qty)
    await update.message.reply_text(f"✅ {update.effective_user.full_name}, вы купили {qty} {stock['symbol']} за {res}ms¢." if success else f"❌ {res}")

async def sellact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or len(context.args) < 2:
        await update.message.reply_text("❌ Использование: sellact *id* *количество или все*")
        return
    try:
        stock_id = int(context.args[0])
        if context.args[1].lower() == 'все':
            qty = await get_user_stock_quantity_async(update.effective_user.id, stock_id)
        else:
            qty = int(context.args[1])
        if qty <= 0: raise ValueError
    except:
        await update.message.reply_text("❌ Неверный формат.")
        return
    stock = await get_stock_async(stock_id)
    if not stock:
        await update.message.reply_text("❌ Акция не найдена.")
        return
    available = await get_user_stock_quantity_async(update.effective_user.id, stock_id)
    if available < qty:
        await update.message.reply_text(f"❌ У вас только {available} {stock['symbol']}.")
        return
    await update.message.reply_text(
        f"❓ {update.effective_user.full_name}, продать {stock['name']} в количестве {qty} шт. за сумму {stock['current_price'] * qty}ms¢.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Подтверждаю", callback_data=f"confirm_sell_{stock_id}_{qty}")]])
    )

async def shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user: return
    await update.message.reply_text("🛍️ Магазин:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📊 Акции", callback_data="shop_stocks")]]))

async def myaction_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user: return
    if update.message.text.lower() == "мои акции":
        total_val = await get_user_portfolio_total_async(update.effective_user.id)
        total_cnt = await get_user_portfolio_count_async(update.effective_user.id)
        await update.message.reply_text(
            f"💼 {update.effective_user.full_name}, ваши акции:\n\nℹ️ Сумма всех ваших акций – {total_val}ms¢\n\n📊 У вас {total_cnt} акций.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("ℹ️ Просмотреть акции", callback_data="view_stocks")]])
        )

# ==================== КЛЮЧИ ====================
async def msh_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or len(context.args) < 1:
        await update.message.reply_text("❌ Использование: /msh *ключ*")
        return
    key = await get_key(context.args[0].strip())
    if not key:
        await update.message.reply_text("⚪ Ключ не найден в базе! Будьте осторожны")
        return
    if key['status'] == 'scam':
        await update.message.reply_text("⚠️ Данный ключ занесён в скам базу!\nНе участвуйте в розыгрышах и др. раздачах.")
    elif key['status'] == 'verified':
        text = f"✅ Канал был верифицирован владельцем! Смело участвуйте и выигрывайте"
        if key.get('channel_name'):
            text += f"\n\n📢 Канал: {key['channel_name']}"
        await update.message.reply_text(text)
    else:
        await update.message.reply_text("✅ Ключ в безопасной базе! Можете участвовать")

async def gmsh_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS and update.effective_user.id != MAIN_ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("❌ Использование: /gmsh *ключ* *статус* [название_канала]\nСтатусы: scam, verified, safe")
        return
    key_code = context.args[0].strip()
    status = context.args[1].lower().strip()
    channel_name = ' '.join(context.args[2:]) if len(context.args) > 2 else None
    if status not in ['scam', 'verified', 'safe']:
        await update.message.reply_text("❌ Статус должен быть: scam, verified, safe")
        return
    if await add_key(key_code, status, update.effective_user.id, None, channel_name):
        await update.message.reply_text(f"✅ Ключ «{key_code}» создан со статусом «{status}»")
    else:
        await update.message.reply_text("❌ Ошибка при создании ключа")

async def rmsh_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS and update.effective_user.id != MAIN_ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    if len(context.args) < 1:
        await update.message.reply_text("❌ Использование: /rmsh *ключ*")
        return
    key = await get_key(context.args[0].strip())
    if not key:
        await update.message.reply_text(f"❌ Ключ не найден")
        return
    await update.message.reply_text(
        f"⚙️ *{update.effective_user.full_name}*, редактируйте ключ *{context.args[0]}*\n\n📊 Текущий статус: *{key['status']}*",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⚠️ Скам", callback_data=f"key_edit_{context.args[0]}_scam"),
             InlineKeyboardButton("✅ Верифицирован", callback_data=f"key_edit_{context.args[0]}_verified"),
             InlineKeyboardButton("🟢 Безопасный", callback_data=f"key_edit_{context.args[0]}_safe")],
            [InlineKeyboardButton("❌ Удалить", callback_data=f"key_delete_{context.args[0]}")]
        ]), parse_mode='Markdown'
    )

async def key_edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, key_code: str, status: str):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS and query.from_user.id != MAIN_ADMIN_ID:
        await safe_answer(query, "❌ У вас нет прав", show_alert=True)
        return
    await update_key_status(key_code, status)
    status_names = {'scam': '⚠️ Скам', 'verified': '✅ Верифицирован', 'safe': '🟢 Безопасный'}
    await query.edit_message_text(f"✅ Ключ «{key_code}» обновлен. Новый статус: {status_names.get(status, status)}")
    await safe_answer(query, "✅ Готово")

async def key_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, key_code: str):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS and query.from_user.id != MAIN_ADMIN_ID:
        await safe_answer(query, "❌ У вас нет прав", show_alert=True)
        return
    await delete_key(key_code)
    await query.edit_message_text(f"✅ Ключ «{key_code}» удален из базы")
    await safe_answer(query, "✅ Удалено")

# ==================== SPRING EVENT ====================
async def sprevent_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user: return
    if datetime.now() < SPRING_EVENT_START:
        await update.message.reply_text("🌸 Ивент еще не начался! Ожидайте 1 марта 2026 года.")
        return
    await update.message.reply_text(
        f"☀️ *{update.effective_user.full_name}*, добро пожаловать в ивент \"Весенний блик!\"\n\n"
        f"ℹ️ Твоя задача выполнить как можно больше заданий получив больше солнышек.\n\n"
        f"⏳ В конце ивента вы сможете обменять солнышки на очень щедрые призы!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🤫 Весенние тайны", callback_data="spring_mysteries")],
            [InlineKeyboardButton("☀️ Сбор солнышек", callback_data="spring_collect")],
            [InlineKeyboardButton("💱 Обменник", callback_data="spring_exchange")],
            [InlineKeyboardButton("🏰 Весенний замок", callback_data="spring_castle")],
            [InlineKeyboardButton("🎯 Задания", callback_data="spring_tasks")]
        ]), parse_mode='Markdown'
    )

async def answer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or len(context.args) < 2:
        await update.message.reply_text("❌ Использование: /answer *айди* *ответ*")
        return
    try:
        qid = int(context.args[0])
        ans = ' '.join(context.args[1:]).strip().lower()
    except:
        await update.message.reply_text("❌ Неверный формат ID вопроса.")
        return
    q = await get_spring_question_async(qid)
    if not q:
        await update.message.reply_text("❌ Вопрос не найден.")
        return
    if q['solved_by']:
        await update.message.reply_text("❌ На этот вопрос уже ответили.")
        return
    if ans != q['answer'].strip().lower():
        await update.message.reply_text("❌ Неправильный ответ. Попробуй еще!")
        return
    if not await solve_spring_question_async(qid, update.effective_user.id):
        await update.message.reply_text("❌ Кто-то уже ответил быстрее!")
        return
    prize_text = ""
    if q['prize_type'] == 'coins':
        await update_balance_async(update.effective_user.id, int(q['prize_value']))
        prize_text = f"{format_amount(int(q['prize_value']))}ms¢"
    elif q['prize_type'] == 'gold':
        prize_text = f"{int(q['prize_value'])}🍩 ms'gold"
    elif q['prize_type'] == 'sun':
        await add_user_suns_async(update.effective_user.id, int(q['prize_value']))
        prize_text = f"{int(q['prize_value'])}☀️ солнышек"
    else:
        prize_text = f"🎁 {q['prize_value']}"
    await update.message.reply_text(f"✅ {update.effective_user.full_name}, вы угадали вопрос.\nВаш приз: {prize_text}.")

async def question_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS and update.effective_user.id != MAIN_ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    if len(context.args) < 1:
        await update.message.reply_text("❌ Использование: /question *вопрос|ответ*")
        return
    full = ' '.join(context.args)
    if '|' not in full:
        await update.message.reply_text("❌ Используйте формат: вопрос|ответ")
        return
    q, a = full.split('|', 1)
    q, a = q.strip(), a.strip()
    if not q or not a:
        await update.message.reply_text("❌ Вопрос и ответ не могут быть пустыми.")
        return
    spring_question_creation[update.effective_user.id] = {'question': q, 'answer': a, 'step': 'prize_type'}
    await update.message.reply_text(
        f"👮‍♂️ Вы установили вопрос «{q}»\nТеперь укажите награду",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💸 ms'coin", callback_data="spring_prize_coins"),
             InlineKeyboardButton("🍩 ms'gold", callback_data="spring_prize_gold")],
            [InlineKeyboardButton("🙊 Секретный приз", callback_data="spring_prize_secret"),
             InlineKeyboardButton("☀️ Солнышки", callback_data="spring_prize_sun")]
        ])
    )

async def spring_prize_value_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in spring_question_creation or spring_question_creation[uid].get('step') != 'prize_value':
        return
    d = spring_question_creation[uid]
    pt = d['prize_type']
    val = update.message.text.strip()
    if pt in ['coins', 'gold', 'sun']:
        try:
            parsed = parse_amount(val) if pt in ['coins', 'gold'] else int(val)
            if parsed <= 0: raise ValueError
        except:
            await update.message.reply_text("❌ Неверный формат числа.")
            return
    else:
        parsed = val
    await create_spring_question_async(question=d['question'], answer=d['answer'], prize_type=pt, prize_value=str(parsed))
    del spring_question_creation[uid]
    await update.message.reply_text("✅ Вопрос успешно добавлен!")

async def exchange_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user: return
    if datetime.now() < SPRING_EVENT_END:
        await update.message.reply_text("❌ Обменник откроется 1 июня 2026 года.")
        return
    if len(context.args) < 1:
        await update.message.reply_text("❌ Использование: /exchange *количество*")
        return
    try:
        amount = int(context.args[0])
    except:
        await update.message.reply_text("❌ Неверный формат числа.")
        return
    if amount not in [100, 500, 1000, 5000]:
        await update.message.reply_text("❌ Доступные значения: 100, 500, 1000, 5000")
        return
    suns = await get_user_suns_async(update.effective_user.id)
    if suns < amount:
        await update.message.reply_text(f"❌ У вас только {suns}☀️. Нужно {amount}☀️.")
        return
    rewards = {100: 1000, 500: 6000, 1000: 15000}
    if amount in rewards:
        await update_balance_async(update.effective_user.id, rewards[amount])
        await add_user_suns_async(update.effective_user.id, -amount)
        await update.message.reply_text(f"✅ Вы обменяли {amount}☀️ на {rewards[amount]}ms¢!")
    else:
        await add_user_suns_async(update.effective_user.id, -amount)
        await update.message.reply_text(f"🎁 {update.effective_user.full_name}, вы получили секретный приз!\nСвяжитесь с администратором: @ahpeplov")

async def put_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or len(context.args) < 1:
        await update.message.reply_text("❌ Использование: /put *айди задания*")
        return
    try:
        tid = int(context.args[0])
    except:
        await update.message.reply_text("❌ Неверный формат ID.")
        return
    task = await get_spring_task_async(tid)
    if not task:
        await update.message.reply_text("❌ Задание не найдено.")
        return
    prog = await get_user_task_progress_async(update.effective_user.id, tid)
    if prog['completed'] == 0:
        await update.message.reply_text("❌ Задание еще не выполнено.")
        return
    if prog['claimed'] == 1:
        await update.message.reply_text("❌ Вы уже получили награду за это задание.")
        return
    success, prize, suns = await claim_task_reward_async(update.effective_user.id, tid)
    if success:
        await update_balance_async(update.effective_user.id, prize)
        await add_user_suns_async(update.effective_user.id, suns)
        await update.message.reply_text(f"✅ {update.effective_user.full_name}, вы выполнили задание и получили {format_amount(prize)}ms¢ и {suns}☀️")
    else:
        await update.message.reply_text("❌ Ошибка при получении награды.")

async def add_task_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS and update.effective_user.id != MAIN_ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Использование: /addtask *описание|цель|мин_награда|макс_награда|мин_солн|макс_солн|тип_игры*\n\n"
            "Типы игр: mines, gold, pyramid, slot, football, basketball, knb, transfer\n"
            "Пример: /addtask Сыграй в мины|5|100|500|1|5|mines"
        )
        return
    parts = ' '.join(context.args).split('|')
    if len(parts) != 7:
        await update.message.reply_text("❌ Должно быть 7 частей, разделенных |")
        return
    desc = parts[0].strip()
    try:
        target = int(parts[1].strip())
        pmin = int(parts[2].strip())
        pmax = int(parts[3].strip())
        smin = int(parts[4].strip())
        smax = int(parts[5].strip())
    except:
        await update.message.reply_text("❌ Цель и награды должны быть числами.")
        return
    gtype = parts[6].strip()
    valid = ['mines', 'gold', 'pyramid', 'slot', 'football', 'basketball', 'knb', 'transfer', None]
    if gtype not in valid and gtype != 'None':
        await update.message.reply_text(f"❌ Неверный тип игры. Допустимые: {', '.join(valid)}")
        return
    tid = await create_spring_task_async(description=desc, target_count=target, prize_min=pmin, prize_max=pmax, sun_min=smin, sun_max=smax, game_type=gtype if gtype != 'None' else None)
    await update.message.reply_text(f"✅ Задание №{tid} успешно создано!")

# last14.py - ЧАСТЬ 5/7 (ивенты, админка, бан/мут, матконкурс, техработы, топы, курс MSG)

# ==================== ИВЕНТЫ ====================
async def events_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user: return
    events = await get_all_events_async()
    available = [e for e in events if e['status'] in ['active', 'scheduled']]
    keyboard = [[InlineKeyboardButton(f"🕘 {e['name']}" if e['status'] == 'scheduled' else e['name'], callback_data=f"event_view_{e['event_id']}")] for e in available] or [[InlineKeyboardButton("⌛ Ожидаем ивенты...", callback_data="noop")]]
    await update.message.reply_text(
        f"🦩 *{update.effective_user.full_name}*, добро пожаловать в категорию \"Ивенты\"\n\nℹ️ Тут ты сможешь увидеть ивенты, которые доступны или будут доступны в ближайшее время!",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
    )

async def setevent_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS and update.effective_user.id != MAIN_ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    await update.message.reply_text(
        "Выберите категорию ивента:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🕘 Запланированный", callback_data="event_type_scheduled"),
             InlineKeyboardButton("🚀 Готовый", callback_data="event_type_ready")]
        ])
    )

async def closeevent_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS and update.effective_user.id != MAIN_ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    events = await get_all_events_async()
    keyboard = [[InlineKeyboardButton(e['name'], callback_data=f"event_close_{e['event_id']}")] for e in events if e['status'] != 'closed']
    if not keyboard:
        await update.message.reply_text("❌ Нет открытых ивентов для закрытия.")
        return
    await update.message.reply_text("🌍 Выберите ивент для внепланового закрытия:", reply_markup=InlineKeyboardMarkup(keyboard))

async def event_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'event_creation' not in context.user_data: return
    d = context.user_data['event_creation']
    step = d.get('step')
    if d['type'] == 'scheduled':
        if step == 'date':
            if not re.match(r'^\d{2}\.\d{2}\.\d{4}$', update.message.text):
                await update.message.reply_text("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ")
                return
            d['date'], d['step'] = update.message.text, 'name'
            await update.message.reply_text("Принял! А теперь напишите название будущего ивента.")
        elif step == 'name':
            d['name'], d['step'] = update.message.text, 'description'
            await update.message.reply_text("🙈 Теперь введите описание ивента.")
        elif step == 'description':
            d['description'], d['step'] = update.message.text, 'confirm'
            await update.message.reply_text(
                f"❕ Проверьте анкету перед созданием!\n\nℹ️ \"{d['name']}\" — {d['description']}.\n\nЗапланировано на {d['date']}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Верно", callback_data="event_confirm_yes"),
                     InlineKeyboardButton("🗿 Сомневаюсь", callback_data="event_confirm_no")]
                ])
            )
    else:
        if step == 'date':
            d['name'], d['step'] = update.message.text, 'description'
            await update.message.reply_text("Введите описание ивента:")
        elif step == 'description':
            d['description'], d['step'] = update.message.text, 'confirm'
            await update.message.reply_text(
                f"❗ Перед отправкой ГОТОВОГО ивента убедитесь в правильности формата:\n\nℹ️ *{d['name']}* — {d['description']}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Готово", callback_data="event_confirm_yes"),
                     InlineKeyboardButton("🗿 Сомневаюсь", callback_data="event_confirm_no")]
                ]), parse_mode='Markdown'
            )

async def event_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    event_id = int(query.data.replace('event_view_', ''))
    event = await get_event_async(event_id)
    if not event:
        await safe_answer(query, "❌ Ивент не найден", show_alert=True)
        return
    if event['status'] == 'scheduled':
        text = f"✨ *{event['name']}* — {event['description']}\n\n📅 Запланировано на {event['date']}"
        keyboard = [[InlineKeyboardButton("🕘 Ивент пока недоступен", callback_data="noop")]]
    elif event['status'] == 'active':
        text = f"✨ *{event['name']}* — {event['description']}"
        keyboard = []
    else:
        text = f"✨ *{event['name']}*"
        keyboard = [[InlineKeyboardButton("❗ Временно закрыт", callback_data="noop")]]
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def event_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    ADMIN_IDS = context.bot_data.get('ADMIN_IDS', [])
    MAIN_ADMIN_ID = context.bot_data.get('MAIN_ADMIN_ID')
    if user_id not in ADMIN_IDS and user_id != MAIN_ADMIN_ID:
        await safe_answer(query, "❌ У вас нет прав", show_alert=True)
        return
    event_type = query.data.replace('event_type_', '')
    context.user_data['event_creation'] = {'type': event_type, 'step': 'date'}
    if event_type == 'scheduled':
        await query.edit_message_text("📅 Введите запланированную дату ивента:\nПример: 24.03.2026")
    else:
        await query.edit_message_text("Введите название ивента:")

async def event_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action = query.data.replace('event_confirm_', '')
    if 'event_creation' not in context.user_data:
        await safe_answer(query, "❌ Сессия создания ивента не найдена", show_alert=True)
        return
    d = context.user_data['event_creation']
    if action == 'no':
        del context.user_data['event_creation']
        await query.edit_message_text("❌ Создание ивента отменено. Начните заново с /setevent")
        await safe_answer(query, "")
        return
    if d['type'] == 'scheduled':
        await create_event_async(name=d['name'], description=d['description'], date=d['date'], status='scheduled')
    else:
        await create_event_async(name=d['name'], description=d['description'], status='active')
    await query.edit_message_text("✅ Ивент успешно создан!")
    del context.user_data['event_creation']

async def event_close_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    event_id = int(query.data.replace('event_close_', ''))
    event = await get_event_async(event_id)
    if not event:
        await safe_answer(query, "❌ Ивент не найден", show_alert=True)
        return
    context.user_data['closing_event_id'] = event_id
    await query.edit_message_text(
        f"ℹ️ *{event['name']}* — {event['description']}\n\nВы хотите закрыть данный ивент?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Да", callback_data="event_close_confirm_yes"),
             InlineKeyboardButton("Нет ⛔", callback_data="event_close_confirm_no")]
        ]), parse_mode='Markdown'
    )

async def event_close_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if data == "event_close_confirm_yes":
        action = "yes"
    elif data == "event_close_confirm_no":
        action = "no"
    else:
        await safe_answer(query, "❌ Неизвестное действие", show_alert=True)
        return
    if action == 'no':
        await query.edit_message_text("Успешно...")
        await asyncio.sleep(1)
        await query.delete_message()
        await safe_answer(query, "")
        return
    event_id = context.user_data.get('closing_event_id')
    if not event_id:
        await safe_answer(query, "❌ Ошибка: ивент не найден", show_alert=True)
        return
    await update_event_status_async(event_id, 'closed')
    await query.edit_message_text("Закрываю...")
    await asyncio.sleep(1)
    await query.delete_message()
    await safe_answer(query, "✅ Ивент закрыт")

# ==================== АДМИНСКИЕ КОМАНДЫ ====================
async def give_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
        target = f"ID: {target_id}"
        if len(context.args) < 1:
            await update.message.reply_text("❌ Использование при ответе: !give *summ*")
            return
        amount = parse_amount(' '.join(context.args))
    else:
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: !give *id or @username* *summ*")
            return
        target = context.args[0]
        amount = parse_amount(' '.join(context.args[1:]))
        if target.startswith('@'):
            ud = await get_user_by_username_async(target[1:])
            if not ud:
                await update.message.reply_text(f"❌ Пользователь {target} не найден.")
                return
            target_id = ud['user_id']
        else:
            try:
                target_id = int(target)
            except:
                await update.message.reply_text("❌ Неверный формат ID.")
                return
    if amount <= 0:
        await update.message.reply_text("❌ Неверная сумма.")
        return
    await update_balance_async(target_id, amount)
    await update.message.reply_text(f"✅ Пользователю {target} начислено {amount}ms¢.")

async def take_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
        target = f"ID: {target_id}"
        if len(context.args) < 1:
            await update.message.reply_text("❌ Использование при ответе: !take *summ*")
            return
        amount = parse_amount(' '.join(context.args))
    else:
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: !take *id or @username* *summ*")
            return
        target = context.args[0]
        amount = parse_amount(' '.join(context.args[1:]))
        if target.startswith('@'):
            ud = await get_user_by_username_async(target[1:])
            if not ud:
                await update.message.reply_text(f"❌ Пользователь {target} не найден.")
                return
            target_id = ud['user_id']
        else:
            try:
                target_id = int(target)
            except:
                await update.message.reply_text("❌ Неверный формат ID.")
                return
    if amount <= 0:
        await update.message.reply_text("❌ Неверная сумма.")
        return
    success = await update_balance_safe_async(target_id, -amount, amount)
    await update.message.reply_text(f"✅ У пользователя {target} списано {amount}ms¢." if success else f"❌ Недостаточно средств у пользователя {target}.")

async def checkhash_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    if len(context.args) < 1:
        await update.message.reply_text("❌ Использование: !checkhash *hash*")
        return
    game = await get_game_hash_async(context.args[0])
    if not game:
        await update.message.reply_text(f"❌ Хэш {context.args[0]} не найден.")
        return
    await update.message.reply_text(
        f"ℹ️ Хэш {context.args[0]}.\n"
        f"Информация: Игра: {game['game_type']}.\n"
        f"Ставка: {game['bet']}ms¢.\n"
        f"Была окончена: {'выигрышем' if game['result'] == 'win' else 'проигрышем' if game['result'] == 'lose' else game['result']}."
    )

async def tcheckhash_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    if len(context.args) < 1:
        await update.message.reply_text("❌ Использование: !tcheckhash *hash*")
        return
    tc = context.bot_data.get('transfer_confirmations', {}).get(context.args[0])
    if not tc:
        await update.message.reply_text(f"❌ Хэш перевода {context.args[0]} не найден.")
        return
    await update.message.reply_text(
        f"ℹ️ Хэш перевода {context.args[0]}.\n"
        f"Отправитель: {tc['from_id']}\n"
        f"Получатель: {tc['to_id']}\n"
        f"Сумма: {tc['amount']}ms¢\n"
        f"Статус: {'подтвержден' if tc.get('completed') else 'ожидает подтверждения'}"
    )

async def reset_stocks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS and update.effective_user.id != MAIN_ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    await update.message.reply_text(
        "⚠️ *ВНИМАНИЕ!*\n\n"
        "Вы собираетесь сбросить ВСЕ акции до 0:\n"
        "• Курсы всех акций станут 0ms¢\n"
        "• Все портфели пользователей будут очищены\n"
        "• Это действие необратимо\n\n"
        "Для подтверждения нажмите кнопку ниже:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚠️ ПОДТВЕРДИТЬ СБРОС", callback_data="confirm_reset_stocks")]]),
        parse_mode='Markdown'
    )

async def reset_stocks_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS and query.from_user.id != MAIN_ADMIN_ID:
        await safe_answer(query, "❌ У вас нет прав", show_alert=True)
        return
    if query.data == "confirm_reset_stocks":
        await safe_answer(query, "⏳ Выполняется сброс...")
        try:
            stocks = await get_all_stocks_async()
            await update_all_stocks_prices_async([(s['stock_id'], 0) for s in stocks])
            await clear_all_portfolios_async()
            await query.edit_message_text(
                "✅ *Все акции успешно сброшены до 0!*\n\n"
                "• Курсы акций обнулены\n"
                "• Портфели пользователей очищены",
                parse_mode='Markdown'
            )
            if KURS_CHANNEL:
                await context.bot.send_message(
                    chat_id=KURS_CHANNEL,
                    text="⚠️ *АДМИНИСТРАТОР СБРОСИЛ ВСЕ АКЦИИ ДО 0*\n\nВсе курсы обнулены. Ожидайте возобновления торгов.",
                    parse_mode='Markdown'
                )
        except Exception as e:
            logging.error(f"Error resetting stocks: {e}")
            await query.edit_message_text("❌ Произошла ошибка при сбросе акций.")

async def set_stocks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS and update.effective_user.id != MAIN_ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    await update.message.reply_text(
        "⚠️ *Подтверждение*\n\n"
        "Вы собираетесь установить ВСЕ акции на 100ms¢.\n"
        "Цены будут изменены, но портфели пользователей останутся без изменений.\n\n"
        "Продолжить?",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ ПОДТВЕРДИТЬ", callback_data="confirm_set_stocks_100")]]),
        parse_mode='Markdown'
    )

async def set_stocks_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS and query.from_user.id != MAIN_ADMIN_ID:
        await safe_answer(query, "❌ У вас нет прав", show_alert=True)
        return
    if query.data == "confirm_set_stocks_100":
        await safe_answer(query, "⏳ Устанавливаем цены...")
        try:
            stocks = await get_all_stocks_async()
            await update_all_stocks_prices_async([(s['stock_id'], 100) for s in stocks])
            await query.edit_message_text(
                "✅ *Все акции установлены на 100ms¢!*\n\n"
                "• Bitcoin: 100ms¢\n"
                "• MonsterC: 100ms¢\n"
                "• Telegram: 100ms¢",
                parse_mode='Markdown'
            )
            if KURS_CHANNEL:
                await context.bot.send_message(
                    chat_id=KURS_CHANNEL,
                    text="📊 *АДМИНИСТРАТОР УСТАНОВИЛ ВСЕ АКЦИИ НА 100ms¢*\n\nТорги продолжаются с новой базовой ценой.",
                    parse_mode='Markdown'
                )
        except Exception as e:
            logging.error(f"Error setting stocks: {e}")
            await query.edit_message_text("❌ Произошла ошибка при установке цен.")

# ==================== БАН / МУТ / КИК ====================
async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != MAIN_ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
        if len(context.args) < 1:
            await update.message.reply_text("❌ Использование: /ban *сколько дней* *причина*")
            return
        try:
            days = int(context.args[0])
        except:
            await update.message.reply_text("❌ Неверный формат дней.")
            return
        reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Не указана"
    else:
        if len(context.args) < 2:
            await update.message.reply_text("❌ Использование: /ban *id or @username* *сколько дней* *причина*")
            return
        target = context.args[0]
        try:
            days = int(context.args[1])
        except:
            await update.message.reply_text("❌ Неверный формат дней.")
            return
        reason = ' '.join(context.args[2:]) if len(context.args) > 2 else "Не указана"
        if target.startswith('@'):
            ud = await get_user_by_username_async(target[1:])
            if not ud:
                await update.message.reply_text(f"❌ Пользователь {target} не найден.")
                return
            target_id = ud['user_id']
        else:
            try:
                target_id = int(target)
            except:
                await update.message.reply_text("❌ Неверный формат ID.")
                return
    if target_id in ADMIN_IDS:
        await update.message.reply_text("❌ Нельзя забанить администратора.")
        return
    await ban_user_async(target_id, days, reason)
    await update.message.reply_text(f"👮‍♂️ Вы успешно забанили пользователя {'навсегда' if days == 0 else f'на {days} дней'} по причине: {reason}.")
    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=f"🚨 Вы были заблокированы в боте {'навсегда' if days == 0 else f'на {days} дней'} по причине: {reason}\n\n❓ Не согласны? Нажмите кнопку ниже",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🧐 Не согласен", url="https://t.me/kleymorf")]])
        )
    except:
        pass

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != MAIN_ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    else:
        if len(context.args) < 1:
            await update.message.reply_text("❌ Использование: /unban *id or @username*")
            return
        target = context.args[0]
        if target.startswith('@'):
            ud = await get_user_by_username_async(target[1:])
            if not ud:
                await update.message.reply_text(f"❌ Пользователь {target} не найден.")
                return
            target_id = ud['user_id']
        else:
            try:
                target_id = int(target)
            except:
                await update.message.reply_text("❌ Неверный формат ID.")
                return
    if not await is_user_banned_async(target_id):
        await update.message.reply_text(f"❌ Пользователь не находится в бане.")
        return
    await unban_user_async(target_id)
    await update.message.reply_text(f"✅ Пользователь успешно разбанен.")
    try:
        await context.bot.send_message(chat_id=target_id, text=f"✅ Ваша блокировка в боте снята.")
    except:
        pass

async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_chat.type not in ["group", "supergroup"]:
        return
    try:
        cm = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if cm.status not in ['administrator', 'creator']:
            await update.message.reply_text("❌ Эта команда только для администраторов.")
            return
    except:
        await update.message.reply_text("❌ Не удалось проверить права.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Ответьте на сообщение пользователя.")
        return
    target = update.message.reply_to_message.from_user
    try:
        tm = await context.bot.get_chat_member(update.effective_chat.id, target.id)
        if tm.status in ['administrator', 'creator']:
            await update.message.reply_text("❌ Нельзя заглушить администратора.")
            return
    except:
        pass
    mute_time = 10
    if context.args:
        try:
            ts = ' '.join(context.args).lower()
            nums = re.findall(r'\d+', ts)
            if nums:
                mute_time = int(nums[0])
                if 'час' in ts:
                    mute_time *= 60
        except:
            pass
    if mute_time > 1440:
        mute_time = 1440
    try:
        from datetime import datetime, timedelta
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=target.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=datetime.now() + timedelta(minutes=mute_time)
        )
        mins_text = "минуту" if mute_time % 10 == 1 and mute_time % 100 != 11 else "минуты" if 2 <= mute_time % 10 <= 4 and (mute_time % 100 < 10 or mute_time % 100 >= 20) else "минут"
        await update.message.reply_text(f"🔇 <b>{target.full_name}</b> был заглушён на <b>{mute_time}</b> {mins_text}.", parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text("❌ Не удалось заглушить пользователя. Убедитесь, что бот является администратором.")

async def kick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_chat.type not in ["group", "supergroup"]:
        return
    try:
        cm = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        if cm.status not in ['administrator', 'creator']:
            await update.message.reply_text("Эта команда только для администраторов.")
            return
    except:
        await update.message.reply_text("Не удалось проверить права.")
        return
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
        target_name = update.message.reply_to_message.from_user.full_name
    else:
        if not context.args:
            await update.message.reply_text("Использование: • Ответьте на сообщение: /кик\n• Или укажите: /кик *id*")
            return
        try:
            target_id = int(context.args[0])
            try:
                target_name = (await context.bot.get_chat_member(update.effective_chat.id, target_id)).user.full_name
            except:
                target_name = f"ID: {target_id}"
        except:
            await update.message.reply_text("Неверный формат.")
            return
    try:
        tm = await context.bot.get_chat_member(update.effective_chat.id, target_id)
        if tm.status in ['administrator', 'creator']:
            await update.message.reply_text("Нельзя кикнуть администратора.")
            return
    except:
        pass
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target_id)
        await context.bot.unban_chat_member(update.effective_chat.id, target_id)
        await update.message.reply_text(f"<blockquote>👢 {target_name} был выпнут из беседы.</blockquote>", parse_mode='HTML')
    except:
        await update.message.reply_text("Не удалось кикнуть пользователя.")

# ==================== МАТЕМАТИЧЕСКИЙ КОНКУРС ====================
async def math_contest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS and update.effective_user.id != MAIN_ADMIN_ID:
        return
    parts = update.message.text.strip().split()
    if len(parts) < 2:
        await update.message.reply_text("❌ Использование: !mt *сумма* или мт *сумма*")
        return
    prize = parse_amount(parts[1])
    if prize <= 0:
        await update.message.reply_text("❌ Неверная сумма.")
        return
    mc = context.bot_data.get('math_contest_pending', {})
    mc[update.effective_user.id] = {'prize': prize}
    context.bot_data['math_contest_pending'] = mc
    await update.message.reply_text(
        f"👨‍⚖️ Конкурс на {format_amount(prize)}ms¢ уже готов!\n\nОсталось ждать подтверждения от администратора...",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Подтверждаю", callback_data="math_contest_confirm")]])
    )

async def math_contest_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS and query.from_user.id != MAIN_ADMIN_ID:
        await safe_answer(query, "Не наглей!🤬", show_alert=True)
        return
    mc = context.bot_data.get('math_contest_pending', {})
    if query.from_user.id not in mc:
        await safe_answer(query, "❌ Конкурс не найден", show_alert=True)
        return
    prize = mc[query.from_user.id]['prize']
    q, opts, correct = generate_math_problem()
    cid = await create_math_contest_async(prize, q, opts[correct], opts, query.from_user.id)
    keyboard = [
        [InlineKeyboardButton(str(opt), callback_data=f"math_answer_{cid}_{i}") for i, opt in enumerate(opts[:5])],
        [InlineKeyboardButton(str(opt), callback_data=f"math_answer_{cid}_{i}") for i, opt in enumerate(opts[5:])]
    ]
    msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"🧮 Math-конкурс!\n\n💸 Награда — {format_amount(prize)}ms¢.\n📝 Пример — {q}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await start_math_contest_async(cid, msg.message_id, update.effective_chat.id)
    del mc[query.from_user.id]
    context.bot_data['math_contest_pending'] = mc

async def math_answer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split('_')
    if len(parts) != 4:
        await safe_answer(query, "❌ Ошибка", show_alert=True)
        return
    cid, idx = int(parts[2]), int(parts[3])
    contest = await get_math_contest_async(cid)
    if not contest or contest['status'] != 'active':
        await safe_answer(query, "❌ Конкурс не найден или завершен", show_alert=True)
        return
    if not await can_user_attempt_async(cid, query.from_user.id):
        last = await get_user_last_attempt_time_async(cid, query.from_user.id)
        if last:
            last_time = datetime.strptime(last, '%Y-%m-%d %H:%M:%S.%f')
            diff = (datetime.now() - last_time).total_seconds()
            if diff < MATH_CONTEST_COOLDOWN:
                await safe_answer(query, f"Подождите {round(MATH_CONTEST_COOLDOWN - diff, 1)} секунд", show_alert=True)
                return
        await safe_answer(query, "✖ Неправильный вариант", show_alert=True)
        return
    is_correct = contest['options'][idx] == contest['correct_answer']
    await add_math_attempt_async(cid, query.from_user.id, idx, is_correct)
    if is_correct:
        if await finish_math_contest_async(cid, query.from_user.id, query.from_user.full_name):
            await update_balance_async(query.from_user.id, contest['prize_amount'])
            await query.edit_message_text(
                f"🧮 Math-конкурс окончен!\n\n"
                f"💸 Награда — {format_amount(contest['prize_amount'])}ms¢ была доставлена пользователю {query.from_user.full_name}\n\n"
                f"Правильный ответ был {contest['correct_answer']}.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏆 Конкурс завершен", callback_data="noop")]])
            )
            await safe_answer(query, f"✅ Вы выиграли {format_amount(contest['prize_amount'])}ms¢!", show_alert=True)
        else:
            await safe_answer(query, "❌ Кто-то уже ответил раньше", show_alert=True)
    else:
        await safe_answer(query, "✖ Неправильный вариант", show_alert=True)

# ==================== ТЕХНИЧЕСКИЕ РАБОТЫ ====================
async def workcondit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS and update.effective_user.id != MAIN_ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    await set_work_conditions(True, update.effective_user.id)
    msg = await update.message.reply_text("Done.")
    try:
        await update.message.delete()
    except:
        pass
    await asyncio.sleep(2)
    try:
        await msg.delete()
    except:
        pass

async def setcondit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS and update.effective_user.id != MAIN_ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    await set_work_conditions(False, update.effective_user.id)
    msg = await update.message.reply_text("Done.")
    try:
        await update.message.delete()
    except:
        pass
    await asyncio.sleep(2)
    try:
        await msg.delete()
    except:
        pass

# ==================== UNTOP / RETURN TOP ====================
async def untop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS and update.effective_user.id != MAIN_ADMIN_ID:
        await update.message.reply_text("Ахуел?")
        return
    if update.message.reply_to_message:
        await add_to_top_exclude_async(update.message.reply_to_message.from_user.id)
        await update.message.reply_text(f"Пользователю {update.message.reply_to_message.from_user.full_name} был наложен ТБАН.\nID: {update.message.reply_to_message.from_user.id}")
        return
    if len(context.args) < 1:
        await update.message.reply_text("Использование: /антоп *@username* или /антоп *id*")
        return
    target = context.args[0]
    if target.startswith('@'):
        ud = await get_user_by_username_async(target[1:])
        if not ud:
            await update.message.reply_text(f"Пользователь @{target[1:]} не найден.")
            return
        tid, tname = ud['user_id'], ud['full_name'] or target[1:]
    else:
        try:
            tid = int(target)
            ud = await get_user_async(tid)
            tname = ud.get('full_name') or ud.get('username') or str(tid)
        except:
            await update.message.reply_text("Неверный ID.")
            return
    await add_to_top_exclude_async(tid)
    await update.message.reply_text(f"Пользователю {tname} был наложен ТБАН.\nID: {tid}")

async def return_top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS and update.effective_user.id != MAIN_ADMIN_ID:
        await update.message.reply_text("У вас нет прав.")
        return
    if len(context.args) < 1:
        await update.message.reply_text("Использование: /втоп *@username* или /втоп *id*")
        return
    target = context.args[0]
    if target.startswith('@'):
        ud = await get_user_by_username_async(target[1:])
        if not ud:
            await update.message.reply_text(f"Пользователь @{target[1:]} не найден.")
            return
        tid, tname = ud['user_id'], ud['full_name'] or target[1:]
    else:
        try:
            tid = int(target)
            ud = await get_user_async(tid)
            tname = ud.get('full_name') or ud.get('username') or str(tid)
        except:
            await update.message.reply_text("Неверный формат ID.")
            return
    await remove_from_top_exclude_async(tid)
    await update.message.reply_text(f"Пользователь {tname} возвращён в топ.\nID: {tid}")

# ==================== КУРС MSG ====================
async def update_msg_rate_job(context: ContextTypes.DEFAULT_TYPE):
    rate = await get_msg_rate()
    if rate >= 48000:
        force_down, force_up = True, False
    elif rate <= 27000:
        force_down, force_up = False, True
    else:
        force_down = force_up = False
    if force_up or (not force_down and random.choice([True, False])):
        new_rate = rate + random.randint(500, 2000)
        change = "📈"
    else:
        new_rate = rate - random.randint(300, 1500)
        change = "📉"
    new_rate = max(25000, min(50000, new_rate))
    await update_msg_rate(new_rate)
    try:
        await context.bot.send_message(
            chat_id=context.bot_data.get('KURS_MSG_CHANNEL', '@kursmsgmonstr'),
            text=f"<tg-emoji emoji-id='5375338737028841420'>🔄</tg-emoji> MSG: {change} {format_amount(new_rate)} ms¢",
            parse_mode='HTML'
        )
    except:
        pass

async def set_msg_rate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id not in ADMIN_IDS and update.effective_user.id != MAIN_ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав.")
        return
    if len(context.args) < 1:
        await update.message.reply_text("❌ Использование: !setmsgrate *курс*")
        return
    try:
        new_rate = int(context.args[0])
        if new_rate < 1000:
            await update.message.reply_text("❌ Курс не может быть меньше 1000")
            return
        await update_msg_rate(new_rate)
        await update.message.reply_text(f"✅ Курс MSG установлен: {format_amount(new_rate)} ms¢")
        try:
            await context.bot.send_message(
                chat_id=context.bot_data.get('KURS_MSG_CHANNEL', '@kursmsgmonstr'),
                text=f"<tg-emoji emoji-id='5375338737028841420'>🔄</tg-emoji> MSG: 📊 {format_amount(new_rate)} ms¢ (установлено администратором)",
                parse_mode='HTML'
            )
        except:
            pass
    except:
        await update.message.reply_text("❌ Неверный формат числа")

# ==================== SPRING EVENT CALLBACKS ====================
async def spring_mysteries_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.edit_message_text(
        f"🤫 *{user.full_name}*, разгадай тайны весны 2026 года, получи огромный бонус за разгаданные тайны\n\n"
        f"Загадки будут пополняться раз в неделю, первый отгадавший загадку получит бонус\n\n"
        f"🤫 Следи за пополнение загадок и всей информацией в нашем телеграмм канале",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📣 Канал", url=SPRING_CHANNEL)],
            [InlineKeyboardButton("🤫 Загадки", callback_data="spring_questions_list")],
            [InlineKeyboardButton("🔙 Назад", callback_data="spring_back_to_menu")]
        ]), parse_mode='Markdown'
    )

async def spring_questions_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    questions = await get_all_spring_questions_async()
    if not questions:
        await query.edit_message_text(
            f"🙈 *{user.full_name}*, загадки разобрали! Следи за пополнением в канале",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📣 Канал", url=SPRING_CHANNEL)],
                [InlineKeyboardButton("🔙 Назад", callback_data="spring_mysteries")]
            ]), parse_mode='Markdown'
        )
        return
    text = f"🍩 *{user.full_name}*, доступные вопросы:\n\n"
    for q in questions:
        text += f"🆔 {q['id']} - {q['question']}\n\n"
    text += f"ℹ️ Для ответа используйте: /answer *айди вопроса* *ответ*\n"
    text += f"Пример: /answer 92 Яблоко"
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📣 Канал", url=SPRING_CHANNEL)],
            [InlineKeyboardButton("🔙 Назад", callback_data="spring_mysteries")]
        ]), parse_mode='Markdown'
    )

async def spring_collect_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    can, mins, secs = await can_collect_sun_async(user.id, 5400)
    if not can:
        await safe_answer(query, f"⏳ Вы уже собирали солнышки, подождите {mins} мин. {secs} сек.", show_alert=True)
        return
    amount = random.randint(1, 99)
    await collect_sun_async(user.id)
    await add_user_suns_async(user.id, amount)
    total = await get_user_suns_async(user.id)
    await query.edit_message_text(
        f"☀️ *{user.full_name}*, вы собрали {amount} солнышек!\n"
        f"📊 Всего у вас: {total}☀️\n\n"
        f"⏳ Следующий сбор будет доступен через 90 минут.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="spring_back_to_menu")]]),
        parse_mode='Markdown'
    )
    await safe_answer(query, f"✅ +{amount}☀️")

async def spring_exchange_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    if datetime.now() < SPRING_EVENT_END:
        await query.edit_message_text(
            f"💱 *{user.full_name}*, обменник еще не доступен!\n\n"
            f"📅 Откроется 1 июня 2026 года.\n"
            f"Копите солнышки до этого времени!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="spring_back_to_menu")]]),
            parse_mode='Markdown'
        )
        return
    suns = await get_user_suns_async(user.id)
    await query.edit_message_text(
        f"💱 *{user.full_name}*, обменник открыт!\n\n"
        f"☀️ У вас {suns} солнышек\n\n"
        f"🔄 Доступные обмены:\n"
        f"• 100☀️ → 1000ms¢\n"
        f"• 500☀️ → 6000ms¢\n"
        f"• 1000☀️ → 15000ms¢\n"
        f"• 5000☀️ → Секретный приз\n\n"
        f"ℹ️ Для обмена напишите /exchange *количество*",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="spring_back_to_menu")]]),
        parse_mode='Markdown'
    )

async def spring_castle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.edit_message_text(
        f"🏰 *{user.full_name}*, добро пожаловать в наш замок!\n\n"
        f"Это замок бота Monstmines.\n\n"
        f"Ожидай появления и доработки в нашем телеграмм канале.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📣 Канал", url=SPRING_CHANNEL)],
            [InlineKeyboardButton("🔙 Назад", callback_data="spring_back_to_menu")]
        ]), parse_mode='Markdown'
    )

async def spring_tasks_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    tasks = await get_all_spring_tasks_async()
    user_tasks = await get_all_user_tasks_async(user.id)
    if not tasks:
        await query.edit_message_text(
            f"⏳ *{user.full_name}*, заданий пока нет, ожидайте пополнения.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="spring_back_to_menu")]]),
            parse_mode='Markdown'
        )
        return
    progress = {}
    for ut in user_tasks:
        progress[ut['id']] = {'progress': ut['progress'], 'completed': ut['completed'], 'claimed': ut['claimed']}
    text = f"📒 *{user.full_name}*, доступные задания:\n\n"
    for task in tasks:
        tid = task['id']
        p = progress.get(tid, {'progress': 0, 'completed': 0, 'claimed': 0})
        status = "✅" if p['completed'] == 1 and p['claimed'] == 0 else "🎁" if p['completed'] == 1 and p['claimed'] == 1 else "⏳"
        text += f"🆔 {tid} {task['description']}\n"
        text += f"Прогресс: {status} {p['progress']} из {task['target_count']}\n\n"
    text += f"ℹ️ Если выполнил задания, введи /put *айди*\n"
    text += f"⏱ Задания обновляются каждый день в 00:00 по МСК"
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="spring_back_to_menu")]]),
        parse_mode='Markdown'
    )

async def spring_back_to_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.edit_message_text(
        f"☀️ *{user.full_name}*, добро пожаловать в ивент \"Весенний блик!\"\n\n"
        f"ℹ️ Твоя задача выполнить как можно больше заданий получив больше солнышек.\n\n"
        f"⏳ В конце ивента вы сможете обменять солнышки на очень щедрые призы!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🤫 Весенние тайны", callback_data="spring_mysteries")],
            [InlineKeyboardButton("☀️ Сбор солнышек", callback_data="spring_collect")],
            [InlineKeyboardButton("💱 Обменник", callback_data="spring_exchange")],
            [InlineKeyboardButton("🏰 Весенний замок", callback_data="spring_castle")],
            [InlineKeyboardButton("🎯 Задания", callback_data="spring_tasks")]
        ]), parse_mode='Markdown'
    )

async def spring_prize_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    if uid not in spring_question_creation:
        await safe_answer(query, "❌ Сессия создания вопроса не найдена", show_alert=True)
        return
    pt = query.data.replace('spring_prize_', '')
    spring_question_creation[uid]['prize_type'] = pt
    spring_question_creation[uid]['step'] = 'prize_value'
    if pt == 'coins':
        await query.edit_message_text("👮‍♂️ Введите сумму ms'коинов за ответ.\nМожно использовать к, кк, ккк\nПример: 100, 1к, 2.5кк")
    elif pt == 'gold':
        await query.edit_message_text("👮‍♂️ Введите количество ms'голдов за ответ.\nМожно использовать к, кк, ккк\nПример: 5, 10к")
    elif pt == 'sun':
        await query.edit_message_text("👮‍♂️ Введите количество солнышек за ответ.\nПример: 50")
    else:
        await query.edit_message_text("👮‍♂️ Введите название секретного приза\nПример: Наклейка в Telegram")


# last14.py - ЧАСТЬ 6/7 (bonus, slot, mailing, user_check, инвестиции, банк, message_handler)

# ==================== BONUS ====================
async def bonus_command(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    query = update.callback_query
    if query.from_user.id != user_id:
        await safe_answer(query, "🙈 Это не ваша кнопка!")
        return
    if await check_ban(update, context):
        return
    user = query.from_user
    ADMIN_IDS = context.bot_data.get('ADMIN_IDS', [])
    if user.id not in ADMIN_IDS and not await check_subscription(update, context, user.id):
        await safe_answer(query, "❌ Вы не подписаны на каналы!")
        return
    can, minutes, seconds = await can_claim_bonus_async(user.id, BONUS_COOLDOWN)
    if not can:
        await safe_answer(query, f"⏱ Вы уже забирали бонус! Подождите {minutes} мин. {seconds} сек.", show_alert=True)
        return
    amount = random.randint(100, 999)
    await claim_bonus_async(user.id, amount)
    await update_balance_async(user.id, amount)
    await query.edit_message_text(
        f"🎁 {user.full_name}, вы получили бонус {amount}ms¢\n"
        f"⏳ Следующий бонус будет доступен через 30 минут."
    )
    await safe_answer(query, f"✅ +{amount}ms¢")

# ==================== SLOT ====================
async def slot_command(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    query = update.callback_query
    if query.from_user.id != user_id:
        await safe_answer(query, "🙈 Это не ваша кнопка!")
        return
    if await check_ban(update, context):
        return
    user = query.from_user
    ADMIN_IDS = context.bot_data.get('ADMIN_IDS', [])
    if user.id not in ADMIN_IDS and not await check_subscription(update, context, user.id):
        await safe_answer(query, "❌ Вы не подписаны на каналы!")
        return
    can, minutes, seconds = await can_claim_slot_async(user.id, 1800)
    if not can:
        await safe_answer(query, f"⏱ Барабан будет доступен через {minutes} мин. {seconds} сек.", show_alert=True)
        return
    await query.edit_message_text(
        f"🎰 {user.full_name}, запустите барабан!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔫 Крутить", callback_data=f"slot_spin_{user_id}")]])
    )
    await safe_answer(query, "")

async def slot_spin(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    query = update.callback_query
    if query.from_user.id != user_id:
        await safe_answer(query, "🙈 Это не ваша кнопка!")
        return
    if await check_ban(update, context):
        return
    user = query.from_user
    ADMIN_IDS = context.bot_data.get('ADMIN_IDS', [])
    if user.id not in ADMIN_IDS and not await check_subscription(update, context, user.id):
        await safe_answer(query, "❌ Вы не подписаны на каналы!")
        return
    can, minutes, seconds = await can_claim_slot_async(user.id, 1800)
    if not can:
        await safe_answer(query, f"⏱ Барабан будет доступен через {minutes} мин. {seconds} сек.", show_alert=True)
        return
    await claim_slot_async(user.id)
    total_weight = sum(SLOT_WEIGHTS)
    rand = random.randint(1, total_weight)
    cumulative = 0
    prize_index = 0
    for i, w in enumerate(SLOT_WEIGHTS):
        cumulative += w
        if rand <= cumulative:
            prize_index = i
            break
    prize_range = SLOT_RANGES[prize_index]
    prize_amount = random.randint(prize_range[0], prize_range[1])
    prize_emoji = SLOT_EMOJIS[prize_index]
    prize_name = SLOT_NAMES[prize_index]
    await safe_answer(query, "🎰 Барабан запущен!")
    message = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            f"{user.full_name}, барабан запущен!\n"
            f"ℹ️ Награды:\n"
            f"🟢 Rare - 10-50ms¢\n"
            f"🔵 Super Rare - 100-200ms¢\n"
            f"🟣 Epic - 500-700ms¢\n"
            f"🟡 Legendary - 800-1200ms¢\n"
            f"🔴 Mythic - 1500-2500ms¢\n"
            f"⚫ Mystical - 10.000-25.000ms¢\n\n"
            f"⏱ Прогресс :"
        )
    )
    asyncio.create_task(slot_animation(context, message, user, prize_emoji, prize_name, prize_amount, user_id))

async def slot_animation(context, message, user, prize_emoji, prize_name, prize_amount, user_id):
    try:
        for i in range(7):
            emojis = random.sample(SLOT_EMOJIS, 3)
            keyboard = [[InlineKeyboardButton(emojis[0], callback_data="noop"), InlineKeyboardButton(emojis[1], callback_data="noop"), InlineKeyboardButton(emojis[2], callback_data="noop")]]
            try:
                await message.edit_text(
                    f"{user.full_name}, барабан запущен!\n"
                    f"ℹ️ Награды:\n"
                    f"🟢 Rare - 10-50ms¢\n"
                    f"🔵 Super Rare - 100-200ms¢\n"
                    f"🟣 Epic - 500-700ms¢\n"
                    f"🟡 Legendary - 800-1200ms¢\n"
                    f"🔴 Mythic - 1500-2500ms¢\n"
                    f"⚫ Mystical - 10.000-25.000ms¢\n\n"
                    f"⏱ Прогресс :",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except:
                pass
            await asyncio.sleep(1)
        emojis = random.sample(SLOT_EMOJIS, 3)
        emojis[1] = prize_emoji
        keyboard = [[InlineKeyboardButton(emojis[0], callback_data="noop"), InlineKeyboardButton(emojis[1], callback_data="noop"), InlineKeyboardButton(emojis[2], callback_data="noop")]]
        await update_balance_async(user_id, prize_amount)
        try:
            await message.edit_text(
                f"🎰 {user.full_name}, вы прокрутили барабан!\n\n"
                f"Вам выпало: {prize_emoji} {prize_name} — {format_amount(prize_amount)}ms¢",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except:
            pass
    except Exception as e:
        logging.error(f"Error in slot animation: {e}")

# ==================== MAILING ====================
async def mailing_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or update.effective_user.id != context.bot_data.get('MAIN_ADMIN_ID'):
        await update.message.reply_text("❌ У вас нет прав на выполнение этой команды.")
        return
    md = context.bot_data.get('mailing_data', {})
    md[update.effective_user.id] = {'step': 'awaiting_text', 'markdown': False, 'inline': False, 'text': None, 'time': time.time()}
    context.bot_data['mailing_data'] = md
    await update.message.reply_text(
        "📃 Введите текст рассылки.\n\n"
        "Если вы хотите использовать кликабельный текст (текст с ссылкой) или инлайн кнопки поставьте галочки ниже\n\n"
        "Формат для текста с ссылкой: (*текст*|*ссылка*)\n"
        "Пример: Привет! (User|https://t.me/durov)\n\n"
        "Формат для кнопок:\n"
        "• Обычная кнопка: *inl|текст*\n"
        "• Кнопка-ссылка: *inl|текст\"ссылка\"*\n"
        "Пример: *inl|Нажми\"https://t.me/durov\"*",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Markdown text", callback_data="mailing_toggle_markdown"),
             InlineKeyboardButton("❌ Inline-keyboard", callback_data="mailing_toggle_inline")]
        ])
    )

async def mailing_handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    md = context.bot_data.get('mailing_data', {})
    if uid not in md or md[uid].get('step') != 'awaiting_text':
        return
    md[uid]['text'] = update.message.text
    md[uid]['step'] = 'awaiting_confirm'
    md[uid]['message_id'] = update.message.message_id
    md[uid]['chat_id'] = update.effective_chat.id
    context.bot_data['mailing_data'] = md
    preview = update.message.text
    if md[uid]['markdown']:
        preview = "🔹 Markdown включен\n\n" + preview
    if md[uid]['inline']:
        preview = "🔹 Inline-кнопки включены\n\n" + preview
    await update.message.reply_text(
        f"☑ Подтвердите рассылку\n\n{preview}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("☑ Подтверждаю", callback_data="mailing_confirm")]])
    )

async def mailing_toggle_markdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    if uid != context.bot_data.get('MAIN_ADMIN_ID'):
        await safe_answer(query, "❌ Это не ваша кнопка!", show_alert=True)
        return
    md = context.bot_data.get('mailing_data', {})
    if uid not in md:
        await safe_answer(query, "❌ Сессия рассылки не найдена.", show_alert=True)
        return
    md[uid]['markdown'] = not md[uid]['markdown']
    status = "✅" if md[uid]['markdown'] else "❌"
    inline_status = "✅" if md[uid]['inline'] else "❌"
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{status} Markdown text", callback_data="mailing_toggle_markdown"),
         InlineKeyboardButton(f"{inline_status} Inline-keyboard", callback_data="mailing_toggle_inline")]
    ]))
    context.bot_data['mailing_data'] = md
    await safe_answer(query, "✅ Настройки обновлены")

async def mailing_toggle_inline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    if uid != context.bot_data.get('MAIN_ADMIN_ID'):
        await safe_answer(query, "❌ Это не ваша кнопка!", show_alert=True)
        return
    md = context.bot_data.get('mailing_data', {})
    if uid not in md:
        await safe_answer(query, "❌ Сессия рассылки не найдена.", show_alert=True)
        return
    md[uid]['inline'] = not md[uid]['inline']
    status = "✅" if md[uid]['markdown'] else "❌"
    inline_status = "✅" if md[uid]['inline'] else "❌"
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{status} Markdown text", callback_data="mailing_toggle_markdown"),
         InlineKeyboardButton(f"{inline_status} Inline-keyboard", callback_data="mailing_toggle_inline")]
    ]))
    context.bot_data['mailing_data'] = md
    await safe_answer(query, "✅ Настройки обновлены")

async def mailing_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    if uid != context.bot_data.get('MAIN_ADMIN_ID'):
        await safe_answer(query, "❌ Это не ваша кнопка!", show_alert=True)
        return
    md = context.bot_data.get('mailing_data', {})
    if uid not in md or md[uid].get('step') != 'awaiting_confirm':
        await safe_answer(query, "❌ Сессия рассылки не найдена.", show_alert=True)
        return
    await safe_answer(query, "✅ Рассылка запущена!")
    progress = await query.message.reply_text("✅ Рассылка пошла!\nПрогресс:\nДоставлено 0 пользователям из 0\n⌛")
    all_users = await get_all_users_async()
    total = len(all_users)
    delivered = 0
    raw = md[uid]['text']
    def replace_link(m):
        text = m.group(1)
        url = m.group(2)
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return f'<a href="{url}">{text}</a>'
    processed = re.sub(r'\(([^|]+)\|([^)]+)\)', replace_link, raw)
    keyboard = []
    final_lines = []
    for line in processed.split('\n'):
        if line.startswith('*inl|'):
            btn = line.replace('*inl|', '').replace('*', '')
            match = re.search(r'(.+?)"([^"]+)"', btn)
            if match:
                keyboard.append([InlineKeyboardButton(match.group(1).strip(), url=match.group(2) if match.group(2).startswith(('http://','https://')) else 'https://'+match.group(2))])
            else:
                keyboard.append([InlineKeyboardButton(btn, callback_data="noop")])
        else:
            final_lines.append(line)
    text = '\n'.join(final_lines)
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    for user_row in all_users:
        target_id = user_row[0]
        try:
            await context.bot.send_message(chat_id=target_id, text=text, parse_mode='HTML' if md[uid]['markdown'] else None, reply_markup=reply_markup)
            delivered += 1
            if delivered % 5 == 0 or delivered == total:
                await progress.edit_text(f"✅ Рассылка пошла!\nПрогресс:\nДоставлено {delivered} пользователям из {total}\n{'⏳' if delivered % 2 == 0 else '⌛'}")
            await asyncio.sleep(0.05)
        except Exception as e:
            if "Forbidden" in str(e) or "blocked" in str(e):
                logging.info(f"User {target_id} blocked the bot")
    await progress.edit_text(f"✅ Рассылка завершена!\nПрогресс:\nДоставлено {delivered} пользователям из {total}\n✅")
    del md[uid]
    context.bot_data['mailing_data'] = md

# ==================== USER CHECK ====================
async def confirm_user_check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split('_')
    if len(parts) != 6:
        await safe_answer(query, "❌ Ошибка формата данных", show_alert=True)
        return
    try:
        creator_id = int(parts[3])
        activations = int(parts[4])
        amount = int(parts[5])
    except:
        await safe_answer(query, "❌ Неверные данные", show_alert=True)
        return
    if creator_id != query.from_user.id:
        await safe_answer(query, "🙈 Это не ваша кнопка!", show_alert=True)
        return
    total = amount * activations
    db_user = await get_user_async(query.from_user.id)
    if db_user['balance'] < total:
        await safe_answer(query, "❌ Недостаточно средств", show_alert=True)
        try:
            await query.message.delete()
        except:
            pass
        return
    await update_balance_async(query.from_user.id, -total)
    check_code, check_number = await create_user_check_async(query.from_user.id, amount, activations)
    if not check_code:
        await update_balance_async(query.from_user.id, total)
        await safe_answer(query, "❌ Ошибка при создании чека", show_alert=True)
        return
    await query.edit_message_text(
        f"🧾 Чек #<b>{check_number}</b> создан!\n\n"
        f"💸 Списано: {format_amount(total)}ms¢\n"
        f"💰 За активацию: {format_amount(amount)}ms¢\n"
        f"📊 Активаций: {activations}\n\n"
        f"<blockquote>☑ Для активации нажми кнопку ниже</blockquote>",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎟️ Активировать", url=f"https://t.me/{context.bot.username}?start=userchk_{check_code}")]]),
        parse_mode='HTML'
    )
    await safe_answer(query, "✅ Чек создан!")

async def activate_user_check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    check_code = query.data.replace('activate_user_check_', '')
    success, result = await use_user_check_async(check_code, query.from_user.id)
    if not success:
        messages = {"not_found": "❌ Чек не найден", "expired": "❌ Срок действия чека истёк", "no_activations": "❌ Активации закончились", "already_used": "❌ Ты уже активировал этот чек", "own_check": "❌ Нельзя активировать свой чек", "error": "❌ Ошибка активации"}
        await safe_answer(query, messages.get(result, "❌ Ошибка"), show_alert=True)
        await query.message.delete()
        return
    await update_balance_async(query.from_user.id, result)
    check = await get_user_check_async(check_code)
    if check and check['creator_id'] != query.from_user.id:
        try:
            await context.bot.send_message(chat_id=check['creator_id'], text=f"<tg-emoji emoji-id='5427009714745517609'>✅</tg-emoji> <i>{query.from_user.full_name}, активировал(а) твой чек и получил(а) {format_amount(result)}ms¢</i>\nОсталось активаций: {check['max_activations'] - check['used_count']}", parse_mode='HTML')
        except:
            pass
    await query.message.edit_text(f"✅ {query.from_user.full_name}, ты успешно активировал чек и получил {format_amount(result)}ms¢!")
    await safe_answer(query, "✅ Чек активирован!")

# ==================== ИНВЕСТИЦИИ (АКЦИИ) CALLBACKS ====================
async def investment_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    if query.data == "view_stocks":
        portfolio = await get_user_portfolio_async(user.id)
        if not portfolio:
            await safe_answer(query, "У вас нет акций.🙁", show_alert=True)
            return
        context.user_data['portfolio'] = [dict(item) for item in portfolio]
        context.user_data['page'] = 0
        await show_portfolio_page(query, context, user.id)
    elif query.data.startswith("portfolio_page_"):
        action = query.data.replace("portfolio_page_", "")
        await handle_portfolio_pagination(query, context, user.id, action)
    elif query.data == "shop_stocks":
        stocks = await get_all_stocks_async()
        available = [s for s in stocks if s['current_price'] > 0]
        if not available:
            await safe_answer(query, "🛒 Сейчас нет доступных акций для покупки.", show_alert=True)
            return
        context.user_data['shop_stocks'] = [dict(s) for s in available]
        context.user_data['shop_page'] = 0
        await show_shop_page(query, context, user.id)
    elif query.data.startswith("shop_page_"):
        action = query.data.replace("shop_page_", "")
        await handle_shop_pagination(query, context, user.id, action)
    elif query.data.startswith("stock_info_"):
        stock_id = int(query.data.replace("stock_info_", ""))
        stock = await get_stock_async(stock_id)
        if not stock:
            await safe_answer(query, "❌ Акция не найдена", show_alert=True)
            return
        await query.edit_message_text(f"ℹ️ Информация о акции {stock['name']}:\n\n📊 Текущий курс — {stock['current_price']}ms¢\n\n🆔 {stock['stock_id']}\n\n— Для покупки введите buyact {stock['stock_id']} *кол-во*")
    elif query.data.startswith("confirm_sell_"):
        parts = query.data.split("_")
        if len(parts) == 4:
            await confirm_sell(query, context, user.id, int(parts[2]), int(parts[3]))
    elif query.data == "cancel_sell":
        await query.message.delete()
        await safe_answer(query, "❌ Продажа отменена")

async def show_portfolio_page(query, context, user_id):
    portfolio = context.user_data.get('portfolio', [])
    page = context.user_data.get('page', 0)
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    items = portfolio[start:end]
    total = (len(portfolio) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    text = f"🏦 Список ваших акций:\n\n"
    for item in items:
        text += f"— 🆔 {item['stock_id']} - {item['name']} : {item['current_price']}ms¢ ({item['quantity']} шт.)\n"
    text += f"\nℹ️ Чтобы продать акцию, напишите следующую команду\n— sellact *id* *сколько штук или все*"
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Назад", callback_data="portfolio_page_prev"))
    nav.append(InlineKeyboardButton(f"{page + 1}/{total}", callback_data="noop"))
    if page < total - 1:
        nav.append(InlineKeyboardButton("➡️ Вперёд", callback_data="portfolio_page_next"))
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([nav]))

async def handle_portfolio_pagination(query, context, user_id, action):
    page = context.user_data.get('page', 0)
    portfolio = context.user_data.get('portfolio', [])
    total = (len(portfolio) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    if action == "next":
        if page >= total - 1:
            await safe_answer(query, "Вы итак на последнем уровне.", show_alert=True)
            return
        context.user_data['page'] = page + 1
    elif action == "prev":
        if page <= 0:
            await safe_answer(query, "Вы итак на минимальном уровне.", show_alert=True)
            return
        context.user_data['page'] = page - 1
    await show_portfolio_page(query, context, user_id)

async def show_shop_page(query, context, user_id):
    stocks = context.user_data.get('shop_stocks', [])
    page = context.user_data.get('shop_page', 0)
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    items = stocks[start:end]
    total = (len(stocks) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    text = "🛒 Доступные акции для покупки:\n\n"
    for item in items:
        text += f"🆔 {item['stock_id']} — {item['name']} курс {item['current_price']}ms¢.\n"
    keyboard = []
    row = []
    for i, item in enumerate(items):
        row.append(InlineKeyboardButton(f"🆔 {item['stock_id']}", callback_data=f"stock_info_{item['stock_id']}"))
        if len(row) == 3 or i == len(items) - 1:
            keyboard.append(row)
            row = []
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Обратно", callback_data="shop_page_prev"))
    if page < total - 1:
        nav.append(InlineKeyboardButton("➡️ Следующая страница", callback_data="shop_page_next"))
    if nav:
        keyboard.append(nav)
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_shop_pagination(query, context, user_id, action):
    page = context.user_data.get('shop_page', 0)
    stocks = context.user_data.get('shop_stocks', [])
    total = (len(stocks) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    if action == "next":
        if page >= total - 1:
            await safe_answer(query, "Это последняя страница", show_alert=True)
            return
        context.user_data['shop_page'] = page + 1
    elif action == "prev":
        if page <= 0:
            await safe_answer(query, "Это первая страница", show_alert=True)
            return
        context.user_data['shop_page'] = page - 1
    await show_shop_page(query, context, user_id)

async def confirm_sell(query, context, user_id, stock_id, quantity):
    if query.message.reply_to_message and query.message.reply_to_message.from_user.id != user_id:
        await safe_answer(query, "🙈 Это не ваша кнопка.", show_alert=True)
        return
    await safe_answer(query, "⏳ Обрабатываем продажу...")
    try:
        stock = await get_stock_async(stock_id)
        if not stock:
            await query.message.reply_text("❌ Акция не найдена")
            return
        success, result = await sell_stock_async(user_id, stock_id, quantity)
        if success:
            await query.message.reply_text(f"✅ Продано {quantity} {stock['symbol']} за {format_amount(stock['current_price'] * quantity)}ms¢.")
            try:
                await query.message.delete()
            except:
                pass
        else:
            await query.message.reply_text(f"❌ {str(result)[:100]}")
    except Exception as e:
        logging.error(f"Error in confirm_sell: {e}")
        try:
            await query.message.reply_text("❌ Произошла ошибка")
        except:
            pass

# ==================== БАНК CALLBACKS ====================
async def bank_create_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    bank_creation_data[user_id] = {'step': 'days'}
    await query.edit_message_text(
        f"ℹ️ Для создания депозита выберите количество дней для депозита.\n\nВыбери:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("1 день (3%)", callback_data="bank_days_1"), InlineKeyboardButton("3 дня (7%)", callback_data="bank_days_3"), InlineKeyboardButton("5 дней (11%)", callback_data="bank_days_5")],
            [InlineKeyboardButton("12 дней (12%)", callback_data="bank_days_12"), InlineKeyboardButton("30 дней (21%)", callback_data="bank_days_30")],
            [InlineKeyboardButton("🔙 Назад", callback_data="bank_back_to_menu")]
        ]), parse_mode='Markdown'
    )

async def bank_days_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    days = int(query.data.replace('bank_days_', ''))
    if user_id not in bank_creation_data:
        bank_creation_data[user_id] = {}
    bank_creation_data[user_id]['days'] = days
    bank_creation_data[user_id]['rate'] = BANK_INTEREST_RATES[days]
    bank_creation_data[user_id]['step'] = 'amount'
    await query.edit_message_text(
        f"🏦 Теперь выберите сумму депозита:\n\n"
        f"📅 Вы выбрали {days} дней ({BANK_INTEREST_RATES[days]}%)\n"
        f"⚠ Максимальная сумма депозита – {format_amount(BANK_MAX_AMOUNT)}ms¢.\n\n"
        f"Выберите:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(format_amount(BANK_PRESET_AMOUNTS[0]), callback_data=f"bank_amount_{BANK_PRESET_AMOUNTS[0]}"),
             InlineKeyboardButton(format_amount(BANK_PRESET_AMOUNTS[1]), callback_data=f"bank_amount_{BANK_PRESET_AMOUNTS[1]}")],
            [InlineKeyboardButton(format_amount(BANK_PRESET_AMOUNTS[2]), callback_data=f"bank_amount_{BANK_PRESET_AMOUNTS[2]}"),
             InlineKeyboardButton(format_amount(BANK_PRESET_AMOUNTS[3]), callback_data=f"bank_amount_{BANK_PRESET_AMOUNTS[3]}")],
            [InlineKeyboardButton(format_amount(BANK_PRESET_AMOUNTS[4]), callback_data=f"bank_amount_{BANK_PRESET_AMOUNTS[4]}")],
            [InlineKeyboardButton("💳 Другое", callback_data="bank_amount_custom")],
            [InlineKeyboardButton("🔙 Назад", callback_data="bank_create")]
        ]), parse_mode='Markdown'
    )

async def bank_amount_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    amount = int(query.data.replace('bank_amount_', ''))
    if user_id not in bank_creation_data or bank_creation_data[user_id].get('step') != 'amount':
        await safe_answer(query, "❌ Сессия создания депозита устарела", show_alert=True)
        return
    bank_creation_data[user_id]['amount'] = amount
    await bank_confirm_deposit(query, context, user_id)

async def bank_amount_custom_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if user_id not in bank_creation_data or bank_creation_data[user_id].get('step') != 'amount':
        await safe_answer(query, "❌ Сессия создания депозита устарела", show_alert=True)
        return
    bank_creation_data[user_id]['step'] = 'custom_amount'
    await query.edit_message_text(f"⚠ Введите сумму:\nМожно использовать к, кк\nМаксимум: {format_amount(BANK_MAX_AMOUNT)}ms¢")

async def bank_confirm_deposit(query, context, user_id):
    d = bank_creation_data[user_id]
    amount, days, rate = d['amount'], d['days'], d['rate']
    user = await get_user_async(user_id)
    if user['balance'] < amount:
        await query.edit_message_text(f"❌ Недостаточно средств. Баланс: {format_amount(user['balance'])}ms¢")
        del bank_creation_data[user_id]
        return
    success, deposit_id = await create_deposit_async(user_id, amount, days, rate)
    if not success:
        await query.edit_message_text(f"❌ {deposit_id}")
        del bank_creation_data[user_id]
        return
    await update_balance_async(user_id, -amount)
    await query.edit_message_text(
        f"🏦 Вы хотите создать депозит 🆔 {deposit_id}.\n\n"
        f"💸 Сумма – {format_amount(amount)}ms¢.\n"
        f"Процентная ставка: {rate}%\n\n"
        f"Подтвердите создание:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Создать", callback_data=f"bank_final_confirm_{deposit_id}")]])
    )
    bank_creation_data[user_id]['step'] = 'final'

async def bank_final_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    deposit_id = int(query.data.replace('bank_final_confirm_', ''))
    deposit = await get_deposit_async(deposit_id)
    if not deposit or deposit['user_id'] != user_id or deposit['status'] != 'active':
        await safe_answer(query, "❌ Депозит не найден или уже неактивен", show_alert=True)
        return
    await query.edit_message_text(
        f"✅ Вы успешно создали депозит 🆔 {deposit_id}!\n\n"
        f"💸 Сумма: {format_amount(deposit['amount'])}ms¢\n"
        f"📅 Дней: {deposit['days']}\n"
        f"📊 Процент: {deposit['interest_rate']}%"
    )
    if user_id in bank_creation_data:
        del bank_creation_data[user_id]

async def bank_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    deposits = await get_user_deposits_async(user_id, 'active')
    if not deposits:
        await query.edit_message_text(
            f"🏧 *{query.from_user.full_name}*, у вас пока нет депозитов!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="bank_back_to_menu")]]), parse_mode='Markdown'
        )
        return
    text = f"🏧 *{query.from_user.full_name}*, список ваших депозитов:\n\n"
    now = datetime.now()
    for dep in deposits:
        try:
            expires = datetime.strptime(dep['expires_at'], '%Y-%m-%d %H:%M:%S')
        except:
            continue
        delta = expires - now
        text += f"🆔 {dep['deposit_id']} — {format_amount(dep['amount'])}ms¢ | {dep['interest_rate']}% — депозит снимется через {delta.days} дн. {delta.seconds//3600} ч. {(delta.seconds%3600)//60} мин. {delta.seconds%60} сек.\n\n"
    keyboard = []
    row = []
    for i, dep in enumerate(deposits):
        row.append(InlineKeyboardButton(f"🆔 {dep['deposit_id']}", callback_data=f"bank_view_{dep['deposit_id']}"))
        if len(row) == 3 or i == len(deposits) - 1:
            keyboard.append(row)
            row = []
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="bank_back_to_menu")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def bank_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    deposit_id = int(query.data.replace('bank_view_', ''))
    deposit = await get_deposit_async(deposit_id)
    if not deposit or deposit['user_id'] != query.from_user.id:
        await safe_answer(query, "❌ Депозит не найден", show_alert=True)
        return
    try:
        created = datetime.strptime(deposit['created_at'], '%Y-%m-%d %H:%M:%S')
        expires = datetime.strptime(deposit['expires_at'], '%Y-%m-%d %H:%M:%S')
    except:
        created = expires = datetime.now()
    delta = expires - datetime.now()
    final_amount = deposit['amount'] + (deposit['amount'] * deposit['interest_rate'] // 100)
    await query.edit_message_text(
        f"Депозит 🆔 {deposit_id}:\n\n"
        f"Депозит был создан: {created.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"💸 Сумма депозита – {format_amount(deposit['amount'])}ms¢\n"
        f"После истечения {delta.days} дн. {delta.seconds//3600} ч. вы получите {format_amount(final_amount)}ms¢.\n\n"
        f"Хотите снять депозит прямо сейчас?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Снять 💸", callback_data=f"bank_withdraw_{deposit_id}"),
             InlineKeyboardButton("Назад 🔙", callback_data="bank_list")]
        ]), parse_mode='Markdown'
    )

async def bank_withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    deposit_id = int(query.data.replace('bank_withdraw_', ''))
    deposit = await get_deposit_async(deposit_id)
    if not deposit or deposit['user_id'] != query.from_user.id:
        await safe_answer(query, "❌ Депозит не найден", show_alert=True)
        return
    penalty = deposit['amount'] * BANK_PENALTY_PERCENT // 100
    return_amount = deposit['amount'] - penalty
    await query.edit_message_text(
        f"Вы точно хотите снять депозит 🆔 {deposit_id}?\n\nВы получите {format_amount(return_amount)}ms¢",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Подтверждаю ✅", callback_data=f"bank_confirm_withdraw_{deposit_id}"),
             InlineKeyboardButton("Назад 🔙", callback_data=f"bank_view_{deposit_id}")]
        ]), parse_mode='Markdown'
    )

async def bank_confirm_withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    deposit_id = int(query.data.replace('bank_confirm_withdraw_', ''))
    deposit = await get_deposit_async(deposit_id)
    if not deposit or deposit['user_id'] != query.from_user.id:
        await safe_answer(query, "❌ Депозит не найден", show_alert=True)
        return
    success, return_amount = await close_deposit_async(deposit_id, BANK_PENALTY_PERCENT)
    if success:
        await update_balance_async(query.from_user.id, return_amount)
        await query.edit_message_text(f"✅ Вы успешно сняли депозит 🆔 {deposit_id}.\n💸 Получено: {format_amount(return_amount)}ms¢")
    else:
        await query.edit_message_text("❌ Ошибка при снятии депозита")

async def bank_convert_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query, "👨‍💻 Конвертация на доработках.", show_alert=True)

async def bank_back_to_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if user_id in bank_creation_data:
        del bank_creation_data[user_id]
    await query.edit_message_text(
        f"🏦 *{query.from_user.full_name}*, добро пожаловать в \"Monst Bank\"\n\n"
        f"Здесь ты можешь создать депозит и обменять валюту (временно недоступно)\n\n"
        f"Выбери действие:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Создать депозит", callback_data="bank_create")],
            [InlineKeyboardButton("🏧 Список депозитов", callback_data="bank_list")],
            [InlineKeyboardButton("⏳ Конвертация", callback_data="bank_convert")]
        ]), parse_mode='Markdown'
    )

# ==================== FINAL MESSAGE HANDLER ====================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message or not is_recent(update):
        return
    if await check_ban(update, context):
        return
    uid = update.effective_user.id
    MAIN_ADMIN_ID = context.bot_data.get('MAIN_ADMIN_ID')
    ADMIN_IDS = context.bot_data.get('ADMIN_IDS', [])
    if await get_work_conditions() and uid not in ADMIN_IDS and uid != MAIN_ADMIN_ID:
        await update.message.reply_text("<tg-emoji emoji-id='5420323339723881652'>⚠️</tg-emoji> Активны технические работы!", parse_mode='HTML')
        return
    md = context.bot_data.get('mailing_data', {})
    if uid in md and md[uid].get('step') == 'awaiting_text':
        await mailing_handle_text(update, context)
        return
    if update.message.chat_shared:
        await promo_handle_chat_shared(update, context)
        return
    if not update.message.text:
        return
    text = update.message.text.strip().lower()
    if text == 'рассылка' and uid == MAIN_ADMIN_ID:
        await mailing_command(update, context)
        return
    if text in ['б', 'бал', 'баланс']:
        await balance(update, context)
    elif text in ['проф', 'profile', '/profile']:
        await profile_command(update, context)
    elif text in ['реф', '/ref', 'ref']:
        await ref_command(update, context)
    elif text in ['топ реф', 'топ рефы', 'топ рефов', 'topref']:
        await top_ref_command(update, context)
    elif text == 'топ':
        await top(update, context)
    elif text in ['/promotion', 'продвижение', '/work', 'заработать']:
        if text in ['/work', 'заработать']:
            await work_command(update, context, 1)
        else:
            await promotion_command(update, context)
    elif text == "/topchat" or text == "топ ч":
        await chat_top(update, context)
    elif text.startswith('мины '):
        await mines_command(update, context)
    elif text.startswith('фб ') or text.startswith('/fb '):
        context.args = text.split()[1:]
        await football_command(update, context)
    elif text.startswith('бк ') or text.startswith('/bk '):
        context.args = text.split()[1:]
        await basketball_command(update, context)
    elif text.startswith('краш ') or text.startswith('/crash ') or text.startswith('к '):
        await crash_command(update, context)
    elif text.startswith('золото '):
        await gold_command(update, context)
    elif text.startswith('кнб ') or text.startswith('/knb '):
        context.args = text.split()[1:]
        await knb_command(update, context)
    elif text.startswith('дартс ') or text.startswith('дс ') or text == 'дартс' or text == 'дс':
        await darts_command(update, context)
    elif text.startswith('рр ') or text.startswith('Рр ') or text.startswith('rr '):
        await rr_command(update, context)
    elif text.startswith('куб ') or text.startswith('кубик ') or text == 'куб' or text == 'кубик':
        await cubic_command(update, context)
    elif text.startswith('рул ') or text.startswith('рулетка ') or text == 'рул' or text == 'рулетка':
        await roulette_command(update, context)
    elif text == "кости" or text.startswith("кости "):
        await dice_command(update, context)
    elif text.startswith('бо ') or text.startswith('Бо ') or text.startswith('боулинг ') or text.startswith('Боулинг '):
        await bowling_command(update, context)
    elif text.startswith('башня ') or text.startswith('/tower '):
        context.args = text.split()[1:] if len(text.split()) > 1 else []
        await tower_command(update, context)
    elif text.startswith('/sprevent'):
        await sprevent_command(update, context)
    elif text.startswith('/msh '):
        await msh_command(update, context)
    elif text.startswith('космо ') or text.startswith('космолёт ') or text == 'космо' or text == 'космолёт':
        await spaceship_command(update, context)
    elif text.startswith('msg ') or text.startswith('мсг ') or text.startswith('мг '):
        context.args = text.split()[1:]
        await msg_transfer_command(update, context)
    elif text.startswith('монетка ') or text.startswith('мон ') or text == 'монетка' or text == 'мон':
        await coinflip_command(update, context)
    elif text == "ивент" or text == "весна":
        await sprevent_command(update, context)
    elif uid in spring_question_creation:
        await spring_prize_value_handler(update, context)
    elif text.startswith('!mt ') or text.startswith('мт '):
        await math_contest_command(update, context)
    elif text in ['кнб', 'knb']:
        await knb_command(update, context)
    elif text == "банк" or text == "Банк":
        if update.effective_chat.type == "private":
            await bank_private_command(update, context)
        else:
            await bank_command(update, context)
    elif text == "акции" or text == "Акции":
        await stocks_info_command(update, context)
    elif 'donat_step' in context.user_data and context.user_data['donat_step'] == 'waiting_amount':
        await donat_handle_text(update, context)
    elif text in ['/donat', '/donate', '/conversion', 'донат', 'конвертация']:
        await donat_command(update, context)
    elif text == "мои акции" or text == "Мои акции":
        await myaction_command(update, context)
    elif text == "магазин" or text == "Магазин" or text == "маг" or text == "Маг":
        await shop_command(update, context)
    elif text.startswith('buyact '):
        context.args = text.replace('buyact ', '').split()
        await buyact_command(update, context)
    elif text.startswith('sellact '):
        context.args = text.replace('sellact ', '').split()
        await sellact_command(update, context)
    elif text in ['/daily', 'бонус']:
        await daily_command(update, context)
    elif text in ['/cases', 'кейсы', 'кейсы']:
        await cases_command(update, context, 1)
    elif text.startswith('пирамида '):
        await pyramid_command(update, context)
    elif text.startswith('п ') or text.startswith('перевод ') or text.startswith('/send '):
        context.args = text.split()[1:] if len(text.split()) > 1 else []
        await transfer_command(update, context)
    elif text.startswith('/антоп ') or text.startswith('/untop ') or text == '/антоп' or text == '/untop':
        await untop_command(update, context)
    elif text.startswith('/втоп ') or text.startswith('/returntop '):
        await return_top_command(update, context)
    elif text.startswith('/coinfall ') or text.startswith('кф '):
        await coinfall_command(update, context)
    elif text.startswith('гет ') or text == 'гет' or text.startswith('/get '):
        await get_user_info_command(update, context)
    elif text.startswith('мут ') or text.startswith('глуш '):
        context.args = text.split()[1:] if len(text.split()) > 1 else []
        await mute_command(update, context)
    elif text == 'мут' or text == 'глуш':
        context.args = []
        await mute_command(update, context)
    elif text.startswith('кик '):
        context.args = text.split()[1:] if len(text.split()) > 1 else []
        await kick_command(update, context)
    elif text == 'кик':
        context.args = []
        await kick_command(update, context)
    elif text.startswith('!give '):
        context.args = text.replace('!give ', '').split()
        await give_command(update, context)
    elif text.startswith('!take '):
        context.args = text.replace('!take ', '').split()
        await take_command(update, context)
    elif text.startswith('промо '):
        context.args = [text[6:].strip()]
        await promo_activate_command(update, context)
    elif text.startswith('!checkhash '):
        context.args = text.replace('!checkhash ', '').split()
        await checkhash_command(update, context)
    elif text == "ивенты" or text == "Ивенты":
        await events_command(update, context)
    elif 'event_creation' in context.user_data:
        await event_text_handler(update, context)
    elif text.startswith('!tcheckhash '):
        context.args = text.replace('!tcheckhash ', '').split()
        await tcheckhash_command(update, context)
    elif text.startswith('/newcheck ') or text.startswith('+чек '):
        context.args = text.split()[1:] if len(text.split()) > 2 else []
        await newcheck_command(update, context)
    elif text == '/checklist':
        await checklist_command(update, context)
