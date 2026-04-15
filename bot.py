import os
import time

print("=== СТАРТ ===")

TOKEN = os.getenv("BOT_TOKEN")
print("TOKEN:", TOKEN)

if not TOKEN:
    print("❌ ТОКЕН НЕ НАЙДЕН")
    time.sleep(60)  # чтобы не закрывался сразу
    exit()
