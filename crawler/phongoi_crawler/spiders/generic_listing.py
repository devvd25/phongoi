"""Spider cấu hình được bằng CSS selector cho các trang tin đăng công khai CHO PHÉP thu thập tự động.

Ví dụ:
    scrapy crawl generic -a start_url=https://example.com/phong-tro \
        -a item_selector=".post-item" -a link_selector="a::attr(href)" \
        -a text_selector=".post-content ::text" -a image_selector="img::attr(src)" -a max_pages=3

Trước khi bật một nguồn, nhóm phải kiểm tra điều khoản sử dụng và robots.txt của trang đó.
Spider luôn tuân thủ robots.txt (ROBOTSTXT_OBEY=True), giãn cách 2 giây và không lưu thông tin cá nhân.
"""

import os

import scrapy

from ..items import RawPostItem

IGNORED_IMAGE_PATTERNS = (
    "base64",
    "spacer.gif",
    "blank.gif",
    "placeholder",
    "logo",
    "icon",
    "favicon",
    "avatar",
    "captcha",
    ".svg",
    "svg+xml",
    "%3csvg",
    "data:image",
    "facebook.com/tr",
    "ev=pageview",
    "noscript=1",
    "google-analytics",
    "googletagmanager",
    "doubleclick",
    "openmap.png",
    "default.jpg",
    "default.png",
    "no-image",
    "noimage",
)


def extract_clean_images(response, scope_selector: str = "") -> list[str]:
    """Trích xuất hình ảnh thực tế của tin đăng, ưu tiên thuộc tính lazy-load và lọc bỏ ảnh rác."""
    root = response.css(scope_selector) if scope_selector else response
    images: list[str] = []
    seen: set[str] = set()

    for img in root.css("img"):
        src = (
            img.attrib.get("data-src")
            or img.attrib.get("data-original")
            or img.attrib.get("data-lazy-src")
            or img.attrib.get("data-lazy")
        )
        if not src:
            srcset = img.attrib.get("srcset")
            if srcset:
                src = srcset.split(",")[0].strip().split()[0]
        if not src:
            src = img.attrib.get("src")

        if not src:
            continue

        src = src.strip()
        lower = src.lower()

        if any(ign in lower for ign in IGNORED_IMAGE_PATTERNS):
            continue

        if len(src) < 5 or src.startswith("#"):
            continue

        full_url = response.urljoin(src)
        if full_url not in seen:
            seen.add(full_url)
            images.append(full_url)
            if len(images) >= 8:
                break

    return images


class GenericListingSpider(scrapy.Spider):
    name = "generic"

    def __init__(self, start_url="", item_selector="", link_selector="a::attr(href)", text_selector="::text",
                 image_selector="img::attr(src)", next_selector="a[rel=next]::attr(href)", max_pages="3", use_playwright="0", **kw):
        super().__init__(**kw)
        if not start_url:
            raise ValueError("Cần truyền -a start_url=...")
        self.start_urls = [start_url]
        self.item_selector, self.link_selector, self.text_selector = item_selector, link_selector, text_selector
        self.image_selector, self.next_selector = image_selector, next_selector
        self.max_pages, self.pages = int(max_pages), 0
        self.use_playwright = use_playwright == "1"
        self.source_name = os.environ.get("SOURCE_NAME", "generic")

    def _req(self, url, cb):
        return scrapy.Request(url, callback=cb, meta={"playwright": True} if self.use_playwright else {})

    async def start(self):
        for u in self.start_urls:
            yield self._req(u, self.parse)

    def parse(self, response):
        self.pages += 1
        if not self.item_selector:
            self.logger.warning("Chưa cấu hình item_selector cho nguồn này, bỏ qua.")
            return
        for node in response.css(self.item_selector):
            link = node.css(self.link_selector).get()
            if link:
                yield self._req(response.urljoin(link), self.parse_post)
        nxt = response.css(self.next_selector).get()
        if nxt and self.pages < self.max_pages:
            yield self._req(response.urljoin(nxt), self.parse)

    def parse_post(self, response):
        h1 = response.css("h1::text").get()
        title = h1.strip() if h1 else ""

        # Lấy text loại bỏ script và style
        text_nodes = response.xpath("//text()[not(ancestor::script) and not(ancestor::style)]").getall()
        body_text = " ".join(t.strip() for t in text_nodes if t.strip())

        full_text = f"{title}. {body_text}" if title else body_text
        scope = self.image_selector if self.image_selector and "::attr" not in self.image_selector else ""
        images = extract_clean_images(response, scope)
        if not images:
            images = [
                response.urljoin(u)
                for u in response.css(self.image_selector).getall()
                if u and not any(ign in u.lower() for ign in IGNORED_IMAGE_PATTERNS)
            ][:8]
        yield RawPostItem(source_name=self.source_name, url=response.url, text=full_text[:5000], images=images)
