"""
Vacancies info from http://hr.ge

comment: ""
"""


import dateparser
import requests
import scrapy

# it is better to have it from api, but for now this is good enough solution

VACANCIES_PER_PAGE = 100  # in api searches


def get_vacancy_result_pages_number():

    resp = requests.post("https://api.hr.ge/api/v3/announcement-search/", json={})

    vacancies_num = resp.json()["data"]["announcements"]["totalCount"]
    pages_num = (vacancies_num // VACANCIES_PER_PAGE) + 1

    return pages_num


class HrGeSpider(scrapy.Spider):
    name = "hr_ge"
    allowed_domains = ["hr.ge"]
    url_base = "https://www.hr.ge"

    def start_requests(self):

        pages_num = get_vacancy_result_pages_number()

        for i in range(1, pages_num + 1):  # [::-1] if wanted to check for cv.ge skips
            start = 100 * (i - 1)

            yield scrapy.http.JsonRequest(
                "https://api.hr.ge/api/v3/announcement-search/",
                data={"Start": start, "Limit": VACANCIES_PER_PAGE},
                meta={"dont_cache": True},
            )

    def parse(self, response):

        # _printed = False
        resp_json = response.json()

        # for vacancy_id in vacancy_ids:
        for i in resp_json["data"]["announcements"]["items"]:
            # skip not on hr.ge cases
            if i.get("detailsProviderWebsite"):
                continue

            vacancy_id = i["announcementId"]

            start_date = dateparser.parse(i["publishDate"])
            end_date = dateparser.parse(i["deadlineDate"])
            company_profile_url = f'https://www.hr.ge/customer/{i["customerId"]}/'
            company_logo_url = (
                f'https://www.hr.ge/customer/{i["logoFilename"]}/'
                if i["logoFilename"]
                else None
            )

            # print("vacancy_id", vacancy_id)
            yield scrapy.Request(
                f"https://www.hr.ge/announcement/{vacancy_id}/",
                meta={
                    "vacancy_id": vacancy_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "company_profile_url": company_profile_url,
                    "company_logo_url": company_logo_url,
                },
                callback=self.parse_individual,
            )

    def parse_individual(self, response):

        vacancy_id = response.meta["vacancy_id"]
        description = " ".join(response.css(".ann-details-description ::text").getall())

        info_panel = response.css(".info-panel")

        title = info_panel.css(".ann-title::text").get()

        locations = info_panel.css(".location__text::text").get().replace("სხვა", " ")

        job_category = {
            "general": response.css(".categories__head-categories::text").get(),
            "specific": response.css(".categories__subcategory::text").get(),
        }

        company = {
            "name": response.css(".company-name::text").get().strip(),
            "profile_url": response.meta["company_profile_url"],
            "logo": response.meta["company_logo_url"],
        }

        item = dict(
            _id=response.request.url,
            description=description,
            vacancy_id=vacancy_id,
            title=title,
            start_date=response.meta["start_date"],
            end_date=response.meta["end_date"],
            locations=locations,
            job_category=job_category,
            company=company,
            source="hr.ge",
            # get only georgian data, as most english pages also have georgian info
            language="ge",
            language_is_supported=True,
        )

        yield item
