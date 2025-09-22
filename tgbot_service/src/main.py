import os
from contextlib import asynccontextmanager
from http import HTTPStatus
from fastapi import FastAPI, Request, Response
from telegram import Update
import httpx
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_DOMAIN = "https://2107667e15b5.ngrok-free.app"
ORCHESTRATOR_URL = "https://localhost:8001"


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

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                ORCHESTRATOR_URL,
                json={"chat_id": chat_id, "text": user_text},
                timeout=30,
            )
            data = response.json()
            reply = data.get("message", "⚠️ Ошибка обработки")
        except Exception as e:
            reply = f"❌ Сервис недоступен: {e}"

    await update.message.reply_text(reply)


bot_builder.add_handler(CommandHandler("start", start))
bot_builder.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
