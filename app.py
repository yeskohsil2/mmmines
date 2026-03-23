from flask import Flask, request
import asyncio
import os
import logging
import threading
import time
from pathlib import Path
from typing import Final, Optional, Any
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, InlineQueryHandler
from database import *
from handlers.callback_handlers import button_handler
from last14 import *

# Константы для улучшения читаемости и типобезопасности
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

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database_with_retry(max_retries: int = 5, delay: int = 5) -> bool:
    """Инициализация базы данных с повторными попытками"""
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

logger.info("Creating application...")
application: Application = Application.builder().token(BOT_TOKEN).build()

# Установка данных в bot_data
application.bot_data.update({
    'ADMIN_IDS': os.getenv('ADMIN_IDS'),
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

# Регистрация обработчиков команд
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
    ("gmsg", give_msg_command), ("tmsg", take_command), ("ban", ban_command),
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
def run_jobs() -> tuple[str, int] | tuple[dict[str, str], int]:
    """Запуск фоновых задач через вебхук"""
    try:
        logger.info("Running background jobs...")
        from telegram.ext import ContextTypes
        
        async def run() -> None:
            """Асинхронная задача для фоновых операций"""
            async with application:
                context = ContextTypes.DEFAULT_TYPE(application)
                await update_stock_prices(context)
                await check_expired_deposits(context)
                await check_expired_dice_games(context)
                await update_msg_rate_job(context)
        
        asyncio.run(run())
        logger.info("Background jobs completed")
        return "OK", 200
    except Exception as e:
        logger.error(f"Error in run_jobs: {e}", exc_info=True)
        return f"Error: {e}", 500


@app.route('/backup', methods=['POST'])
def create_backup() -> tuple[dict[str, Any], int] | tuple[str, int]:
    """Создание бэкапа базы данных"""
    try:
        secret: Optional[str] = request.headers.get('X-Backup-Secret')
        if secret != os.getenv('BACKUP_SECRET', 'your-secret-key-here'):
            logger.warning("Неавторизованная попытка создания бэкапа")
            return "Unauthorized", 401

        logger.info("📦 Создание бэкапа через вебхук...")
        backup_path: Optional[Path] = backup_manager.create_backup()

        if backup_path:
            stats: dict[str, Any] = backup_manager.get_backup_stats()
            logger.info(f"✅ Бэкап успешно создан: {backup_path}")
            return {
                "status": "success",
                "backup": str(backup_path),
                "stats": stats
            }, 200
        else:
            logger.error("❌ Не удалось создать бэкап")
            return {"status": "error", "message": "Failed to create backup"}, 500

    except Exception as e:
        logger.error(f"Ошибка при создании бэкапа: {e}")
        return {"status": "error", "message": str(e)}, 500


@app.route('/backup/latest', methods=['GET'])
def get_latest_backup() -> tuple[dict[str, Any], int] | tuple[str, int]:
    """Получение информации о последнем бэкапе"""
    try:
        secret: Optional[str] = request.headers.get('X-Backup-Secret')
        if secret != os.getenv('BACKUP_SECRET', 'your-secret-key-here'):
            return "Unauthorized", 401

        stats: dict[str, Any] = backup_manager.get_backup_stats()
        return stats, 200

    except Exception as e:
        return {"error": str(e)}, 500


@app.route('/backup/restore', methods=['POST'])
def restore_backup() -> tuple[dict[str, str], int] | tuple[str, int]:
    """Восстановление базы данных из последнего бэкапа"""
    try:
        secret: Optional[str] = request.headers.get('X-Backup-Secret')
        if secret != os.getenv('BACKUP_SECRET', 'your-secret-key-here'):
            return "Unauthorized", 401

        logger.info("🔄 Восстановление из последнего бэкапа...")

        if backup_manager.restore_last_backup():
            logger.info("✅ База данных восстановлена из бэкапа")
            return {"status": "success", "message": "Database restored from latest backup"}, 200
        else:
            return {"status": "error", "message": "No backups available"}, 404

    except Exception as e:
        logger.error(f"Ошибка восстановления: {e}")
        return {"status": "error", "message": str(e)}, 500


@app.route('/', methods=['GET'])
def health() -> tuple[str, int]:
    """Проверка работоспособности сервиса"""
    return "Bot running", 200


def run_flask() -> None:
    """Запуск Flask сервера"""
    port: int = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port)


if __name__ == "__main__":
    logger.info("Starting Flask in separate thread...")
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    logger.info("Starting bot in main thread...")
    application.run_polling()
