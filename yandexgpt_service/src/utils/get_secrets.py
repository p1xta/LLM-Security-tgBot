import json
from typing import Optional, Dict
import time
import os
import requests
import jwt
from dotenv import load_dotenv


load_dotenv()

# SERVICE_ACCOUNT_ID = os.getenv("SERVICE_ACCOUNT_ID")
# KEY_ID = os.getenv("KEY_ID")
# PRIVATE_KEY = os.getenv("PRIVATE_KEY")
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
    print(FOLDER_ID)
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
            print("Network error when calling Lockbox list API: %s", e)
            break

        if resp.status_code in (401, 403):
            print("Auth error from Lockbox API: %s %s", resp.status_code, resp.text)
            break

        if not resp.ok:
            print("Error listing secrets: %s %s", resp.status_code, resp.text)
            break

        try:
            body = resp.json()
        except json.JSONDecodeError as e:
            print("Failed to parse JSON from list response: %s", e)
            break

        for secret in body.get("secrets", []):
            secret_id = secret.get("id")
            if not secret_id:
                continue

            payload_url = f"{payload_base}/{secret_id}/payload"
            try:
                p_resp = requests.get(payload_url, headers=headers, timeout=timeout)
            except requests.RequestException as e:
                print("Network error when fetching payload for %s: %s", secret_id, e)
                continue

            if not p_resp.ok:
                print("Error fetching payload for %s: %s %s", secret_id, p_resp.status_code, p_resp.text)
                continue

            try:
                payload_json = p_resp.json()
            except json.JSONDecodeError:
                print("Failed to parse JSON payload for %s. Raw: %s", secret_id, p_resp.text)
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