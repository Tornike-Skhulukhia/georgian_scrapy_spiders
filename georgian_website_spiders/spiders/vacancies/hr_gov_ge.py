import scrapy
from urllib.parse import urljoin
from datetime import datetime
from bs4 import BeautifulSoup as bs
import logging
import re


class HrGovGeSpider(scrapy.Spider):
    name = "hr_gov_ge"
    base_url = "https://www.hr.gov.ge/"
    source = "hr.gov.ge"

    def start_requests(self):
        # to get all data
        # post_data = {"archive": "true"}

        # to get currently visible(mostly active vacancies) data
        post_data = {}

        yield scrapy.FormRequest(
            self.base_url,
            callback=self.parse,
            formdata=post_data,
            meta={"dont_cache": True},
        )

    def parse(self, response):
        # next page
        next_href = response.css("li.PagedList-skipToNext a ::attr(href)").get()
        if next_href:
            # send post( OMG :-( )
            next_pg_num = int(next_href.split("=")[-1])

            logging.info(f"Getting page N{next_pg_num}")
            # use this to get all vacancies
            # post_data = {"pageNo": str(next_pg_num), "archive": "true"}

            # use this to get only currently visible listings(sometimes even not actives are visible)
            post_data = {"pageNo": str(next_pg_num)}

            yield scrapy.FormRequest(
                self.base_url,
                callback=self.parse,
                formdata=post_data,
                meta={"dont_cache": True},
            )

        # individual item
        for rel_url in response.css(
            'table#mytable td[style="text-align:left"] a ::attr(href)'
        ).getall():
            yield scrapy.Request(
                urljoin(self.base_url, rel_url), callback=self.parse_individual
            )

    def parse_individual(self, response):
        # vacancy_id = int(response.request.url.split("/")[-1])
        vacancy_id = int(re.search("Details\/(\d{1,7})", response.request.url).group(1))

        source = self.source

        _sel = 'dl[class="dl-horizontal"] d{}'

        soup = bs(response.text, "lxml")

        dts = [i.text.replace(":", "").strip() for i in soup.select(_sel.format("t"))]
        dds = [i.text.strip() for i in soup.select(_sel.format("d"))]

        assert len(dds) == len(dts)

        info = dict(zip(dts, dds))

        title = info.get("პოზიციის დასახელება")

        end_date = info.get("განცხადების ბოლო ვადა")
        if end_date:
            end_date = datetime.strptime(end_date, "%d.%m.%Y")

        desc_ = bs(response.text, "lxml").text
        description = desc_[: desc_.rfind("ონლაინ დახმარება")]

        locations = [info.get("სამსახურის ადგილმდებარეობა")]

        vip_status = False

        salary = info.get("თანამდებობრივი სარგო")
        if salary:
            match = re.search(r"(\d{3,5}).*დან (\d{3,5}).*მდე", salary)
            match_1 = re.search(r"(\d{3,5}).*დან", salary)
            match_2 = re.search(r"(\d{3,5}).*მდე", salary)

            if match:
                salary = {
                    "from": int(match.group(1)),
                    "to": int(match.group(2)),
                }

            elif salary == "ანაზღაურების გარეშე":
                salary = {"from": 0, "to": 0}

            elif salary == "შეთანხმებით":
                salary = None

            elif match_1:
                salary = {"from": int(match_1.group(1))}

            elif match_2:
                salary = {"to": int(match_2.group(1))}

            elif "ლარი" in salary:
                num = int(re.search(r"(\d{3,5})", salary).group(1))
                salary = {"from": num, "to": num}

            # not 100% sure if it is always GEL ...
            if salary is not None:
                salary["currency"] = "GEL"

        education = info.get("მინიმალური განათლება")

        experience = None
        _exp = info.get("სამუშაო გამოცდილება")
        if _exp:
            if _exp == "ერთ წლამდე":
                experience = {"from": 0, "to": 1}
            elif _exp == "გამოცდილების გარეშე":
                experience = {"from": 0, "to": 0}
            elif "-" in _exp and "წელი" in _exp:
                _exp = _exp.replace("წელი", "").split("-")
                experience = {"from": int(_exp[0]), "to": int(_exp[1])}
            else:
                exp_num = int(_exp.split(" ")[0])
                experience = {"from": exp_num}

        job_category = {"general": info.get("კატეგორია")}

        work_time_type = info.get("სამუშაოს ტიპი")

        company = {
            "name": info.get("ორგანიზაცია"),
        }

        language = "ge"

        language_is_supported = True

        yield dict(
            _id=response.request.url,
            vacancy_id=vacancy_id,
            source=source,
            title=title,
            end_date=end_date,
            description=description,
            locations=locations,
            vip_status=vip_status,
            salary=salary,
            education=education,
            experience=experience,
            job_category=job_category,
            work_time_type=work_time_type,
            company=company,
            language=language,
            language_is_supported=language_is_supported,
        )
