import os
import re
from collections import Counter
from typing import Dict, Set, Tuple

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN не найден")

MAX_USERS = 5

# user_id -> {"name": str, "slots": set[(date, hour)]}
users_data: Dict[int, dict] = {}


def normalize_name(user) -> str:
    if user.username:
        return f"@{user.username}"
    full_name = " ".join(filter(None, [user.first_name, user.last_name])).strip()
    return full_name or str(user.id)


def parse_input(text: str) -> Set[Tuple[str, int]]:
    """
    Поддерживает оба формата:
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
            if not t:
                continue
            if not t.isdigit():
                continue

            hour = int(t)
            if 0 <= hour <= 23:
                slots.add((date_part, hour))

    return slots


def format_slots(slots: Set[Tuple[str, int]]) -> str:
    sorted_slots = sorted(slots, key=lambda x: (x[0], x[1]))
    return "\n".join(f"{date} {hour:02d}:00" for date, hour in sorted_slots)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет.\n\n"
        "Отправь даты и часы в формате:\n"
        "11.04 15,16\n"
        "12.04 14\n\n"
        "Можно и так:\n"
        "11.04: 15, 16\n"
        "12.04: 14\n\n"
        "Команды:\n"
        "/result — показать совпадения\n"
        "/who — кто уже отправил\n"
        "/reset — очистить всё"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return

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
        f"{action_text} твои варианты:\n\n{format_slots(slots)}"
    )


async def who(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not users_data:
        await update.message.reply_text("Пока никто ничего не отправил.")
        return

    lines = [f"Сейчас есть данные от {len(users_data)} из {MAX_USERS}:\n"]
    for idx, data in enumerate(users_data.values(), start=1):
        lines.append(f"{idx}. {data['name']} — {len(data['slots'])} слотов")

    await update.message.reply_text("\n".join(lines))


async def result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not users_data:
        await update.message.reply_text("Пока нет данных.")
        return

    all_slot_sets = [data["slots"] for data in users_data.values()]
    participant_count = len(all_slot_sets)

    counter = Counter()
    for slot_set in all_slot_sets:
        counter.update(slot_set)

    full_matches = set.intersection(*all_slot_sets) if all_slot_sets else set()

    lines = [f"Участников с данными: {participant_count}\n"]

    if full_matches:
        lines.append("Совпадают у всех:\n")
        for date, hour in sorted(full_matches, key=lambda x: (x[0], x[1])):
            lines.append(f"• {date} {hour:02d}:00")
    else:
        lines.append("Полных совпадений у всех нет.")

    lines.append("\nЛучшие варианты по числу совпадений:\n")

    sorted_slots = sorted(
        counter.items(),
        key=lambda x: (-x[1], x[0][0], x[0][1])
    )

    for idx, ((date, hour), count) in enumerate(sorted_slots[:10], start=1):
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

    await update.message.reply_text("\n".join(lines))


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    users_data.clear()
    await update.message.reply_text("Все данные очищены.")


def main() -> None:
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("result", result))
    app.add_handler(CommandHandler("who", who))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
