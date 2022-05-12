"""
Georgian synonims from http://www.nplg.gov.ge/gwdict/index.php?a=list&d=17&p=1

result structure:
    word: str,
    synonims: list,
    url: str,

comment: ""
"""
import scrapy


class NplGGovGeSpider(scrapy.Spider):
    name = "nplg_gov_ge_word_synonims"
    start_urls = ["http://www.nplg.gov.ge/gwdict/index.php?a=list&d=17&p=1"]

    def parse(self, response):
        # next pages
        next_page_url = response.xpath("//*[contains(text(), 'Next')]/@href").get()

        if next_page_url:
            yield scrapy.Request(response.urljoin(next_page_url))

        # individual
        for i in [
            response.urljoin(i)
            for i in response.css(".box .inlinetable dt a::attr(href)").getall()
        ]:
            yield scrapy.Request(i, callback=self.parse_individual)

    def parse_individual(self, response):
        word = response.css("h1.term ::text").get()

        try:
            synonims = [
                i.strip().rstrip("!?.,")
                for i in response.css(".gwsyn ::text").getall()[1:][0].split(",")
            ]
        except IndexError:
            synonims = []

        yield {
            "word": word,
            "synonims": synonims,
            "url": response.url,
        }
