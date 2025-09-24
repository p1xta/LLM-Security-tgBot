import os
import tempfile
import boto3
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders import UnstructuredHTMLLoader

from log.logger import logger


def read_file(filepath):
    if filepath.endswith(".pdf"):
        loader = PyPDFLoader(filepath)
    elif filepath.endswith(".txt"):
        loader = TextLoader(filepath, encoding="utf-8")
    elif filepath.endswith(".html", ".htm"):
        loader = UnstructuredHTMLLoader(filepath)
    
    loaded = loader.load()
    
    valid_docs = [
        doc for doc in loaded
        if hasattr(doc, 'page_content') and
        isinstance(doc.page_content, str) and
        doc.page_content.strip()
    ]
    
    return valid_docs

class S3Bridge:
    def __init__(self, *args, **kwargs):
        self.client = boto3.client(*args, **kwargs)

    def upload_to_s3(self, s3_bucket: str, local_file_path: Path, dest_file_path: str):
        try:
            self.client.upload_file(
                local_file_path, s3_bucket, dest_file_path
            )
            logger.info(f"Файл {local_file_path} успешно отправлен в bucket {s3_bucket}.")
        except FileNotFoundError:
            logger.error(f"Файл {local_file_path} не найден.")
        except Exception as e:
            logger.error(f"Ошибка загрузки файла: {e}")

    def delete_from_s3(self, s3_bucket: str, user_id: str, file_name: str):
        try:
            self.client.delete_object(
                Bucket=s3_bucket, 
                Key=f"{user_id}/{file_name}"
            )
            logger.info(f"Файл {file_name} успешно удален из bucket {s3_bucket}.")
        except FileNotFoundError:
            logger.error(f"Файл {file_name} не найден.")
        except Exception as e:
            logger.error(f"Ошибка загрузки файла: {e}")

    def download_from_s3(self, s3_bucket: str, s3_folder: str = ""):
        try:
            objects = self.client.list_objects_v2(
                Bucket=s3_bucket, Prefix=s3_folder
            )
        except Exception as e:
            logger.error(f"Ошибка подключения: {e}")
            return None

        if "Contents" not in objects:
            return []

        local_files = []
        with tempfile.TemporaryDirectory() as tmpdir:
            for obj in objects["Contents"]:
                key = obj.get("Key")
                if not key or not isinstance(key, str) or key.endswith("/"):
                    continue

                size = obj.get("Size", 0)
                if size == 0:
                    continue

                local_path = os.path.join(tmpdir, os.path.basename(key))
                try:
                    self.client.download_file(s3_bucket, key, local_path)
                    
                    docs = read_file(local_path)
                    
                    if os.path.getsize(local_path) == 0:
                        continue
                    local_files.extend(docs)
                except Exception as e:
                    logger.error(f"Ошибка скачивания {key}: {e}")
                    continue

            return local_files

    def get_loaded_filenames(self, s3_bucket: str, s3_folder: str = "") -> list:
        try:
            objects = self.client.list_objects_v2(
                Bucket=s3_bucket,
                Prefix=s3_folder
            )
        except Exception as e:
            logger.error(f"Ошибка подключения: {e}")
            return []

        if "Contents" not in objects:
            return []

        filenames = []
        for obj in objects["Contents"]:
            key = obj.get("Key")
            size = obj.get("Size", 0)

            if not key or key.endswith("/") or size == 0:
                continue

            filenames.append(os.path.basename(key))

        return filenames