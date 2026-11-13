"""Cấu hình Scrapy: thu thập có trách nhiệm (tuân thủ robots.txt, giãn cách, tự điều tốc)."""

BOT_NAME = "phongoi_crawler"
SPIDER_MODULES = ["phongoi_crawler.spiders"]
NEWSPIDER_MODULE = "phongoi_crawler.spiders"

USER_AGENT = "PhongOiResearchBot/1.0 (+de tai NCKH sinh vien; lien he qua email nhom nghien cuu)"
ROBOTSTXT_OBEY = True
DOWNLOAD_DELAY = 2
CONCURRENT_REQUESTS_PER_DOMAIN = 1
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 2
AUTOTHROTTLE_MAX_DELAY = 20
HTTPCACHE_ENABLED = False
FEED_EXPORT_ENCODING = "utf-8"

# Validate every scheduled request, including links and redirect targets, to
# prevent DNS rebinding/redirects from turning the crawler into an SSRF proxy.
DOWNLOADER_MIDDLEWARES = {
    "phongoi_crawler.network_safety.PublicNetworkOnlyMiddleware": 50,
}


ITEM_PIPELINES = {"phongoi_crawler.pipelines.PostToBackendPipeline": 300}

# Bật Playwright cho trang động khi đã cài scrapy-playwright:
#   pip install scrapy-playwright && playwright install chromium
try:
    import scrapy_playwright  # noqa: F401

    DOWNLOAD_HANDLERS = {
        "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
        "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    }
    TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
except ImportError:
    pass
