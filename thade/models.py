from django.db import models
from django.utils.translation import gettext_lazy as _


# Create your models here.
class Company(models.Model):
    code = models.CharField(max_length=8, unique=True)
    name = models.CharField(max_length=256)
    website = models.CharField(max_length=256)
    stock_exchange = models.CharField(max_length=8)

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
    fee = models.FloatField()
    deploy_date = models.DateTimeField()
    stocks_per_trade = models.IntegerField()
    algorithm = models.CharField(max_length=256)
    investment_vnd = models.IntegerField()

    state = models.BooleanField(default=False)

    def __str__(self):
        return f"Bot(bid={self.bid!r})"


class BotLog(models.Model):
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE)
    last_updated_record = models.ForeignKey(Record, on_delete=models.PROTECT)

    # Driving attributes
    balance_vnd = models.IntegerField()
    stocks = models.IntegerField()

    class Signal(models.TextChoices):
        BUY = 'BUY', _('Buy')
        SELL = 'SELL', _('Sell')
        HOLD = 'HOLD', _('Hold')
        NOT_BUY = 'NOT_BUY', _('Cannot afford to Buy')
        NOT_SELL = 'NOT_SELL', _('Not enough stocks to Sell')
        ERR = 'ERR', _('Invalid signal')

    signal = models.CharField(
        max_length=16,
        choices=Signal.choices,
        default=Signal.ERR
    )

    log_str = models.CharField(max_length=128)

    # Statistical attributes
    all_time_min_total_vnd = models.IntegerField()
    all_time_max_total_vnd = models.IntegerField()

    control_balance_vnd = models.IntegerField()
    control_stocks = models.IntegerField()

    def __str__(self):
        return f"BotLog(bot={self.bot!r}, record={self.last_updated_record!r})"
