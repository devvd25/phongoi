"""Gửi từng tin thô về backend (/api/admin/ingest); backend lo trích xuất, gộp trùng, chấm rủi ro."""

import os

import httpx


class PostToBackendPipeline:
    def __init__(self, crawler):
        self.crawler = crawler
        self.url = os.environ.get("BACKEND_URL", "http://localhost:8000") + "/api/admin/ingest"
        self.token = os.environ.get("INGEST_TOKEN", "dev-ingest-token")
        self.run_id = os.environ.get("RUN_ID")
        self.client = httpx.Client(timeout=30)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def close_spider(self):
        self.client.close()

    def process_item(self, item):
        spider = self.crawler.spider
        params = {"run_id": self.run_id} if self.run_id else None
        payload = {k: v for k, v in dict(item).items() if v is not None}
        payload.setdefault("source_name", os.environ.get("SOURCE_NAME", spider.name))
        r = self.client.post(self.url, json=payload, params=params, headers={"X-Ingest-Token": self.token})
        spider.logger.info("ingest %s -> %s", payload.get("url"), r.json() if r.status_code == 200 else r.status_code)
        return item
