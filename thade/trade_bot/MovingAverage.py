from django.db.models import QuerySet

from thade.trade_bot.Algorithm import Algorithm
from numpy import mean


class MovingAverage(Algorithm):
    def __init__(self):
        super().__init__()
        self.close_50 = QuerySet()
        self.close_200 = QuerySet()
        self.moving_50 = 0
        self.moving_200 = 0

    def _extract(self):
        if self.data.count() < 200:
            raise UserWarning('Not enough records to compute moving average: {} < 200'.format(self.data.count()))
        else:
            self.data = self.data.order_by('-utc_trading_date')
            close_records = self.data.values_list('close_vnd', flat=True)
            self.close_50 = close_records[:50]
            self.close_200 = close_records[:200]

    def compute(self):
        super().compute()
        self.moving_50 = mean(self.close_50)
        self.moving_200 = mean(self.close_200)

    def action(self):
        super().action()
        if self.moving_50 >= self.moving_200:
            return self.BUY
        elif self.moving_50 < self.moving_200:
            return self.SELL

    def __str__(self):
        return 'MovingAverage'

