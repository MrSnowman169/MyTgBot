#!/usr/bin/env python3
# Telegram бот: показывает анкету при /start и пересылает все сообщения админу

import os
import threading # Для работы 24/7 на Replit
from flask import Flask # Для работы 24/7 на Replit
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# === Настройки ===
# Считываем из переменных окружения (Secrets Replit)
BOT_TOKEN = os.getenv("BOT_TOKEN") 
ADMIN_ID_STR = os.getenv("ADMIN_ID")

if not BOT_TOKEN:
    raise SystemExit("❌ Укажи BOT_TOKEN в переменных окружения (Secrets).")

if not ADMIN_ID_STR or not ADMIN_ID_STR.isdigit():
    raise SystemExit("❌ Укажи ADMIN_ID в переменных окружения (Secrets).")

ADMIN_ID = int(ADMIN_ID_STR)

# === Временное хранилище для ЧС (Не сохраняется после перезапуска!) ===
BLACKLISTED_USER_IDS = set() 
# Если нужен постоянный черный список, нужно использовать базу данных или файл.
# ---------------------------------------------------------------------


# === Команда /cs (Черный список) ===
async def blacklist_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Админ управляет черным списком. ID берется из аргументов команды."""
    
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        # Показать текущий список
        if BLACKLISTED_USER_IDS:
            await update.message.reply_text(
                f"🚫 Текущий ЧС (ID пользователей): {', '.join(map(str, BLACKLISTED_USER_IDS))}"
            )
        else:
            await update.message.reply_text("🚫 Черный список пуст. Для добавления: /cs ID_пользователя")
        return

    try:
        # Пытаемся получить ID из аргумента команды
        user_id = int(context.args[0])
        
        if user_id in BLACKLISTED_USER_IDS:
            BLACKLISTED_USER_IDS.remove(user_id)
            action = "разблокирован"
        else:
            BLACKLISTED_USER_IDS.add(user_id)
            action = "заблокирован"
            
        await update.message.reply_text(
            f"✅ Пользователь с ID **{user_id}** {action}. Сообщения от него {'больше не будут' if action == 'заблокирован' else 'снова будут'} пересылаться.",
            parse_mode='Markdown'
        )

    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат. Используйте: /cs ID_пользователя. ID берется из пересланного сообщения."
        )


# === Команда /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # --- ПРОВЕРКА ЧС ---
    if user.id in BLACKLISTED_USER_IDS:
        await update.message.reply_text("🚫 Вы не можете использовать этого бота.")
        return
    # -------------------

    # --- анкетный текст (можно изменить как хочешь) ---
    text = (
        f"👋 Привет, {user.first_name or ''}!\n\n"
        "📋 Это бот анкеты.\n\n"
        "Пожалуйста, укажи свои данные:\n"
        "1️⃣ 1Имя и возраст\n"
        "2️⃣ Город проживания\n"
        "3️⃣ Чем увлекаешься?\n"
        "4️⃣ Почему решил написать?\n\n"
        "📝 Напиши всё одним сообщением ниже 👇"
    )
    # ---------------------------------------------------

    await update.message.reply_text(text)

    # уведомление админу, что кто-то запустил бота
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🟢 Новый пользователь: {user.first_name or ''} {user.last_name or ''}\n"
                 f"ID: {user.id}\nUsername: @{user.username if user.username else 'нет'}"
        )
    except Exception:
        pass


# === пересылка сообщений от пользователей админу ===
async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # --- ПРОВЕРКА ЧС ---
    if user.id in BLACKLISTED_USER_IDS:
        return # Игнорируем сообщение от заблокированного пользователя
    # -------------------

    msg = update.message

    try:
        info = (
            f"📨 Сообщение от:\n"
            f"Имя: {user.first_name or ''} {user.last_name or ''}\n"
            f"Username: @{user.username if user.username else 'нет'}\n"
            f"ID: {user.id}"
        )
        await context.bot.send_message(chat_id=ADMIN_ID, text=info)
        await context.bot.forward_message(
            chat_id=ADMIN_ID,
            from_chat_id=msg.chat.id,
            message_id=msg.message_id
        )
    except Exception as e:
        print(f"Ошибка при пересылке: {e}")


# === ответы админа пользователям ===
async def reply_from_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (код функции не менялся) ...
    msg = update.message
    if update.effective_user.id != ADMIN_ID:
        return

    reply = msg.reply_to_message
    if not reply:
        await msg.reply_text("⚠️ Ответь на пересланное сообщение от пользователя.")
        return

    target_user = None
    if reply.forward_from:
        target_user = reply.forward_from.id
    else:
        import re
        m = re.search(r"ID[:\s]+(\d{5,})", reply.text or "")
        if m:
            target_user = int(m.group(1))

    if not target_user:
        await msg.reply_text("❌ Не удалось определить, кому отправить сообщение.")
        return

    try:
        if msg.text:
            await context.bot.send_message(chat_id=target_user, text=msg.text)
        elif msg.photo:
            await context.bot.send_photo(chat_id=target_user, photo=msg.photo[-1].file_id, caption=msg.caption or "")
        elif msg.document:
            await context.bot.send_document(chat_id=target_user, document=msg.document.file_id, caption=msg.caption or "")
        elif msg.sticker:
            await context.bot.send_sticker(chat_id=target_user, sticker=msg.sticker.file_id)
        elif msg.voice:
            await context.bot.send_voice(chat_id=target_user, voice=msg.voice.file_id)
        else:
            await msg.reply_text("⚠️ Этот тип сообщений пока не поддерживается.")
            return

        await msg.reply_text("✅ Ответ отправлен пользователю.")
    except Exception as e:
        await msg.reply_text(f"Ошибка при отправке: {e}")


# === Запуск Flask для 24/7 ===
def run_flask():
    """Запускает минимальный веб-сервер, чтобы Replit не выключал бот."""
    app = Flask(__name__)
    
    @app.route('/')
    def keep_alive():
        return "Bot is alive! (24/7 check)"
        
    # Replit использует порт 8080 для веб-сервисов
    app.run(host="0.0.0.0", port=8080)

# === запуск приложения ===
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cs", blacklist_user)) # Новый обработчик для ЧС
    app.add_handler(MessageHandler(filters.ALL & (~filters.User(ADMIN_ID)), forward_to_admin))
    app.add_handler(MessageHandler(filters.ALL & filters.User(ADMIN_ID), reply_from_admin))

    # --- Запуск Flask в отдельном потоке для 24/7 ---
    threading.Thread(target=run_flask).start()
    print("🌐 Запущен веб-сервер для поддержки 24/7.")
    # --------------------------------------------------
    
    print("✅ Бот запущен и ждет команд.")
    app.run_polling(poll_interval=1)


if __name__ == "__main__":
    main()
