"""
Georgian literature texts from http://nplg.gov.ge/greenstone3/library/collection/vertwo/browse/CL3/

result structure:
    url: str,
    century_text: str,
    fulltext: str,

comment: ""
"""
import scrapy


class NplgGovGeGeorgianLiteratureSpider(scrapy.Spider):
    name = "nplg_gov_ge_georgian_literature"
    start_urls = [
        "http://nplg.gov.ge/greenstone3/library/collection/vertwo/browse/CL3/"
    ]

    def parse(self, response):
        centuries_lists_number = len(
            response.css('table#classifiernodelist table[id^="title"]')
        )

        for i in range(1, centuries_lists_number + 1):
            century_books_url = f"{self.start_urls[0]}{i}"

            yield scrapy.Request(
                century_books_url, callback=self.parse_century_books_list
            )

    def parse_century_books_list(self, response):
        meta_info = {
            "century_text": response.css('a[href^="javascript:toggleSection"] ::text')
            .get()
            .strip(),
        }

        for url in {
            response.urljoin(i)
            for i in response.css(
                '.childrenlist tr td a[href^="library/collection/vertwo/document/"] ::attr(href)'
            ).getall()
        }:
            yield scrapy.Request(
                url, callback=self.parse_individual_book_page, meta=meta_info
            )

    def parse_individual_book_page(self, response):
        data = {
            "url": response.request.url,
            "century_text": response.meta["century_text"],
        }

        data["fulltext"] = " ".join(
            " ".join(
                response.css("div#gs-document div#gs-document-text ::text").getall()
            ).split()
        )

        yield data
