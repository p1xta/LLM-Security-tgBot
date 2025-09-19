import requests
import time
import jwt
import logging
import os
from dotenv import load_dotenv

load_dotenv()

SERVICE_ACCOUNT_ID = os.getenv("SERVICE_ACCOUNT_ID")
KEY_ID = os.getenv("KEY_ID")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
FOLDER_ID = os.getenv("FOLDER_ID")


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class YandexGPTBot:
    def __init__(self):
        self.iam_token = None
        self.token_expires = 0

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

    def ask_gpt(self, user_prompt, sys_prompt):
        """Запрос к Yandex GPT API"""
        try:
            iam_token = self.get_iam_token()

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {iam_token}",
                "x-folder-id": FOLDER_ID,
            }

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
                        "text": sys_prompt
                    },
                    {
                        "role": "user", 
                        "text": user_prompt
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
