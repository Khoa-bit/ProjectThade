from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# Create your models here.
class Company(models.Model):
    code = models.CharField(max_length=8, unique=True)
    name = models.CharField(max_length=256)
    website = models.CharField(max_length=256)
    stock_exchange = models.CharField(max_length=8)
    last_records_fetched = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Company(code={self.code!r}, name={self.name!r})"


class Record(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    rid = models.CharField(max_length=16, unique=True)  # ID format: CODE+YYYY+MM+DD
    utc_trading_date = models.DateTimeField()  # Low frequency trading
    reference_price_vnd = models.IntegerField()
    close_vnd = models.IntegerField()
    volume = models.IntegerField()
    open_vnd = models.IntegerField()
    highest_vnd = models.IntegerField()
    lowest_vnd = models.IntegerField()

    def __str__(self):
        return f"Record(rid={self.rid!r})"


class Bot(models.Model):
    bid = models.CharField(max_length=64, unique=True)  # ID format: CODE-YYYYmmdd-HHMMSS+zzzz-NAME
    name = models.CharField(max_length=256)
    company = models.ForeignKey(Company, on_delete=models.PROTECT)
    fee = models.DecimalField(max_digits=12, decimal_places=6)
    deploy_date = models.DateTimeField()
    stocks_per_trade = models.IntegerField()
    algorithm = models.CharField(max_length=256)

    is_active = models.BooleanField(default=False)

    def __str__(self):
        return f"Bot(bid={self.bid!r})"


class BotLog(models.Model):
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE)
    last_updated_record = models.ForeignKey(Record, on_delete=models.PROTECT)

    # Driving attributes
    decimal_balance_vnd = models.DecimalField(max_digits=16, decimal_places=4)
    stocks = models.IntegerField()

    class Signal(models.TextChoices):
        BUY = 'BUY', _('Buy')
        SELL = 'SELL', _('Sell')
        HOLD = 'HOLD', _('Hold')
        NOT_BUY = 'NOT_BUY', _('Cannot afford to Buy')
        NOT_SELL = 'NOT_SELL', _('Not enough stocks to Sell')
        INVEST = 'INVEST', _('Invest')
        WITHDRAW = 'WITHDRAW', _('Withdraw')
        ERR = 'ERR', _('Invalid signal')
        DEPLOY = 'DEPLOY', _('Deployed')

    signal = models.CharField(
        max_length=16,
        choices=Signal.choices,
        default=Signal.ERR
    )

    log_str = models.CharField(max_length=128)

    # Statistical attributes
    decimal_investment_vnd = models.DecimalField(max_digits=16, decimal_places=4)
    all_time_min_total_vnd = models.DecimalField(max_digits=16, decimal_places=4)
    all_time_max_total_vnd = models.DecimalField(max_digits=16, decimal_places=4)

    control_decimal_balance_vnd = models.DecimalField(max_digits=16, decimal_places=4)
    control_stocks = models.IntegerField()

    def __str__(self):
        return f"BotLog(bot={self.bot!r}, record={self.last_updated_record!r})"
