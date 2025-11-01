#!/usr/bin/env python3
# Telegram бот: показывает анкету при /start и пересылает все сообщения админу

import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# === Настройки ===
BOT_TOKEN = "8370546925:AAFaP7bQCG_HBqZ3duloO2yA7T96vXZho1g"  # токен вставляется в Render
ADMIN_ID = 6115320432  # ← твой Telegram ID (админ)

if not BOT_TOKEN:
    raise SystemExit("❌ Укажи BOT_TOKEN в настройках Render (переменная окружения).")

# === Команда /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # --- анкетный текст (можно изменить как хочешь) ---
    text = (
        f"👋 Привет, {user.first_name or ''}!\n\n"
        "📋 Это бот анкеты.\n\n"
        "Пожалуйста, укажи свои данные:\n"
        "1️⃣ Имя и возраст\n"
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


# === запуск приложения ===
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL & (~filters.User(ADMIN_ID)), forward_to_admin))
    app.add_handler(MessageHandler(filters.ALL & filters.User(ADMIN_ID), reply_from_admin))

    print("✅ Бот запущен и работает 24/7 (если на Render).")
    app.run_polling()


if __name__ == "__main__":
    main()
