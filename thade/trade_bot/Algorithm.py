from decimal import Decimal

from django.db.models import QuerySet


class Algorithm:
    BUY = 0
    SELL = 1
    HOLD = 2

    def __init__(self, fee=Decimal(0)):
        self.data = QuerySet()
        self.TRADE_FEE = fee

    def set_fee(self, fee: Decimal):
        self.TRADE_FEE = fee

    def _extract(self):
        pass

    def update_data(self, data: QuerySet):
        self.data = data
        self._extract()

    def compute(self):
        self._extract()

    def action(self):
        self.compute()

    def __str__(self):
        return "Algorithm"
