import json
from typing import Optional, Dict
import time
import os
import requests
import jwt
from dotenv import load_dotenv

from src.log.logger import logger

load_dotenv()

SERVICE_ACCOUNT_ID = os.getenv("SERVICE_ACCOUNT_ID")
KEY_ID = os.getenv("KEY_ID")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
FOLDER_ID = os.getenv("FOLDER_ID")

def get_iam_token(iam_token):
    """Получение IAM-токена (с кэшированием на 1 час)"""
    token_expires = 3600
    if iam_token and time.time() < token_expires:
        return iam_token

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
            "https://iam.api.cloud.yandex.net/iam/v1/tokens",
            json={"jwt": encoded_token},
            timeout=10,
        )

        if response.status_code != 200:
            raise Exception(f"Ошибка генерации токена: {response.text}")

        token_data = response.json()
        iam_token = token_data["iamToken"]
        token_expires = (
            now + 3500
        )

        logger.info("IAM token generated successfully")
        return iam_token

    except Exception as e:
        logger.error(f"Error generating IAM token: {str(e)}")
        raise

def get_all_secrets_payload(folder_id: Optional[str] = FOLDER_ID, timeout: int = 10) -> Dict[str, Dict[str, str]]:
    headers = {
        "Authorization": f"Bearer {get_iam_token(None)}",
        "Accept": "application/json",
    }

    base_list_url = "https://lockbox.api.cloud.yandex.net/lockbox/v1/secrets"
    payload_base = "https://payload.lockbox.api.cloud.yandex.net/lockbox/v1/secrets"

    entries_map: Dict[str, str] = {}
    params = {}
    if folder_id:
        params['folderId'] = folder_id

    next_page_token = None
    while True:
        if next_page_token:
            params['pageToken'] = next_page_token
        try:
            resp = requests.get(base_list_url, headers=headers, params=params or None, timeout=timeout)
        except requests.RequestException as e:
            logger.error(f"Network error when calling Lockbox list API: {e}")
            break

        if resp.status_code in (401, 403):
            logger.error(f"Auth error from Lockbox API: {resp.status_code}, {resp.text}")
            break

        if not resp.ok:
            logger.error("Error listing secrets: {resp.status_code}, {resp.text}")
            break

        try:
            body = resp.json()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from list response: {e}")
            break

        for secret in body.get("secrets", []):
            secret_id = secret.get("id")
            if not secret_id:
                continue

            payload_url = f"{payload_base}/{secret_id}/payload"
            try:
                p_resp = requests.get(payload_url, headers=headers, timeout=timeout)
            except requests.RequestException as e:
                logger.error(f"Network error when fetching payload for secrets: {e}")
                continue

            if not p_resp.ok:
                logger.error("Error fetching payload for one of the secrets.")
                continue

            try:
                payload_json = p_resp.json()
            except json.JSONDecodeError:
                logger.error("Failed to parse JSON payload for one of the secrets.")
                continue

            entries = payload_json.get("entries")
            if not isinstance(entries, list):
                continue

            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                key = entry.get("key")
                if not key:
                    continue
                if "textValue" in entry:
                    entries_map[key] = entry["textValue"]
                elif "binaryValue" in entry:
                    entries_map[key] = entry["binaryValue"]

        next_page_token = body.get("nextPageToken")
        if not next_page_token:
            break

    return entries_map