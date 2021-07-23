import warnings

from thade.trade_bot.Algorithm import Algorithm
from thade.models import Company
from numpy import mean


class MovingAverage(Algorithm):
    def __init__(self):
        super().__init__()
        self.close_50 = []
        self.close_200 = []
        self.moving_50 = 0
        self.moving_200 = 0

    def _extract(self):
        if self.data.count() < 200:
            warnings.warn('Not enough records to compute moving average: {} < 200', self.data.count())
        else:
            self.data.order_by('-utc_trading_date')
            self.close_50 = [x.close_vnd for x in self.data[:50]]
            self.close_200 = [x.close_vnd for x in self.data[:200]]

    def compute(self):
        super().compute()
        self.moving_50 = mean(self.close_50)
        self.moving_200 = mean(self.close_200)

    def action(self):
        super().action()
        if self.moving_50 >= self.moving_200:
            return self.BUY
        else:
            return self.SELL

    def __str__(self):
        return 'MovingAverage'

