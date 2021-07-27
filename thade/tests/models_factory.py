import django.db.utils
import factory
import string

from django.utils import timezone
from factory import fuzzy

from thade.models import Company, Record, Bot, BotLog


class CompanyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Company

    code = factory.Faker('lexify', text="???", letters=string.ascii_uppercase)
    name = factory.Faker('company')
    website = factory.Faker('domain_name')
    stock_exchange = factory.Faker('random_element', elements=('HOSE', 'HNX', 'UPCoM'))
    last_records_fetched = timezone.now()


class RecordFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Record
        exclude = ('close_fluctuation', 'open_fluctuation', 'highest_fluctuation', 'lowest_fluctuation')

    company = factory.Iterator(Company.objects.all())

    rid = factory.LazyAttribute(
        lambda this: '{}{:04}{:02}{:02}'.format(
            this.company.code,
            this.utc_trading_date.year,
            this.utc_trading_date.month,
            this.utc_trading_date.day
        ).upper()
    )  # ID format: CODE+YYYY+MM+DD

    # utc_trading_date = timezone.now().replace(hour=2, minute=0, second=0, microsecond=0)
    utc_trading_date = factory.Sequence(
        lambda n: timezone.now().replace(hour=2, minute=0, second=0, microsecond=0) - timezone.timedelta(days=n)
    )

    # Reference stock: CTCP Tập đoàn Hòa Phát - HPG (on July 2021)
    reference_price_vnd = factory.Faker('random_int', min=30000, max=60000, step=100)

    close_fluctuation = factory.Faker('random_int', min=-5000, max=5000, step=100)
    close_vnd = factory.LazyAttribute(lambda this: this.reference_price_vnd + this.close_fluctuation)

    volume = factory.Faker('random_int', min=10000000, max=40000000, step=100)

    open_fluctuation = factory.Faker('random_int', min=-5000, max=5000, step=100)
    open_vnd = factory.LazyAttribute(lambda this: this.reference_price_vnd + this.open_fluctuation)

    highest_fluctuation = factory.Faker('random_int', min=0, max=2000, step=100)
    highest_vnd = factory.LazyAttribute(lambda this: max(this.close_vnd, this.open_vnd) + this.highest_fluctuation)

    lowest_fluctuation = factory.Faker('random_int', min=-2000, max=0, step=100)
    lowest_vnd = factory.LazyAttribute(lambda this: min(this.close_vnd, this.open_vnd) + this.lowest_fluctuation)


def seed(records=5, days_from_now=0, company: Company = None) -> Company:
    """
    Seed database with a fake Company and fake Records.
    Note: Resetting RecordFactory's sequence counter

    :param records: Number of records to seed
    :param days_from_now: Number of past days from today to start seeding from.
    :param company: A company without records to seed (set None: auto created)
    :return: Company
    """
    RecordFactory.reset_sequence(days_from_now)

    if company is None:
        # Company code has to be unique
        while True:
            try:
                company = CompanyFactory()
            except django.db.utils.IntegrityError:
                continue
            else:
                break
    elif company.record_set.count():
        raise Exception("Company already has records.\n{} has {} record(s)".format(company,
                                                                                   company.record_set.count()))

    RecordFactory.create_batch(records, company=company)

    RecordFactory.reset_sequence()
    return company


class BotFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Bot

    bid = factory.LazyAttribute(
        lambda this: '{}-{:%Y%m%d-%H%M%S%z}-{}'.format(this.company.code, this.deploy_date, this.name)
    )
    name = factory.Faker('first_name')
    company = factory.Iterator(Company.objects.all())
    fee = 0.0035
    deploy_date = timezone.now()
    stocks_per_trade = factory.Faker('random_int', min=10, max=100, step=10)
    algorithm = 'MovingAverage'
    investment_vnd = factory.Faker('random_int', min=1000000, max=50000000, step=1000000)
    state = False


class BotLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BotLog

    bot = factory.Iterator(Bot.objects.all())
    last_updated_record = factory.Iterator(Record.objects.all())
    decimal_balance_vnd = factory.Faker('pydecimal', min_value=0, max_value=50000000, right_digits=3)
    stocks = factory.Faker('random_int', min=0, max=1000)
    signal = fuzzy.FuzzyChoice(BotLog.Signal, getter=lambda c: c[0])
    log_str = factory.LazyAttribute(
        lambda this: '{} - {}: {} __ {}\n'.format(timezone.now(), this.last_updated_record.rid,
                                                  this.signal, this.bot.company.code)
    )
    investment_vnd = factory.Faker('random_int', min=0, max=50000000, step=1000)
    all_time_min_total_vnd = factory.Faker('pydecimal', min_value=0, max_value=50000000, right_digits=3)
    all_time_max_total_vnd = factory.Faker('pydecimal', min_value=0, max_value=50000000, right_digits=3)
    control_decimal_balance_vnd = factory.Faker('pydecimal', min_value=0, max_value=50000000, right_digits=3)
    control_stocks = factory.Faker('random_int', min=0, max=1000)
