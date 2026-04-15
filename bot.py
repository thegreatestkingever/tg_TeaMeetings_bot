import os
from collections import Counter

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
    raise ValueError("BOT_TOKEN не найден в переменных окружения")

users_data = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет!\n\n"
        "Отправь даты и часы в таком формате:\n"
        "11.04: 15, 16\n"
        "12.04: 18\n\n"
        "Потом напиши /result"
    )


def parse_input(text: str) -> set[tuple[str, int]]:
    result = set()
    lines = text.splitlines()

    for line in lines:
        line = line.strip()
        if not line or ":" not in line:
            continue

        date_part, time_part = line.split(":", 1)
        date_part = date_part.strip()
        time_part = time_part.strip()

        if not date_part or not time_part:
            continue

        times = [t.strip() for t in time_part.split(",")]

        for t in times:
            if t.isdigit():
                hour = int(t)
                if 0 <= hour <= 23:
                    result.add((date_part, hour))

    return result


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    user_id = update.message.from_user.id
    text = update.message.text.strip()

    slots = parse_input(text)

    if not slots:
        await update.message.reply_text(
            "Не поняла формат.\n\n"
            "Пример:\n"
            "11.04: 15, 16\n"
            "12.04: 18"
        )
        return

    users_data[user_id] = slots

    pretty_slots = sorted(slots, key=lambda x: (x[0], x[1]))
    lines = [f"{date} {hour:02d}:00" for date, hour in pretty_slots]

    await update.message.reply_text(
        "Принято:\n" + "\n".join(lines)
    )


async def result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not users_data:
        await update.message.reply_text("Пока нет данных")
        return

    counter = Counter()

    for slots in users_data.values():
        counter.update(slots)

    sorted_slots = sorted(counter.items(), key=lambda x: (-x[1], x[0][0], x[0][1]))

    lines = ["Лучшие варианты:\n"]
    for i, ((date, hour), count) in enumerate(sorted_slots[:5], start=1):
        lines.append(f"{i}. {date} {hour:02d}:00 — {count} чел")

    await update.message.reply_text("\n".join(lines))


def main() -> None:
    app
