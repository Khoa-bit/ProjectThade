import warnings
from datetime import datetime, timedelta

import yaml
from django.test import TestCase

from bs4 import BeautifulSoup
from time import sleep

from django.utils import timezone

from projectthade.settings import BASE_DIR
from thade.backtesting.scrape_stock import (
    make_soup,
    fetch_company,
    fetch_records,
    clear_records,
    request_company_desc,
    request_records,
    parse_and_save_record,
)
from thade.models import Company, Record
from thade.tests.models_factory import CompanyFactory, RecordFactory, seed

# Global constant variables
TEST = yaml.safe_load(open(BASE_DIR / "config.yaml"))["TEST"]
NAIVE_DATETIME = TEST["NAIVE_DATETIME_ISO"]
AWARE_DATETIME = TEST["AWARE_DATETIME_ISO"]


# Create your tests here.
class ScrapeStockTests(TestCase):
    def test_make_soup_with_valid_url(self):
        """
        make_soup() returns a BeautifulSoup object for valid urls.
        """
        company_codes = ["agg", "chp", "pnj"]
        for company_code in company_codes:
            url = f"https://www.cophieu68.vn/historyprice.php?currentPage=0&id={company_code}"
            self.assertIsInstance(
                make_soup(url), BeautifulSoup, "Return BeautifulSoup Object"
            )
            print(f"Passed: Code {company_code.upper()}")
            sleep(1)

        for i in [40, 120]:
            url = f"https://www.cophieu68.vn/historyprice.php?currentPage={i}&id=EVE"
            self.assertIsInstance(
                make_soup(url), BeautifulSoup, "Return BeautifulSoup Object"
            )
            print(f"Passed: Page {i}")
            sleep(1)

    def test_make_soup_with_invalid_url(self):
        """
        make_soup() returns suitable exceptions for wrong urls or invalid urls, which doesn't fit scraping structure.
        """
        wrong_urls = [
            "https://duckduckgo.com/",
            "https://www.python.org/",
            "https://www.stockbiz.vn/Stocks/tra/HistoricalQuotes.aspx",
            "https://finance.tvsi.com.vn/data/IndicesStats",
            "https://www.bvsc.com.vn/HistoricalQuotesCompany.aspx",
            "https://www.ssi.com.vn/quan-he-nha-dau-tu/lich-su-gia",
            "https://www.cophieu68.vn/index.php",
            "https://www.cophieu68.vn/snapshot.php?id=HPG",
            "https://www.cophieu68.vn/historyprice.php?id=VHM",
            "https://www.cophieu68.vn/historyprice.php?currentPage=zero&id=vhm",
            "https://www.cophieu68.vn/historyprice.php?currentPage=2&id=243",
            "https://www.cophieu68.vn/historyprice.php?id=VHM&currentPage=2",
            "https://www.cophieu68.vn/historyprice.php?currentPage=-2&id=AAA",
            "https://www.cophieu68.vn/historyprice.php?currentPage=-20&id=AAA",
            "https://www.cophieu68.vn/historyprice.php?currentPage=-90&id=AAA",
            "https://www.cophieu68.vn/profilesymbol.php?id=35",
        ]
        for wrong_url in wrong_urls:
            with self.assertRaisesMessage(
                Exception,
                "Invalid url (Is the url from https://www.cophieu68.vn/historyprice.php?): "
                + wrong_url,
                msg="Raise Exception for invalid urls",
            ):
                make_soup(wrong_url)
            print(f"Passed: {wrong_url}")

        invalid_structures = [
            "https://www.cophieu68.vn/historyprice.php?currentPage=2&id=JJJ",
            "https://www.cophieu68.vn/historyprice.php?currentPage=2&id=XYZ",
            "https://www.cophieu68.vn/profilesymbol.php?id=ZZZ",
            "https://www.cophieu68.vn/profilesymbol.php?id=YYY",
        ]
        for url in invalid_structures:
            with self.assertRaisesMessage(
                Exception,
                "Given url doesn't fit scraping structure (Probably due to invalid company code): "
                + url,
                msg="Raise Exception for invalid structure urls",
            ):
                make_soup(url)
            print(f"Passed: {url}")
            sleep(1)

    def test_fetch_company_with_a_company_code_that_already_exists_in_db(self):
        """fetch_company() shouldn't fetch new Company if it already exists in database"""
        company_in_db = CompanyFactory(code="OLD")

        number_of_companies_before_fetching = Company.objects.count()
        fetched_company = fetch_company("OLD")
        number_of_companies_after_fetching = Company.objects.count()

        self.assertIsInstance(fetched_company, Company, "Return Company object")
        self.assertEqual(
            fetched_company.code, company_in_db.code, "Is the same company"
        )
        self.assertEqual(
            number_of_companies_before_fetching,
            number_of_companies_after_fetching,
            "No changes to database",
        )

    def test_fetch_company_with_a_new_valid_company_code(self):
        """fetch_company() should fetch new Company if it doesn't already exist in database"""
        number_of_companies_before_fetching = Company.objects.count()
        fetched_company = fetch_company("AAA")
        number_of_companies_after_fetching = Company.objects.count()

        self.assertIsInstance(fetched_company, Company, "Return Company object")
        self.assertEqual(
            number_of_companies_before_fetching + 1,
            number_of_companies_after_fetching,
            "1 more Company added to database",
        )

    def test_fetch_record_without_any_records(self):
        """
        IDK how to properly test this because I admitted trust the website 100% and fetch data change day by day
        If this test fail, It's because the test is ran on holidays when the market is closed so there is no new record.
        Need Improvement :3
        """
        company = CompanyFactory(code="AAA")
        fetch_records(company)
        self.assertNotEqual(
            Record.objects.filter(company__code__exact="AAA").count(),
            0,
            "New records have been fetched",
        )

    def test_fetch_record_with_existing_records(self):
        """
        IDK how to properly test this because I admitted trust the website 100% and fetch data change day by day
        If this test fail, It's because the test is ran on holidays when the market is closed so there is no new record.
        Need Improvement :3
        """
        company = CompanyFactory(code="AAA")
        seed(company=company, days_from_now=10)
        fetch_records(company)
        self.assertNotEqual(
            Record.objects.filter(company__code__exact="AAA").count(),
            0,
            "New records have been fetched",
        )

    def test_fetch_record_with_existing_records_in_invalid_data_structure(self):
        """
        This test is not necessary and not working because Django prevents inserting naive datetime objects.
        IDK how to properly test this because I admitted trust the website 100% and fetch data change day by day
        If this test fail, It's because the test is ran on holidays when the market is closed so there is no new record.
        Need Improvement :3
        """
        company = CompanyFactory(code="AAA")

        with warnings.catch_warnings(record=True) as w:
            last_record = RecordFactory(
                company=company, utc_trading_date=NAIVE_DATETIME
            )
            self.assertEqual(w[-1].category, RuntimeWarning)
            self.assertEqual(
                str(w[-1].message),
                "DateTimeField Record.utc_trading_date received a naive datetime ({})"
                " while time zone support is active.".format(NAIVE_DATETIME),
            )

        # This exception will not raise the Exception
        # because Django prevents inserting naive datetime objects through ORM.

        # with self.assertRaisesMessage(Exception, "The latest record is not timezone aware: {}".format(last_record)):
        #     fetch_records(company)

    def test_clear_records(self):
        """clear_records() should delete all records from a Company object."""
        clear_company = seed(50)
        dummy_company = seed(10)

        self.assertEqual(
            Company.objects.first().code,
            clear_company.code,
            "The clear company exists in database",
        )
        self.assertEqual(
            clear_company.record_set.count(),
            50,
            "Exactly 50 new records are created and related to the company",
        )
        self.assertEqual(
            Record.objects.count(), 60, "Exactly 60 new records exist in db"
        )
        clear_records(clear_company)
        self.assertEqual(
            Company.objects.first().code,
            clear_company.code,
            "The clear company still exists in database",
        )
        self.assertEqual(
            clear_company.record_set.count(),
            0,
            "No records left are related to the company",
        )
        self.assertEqual(
            Record.objects.count(), 10, "Exactly 10 new records exist in db"
        )

    def test_request_company_desc(self):
        """request_company_desc() should fetch data for companies and save them to database"""
        company_AAA = Company(code="AAA")
        request_company_desc(company_AAA)

        self.assertEqual(company_AAA.code, "AAA")
        self.assertEqual(company_AAA.name, "CTCP Nhựa An Phát Xanh")
        self.assertEqual(company_AAA.website, "anphatbioplastics.com")
        self.assertEqual(company_AAA.stock_exchange, "HOSE")

        company_HPG = Company(code="HPG")
        request_company_desc(company_HPG)

        self.assertEqual(company_HPG.code, "HPG")
        self.assertEqual(company_HPG.name, "CTCP Tập đoàn Hòa Phát")
        self.assertEqual(company_HPG.website, "hoaphat.com.vn")
        self.assertEqual(company_HPG.stock_exchange, "HOSE")

        self.assertQuerysetEqual(
            list(Company.objects.all()),
            [company_AAA, company_HPG],
            msg="2 companies exist in db",
        )

    def test_request_records_without_last_update(self):
        """
        IDK how to properly test this because I admitted trust the website 100% and fetch data change day by day
        If this test fail, It's because the test is ran on holidays when the market is closed so there is no new record.
        Need Improvement :3
        """
        company = CompanyFactory(code="AAA")
        last_update = None
        request_records(company, last_update)
        self.assertNotEqual(
            Record.objects.filter(company__code__exact="AAA").count(),
            0,
            "New records have been fetched",
        )
        self.assertNotEqual(
            company.record_set.count(),
            0,
            "New records are added and related to the company",
        )

    def test_request_records_with_last_update(self):
        """
        IDK how to properly test this because I admitted trust the website 100% and fetch data change day by day
        If this test fail, It's because the test is ran on holidays when the market is closed so there is no new record.
        Need Improvement :3
        """
        company = CompanyFactory(code="AAA")
        request_records(company, AWARE_DATETIME)
        self.assertNotEqual(
            Record.objects.filter(company__code__exact="AAA").count(),
            0,
            "New records have been fetched",
        )
        self.assertNotEqual(
            company.record_set.count(),
            0,
            "New records are added and related to the company",
        )

    def test_parse_and_save_record_without_last_update(self):
        """
        IDK how to properly test this because I admitted trust the website 100% and fetch data change day by day
        If this test fail, It's because the test is ran on holidays when the market is closed so there is no new record.
        Need Improvement :3
        """
        company = CompanyFactory(code="AAA")
        list_stripped_string = [
            "#1",
            "16-07-2021",
            "15.95",
            "-0.20",
            "-1.25%",
            "15.75",
            "3,757,400",
            "16.05",
            "16.05",
            "15.70",
            "0",
            "14,900",
            "329,800",
        ]
        last_update = None
        parse_and_save_record(list_stripped_string, company, last_update)

        self.assertEqual(
            Record.objects.filter(company__code__exact="AAA").count(),
            1,
            "A New record has been fetched",
        )
        self.assertEqual(
            company.record_set.count(),
            1,
            "A new record is added and related to the company",
        )

    def test_parse_and_save_record_with_last_update(self):
        """
        IDK how to properly test this because I admitted trust the website 100% and fetch data change day by day
        If this test fail, It's because the test is ran on holidays when the market is closed so there is no new record.
        Need Improvement :3
        """
        company = CompanyFactory(code="AAA")
        list_stripped_string = [
            "#1",
            "16-07-2021",
            "15.95",
            "-0.20",
            "-1.25%",
            "15.75",
            "3,757,400",
            "16.05",
            "16.05",
            "15.70",
            "0",
            "14,900",
            "329,800",
        ]
        parse_and_save_record(list_stripped_string, company, AWARE_DATETIME)

        self.assertEqual(
            Record.objects.filter(company__code__exact="AAA").count(),
            1,
            "A New record has been fetched",
        )
        self.assertEqual(
            company.record_set.count(),
            1,
            "A new record is added and related to the company",
        )
