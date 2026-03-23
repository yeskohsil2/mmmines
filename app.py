from flask import Flask, request
import asyncio
import os
import logging
import threading
import time
from typing import Final, Optional, Any
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, InlineQueryHandler
from database import *
from handlers.callback_handlers import button_handler
from last14 import *

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы
BOT_TOKEN: Final[str | None] = os.getenv('BOT_TOKEN')
ADMIN_IDS_ENV: Final[str | None] = os.getenv('ADMIN_IDS')
DATABASE_URL: Final[str | None] = os.getenv('DATABASE_URL')

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is required!")

if not ADMIN_IDS_ENV:
    os.environ['ADMIN_IDS'] = '6025818386,8555637694,7019856389,6219530066'
    print("ADMIN_IDS не найден, используй по умолчанию")

print("=== STARTING APP ===")
print(f"BOT_TOKEN exists: {bool(BOT_TOKEN)}")
print(f"ADMIN_IDS exists: {bool(os.getenv('ADMIN_IDS'))}")
print(f"DATABASE_URL exists: {bool(DATABASE_URL)}")
print("=== END CHECK ===")

# Инициализация БД с retry
def init_database_with_retry(max_retries: int = 5, delay: int = 5) -> bool:
    for attempt in range(max_retries):
        try:
            init_db()
            init_promotion_db()
            init_currency_db()
            init_chats_db()
            init_cases_db()
            init_keys_db()
            init_logs_db()
            init_work_conditions_db()
            init_games_db()
            logger.info("All databases initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Database init attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                logger.critical("Failed to initialize database after all retries")
                raise
    return False

init_database_with_retry()

# СОЗДАЁМ APPLICATION
logger.info("Creating application...")
application = Application.builder().token(BOT_TOKEN).build()

# Преобразуем ADMIN_IDS в список чисел
admin_ids_str = os.getenv('ADMIN_IDS', '')
admin_ids_list = [int(x.strip()) for x in admin_ids_str.split(',') if x.strip()]

application.bot_data.update({
    'ADMIN_IDS': admin_ids_list,  # ← теперь это список чисел
    'MAIN_ADMIN_ID': MAIN_ADMIN_ID,
    'CHANNEL_USERNAME': CHANNEL_USERNAME,
    'CHANNEL2_USERNAME': CHANNEL2_USERNAME,
    'KURS_CHANNEL': KURS_CHANNEL,
    'COOLDOWN_SECONDS': COOLDOWN_SECONDS,
    'KURS_MSG_CHANNEL': '@kursmsgmonstr',
    'MINES_SESSIONS': MINES_SESSIONS,
    'GOLD_SESSIONS': GOLD_SESSIONS,
    'PYRAMID_SESSIONS': PYRAMID_SESSIONS,
    'TOWER_SESSIONS': TOWER_SESSIONS,
    'RR_SESSIONS': RR_SESSIONS,
    'BOWLING_SESSIONS': BOWLING_SESSIONS,
    'dice_cooldown': dice_cooldown,
    'LAST_CLICK_TIME': LAST_CLICK_TIME,
    'KHB_GAMES': KHB_GAMES,
    'KHB_DUELS': KHB_DUELS,
    'COINFLIP_SESSIONS': COINFLIP_SESSIONS,
    'CASES_SESSIONS': CASES_SESSIONS,
    'SPACESHIP_SESSIONS': SPACESHIP_SESSIONS,
    'CRASH_SESSIONS': CRASH_SESSIONS,
    'math_contest_pending': math_contest_pending,
    'pending_transfers': pending_transfers,
    'transfer_confirmations': transfer_confirmations,
    'mailing_data': mailing_data,
    'DICE_SESSIONS': DICE_SESSIONS,
    'pending_msg_transfers': pending_msg_transfers,
    'ROULETTE_SESSIONS': ROULETTE_SESSIONS,
    'DARTS_SESSIONS': DARTS_SESSIONS,
})

# Добавляем обработчики команд
commands = [
    ("start", start), ("game", games), ("games", games), ("help", help_command),
    ("support", support), ("mines", mines_command), ("gold", gold_command),
    ("pyramid", pyramid_command), ("tower", tower_command), ("bowling", bowling_command),
    ("crash", crash_command), ("cubic", cubic_command), ("roulette", roulette_command),
    ("darts", darts_command), ("coinflip", coinflip_command), ("knb", knb_command),
    ("football", football_command), ("fb", football_command), ("basketball", basketball_command),
    ("bk", basketball_command), ("rr", rr_command), ("dice", dice_command),
    ("coinfall", coinfall_command), ("spaceship", spaceship_command), ("space", spaceship_command),
    ("balance", balance), ("top", top), ("topchat", chat_top), ("profile", profile_command),
    ("ref", ref_command), ("topref", top_ref_command), ("donat", donat_command),
    ("daily", daily_command), ("cases", cases_command), ("transfer", transfer_command),
    ("send", transfer_command), ("promo", promo_activate_command), ("promotion", promotion_command),
    ("work", work_command), ("setpromo", setpromo_command), ("checkprom", checkprom_command),
    ("delpromo", delpromo_command), ("newcheck", newcheck_command), ("checklist", checklist_command),
    ("mailing", mailing_command), ("setevent", setevent_command), ("closeevent", closeevent_command),
    ("events", events_command), ("resetstocks", reset_stocks_command), ("setstocks", set_stocks_command),
    ("get", get_user_info_command), ("workcondit", workcondit_command), ("setcondit", setcondit_command),
    ("bank", bank_command), ("buyact", buyact_command), ("sellact", sellact_command),
    ("shop", shop_command), ("stocks", stocks_info_command), ("msg", transfer_command),
    ("gmsg", give_msg_command), ("tmsg", take_msg_command), ("ban", ban_command),
    ("unban", unban_command), ("msh", msh_command), ("gmsh", gmsh_command),
    ("rmsh", rmsh_command), ("put", put_command), ("exchange", exchange_command),
    ("addtask", add_task_command), ("answer", answer_command), ("question", question_command),
    ("sprevent", sprevent_command)
]

for cmd_name, handler in commands:
    application.add_handler(CommandHandler(cmd_name, handler))

application.add_handler(InlineQueryHandler(inline_query_handler))
application.add_handler(MessageHandler(filters.Regex(r'^кости(\s|$)'), dice_command))
application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND, bank_text_handler))
application.add_handler(MessageHandler(filters.ALL, message_handler))
application.add_handler(CallbackQueryHandler(button_handler))

