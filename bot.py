import os
import re
from collections import Counter
from typing import Dict, Set, Tuple, Optional, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN не найден")

MAX_USERS = 5

# user_id -> {"name": str, "slots": set[(date, hour)]}
users_data: Dict[int, dict] = {}

# Согласованный слот
agreed_slot: Optional[Tuple[str, int]] = None

# Последние лучшие варианты из /result
last_ranked_slots: List[Tuple[str, int]] = []
def normalize_name(user) -> str:
    if user.username:
        return f"@{user.username}"
    full_name = " ".join(filter(None, [user.first_name, user.last_name])).strip()
    return full_name or str(user.id)
def parse_input(text: str) -> Set[Tuple[str, int]]:
    """
    Поддерживает:
    11.04 15,16
    11.04: 15, 16
    """
    slots: Set[Tuple[str, int]] = set()
    lines = text.splitlines()
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        line = line.replace(":", " ", 1)
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            continue
        date_part, times_part = parts
        date_part = date_part.strip()
        times_part = times_part.strip()

        if not re.fullmatch(r"\d{1,2}\.\d{1,2}", date_part):
            continue
        for t in times_part.split(","):
            t = t.strip()
            if not t or not t.isdigit():
                continue

            hour = int(t)
            if 0 <= hour <= 23:
                slots.add((date_part, hour))
    return slots
def format_slot(slot: Tuple[str, int]) -> str:
    date, hour = slot
    return f"{date} {hour:02d}:00"
def format_slots(slots: Set[Tuple[str, int]]) -> str:
    sorted_slots = sorted(slots, key=lambda x: (x[0], x[1]))
    return "\n".join(format_slot(slot) for slot in sorted_slots)
def build_main_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📌 Напомнить дату события", callback_data="remind_agreed")],
        [InlineKeyboardButton("🗑 Назначить новую дату", callback_data="reset_all")],
    ]
    return InlineKeyboardMarkup(keyboard)
def build_result_keyboard(slot_count: int) -> InlineKeyboardMarkup:
    rows = []
    for i in range(min(slot_count, 5)):
        rows.append([
            InlineKeyboardButton(
                f"✅ Согласовать #{i + 1}",
                callback_data=f"agree_{i}"
            )
        ])
    rows.append([
        InlineKeyboardButton("📌 Напомнить дату события", callback_data="remind_agreed")
    ])
    rows.append([
        InlineKeyboardButton("🗑 Назначить новую дату", callback_data="reset_all")
    ])
    return InlineKeyboardMarkup(rows)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Привет.\n\n"
        "Отправь даты и часы в формате:\n"
        "11.04 15,16\n"
        "12.04 14\n\n"
        "Можно и так:\n"
        "11.04: 15, 16\n"
        "12.04: 14\n\n"
        "Команды:\n"
        "/result — показать лучшие варианты\n"
        "/who — кто уже отправил\n"
        "/agreed — показать согласованную дату\n"
        "/reset — очистить всё\n\n"
        "Также можно пользоваться кнопками ниже."
    )
    await update.message.reply_text(text, reply_markup=build_main_keyboard())
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return
    global users_data
    user = update.effective_user
    user_id = user.id
    name = normalize_name(user)
    text = update.message.text or ""
    slots = parse_input(text)
    if not slots:
        await update.message.reply_text(
            "Не поняла формат.\n\n"
            "Пример:\n"
            "11.04 15,16\n"
            "12.04 14"
        )
        return
is_new_user = user_id not in users_data

if is_new_user and len(users_data) >= MAX_USERS:
await update.message.reply_text(
            f"Лимит участников уже достигнут: {MAX_USERS}."
        )
        return
    users_data[user_id] = {
        "name": name,
        "slots": slots,
    }
    action_text = "Сохранила" if is_new_user else "Обновила"
    await update.message.reply_text(
        f"{action_text} твои варианты:\n\n{format_slots(slots)}",
        reply_markup=build_main_keyboard()
    )
