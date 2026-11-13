"""Spider đọc bộ tin mẫu cục bộ (fixtures/sample_posts.json) để chạy thử toàn bộ luồng không cần Internet.

    scrapy crawl sample_feed
"""

import json
from pathlib import Path

import scrapy

from ..items import RawPostItem

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "sample_posts.json"


class SampleFeedSpider(scrapy.Spider):
    name = "sample_feed"

    async def start(self):
        # Không cần tải trang: đọc thẳng file mẫu và phát từng tin như khi thu thập thật.
        for post in json.loads(FIXTURES.read_text(encoding="utf-8")):
            yield RawPostItem(**post)
