import os
from contextlib import asynccontextmanager
from http import HTTPStatus
from fastapi import FastAPI, Request, Response
from telegram import Update
import httpx
import uvicorn
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from config.settings import get_settings
from utils.get_secrets import get_all_secrets_payload

settings = get_settings()

secrets_dict = get_all_secrets_payload()
TELEGRAM_TOKEN = secrets_dict["TELEGRAM_TOKEN"]
WEBHOOK_DOMAIN = ""
ORCHESTRATOR_URL = settings.ORCHESTRATOR_URL


bot_builder = (
    Application.builder()
    .token(TELEGRAM_TOKEN)
    .updater(None)
    .build()
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await bot_builder.bot.setWebhook(url=WEBHOOK_DOMAIN)
    async with bot_builder:
        await bot_builder.start()
        yield
        await bot_builder.stop()


app = FastAPI(lifespan=lifespan)


@app.post("/")
async def process_update(request: Request):
    message = await request.json()
    update = Update.de_json(data=message, bot=bot_builder.bot)
    await bot_builder.process_update(update)
    return Response(status_code=HTTPStatus.OK)


# --- Handlers ---
async def start(update: Update, _: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет 👋 Я корпоративный ассистент. Напиши вопрос.")


async def handle_message(update: Update, _: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    message_id = update.message.message_id
    message_date = update.message.date.strftime("%Y-%m-%d %H:%M:%S")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{ORCHESTRATOR_URL}/process",
                json={
                    "user_id": user_id,
                    "message_id": message_id,
                    "chat_id": chat_id, 
                    "text": user_text,
                    "timestamp": message_date
                },
                timeout=30,
            )
            data = response.json()
            reply = data.get("message", "⚠️ Ошибка обработки")
        except Exception as e:
            reply = f"❌ Сервис недоступен: {e}"

    await update.message.reply_text(reply)


if __name__ == "__main__":
    bot_builder.add_handler(CommandHandler("start", start))
    bot_builder.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ['PORT']))