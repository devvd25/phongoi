import scrapy


class RawPostItem(scrapy.Item):
    source_name = scrapy.Field()
    url = scrapy.Field()
    text = scrapy.Field()
    images = scrapy.Field()
    posted_at = scrapy.Field()
    poster_account_age_days = scrapy.Field()
