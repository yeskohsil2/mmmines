# handlers/callback_handlers.py
import logging
import asyncio
from typing import Optional, Callable, Any
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from .games import (
    handle_mines_callbacks, handle_gold_callbacks, handle_pyramid_callbacks,
    handle_tower_callbacks, handle_rr_callbacks, handle_dice_callbacks,
    handle_coinfall_callbacks, handle_knb_callbacks, handle_dice_game_callbacks
)
from .bank import handle_bank_callbacks
from .investments import handle_investment_callbacks
from .admin import (
    handle_admin_callbacks, handle_mailing_callbacks, handle_check_callbacks,
    handle_top_exclude_callbacks, math_contest_confirm_callback, math_answer_callback
)
from .events import (
    handle_events_callbacks, handle_spring_callbacks
)
from .common import (
    handle_common_callbacks, handle_subscription_check, handle_help_callbacks,
    handle_transfer_callbacks, safe_answer, format_amount, get_user_async
)

# ===== ВСПОМОГАТЕЛЬНЫЙ ИМПОРТ ДЛЯ ОСТАЛЬНЫХ ФУНКЦИЙ =====
_last14_module = None


def _get_last14():
    """Ленивый импорт last14 для избежания циклических зависимостей"""
    global _last14_module
    if _last14_module is None:
        import last14
        _last14_module = last14
    return _last14_module


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Основной роутер для всех callback запросов"""
    if not update.callback_query:
        return
    
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    
    logging.debug(f"Callback received: {data} from user {user_id}")
    
    # ===== ЗАГЛУШКИ =====
    if data == "noop":
        await safe_answer(query, "")
        return
    
    if data.startswith("dead_") or "dead_" in data:
        await safe_answer(query, "🙈 Игра завершена")
        return
    
    # ===== ОБЩИЕ КНОПКИ =====
    if await handle_common_callbacks(update, context, data, user_id):
        return
    
    # ===== ИГРЫ =====
    if data.startswith(("mines_cell_", "mines_take_", "mines_cancel_", "mines_dead_")):
        await handle_mines_callbacks(update, context, data, user_id)
        return
    
    if data.startswith(("dice_num_", "dice_even_", "dice_odd_", "dice_big_", "dice_small_", "dice_equal_", "dice_cancel_")):
        await handle_dice_game_callbacks(update, context, data, user_id)
        return
    
    if data.startswith(("gold_left_", "gold_right_", "gold_take_", "gold_dead_")):
        await handle_gold_callbacks(update, context, data, user_id)
        return
    
    if data.startswith(("pyr_", "take_", "cancel_")):
        await handle_pyramid_callbacks(update, context, data, user_id)
        return
    
    if data.startswith(("tower_cell_", "tower_take_", "tower_cancel_", "tower_dead_")):
        await handle_tower_callbacks(update, context, data, user_id)
        return
    
    if data.startswith(("rr_bullets_", "rr_cell_", "rr_cancel")):
        await handle_rr_callbacks(update, context, data, user_id)
        return
    
    if data.startswith(("dice_join_", "dice_leave_")):
        await handle_dice_callbacks(update, context, data, user_id)
        return
    
    if data.startswith(("coinfall_join", "coinfall_start", "coinfall_claim_", "coinfall_claimed", "coinfall_join_disabled")):
        await handle_coinfall_callbacks(update, context, data, user_id)
        return
    
    if data.startswith(("knb:choice:", "knb:pvp:", "knb_accept_", "knb_cancel_")):
        await handle_knb_callbacks(update, context, data, user_id)
        return
    
    # ===== ИНВЕСТИЦИИ =====
    if data.startswith(("view_stocks", "portfolio_page_", "shop_stocks", "shop_page_", 
                        "stock_info_", "confirm_sell_", "cancel_sell")):
        await handle_investment_callbacks(update, context, data, user_id)
        return
    
    # ===== БАНК =====
    if data.startswith(("bank_", "bank_create", "bank_list", "bank_convert", 
                        "bank_back_to_menu", "bank_days_", "bank_amount_", 
                        "bank_view_", "bank_withdraw_", "bank_confirm_withdraw_", 
                        "bank_final_confirm_")):
        await handle_bank_callbacks(update, context, data, user_id)
        return
    
    # ===== ИВЕНТЫ =====
    if data.startswith(("spring_", "spring_mysteries", "spring_questions_list", 
                        "spring_collect", "spring_exchange", "spring_castle", 
                        "spring_tasks", "spring_back_to_menu", "spring_prize_")):
        await handle_spring_callbacks(update, context, data, user_id)
        return
    
    # ===== MATH КОНКУРС (АДМИН) =====
    if data.startswith(("math_contest_confirm", "math_answer_")):
        if data == "math_contest_confirm":
            await math_contest_confirm_callback(update, context)
        elif data.startswith("math_answer_"):
            await math_answer_callback(update, context)
        return
    
    # ===== ОБЫЧНЫЕ ИВЕНТЫ =====
    if data.startswith(("event_view_", "event_type_", "event_confirm_", "event_close_", "event_close_confirm_")):
        await handle_events_callbacks(update, context, data, user_id)
        return
    
    # ===== АДМИНКА =====
    if data.startswith(("bonus_", "slot_", "slot_spin_")):
        await handle_admin_callbacks(update, context, data, user_id)
        return
    
    if data.startswith(("mailing_toggle_markdown", "mailing_toggle_inline", "mailing_confirm")):
        await handle_mailing_callbacks(update, context, data, user_id)
        return
    
    if data.startswith(("confirm_user_check_", "activate_user_check_", "checklist_page_")):
        await handle_check_callbacks(update, context, data, user_id)
        return
    
    if data.startswith(("switch_to_chat_top", "switch_to_global_top")):
        await handle_top_exclude_callbacks(update, context, data, user_id)
        return
    
    if data.startswith(("confirm_reset_stocks", "confirm_set_stocks_100")):
        await handle_admin_callbacks(update, context, data, user_id)
        return
    
    if data == "check_subscription":
        await handle_subscription_check(update, context, data, user_id)
        return
    
    if data.startswith("help_"):
        await handle_help_callbacks(update, context, data, user_id)
        return
    
    # ===== ПЕРЕВОДЫ =====
    if data.startswith("confirm_msg_"):
        transfer_id = data.replace("confirm_msg_", "")
        last14 = _get_last14()
        await last14.confirm_msg_transfer(update, context, transfer_id)
        return
    
    if data.startswith(("confirm_transfer_", "final_confirm_")):
        await handle_transfer_callbacks(update, context, data, user_id)
        return
    
    # ===== ПРОДВИЖЕНИЕ =====
    last14 = _get_last14()
    
    if data == "promo_rules":
        await last14.promo_rules_callback(update, context)
        return
    
    if data == "promo_channel":
        await last14.promo_price_input(update, context, 'channel')
        return
    
    if data == "promo_chat":
        await last14.promo_price_input(update, context, 'chat')
        return
    
    if data == "promo_my_tasks":
        await last14.my_tasks_command(update, context, 1)
        return
    
    if data == "promo_tasks":
        await last14.promo_tasks_command(update, context, 1)
        return
    
    if data.startswith("promo_price_"):
        price = int(data.replace("promo_price_", ""))
        await last14.promo_users_count(update, context, price)
        return
    
    if data.startswith("promo_users_"):
        if data == "promo_users_max":
            users = context.user_data.get('promo_max_users', 1)
        else:
            users = int(data.replace("promo_users_", ""))
        await last14.promo_confirm(update, context, users)
        return
    
    if data == "promo_back_to_menu":
        user = query.from_user
        db_user = await get_user_async(user.id)
        msg_balance = db_user.get('msg_balance', 0)
        
        text = (
            f"⚙️ {user.full_name}, что ты хочешь рекламировать?\n\n"
            f"⚠️ Продвигая канал/группу или же чат вы автоматически принимаете правила продвижения!\n\n"
            f"🍯 Баланс: {format_amount(msg_balance)} MSG"
        )
        
        keyboard = [
            [InlineKeyboardButton("📢 Продвигать канал", callback_data="promo_channel")],
            [InlineKeyboardButton("💬 Продвигать чат/группу", callback_data="promo_chat")],
            [InlineKeyboardButton("🎯 Активные задания", callback_data="promo_my_tasks")],
            [InlineKeyboardButton("📕 Правила", callback_data="promo_rules")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return
    
    if data == "promo_back_to_price":
        promo_type = context.user_data.get('promo_type', 'channel')
        await last14.promo_price_input(update, context, promo_type)
        return
    
    if data == "promo_cancel":
        await query.edit_message_text("❌ Действие отменено")
        context.user_data.clear()
        return
    
    if data.startswith("promo_task_"):
        task_id = int(data.replace("promo_task_", ""))
        await last14.promo_task_view(update, context, task_id)
        return
    
    if data.startswith("my_tasks_page_"):
        page = int(data.replace("my_tasks_page_", ""))
        await last14.my_tasks_command(update, context, page)
        return
    
    if data.startswith("promo_check_"):
        task_id = int(data.replace("promo_check_", ""))
        await last14.promo_check_task(update, context, task_id)
        return
    
    if data.startswith("promo_report_"):
        if "promo_report_reason_" in data:
            parts = data.split('_')
            task_id = int(parts[3])
            reason = parts[4]
            await last14.promo_report_submit(update, context, task_id, reason)
        else:
            task_id = int(data.replace("promo_report_", ""))
            await last14.promo_report_task(update, context, task_id)
        return
    
    if data.startswith("promo_tasks_page_"):
        page = int(data.replace("promo_tasks_page_", ""))
        await last14.promo_tasks_command(update, context, page)
        return
    
    if data.startswith("promo_admin_delete_"):
        task_id = int(data.replace("promo_admin_delete_", ""))
        await last14.delete_task(task_id)
        await safe_answer(query, "✅ Задание удалено")
        await query.edit_message_text("✅ Задание удалено")
        return
    
    if data.startswith("promo_admin_keep_"):
        await safe_answer(query, "✅ Задание оставлено")
        await query.edit_message_text("✅ Задание оставлено")
        return
    
    if data == "work_refresh":
        await last14.work_command(update, context, 1)
        return
    
    if data.startswith("work_page_"):
        page = int(data.replace("work_page_", ""))
        await last14.work_command(update, context, page)
        return
    
    if data.startswith("work_task_"):
        task_id = int(data.replace("work_task_", ""))
        await last14.work_task_view(update, context, task_id)
        return
    
    if data.startswith("work_check_"):
        task_id = int(data.replace("work_check_", ""))
        await last14.work_check_task(update, context, task_id)
        return
    
    if data.startswith("work_report_reason_"):
        parts = data.split('_')
        task_id = int(parts[3])
        reason = parts[4]
        await last14.work_report_submit(update, context, task_id, reason)
        return
    
    if data.startswith("work_report_"):
        task_id = int(data.replace("work_report_", ""))
        await last14.work_report_task(update, context, task_id)
        return
    
    # ===== DONAT =====
    if data == "donat_exchange":
        await last14.donat_exchange_callback(update, context)
        return
    
    if data.startswith("donat_amount_"):
        if data == "donat_amount_max":
            db_user = await get_user_async(query.from_user.id)
            amount = db_user.get('msg_balance', 0)
        else:
            amount = int(data.replace("donat_amount_", ""))
        await last14.donat_amount_callback(update, context, amount)
        return
    
    if data == "donat_confirm":
        await last14.donat_confirm_callback(update, context)
        return
    
    if data == "donat_back":
        await last14.donat_back_callback(update, context)
        return
    
    # ===== DAILY =====
    if data == "daily_claim":
        await last14.daily_claim_callback(update, context)
        return
    
    # ===== CASES =====
    if data == "cases_refresh":
        await last14.cases_command(update, context, 1)
        return
    
    if data.startswith("cases_page_"):
        page = int(data.replace("cases_page_", ""))
        await last14.cases_command(update, context, page)
        return
    
    if data.startswith("case_open_"):
        case_type = data.replace("case_open_", "")
        await last14.case_open_callback(update, context, case_type)
        return
    
    if data.startswith("case_cell_"):
        parts = data.split('_')
        target_id = int(parts[2])
        cell_idx = int(parts[3])
        await last14.case_cell_callback(update, context, target_id, cell_idx)
        return
    
    if data.startswith(("case_dead_", "case_finished_")):
        await safe_answer(query, "🙈 Эта ячейка уже открыта")
        return
    
    # ===== SPACESHIP =====
    if data.startswith("spaceship_cell_"):
        parts = data.split('_')
        target_id = int(parts[2])
        level = int(parts[3])
        position = int(parts[4])
        await last14.spaceship_cell_callback(update, context, target_id, level, position)
        return
    
    if data.startswith("spaceship_take_"):
        target_id = int(data.split('_')[2])
        await last14.spaceship_take_callback(update, context, target_id)
        return
    
    if data.startswith("spaceship_dead"):
        await safe_answer(query, "🙈 Эта игра завершена")
        return
    
    # ===== КЛЮЧИ =====
    if data.startswith("key_edit_"):
        parts = data.split('_')
        key_code = parts[2]
        status = parts[3]
        await last14.key_edit_callback(update, context, key_code, status)
        return
    
    if data.startswith("key_delete_"):
        key_code = data.replace("key_delete_", "")
        await last14.key_delete_callback(update, context, key_code)
        return
    
    # Если ничего не подошло
    logging.warning(f"Unhandled callback: {data}")
    await safe_answer(query, "❌ Неизвестная команда")
