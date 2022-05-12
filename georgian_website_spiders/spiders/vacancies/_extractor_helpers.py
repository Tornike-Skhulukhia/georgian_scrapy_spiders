import re
from datetime import datetime

import dateparser
from bs4 import BeautifulSoup as bs
from dateutil.relativedelta import relativedelta


def extract_dates(url, html_text):
    """
    extract dates from given html text and its url.
    Decide which site to use based on url.
    currently supported:
        . jobs.ge - using full description
        . cv.ge - using specific div's html containing dates info
    returns dict of {
        start_date: datetime_or_none,
        end_date: datetime_or_none,
    }
    """
    start_date, end_date = None, None

    if ".cv.ge/" in url:
        source = "cv.ge"
    else:
        source = "jobs.ge"

    soup = bs(html_text, "lxml")

    if source == "jobs.ge":
        upper_info = [i.text.lower().strip() for i in soup.select("td.dtitle")]

        lang = ["ge", "en"]["/en/" in url]

        for text_info in upper_info:
            if lang == "en":
                if "published" not in text_info or "deadline" not in text_info:
                    continue
            else:
                if "გამოქვეყნდა" not in text_info or "ბოლო ვადა" not in text_info:
                    continue

            m1 = re.search(r"(published|გამოქვეყნდა):\s+(\d{1,2}\s+\b\w+\b)", text_info)
            m2 = re.search(
                r"(deadline|ბოლო ვადა):\s+(\d{1,2}\s+\b\w+\b)",
                text_info,
            )

            start_date = dateparser.parse(m1.group(2))
            end_date = dateparser.parse(m2.group(2))

    elif source == "cv.ge":
        dates_spl = [
            i.strip() for i in soup.select(".list-item-time")[0].text.split(" - ")
        ]
        # make month max 3 letters
        for index, i in enumerate(dates_spl):
            if len(dates_spl[index].split()[-1]) > 3:
                dates_spl[
                    index
                ] = f"{dates_spl[index].split()[0]} {dates_spl[index].split()[-1][:3]}"

        start_date, end_date = [dateparser.parse(i) for i in dates_spl]

    if start_date is not None and end_date is not None:
        # year refine | remove 1 year
        if start_date > datetime.today():
            start_date -= relativedelta(years=1)
            end_date -= relativedelta(years=1)

        while end_date <= start_date:
            end_date += relativedelta(years=1)

        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)

    return {"start_date": start_date, "end_date": end_date}