async def who(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not users_data:
        await update.message.reply_text("Пока никто ничего не отправил.")
        return

    lines = [f"Сейчас есть данные от {len(users_data)} из {MAX_USERS}:\n"]
    for idx, data in enumerate(users_data.values(), start=1):
        lines.append(f"{idx}. {data['name']} — {len(data['slots'])} слотов")

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=build_main_keyboard()
    )
async def result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global last_ranked_slots
    if not users_data:
        await update.message.reply_text("Пока нет данных.")
        return
    all_slot_sets = [data["slots"] for data in users_data.values()]
    participant_count = len(all_slot_sets)
    counter = Counter()
    for slot_set in all_slot_sets:
        counter.update(slot_set)
    full_matches = set.intersection(*all_slot_sets) if all_slot_sets else set()
    sorted_slots = sorted(
        counter.items(),
        key=lambda x: (-x[1], x[0][0], x[0][1])
    )
    last_ranked_slots = [slot for slot, _ in sorted_slots[:5]]
    lines = [f"Участников с данными: {participant_count}\n"]
    if full_matches:
        lines.append("Совпадают у всех:\n")
        for slot in sorted(full_matches, key=lambda x: (x[0], x[1])):
            lines.append(f"• {format_slot(slot)}")
    else:
        lines.append("Полных совпадений у всех нет.")
    lines.append("\nЛучшие варианты:\n")
    for idx, ((date, hour), count) in enumerate(sorted_slots[:5], start=1):
        matching_users = [
            data["name"]
            for data in users_data.values()
            if (date, hour) in data["slots"]
        ]
        names_text = ", ".join(matching_users)
        lines.append(
            f"{idx}. {date} {hour:02d}:00 — {count}/{participant_count} "
            f"({names_text})"
        )
    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=build_result_keyboard(len(last_ranked_slots))
    )
async def agreed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not agreed_slot:
        await update.message.reply_text(
            "Пока согласованной даты нет.",
            reply_markup=build_main_keyboard()
        )
        return
    await update.message.reply_text(
        f"📌 Согласованная дата события:\n{format_slot(agreed_slot)}",
        reply_markup=build_main_keyboard()
    )
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global users_data, agreed_slot, last_ranked_slots

    users_data.clear()
    agreed_slot = None
    last_ranked_slots = []
    await update.message.reply_text(
        "Все данные очищены.\nМожно согласовывать новую дату.",
        reply_markup=build_main_keyboard()
    )
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global agreed_slot, users_data, last_ranked_slots

    query = update.callback_query
    if not query:
        return
    await query.answer()
    data = query.data or ""

    if data.startswith("agree_"):
        if not last_ranked_slots:
            await query.message.reply_text("Сначала нужно получить варианты через /result.")
            return
        try:
            idx = int(data.split("_")[1])
        except (IndexError, ValueError):
            await query.message.reply_text("Не удалось определить выбранный вариант.")
            return
if idx < 0 or idx >= len(last_ranked_slots):
            await query.message.reply_text("Такого варианта уже нет.")
            return

        agreed_slot = last_ranked_slots[idx]

        await query.message.reply_text(
            f"✅ Дата согласована:\n{format_slot(agreed_slot)}",
            reply_markup=build_main_keyboard()
        )
        return
    if data == "remind_agreed":
        if not agreed_slot:
            await query.message.reply_text(
                "Пока согласованной даты нет.",
                reply_markup=build_main_keyboard()
            )
        else:
            await query.message.reply_text(
                f"📌 Согласованная дата события:\n{format_slot(agreed_slot)}",
                reply_markup=build_main_keyboard()
            )
        return
    if data == "reset_all":
        users_data.clear()
        agreed_slot = None
        last_ranked_slots = []

        await query.message.reply_text(
            "🗑 Предыдущие данные удалены.\n"
            "Можно присылать новые варианты даты.",
            reply_markup=build_main_keyboard()
        )
        return
def main() -> None:
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("result", result))
    app.add_handler(CommandHandler("who", who))
    app.add_handler(CommandHandler("agreed", agreed))
    app.add_handler(CommandHandler("reset", reset))

    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
