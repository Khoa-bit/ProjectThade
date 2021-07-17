from django.db import models


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
