import re
import warnings
from datetime import datetime
from time import sleep

import requests
from bs4 import BeautifulSoup, element
from django.utils import timezone
from requests.exceptions import SSLError, ConnectionError

from projectthade.settings import HCM_TZ
from thade.models import Record, Company


def make_soup(url: str) -> BeautifulSoup:
    """
    Fetch html source code from url and Parse to Beautiful soup

    :param url: must be from "www.cophieu68.vn/..."
    """
    match_his_price = re.match(r"^https://www.cophieu68.vn/historyprice.php\?currentPage=\d+&id=([a-z]|[A-Z]){3}$", url)
    match_profile_symbol = re.match(r"^https://www.cophieu68.vn/profilesymbol.php\?id=([a-z]|[A-Z]){3}$", url)
    if not match_his_price and not match_profile_symbol:
        raise Exception("Invalid url (Is the url from https://www.cophieu68.vn/historyprice.php?): " + url)

    response = requests.get(url, verify=False)
    response.encoding = 'utf-8'

    soup = BeautifulSoup(response.text, 'lxml')
    if soup.title is None:
        raise Exception("Given url doesn't fit scraping structure (Probably due to invalid company code): " + url)

    return soup


def request_records(company_instance: Company, last_update: datetime = None):
    """Scrape and add new records to SQL session"""
    page_number = 1
    rows_added = 0
    is_adding = True

    while is_adding:
        print('Current page number: ' + str(page_number))
        url = f"https://www.cophieu68.vn/historyprice.php?currentPage={page_number}&id={company_instance.code}"

        soup = make_soup(url)

        stock_history = soup.select_one("table[class='stock']")
        cursor = stock_history.tr

        is_adding = False
        while cursor is not None:
            # Condition to skip table Header and Label for additional info on ngày giao dịch không hưởng quyền
            if type(cursor) is not element.NavigableString and len(cursor.attrs) == 0:
                is_adding = parse_and_save_record(cursor.stripped_strings, company_instance, last_update)
                if is_adding:
                    rows_added += 1
                else:
                    break

            cursor = cursor.next_sibling

        page_number += 1
        sleep(1)

    print("{} record(s) added".format(rows_added))


def parse_and_save_record(stripped_strings, company_instance: Company, last_update: datetime = None) -> bool:
    """Parse stripped string to initialize Record instance and add new instance to SQLSession"""
    raw_data = list(stripped_strings)

    # VN Market opens at 09:00:00+07:00
    naive_trading_date = timezone.datetime.strptime(raw_data[1], "%d-%m-%Y") + timezone.timedelta(hours=9)
    local_trading_date = HCM_TZ.localize(naive_trading_date, is_dst=None)
    utc_trading_date = local_trading_date.astimezone(timezone.get_current_timezone())

    # Exit if the fetched record is already the latest
    if last_update is not None and utc_trading_date <= last_update:
        return False

    rid = "{}{:%Y%m%d}".format(company_instance.code, utc_trading_date)  # ID format: CODE+YYYY+MM+DD
    reference_price_vnd = int(float(raw_data[2]) * 1000)
    close_vnd = int(float(raw_data[5]) * 1000)
    volume = int(raw_data[6].replace(',', ''))
    open_vnd = int(float(raw_data[7]) * 1000)
    highest_vnd = int(float(raw_data[8]) * 1000)
    lowest_vnd = int(float(raw_data[9]) * 1000)

    record = Record(company=company_instance, rid=rid, utc_trading_date=utc_trading_date,
                    reference_price_vnd=reference_price_vnd, close_vnd=close_vnd, volume=volume, open_vnd=open_vnd,
                    highest_vnd=highest_vnd, lowest_vnd=lowest_vnd)

    record.save()
    return True


def request_company_desc(company_instance: Company):
    """Scrape and add new company's details to SQL session"""
    profile_url = "https://www.cophieu68.vn/profilesymbol.php?id=" + company_instance.code

    soup = make_soup(profile_url)

    # Get Company name
    name = re.sub(r'( - [\w\d]*)$', '', soup.h1.string)

    # Get Company website
    left_snapshot = soup.select_one('div[class="snapshotLeft2"]')
    href = left_snapshot.find('a')['href']
    website = re.sub(r'^(http(s?)[:/]*){1,2}[w.]{0,4}|[/]$', '', href)

    # Get Company current stock Exchange
    stock_exchange = list(left_snapshot.select_one('table').stripped_strings)[2]

    # Create and log
    company_instance.name = name
    company_instance.website = website
    company_instance.stock_exchange = stock_exchange
    company_instance.last_records_fetched = timezone.now()
    company_instance.save()
    print("{} company added".format(company_instance.code))


def fetch_company(company_code: str) -> Company:
    """Get Company object if it exists else create and fetch data for it."""
    company_instance, is_created = Company.objects.get_or_create(code=company_code)
    if is_created:
        request_company_desc(company_instance)
    else:
        print("Found company: {}".format(company_code))
    return company_instance


def fetch_records(company_instance: Company):
    """
    Fetch all records of a company from the last update to now.

    :param company_instance: The company to fetch records for.
    """
    latest_record = Record.objects.filter(company__code__exact=company_instance.code).order_by(
        '-utc_trading_date').first()
    if latest_record is None:
        last_update = None
    else:
        last_update = latest_record.utc_trading_date
        if timezone.is_naive(last_update):
            # Validate last update
            raise Exception("The latest record is not timezone aware: {}", latest_record)

    request_records(company_instance, last_update)
    company_instance.last_records_fetched = timezone.now()
    company_instance.save()


def clear_records(company_instance: Company):
    company_instance.record_set.all().delete()


def update_records(company_code: str, clear=False):
    """
    Main method to fetch and update database

    :param company_code: The company's code to update records for.
    :param clear: Delete all previously fetched records from the company.
    """
    company_code = company_code.upper()

    company_instance = fetch_company(company_code)

    fetch_records(company_instance)
