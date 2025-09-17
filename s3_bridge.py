import os
import tempfile
from pathlib import Path

import boto3


def load_and_index_documents(*args, **kwargs):
    raise NotImplementedError()


class S3Bridge:
    def __init__(self, s3_bucket, *args, **kwargs):
        self.client = boto3.client(*args, **kwargs)

    def upload_to_s3(self, s3_bucket: str, local_file_path: Path):
        try:
            self.client.upload_file(
                local_file_path, s3_bucket, local_file_path
            )
            print(
                f"Файл {local_file_path} успешно отправлен в bucket {s3_bucket}."
            )
        except FileNotFoundError:
            print(f"Файл {local_file_path} не найден.")
        except Exception as e:
            print(f"Ошибка загрузки файла: {e}")

    def download_from_s3(self, s3_bucket: str):
        try:
            objects = self.client.list_objects_v2(
                Bucket=s3_bucket, Prefix=s3_bucket
            )
        except Exception as e:
            print(f"Ошибка подключения: {e}")
            return None

        if "Contents" not in objects:
            return load_and_index_documents([])

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
                    if os.path.getsize(local_path) == 0:
                        continue
                    local_files.append(local_path)
                except Exception as e:
                    print(f"Ошибка скачивания {key}: {e}")
                    continue

            return load_and_index_documents(local_files)
