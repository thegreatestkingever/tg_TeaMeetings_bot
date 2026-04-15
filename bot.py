import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

print("=== СТАРТ ===")
print("TOKEN есть:", bool(TOKEN))

if not TOKEN:
    raise ValueError("BOT_TOKEN не найден")

users_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Отправь варианты дат и времени, например:\n11.04 15,16\n12.04 14"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    slots = set()

    for line in text.split("\n"):
        parts = line.strip().split()
        if len(parts) >= 2:
            date = parts[0]
            times = parts[1].split(",")
            for t in times:
                slots.add(f"{date} {t}")

    users_data[user_id] = slots
    await update.message.reply_text("Принято")

async def result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not users_data:
        await update.message.reply_text("Нет данных")
        return

    common = set.intersection(*users_data.values())

    if not common:
        await update.message.reply_text("Совпадений нет")
    else:
        await update.message.reply_text(
            "Подходят варианты:\n" + "\n".join(sorted(common))
        )

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("result", result))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
