import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()


def get_supabase_client() -> Client:
    supabase_url = os.environ.get("SUPABASE_URL")
    if not supabase_url:
        raise ValueError("SUPABASE_URL is not set")
    supabase_key = os.environ.get("SUPABASE_KEY")
    if not supabase_key:
        raise ValueError("SUPABASE_KEY is not set")
    return create_client(supabase_url, supabase_key)


class Bucket:
    def __init__(self, bucket_name: str) -> None:
        self.bucket_name = bucket_name
        self.client = get_supabase_client()

    def list_files(
        self,
        path: str,
        sort_by: dict | None = None,
    ) -> list[dict]:
        default_sort = {"column": "name", "order": "desc"}
        response = self.client.storage.from_(self.bucket_name).list(path, sort_by or default_sort)
        return response if isinstance(response, list) else []

    def list_public_urls(self, path: str, expires_in: int = 60 * 30) -> dict[str, str]:
        files = self.list_files(path)
        if not files:
            raise ValueError("No files found")
        filenames = [f"{path}/{file['name']}" for file in files]
        response = self.client.storage.from_(self.bucket_name).create_signed_urls(
            filenames, expires_in
        )
        return {
            Path(file["name"]).stem: url["signedURL"]
            for file, url in zip(files, response)
        }


if __name__ == "__main__":
    # uv run python -m siliconcrowds.bucket
    from rich import print as rich_print

    bucket = Bucket("pilot_images")
    files = bucket.list_files(path="pilot_images")

    public_urls = bucket.list_public_urls(path="pilot_images")
    print("================ Public URLs: ==================")
    rich_print("Number of public URLs: ", len(public_urls))
    rich_print(public_urls)
