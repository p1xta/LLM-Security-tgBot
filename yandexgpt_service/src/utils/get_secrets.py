import json
from typing import Optional, Dict
import os
import requests
from dotenv import load_dotenv

from log.logger import logger


load_dotenv()

FOLDER_ID = os.getenv("FOLDER_ID")


def get_iam_token_on_YC_vm():
    header = {
        "Metadata-Flavor":"Google"
    }
    url = "http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token"
    response = requests.get(url=url, headers=header)
    json_response = response.json()
    return json_response['access_token']

def get_all_secrets_payload(folder_id: Optional[str] = FOLDER_ID, timeout: int = 10) -> Dict[str, Dict[str, str]]:
    headers = {
        "Authorization": f"Bearer {get_iam_token_on_YC_vm()}",
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
            logger.error(f"Ошибка сети при обращении к Lockbox list API: {e}")
            break

        if resp.status_code in (401, 403):
            logger.error(f"Ошибка авторизации в Lockbox API: {resp.status_code}, {resp.text}")
            break

        if not resp.ok:
            logger.error(f"Ошибка при получении списка секретов: {resp.status_code}, {resp.text}")
            break

        try:
            body = resp.json()
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка при парсинге JSON ответа: {e}")
            break

        for secret in body.get("secrets", []):
            secret_id = secret.get("id")
            if not secret_id:
                continue

            payload_url = f"{payload_base}/{secret_id}/payload"
            try:
                p_resp = requests.get(payload_url, headers=headers, timeout=timeout)
            except requests.RequestException as e:
                logger.error(f"Ошибка сети при получении payload для секрета: {e}")
                continue

            if not p_resp.ok:
                logger.error("Ошибка при получении payload для секрета.")
                continue

            try:
                payload_json = p_resp.json()
            except json.JSONDecodeError:
                logger.error("Ошибка парсинга JSON payload для секрета.")
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
    logger.info(f"Успешно загружено {len(entries_map)} секретов из Lockbox.")
    return entries_map