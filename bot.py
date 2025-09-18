import logging
import os
import re
import time

import jwt
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from s3_bridge import S3Bridge
from faiss_bridge import FAISSbridge


load_dotenv()

S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")
S3_PREFIX = os.getenv("S3_PREFIX")

SERVICE_ACCOUNT_ID = os.getenv("SERVICE_ACCOUNT_ID")
KEY_ID = os.getenv("KEY_ID")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
FOLDER_ID = os.getenv("FOLDER_ID")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class YandexGPTBot:
    def __init__(self):
        self.iam_token = None
        self.token_expires = 0
        self.s3 = S3Bridge(
            's3',
            endpoint_url=S3_ENDPOINT,
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
            region_name='ru-central1'
        )
        self.faiss = FAISSbridge()

    def get_iam_token(self):
        """Получение IAM-токена (с кэшированием на 1 час)"""
        if self.iam_token and time.time() < self.token_expires:
            return self.iam_token

        try:
            now = int(time.time())
            payload = {
                "aud": "https://iam.api.cloud.yandex.net/iam/v1/tokens",
                "iss": SERVICE_ACCOUNT_ID,
                "iat": now,
                "exp": now + 3600,
            }

            encoded_token = jwt.encode(
                payload,
                PRIVATE_KEY,
                algorithm="PS256",
                headers={"kid": KEY_ID},
            )

            response = requests.post(
                "https://iam.api.cloud.yandex.net/iam/v1/tokens",  # save this
                json={"jwt": encoded_token},
                timeout=10,
            )

            if response.status_code != 200:
                raise Exception(f"Ошибка генерации токена: {response.text}")

            token_data = response.json()
            self.iam_token = token_data["iamToken"]
            self.token_expires = (
                now + 3500
            )  # На 100 секунд меньше срока действия

            logger.info("IAM token generated successfully")
            return self.iam_token

        except Exception as e:
            logger.error(f"Error generating IAM token: {str(e)}")
            raise

    def ask_gpt(self, question):
        """Запрос к Yandex GPT API"""
        try:
            iam_token = self.get_iam_token()

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {iam_token}",
                "x-folder-id": FOLDER_ID,
            }
            
            docs = self.s3.download_from_s3("tgbot-storage")
            self.faiss.store_doc_vectors(docs)
            retrieved_docs = self.faiss.find_relevant_data(question)

            context_chunks = "\n\n".join([doc.page_content for doc in retrieved_docs])

            data = {
                "modelUri": f"gpt://{FOLDER_ID}/yandexgpt-lite",
                "completionOptions": {
                    "stream": False,
                    "temperature": 0.6,
                    "maxTokens": 2000,
                },
                "messages": [
                    {
                        "role": "system",
                        "text": (
                            "Ты — корпоративный ассистент. Отвечай строго по документам. "
                            "Если информации нет — скажи 'В документах не указано'.\n\n"
                            f"Контекст из документов:\n{context_chunks}"
                        )
                    },
                    {
                        "role": "user", 
                        "text": question
                    }],
            }

            response = requests.post(
                "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",  # save this
                headers=headers,
                json=data,
                timeout=30,
            )

            if response.status_code != 200:
                logger.error(f"Yandex GPT API error: {response.text}")
                raise Exception(f"Ошибка API: {response.status_code}")

            return response.json()["result"]["alternatives"][0]["message"][
                "text"
            ]

        except Exception as e:
            logger.error(f"Error in ask_gpt: {str(e)}")
            raise


# Создаем экземпляр бота
yandex_bot = YandexGPTBot()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "Привет! Я бот для работы с Yandex GPT. Просто напиши мне свой вопрос"
    )


patterns = {
    "prompt_injection": [
        r"(?i)(игнорируй|забудь|смени|измени).*(инструкц|правил|систем|предыдущ)",
        r"(?i)(выполни|сделай|напиши).*(как|вместо|в роли).*(пользователь|систем|админ)",
        r"(?i)(ignore|forget|override|system).*(prompt|instructions|previous)",
    ],
    "leak_sensitive_data": [
        r"(?i)(парол|креденш|токен|api[_-]?key|секрет|auth|ключ|access[_-]?key)",
        r"(?i)(личн|персональн|конфиденц|паспорт|банковск|карт|счет|password|credit|card)",
    ],
    "code_execution": [
        r"(?i)(exec|eval|system|os\.|subprocess|компилир|выполни.*код|запусти.*програм)",
        r"(`{3}|\b(?:import|fork|execve|socket|syscall)\b)",
    ],
    "bypass_filters": [
        r"(?i)(обойди|обход|bypass|обмани|фильтр|модерац)",
        r"(\bне\s+проверяй\b|\bignore\s+filter\b)",
        r"(\\x[0-9a-fA-F]|урл|кодировк|base64)",
    ],
}


def check_fraud(text):
    alerts = []
    for category, pattern_list in patterns.items():
        for pattern in pattern_list:
            if re.search(pattern, text):
                alerts.append((category, pattern))
                break
    return alerts


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    user_message = update.message.text

    print(user_message)

    alerts = check_fraud(user_message)

    for alert in alerts:
        print(
            f"\n\nERROR: {update.effective_user.id} TRIED TO FRAUD THE MODEL\ntype: {alert[0]}\nmessage: {user_message}\n\n"
        )
        raise Exception("Somebody tried to fraud the model")

    if not user_message.strip():
        await update.message.reply_text("Пожалуйста, введите вопрос")
        return

    try:
        # Показываем статус "печатает"
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action="typing"
        )

        response = yandex_bot.ask_gpt(user_message)
        await update.message.reply_text(response)

    except Exception as e:
        logger.error(f"Error handling message: {str(e)}")
        await update.message.reply_text(
            "Извините, произошла ошибка при обработке вашего запроса. "
            "Пожалуйста, попробуйте позже."
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "Произошла ошибка. Пожалуйста, попробуйте позже."
        )


def main():
    """Основная функция"""
    try:
        # Проверяем возможность генерации токена при запуске
        yandex_bot.get_iam_token()
        logger.info("IAM token test successful")

        application = Application.builder().token(TELEGRAM_TOKEN).build()

        application.add_handler(CommandHandler("start", start))
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        )
        application.add_error_handler(error_handler)

        logger.info("Бот запускается...")
        application.run_polling()

    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}")


if __name__ == "__main__":
    main()
