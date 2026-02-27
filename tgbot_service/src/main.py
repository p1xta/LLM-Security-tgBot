import os
from contextlib import asynccontextmanager
from http import HTTPStatus
from fastapi import FastAPI, Request, Response
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import httpx
import uvicorn
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, CallbackQueryHandler, filters

from config.settings import get_settings
from utils.get_secrets import get_all_secrets_payload
from utils.get_iam_token import get_iam_token_on_YC_vm
from log.logger import logger

settings = get_settings()

secrets_dict = get_all_secrets_payload()
TELEGRAM_TOKEN = secrets_dict["TELEGRAM_TOKEN"]
S3_BUCKET = secrets_dict["S3_BUCKET"]
WEBHOOK_DOMAIN = os.environ.get("WEBHOOK_URL", "")
ORCHESTRATOR_URL = settings.ORCHESTRATOR_URL

# --- состояния пользователей ---
user_state = {}  # user_id -> "state"

bot_builder = (
    Application.builder()
    .token(TELEGRAM_TOKEN)
    .updater(None)
    .build()
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Запуск FastAPI приложения и установка WebHook")
    async with bot_builder:
        logger.info("Бот запущен")
        await bot_builder.start()
        yield
        await bot_builder.stop()
        logger.info("Бот остановлен")


app = FastAPI(lifespan=lifespan)


@app.post("/")
async def process_update(request: Request):
    message = await request.json()
    logger.info(f"Получено сообщение: {message}")
    update = Update.de_json(data=message, bot=bot_builder.bot)
    await bot_builder.process_update(update)
    return Response(status_code=HTTPStatus.OK)


# --- Handlers ---
async def start(update: Update, _: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Пользователь {update.message.from_user} вызвал команду /start")
    await update.message.reply_text("Привет 👋 Я корпоративный ассистент.\
                                    Доступные команды: \n \
                                    /upload - загрузка файлов в ваше хранилище. \
                                    На основе этих файлов модель будет отвечать на вопросы.\n \
                                    /delete - удаление файлов из хранилища. \n\n \
                                    Чтобы спросить что-то, просто напишите сообщение!")

async def start_upload(update: Update, _: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_state[user_id] = "awaiting_file"
    logger.info(f"Пользователь {user_id} начал процесс загрузки файлов")
    await update.message.reply_text("📂 Пришлите документ, который нужно загрузить.")

async def start_delete(update: Update, _: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    async with httpx.AsyncClient() as client:
        try:
            iam_token = await get_iam_token_on_YC_vm(client)
            response = await client.post(
                f"{ORCHESTRATOR_URL}/get_filenames",
                headers={"Authorization": f"Bearer {iam_token}"},
                data={"bucket": S3_BUCKET, "user_id": str(user_id)},
                timeout=30,
            )
            data = response.json()
            files = data.get("files", [])

            if not files:
                await update.message.reply_text("Файлы не найдены.")
                return

            keyboard = [
                [InlineKeyboardButton(f, callback_data=f"delete:{f}")]
                for f in files
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "Выберите файл для удаления:", reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Ошибка при получении списка файлов: {e}")
            await update.message.reply_text(f"❌ Не удалось получить список файлов: {e}")

async def handle_document(update: Update, _: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_state.get(user_id) != "awaiting_file":
        await update.message.reply_text("⚠️ Чтобы загрузить документ, сначала вызовите /upload")
        return

    document = update.message.document
    if not document:
        await update.message.reply_text("❌ Сообщение не содержит документа.")
        return

    file = await document.get_file()
    file_path = f"/tmp/{document.file_name}"
    await file.download_to_drive(file_path)

    logger.info(f"Пользователь {user_id} загрузил файл {document.file_name}")
    
    async with httpx.AsyncClient() as client:
        try:
            if file.file_size > 30 * 1024 * 1024:
                logger.info(f"Попытка загрузить файл размером более 30 Мбайт")
                raise Exception("Размер файла не должен превышать 30 Мбайт")
            iam_token = await get_iam_token_on_YC_vm(client)
            print(iam_token)
            with open(file_path, "rb") as f:
                file_content = f.read()
                response = await client.post(
                    f"{ORCHESTRATOR_URL}/upload",
                    headers={
                        "Authorization": f"Bearer {iam_token}"
                    },
                    data={"user_id": str(user_id), "bucket": S3_BUCKET},
                    files={"file": (document.file_name, file_content, document.mime_type)},
                    timeout=300,
                )
            data = response.json()
            reply = data.get("message", "⚠️ Ошибка обработки")
            logger.info(f"Ответ от оркестратора для {user_id}: {reply}")
        except Exception as e:
            reply = f"❌ Ошибка: {e}"
            logger.error(f"Ошибка при загрузке файла от {user_id}: {e}")

    user_state.pop(user_id, None)
    await update.message.reply_text(reply)

async def handle_delete_callback(update: Update, _: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if not data.startswith("delete:"):
        return

    file_name = data.split("delete:")[1]

    async with httpx.AsyncClient() as client:
        try:
            iam_token = await get_iam_token_on_YC_vm(client)
            response = await client.post(
                f"{ORCHESTRATOR_URL}/delete_file",
                headers={
                    "Authorization": f"Bearer {iam_token}"
                },
                data={"bucket": S3_BUCKET, "user_id": str(user_id), "file_name": file_name},
                timeout=30,
            )
            result = response.json()
            msg = result.get("message", f"Файл {file_name} удалён.")
        except Exception as e:
            logger.error(f"Ошибка при удалении файла {file_name}: {e}")
            msg = f"❌ Не удалось удалить файл {file_name}: {e}"

    await query.edit_message_text(msg)

async def handle_message(update: Update, _: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.message.chat_id
    user_id = update.message.from_user.id
    message_id = update.message.message_id
    message_date = update.message.date.strftime("%Y-%m-%d %H:%M:%S")

    processing_message = await update.message.reply_text("Обработка запроса...")
    logger.info(f"Обрабатывается сообщение от {user_id} ({chat_id}): {user_text}")

    async with httpx.AsyncClient() as client:
        try:
            iam_token = await get_iam_token_on_YC_vm(client)
            response = await client.post(
                f"{ORCHESTRATOR_URL}/process",
                headers={
                    "Authorization": f"Bearer {iam_token}"
                },
                json={
                    "user_id": user_id,
                    "message_id": message_id,
                    "chat_id": chat_id, 
                    "text": user_text,
                    "timestamp": message_date
                },
                timeout=300,
            )
            data = response.json()
            reply = data.get("message", "⚠️ Ошибка обработки")
            logger.info(f"Ответ пользователю {user_id}: {reply}")
        except Exception as e:
            reply = f"❌ Сервис недоступен: {e}"
            logger.error(f"Ошибка при запросе к оркестратору: {e}")

    await processing_message.edit_text(reply)


if __name__ == "__main__":
    bot_builder.add_handler(CommandHandler("start", start))
    bot_builder.add_handler(CommandHandler("upload", start_upload))
    bot_builder.add_handler(CommandHandler("delete", start_delete))
    bot_builder.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    bot_builder.add_handler(CallbackQueryHandler(handle_delete_callback, pattern=r"^delete:"))
    bot_builder.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ['PORT']))