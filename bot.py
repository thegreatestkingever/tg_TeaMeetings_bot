from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")

users_data = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Отправь даты в формате:\n\n"
        "11.04: 15, 16\n"
        "12.04: 18"
    )

def parse_input(text):
    result = set()
    lines = text.split("\n")

    for line in lines:
        if ":" in line:
            date_part, time_part = line.split(":", 1)
            date = date_part.strip()
            times = time_part.split(",")

            for t in times:
                t = t.strip()
                if t.isdigit():
                    hour = int(t)
                    if 0 <= hour <= 23:
                        result.add((date, hour))

    return result


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    slots = parse_input(text)

    if not slots:
        await update.message.reply_text("Не поняла формат. Пример:\n11.04: 15, 16\n12.04: 18")
        return

    users_data[user_id] = slots
    await update.message.reply_text("Принято")


async def result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not users_data:
        await update.message.reply_text("Пока нет данных")
        return

    counter = {}

    for user_slots in users_data.values():
        for slot in user_slots:
            counter[slot] = counter.get(slot, 0) + 1

    sorted_slots = sorted(counter.items(), key=lambda x: (-x[1], x[0][0], x[0][1]))

    text = "Лучшие варианты:\n\n"

    for i, (slot, count) in enumerate(sorted_slots[:5], start=1):
        date, hour = slot
        text += f"{i}. {date} {hour}:00 — {count} чел\n"

    await update.message.reply_text(text)


def main():
    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .read_timeout(60)
        .write_timeout(60)
        .connect_timeout(60)
        .pool_timeout(60)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("result", result))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен...")
