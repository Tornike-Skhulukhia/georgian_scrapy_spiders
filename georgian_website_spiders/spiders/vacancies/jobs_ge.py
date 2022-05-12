# -*- coding: utf-8 -*-
"""
    supply arguments language en/ge for 2 language crawl,
    like this:
        scrapy crawl jobs_ge -a language=ge
        scrapy crawl jobs_ge -a language=en
"""

import re
import scrapy
from urllib.parse import urljoin
from ._extractor_helpers import (
    extract_dates,
)


def _get_individual_data_from_tr(self, tr, base_url):
    _, title_td, logo_td, company_td, start_td, end_td = tr.css("td")

    # use as URL
    _id = urljoin(base_url, title_td.css("a.vip ::attr(href)").get())
    vacancy_id = int(re.search(r"&id=(\d{1,7})", _id).group(1))
    language = self.language

    title = title_td.css("a.vip ::text").get().strip()
    location = title_td.css("i ::text").get()

    company_name = "".join(company_td.css("::text").getall())
    company_profile_url = urljoin(base_url, company_td.css("a ::attr(href)").get())

    company_website = logo_td.css("a ::attr(href)").get()
    if company_website and (
        company_website.startswith("/ge/?") or company_website.startswith("/en/?")
    ):
        company_website = None

    company_logo_small = logo_td.css("img ::attr(src)").get()
    if company_logo_small:
        company_logo_small = urljoin(base_url, company_logo_small)
    # no custom logo case
    if company_logo_small == "https://jobs.ge/i/pix.gif":
        company_logo_small = None

    company_logo_large = (
        company_logo_small.replace("/logo_icon/", "/logo/")
        if company_logo_small
        else None
    )

    return {
        "_id": _id,
        "language": language,
        "title": title,
        "locations": location if not location else [location.replace("-", "").strip()],
        "company": {
            "name": company_name.strip() if company_name else company_name,
            "profile_url": company_profile_url,
            "website": company_website,
            "logo_small": company_logo_small,
            "logo_large": company_logo_large,
        },
        "vacancy_id": vacancy_id,
    }


class JobsGeSpider(scrapy.Spider):
    name = "jobs_ge"
    base_url = "https://jobs.ge"

    def start_requests(self):
        # get from command line
        assert self.language in ["en", "ge"]

        self.ajax_url_base = (
            f"https://jobs.ge/{self.language}/?page={{}}&for_scroll=yes"
        )
        self.seen_urls = set()
        self.start_urls = [f"https://jobs.ge/{self.language}"]

        # GO
        yield scrapy.Request(self.start_urls[0], meta={"dont_cache": True})

    def parse(self, response):
        # get vip urls from first page
        if response.request.url == self.start_urls[0]:
            elems = response.css("div.vipEntries tr")

            for tr_elem in elems[1:]:  # skip titles - first row
                individual_data = _get_individual_data_from_tr(
                    self, tr_elem, self.base_url
                )

                url = individual_data["_id"]
                self.seen_urls.add(url)

                yield scrapy.Request(
                    url,
                    callback=self.parse_individual,
                    meta={"data": {"vip_status": "vip", **individual_data}},
                )

            yield scrapy.Request(
                self.ajax_url_base.format(1), meta={"page": 1, "dont_cache": True}
            )
        else:
            # save data from pages
            curr_page = response.meta["page"]

            # if curr_page == 3: breakpoint()

            elems = response.css("#temp_table tr")
            try:
                last_url = urljoin(self.base_url, elems[-1].css("a.vip ::attr(href)").get())
            except IndexError:
                return

            # get next page if any more new urls left
            if last_url not in self.seen_urls:
                yield scrapy.Request(
                    self.ajax_url_base.format(curr_page + 1),
                    meta={"page": curr_page + 1, "dont_cache": True},
                )

                for tr_elem in elems:
                    individual_data = _get_individual_data_from_tr(
                        self, tr_elem, self.base_url
                    )

                    url = individual_data["_id"]
                    self.seen_urls.add(url)

                    yield scrapy.Request(
                        url,
                        callback=self.parse_individual,
                        meta={"data": {**individual_data, "vip_status": None}},
                    )

    def parse_individual(self, response):
        description = "".join(
            [j for i in response.css("table tr")[1:] for j in i.css("::text").getall()]
        )
        language_is_supported = (
            "იხილეთ ამ განცხადების სრული ტექსტი ინგლისურ ენაზე" not in description
            and "See full text of this announcement in Georgian" not in description
        )

        dates_resp = extract_dates(response.request.url, response.text)
        start_date, end_date = dates_resp.get("start_date"), dates_resp.get("end_date")

        yield dict(
            description=description,
            language_is_supported=language_is_supported,
            source="jobs.ge",
            start_date=start_date,
            end_date=end_date,
            **response.meta["data"],
        )
