"""
Vacancies info from http://cv.ge

comment: ""
"""

import re
import scrapy
from urllib.parse import urljoin
from ._extractor_helpers import (
    extract_dates,
)


class CvGeSpider(scrapy.Spider):
    name = "cv_ge"
    allowed_domains = ["cv.ge"]
    url_base = "https://www.cv.ge"

    def start_requests(self):
        yield scrapy.Request(
            "https://www.cv.ge/announcements/all?page=1", meta={"dont_cache": True}
        )

    def parse(self, response):
        # next page
        next_page_url = response.css('a[aria-label="Next"] ::attr(href)').get()
        if next_page_url:
            yield scrapy.Request(
                urljoin(self.url_base, next_page_url), meta={"dont_cache": True}
            )

        # individual links
        for div in response.css("div.list-item"):
            rel_url = div.css("a.announcement-list-item ::attr(href)").get()

            vip_status = div.css("p.list-item-location ::text").get().strip()
            if vip_status == "რეგულარი":
                vip_status = None

            dates_resp = extract_dates(response.request.url, div.get())

            start_date, end_date = dates_resp.get("start_date"), dates_resp.get(
                "end_date"
            )

            url = urljoin(self.url_base, rel_url)
            yield scrapy.Request(
                url,
                callback=self.parse_individual,
                meta={
                    "vip_status": vip_status,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )

    def parse_individual(self, response):
        vacancy_id = int(re.search(r"/(\d{5,7})/", response.request.url).group(1))
        description = "".join(response.css(".content-wrap ::text").getall())

        locations = [
            i.strip()
            for i in response.css(".page-hero-details .item-badge ::text")
            .get()
            .split(",")
        ]

        posting_details = {}
        for div in response.css(".page-hero-details"):
            # skip first row
            if not div.css("strong").get():
                continue

            if len(div.css("strong").getall()) > 1:  # :-(
                # ex:  განათლება: ბაკალავრი ენები: ინგლისური, რუსული  - on same line
                for span in div.css("span"):
                    key_base = span.css("strong ::text").get()

                    if key_base and key_base.strip():
                        value = (
                            " ".join(span.css("::text").getall())
                            .replace(key_base, "")
                            .strip()
                        )
                        posting_details[key_base.replace(":", "").strip()] = value
            else:
                key_base = div.css("strong ::text").get()

                if key_base and key_base.strip():
                    value = (
                        " ".join(div.css("::text").getall())
                        .replace(key_base, "")
                        .strip()
                    )
                    posting_details[key_base.replace(":", "").strip()] = value

        salary = posting_details.get("ხელფასი")
        if salary:
            salary = salary.replace("ბონუსი", "")  # from hr.ge, maybe not needed here
            if "-" in salary:
                salary_nums = salary.replace("+", "").split("-")
            else:
                if "+" in salary:
                    salary_nums = [salary.replace("+", ""), None]
                else:
                    salary_nums = [salary, salary]

            salary = {
                "from": int(salary_nums[0]),
                "to": int(salary_nums[1]) if salary_nums[1] is not None else None,
            }

        education = posting_details.get("განათლება")
        if education:
            education = education.strip()

        languages = posting_details.get("ენები")
        if languages:
            languages = [i.strip() for i in languages.split(",")]

        driver_license = posting_details.get("მართვის მოწმობა")
        if driver_license and "," in driver_license:
            driver_license = [i.strip() for i in driver_license.split(",")]

        if posting_details:
            last_info_key = list(posting_details.keys())[-1]
            job_category = {
                "general": last_info_key.strip(),
                "specific": [
                    i.strip() for i in posting_details[last_info_key].split(",")
                ],
            }
        else:
            job_category = {"general": "", "specific": ""}

        work_time_type = response.css("span.entry-location ::text").get()
        if work_time_type:
            work_time_type = work_time_type.strip()

        experience = posting_details.get("გამოცდილება")
        if experience:
            experience = experience.strip()
            if experience == "გამოცდილების გარეშე":
                experience = {
                    "from": 0,
                    "to": 0,
                }
            elif experience == "ერთ წელზე ნაკლები":
                experience = {
                    "from": 0,
                    "to": 1,
                }
            elif "-" in experience:
                spl = experience.replace("წლამდე", "").split("-")
                experience = {
                    "from": int(spl[0]),
                    "to": int(spl[1]),
                }
            elif experience == "10 წელზე მეტი":
                experience = {
                    "from": 10,
                    "to": 100,
                }
            else:
                print("Experience not identified:", experience)
                experience = {}

        company_div = response.css('aside[class*="company-info-widget"]')
        company = {
            "logo_large": company_div.css(
                "figure.card-info-thumb img ::attr(src)"
            ).get(),
            "name": " ".join(response.css(".entry-company ::text").getall()).strip(),
            "website": company_div.css("p.card-info-link a ::attr(href)").get(),
            "profile_url": urljoin(
                self.url_base, response.css("span.entry-company a ::attr(href)").get()
            ),
        }

        item = dict(
            _id=response.request.url,
            vacancy_id=vacancy_id,
            description=description,
            start_date=response.meta["start_date"],
            end_date=response.meta["end_date"],
            vip_status=response.meta["vip_status"],
            title=response.css("h1.page-title::text")
            .get()
            .replace("\xa0", " ")
            .strip(),
            locations=locations,
            salary=salary,
            education=education,
            languages=languages,
            driver_license=driver_license,
            job_category=job_category,
            work_time_type=work_time_type,
            experience=experience,
            company=company,
            source="cv.ge",
            # get only georgian data, as most english pages also have georgian info
            language="ge",
            language_is_supported=True,
        )

        yield item