logger.info("Application created successfully")


@app.route('/run_jobs', methods=['POST'])
def run_jobs():
    """Запуск фоновых задач по запросу с телефона"""
    try:
        logger.info("Running background jobs...")
        from telegram.ext import ContextTypes
        
        async def run():
            async with application:
                context = ContextTypes.DEFAULT_TYPE(application)
                await update_stock_prices(context)
                await check_expired_deposits(context)
                await check_expired_dice_games(context)
                await update_msg_rate_job(context)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run())
        loop.close()
        
        logger.info("Background jobs completed")
        return "OK", 200
    except Exception as e:
        logger.error(f"Error in run_jobs: {e}", exc_info=True)
        return f"Error: {e}", 500


@app.route('/', methods=['GET'])
def health():
    return "Bot running", 200


# Функция для запуска Flask в отдельном потоке
def run_flask():
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port)


# ЗАПУСКАЕМ FLASK В ОТДЕЛЬНОМ ПОТОКЕ, А БОТА В ГЛАВНОМ С СОЗДАНИЕМ EVENT LOOP
if __name__ == "__main__":
    logger.info("Starting Flask in separate thread...")
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    logger.info("Starting bot in main thread...")
    
    # Создаём event loop для Python 3.14.3
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(application.run_polling())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        loop.close()
