from django.test import TestCase
from django.utils import timezone

from thade.tests.models_factory import CompanyFactory, RecordFactory, seed
from thade.models import Company, Record


class ModelsFactoryTest(TestCase):
    def test_default_seed(self):
        """Default seed() should return Records with predictable rid"""
        company = seed()

        seeded_records = company.record_set.order_by("-utc_trading_date")
        tz_now = timezone.now().date()
        tz_4_days_ago = tz_now - timezone.timedelta(days=4)
        self.assertEqual(
            seeded_records.first().rid,
            "{}{:04}{:02}{:02}".format(
                company.code, tz_now.year, tz_now.month, tz_now.day
            ),
            "First record should be timezone.now()",
        )

        self.assertEqual(
            seeded_records.last().rid,
            "{}{:04}{:02}{:02}".format(
                company.code, tz_4_days_ago.year, tz_4_days_ago.month, tz_4_days_ago.day
            ),
            "Last record should be 4 days apart.",
        )
        self.assertIsInstance(company, Company, "Return Company object")
        self.assertEqual(
            company.record_set.count(),
            5,
            "Exactly 5 new records are created and related to the company",
        )
        self.assertEqual(Record.objects.count(), 5, "Exactly 5 new records exist in db")

    def test_seed_with_input_records(self):
        """seed() should return correct number of Records with predictable rid"""
        company = seed(records=50)

        seeded_records = company.record_set.order_by("-utc_trading_date")
        tz_now = timezone.now().date()
        tz_49_days_ago = tz_now - timezone.timedelta(days=49)
        self.assertEqual(
            seeded_records.first().rid,
            "{}{:04}{:02}{:02}".format(
                company.code, tz_now.year, tz_now.month, tz_now.day
            ),
            "First record should be timezone.now()",
        )

        self.assertEqual(
            seeded_records.last().rid,
            "{}{:04}{:02}{:02}".format(
                company.code,
                tz_49_days_ago.year,
                tz_49_days_ago.month,
                tz_49_days_ago.day,
            ),
            "Last record should be 49 days apart.",
        )
        self.assertIsInstance(company, Company, "Return Company object")
        self.assertEqual(
            company.record_set.count(),
            50,
            "Exactly 50 new records are created and related to the company",
        )
        self.assertEqual(
            Record.objects.count(), 50, "Exactly 50 new records exist in db"
        )

    def test_seed_with_input_days_from_now(self):
        """seed() should return Records with predictable rid and utc_trading_date"""
        company = seed(days_from_now=10)

        seeded_records = company.record_set.order_by("-utc_trading_date")
        tz_10_days_ago = timezone.now().date() - timezone.timedelta(days=10)
        tz_14_days_ago = tz_10_days_ago - timezone.timedelta(days=4)
        self.assertEqual(
            seeded_records.first().rid,
            "{}{:04}{:02}{:02}".format(
                company.code,
                tz_10_days_ago.year,
                tz_10_days_ago.month,
                tz_10_days_ago.day,
            ),
            "First record should be 10 days after timezone.now()",
        )

        self.assertEqual(
            seeded_records.last().rid,
            "{}{:04}{:02}{:02}".format(
                company.code,
                tz_14_days_ago.year,
                tz_14_days_ago.month,
                tz_14_days_ago.day,
            ),
            "Last record should be 4 days apart which is 14 days after timezone.now().",
        )
        self.assertIsInstance(company, Company, "Return Company object")
        self.assertEqual(
            company.record_set.count(),
            5,
            "Exactly 5 new records are created and related to the company",
        )
        self.assertEqual(Record.objects.count(), 5, "Exactly 5 new records exist in db")

    def test_seed_with_input_records_and_days_from_now(self):
        """seed() should return correct number of Records with predictable rid and utc_trading_date"""
        company = seed(records=50, days_from_now=10)

        seeded_records = company.record_set.order_by("-utc_trading_date")
        tz_10_days_ago = timezone.now().date() - timezone.timedelta(days=10)
        tz_59_days_ago = tz_10_days_ago - timezone.timedelta(days=49)
        self.assertEqual(
            seeded_records.first().rid,
            "{}{:04}{:02}{:02}".format(
                company.code,
                tz_10_days_ago.year,
                tz_10_days_ago.month,
                tz_10_days_ago.day,
            ),
            "First record should be 10 days after timezone.now()",
        )

        self.assertEqual(
            seeded_records.last().rid,
            "{}{:04}{:02}{:02}".format(
                company.code,
                tz_59_days_ago.year,
                tz_59_days_ago.month,
                tz_59_days_ago.day,
            ),
            "Last record should be 49 days apart which is 59 days after timezone.now().",
        )
        self.assertIsInstance(company, Company, "Return Company object")
        self.assertEqual(
            company.record_set.count(),
            50,
            "Exactly 50 new records are created and related to the company",
        )
        self.assertEqual(
            Record.objects.count(), 50, "Exactly 50 new records exist in db"
        )

    def test_seed_with_input_company(self):
        """seed() should be able to generate records for inputted Company objects"""
        seed_company = Company(
            code="AKZ",
            name="Alpha Kepler Zaid",
            website="alphakelperzaid.com",
            stock_exchange="HOSE",
        )
        seed_company.save()
        company1 = seed(company=seed_company)

        self.assertIsInstance(company1, Company, "Return Company object")
        self.assertIs(seed_company, company1, "Is the same Company object")
        self.assertEqual(
            company1.record_set.count(),
            5,
            "Exactly 5 new records are created and related to the company 1",
        )
        self.assertEqual(
            seed_company.record_set.count(),
            5,
            "Exactly 5 new records are created and related to the company 1",
        )
        self.assertEqual(Record.objects.count(), 5, "Exactly 5 new records exist in db")

        seed_company_factory = CompanyFactory()
        company2 = seed(company=seed_company_factory)

        self.assertIsInstance(company2, Company, "Return Company object")
        self.assertIs(seed_company_factory, company2, "Is the same Company object")
        self.assertEqual(
            company2.record_set.count(),
            5,
            "Exactly 5 new records are created and related to the company 2",
        )
        self.assertEqual(
            seed_company_factory.record_set.count(),
            5,
            "Exactly 5 new records are created and related to the company 2",
        )
        self.assertEqual(
            Record.objects.count(), 10, "Exactly 10 new records exist in db"
        )

    def test_seed_with_input_records_and_company(self):
        """
        Most common case:
        seed() should be able to generate correct number of records for inputted Company objects
        """
        seed_company_factory = CompanyFactory()
        company = seed(records=50, company=seed_company_factory)

        self.assertIsInstance(company, Company, "Return Company object")
        self.assertIs(seed_company_factory, company, "Is the same Company object")
        self.assertEqual(
            company.record_set.count(),
            50,
            "Exactly 50 new records are created and related to the seed company",
        )
        self.assertEqual(
            seed_company_factory.record_set.count(),
            50,
            "Exactly 50 new records are created and related to the seed company",
        )
        self.assertEqual(
            Record.objects.count(), 50, "Exactly 50 new records exist in db"
        )

    def test_seed_with_input_company_with_records(self):
        """seed() should be able to raise predictable Exception when inputted Company objects already have records"""
        # Manually insert a record to a company object and use seed() on it
        manual_record_company = CompanyFactory()
        RecordFactory(company=manual_record_company)  # Add a record to the company

        self.assertEqual(
            manual_record_company.record_set.count(),
            1,
            "Exactly 1 new record is related to the company",
        )
        self.assertEqual(Record.objects.count(), 1, "Exactly 1 record exists in db")
        with self.assertRaisesMessage(
            Exception,
            "Company already has records.\n{} has {} record(s)".format(
                manual_record_company, manual_record_company.record_set.count()
            ),
        ):
            seed(company=manual_record_company)
        self.assertEqual(
            manual_record_company.record_set.count(),
            1,
            "Exactly 1 new record is related to the company after fail seeding",
        )
        self.assertEqual(
            Record.objects.count(),
            1,
            "Exactly 1 record exists in db  after fail seeding",
        )

        # Using seed() twice
        seed_company = CompanyFactory()
        seed(company=seed_company)

        self.assertEqual(
            seed_company.record_set.count(),
            5,
            "Exactly 5 new records are related to the seeded company",
        )
        self.assertEqual(
            Record.objects.count(),
            6,
            "Exactly 6 records exist in db  after fail seeding",
        )
        with self.assertRaisesMessage(
            Exception,
            "Company already has records.\n{} has {} record(s)".format(
                seed_company, seed_company.record_set.count()
            ),
        ):
            seed(company=seed_company)
        self.assertEqual(
            seed_company.record_set.count(),
            5,
            "Exactly 5 new records are related to the seeded company after fail seeding",
        )
        self.assertEqual(
            Record.objects.count(),
            6,
            "Exactly 6 records exist in db  after fail seeding",
        )
