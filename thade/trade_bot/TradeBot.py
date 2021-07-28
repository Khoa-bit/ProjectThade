import os
import warnings
from decimal import Decimal

from django.utils import timezone
from faker import Faker

from projectthade.settings import BASE_DIR
from thade.models import Company, Record, Bot, BotLog
from thade.trade_bot.Algorithm import Algorithm
from thade.trade_bot.MovingAverage import MovingAverage


class TradeBot:
    def __init__(self, balance_vnd: Decimal, company: Company, fee: Decimal, algorithm: Algorithm,
                 name: str = None, stocks=0, stocks_per_trade=50, deploy_date=timezone.now(),
                 decimal_investment_vnd: Decimal = None, all_time_min_total_vnd: Decimal = None,
                 all_time_max_total_vnd: Decimal = None, control_decimal_balance_vnd: Decimal = None,
                 control_stocks: int = None,
                 last_update_record: Record = None, model: Bot = None
                 ):
        """

        :param balance_vnd: The Balance to start with (VND)
        :param company: A Company that is assigned to this bot
        :param fee: Trading fee/tax
        :param algorithm: Children of Algorithm class
        :param name: Unique name for bot
        :param stocks: Bought stocks
        :param stocks_per_trade: Amount of stocks to trade on every action (BUY/SELL)
        :param deploy_date: When this bot was deployed
        :param decimal_investment_vnd: Total investment has been put into this bot
        :param all_time_min_total_vnd: The lowest total the bot has reached
        :param all_time_max_total_vnd: The highest total the bot has reached
        :param control_decimal_balance_vnd: The Balance to start with to BUY and HOLD only (VND)
        :param control_stocks: Held stocks
        :param last_update_record: Record exists in database and belongs to the same company
        :param model: Bot's model exists in database and has the same bid
        """

        # Driving attributes
        self.name = name
        self.decimal_balance_vnd = balance_vnd
        self.company = company
        self.fee = fee
        self.deploy_date = deploy_date
        self.stocks = stocks
        self.stocks_per_trade = stocks_per_trade
        self.algorithm = algorithm
        self.algorithm.set_fee(fee)

        if self.name is None:
            fake = Faker()
            self.name = fake.first_name()
        elif len(self.name) > 34 or self.name.find(' ') != -1:
            raise UserWarning("Bot's name must be a WORD having less then 34 characters: {}".format(self.name))

        # Statistical attributes
        self.decimal_investment_vnd = decimal_investment_vnd or balance_vnd
        self.all_time_min_total_vnd = all_time_min_total_vnd or balance_vnd
        self.all_time_max_total_vnd = all_time_max_total_vnd or balance_vnd

        self.control_decimal_balance_vnd = control_decimal_balance_vnd or balance_vnd
        self.control_stocks = control_stocks or stocks

        if last_update_record is None:
            # Get last_updated_record which is the nearest to deployed date
            self.last_updated_record = self.company.record_set.filter(
                utc_trading_date__lte=self.deploy_date).order_by('-utc_trading_date').first()

            if self.last_updated_record is None:
                self.last_updated_record = self.company.record_set.order_by('-utc_trading_date').last()
                warnings.warn(
                    'The deploy date is earlier than when '
                    '{0} first went official on the stock market: {1} < {2}\n=> last_updated_record = {2}'.format(
                        self.company, self.deploy_date, self.last_updated_record)
                )
        elif last_update_record.id is None or last_update_record.company != self.company:
            raise UserWarning('last_update_record must exists in database and'
                              f' belongs the same company as the bot: {last_update_record}')
        else:
            self.last_updated_record = last_update_record

        # Generate bid for Bot
        self.bid = '{}-{:%Y%m%d-%H%M%S%z}-{}'.format(
            self.company.code,
            self.deploy_date,
            self.name.upper()
        )

        # Setup for tracking in database
        if model is None:
            self.is_active = False
            self.is_tracking = False
            self.model = Bot(
                bid=self.bid,
                name=self.name,
                company=self.company,
                fee=self.fee,
                deploy_date=self.deploy_date,
                stocks_per_trade=self.stocks_per_trade,
                algorithm=str(self.algorithm),
                is_active=self.is_active,
            )
        elif model.id is None or model.bid != self.bid:
            raise UserWarning('Bot model must exists in database and'
                              f' has the same bid as the bot: {model}')
        else:
            self.model = model
            self.is_active = model.is_active
            self.is_tracking = True

        self.log(f'{self.name} is deployed', BotLog.Signal.DEPLOY)

    def track(self):
        """
        Save this bot into database and start tracking its actions through database.\n
        Or else still track its actions into a txt file.

        :return:
        """
        self.model.save()
        self.is_tracking = True
        self.write_txt('Moved to database')
        self.log(f'{self.name} is deployed', BotLog.Signal.DEPLOY)

    def delete_all_logs(self):
        """Deleting permanently its bot instance and all of its logs"""
        if self.is_tracking:
            print(self.model.delete())
        else:
            warnings.warn("This bot has not yet been tracked through database")
            log_txt_path = BASE_DIR / 'thade/trade_bot/logs/{}_{}_{}.txt'.format(self.name, self.company.code,
                                                                                 self.algorithm)
            if os.path.exists(log_txt_path):
                os.remove(log_txt_path)

    def toggle(self):
        self.is_active = not self.is_active
        if self.is_tracking:
            self.model.is_active = self.is_active
            self.model.save()

    def invest(self, balance_vnd: Decimal):
        """

        :param balance_vnd: The Balance to invest more into (VND)
        :return:
        """
        self.decimal_balance_vnd += balance_vnd
        self.decimal_investment_vnd += balance_vnd
        self.control_decimal_balance_vnd += balance_vnd
        self.log(f'Invest {balance_vnd} VND', BotLog.Signal.INVEST)

    def withdraw(self, balance_vnd: int):
        """

        :param balance_vnd: The Balance to withdraw (VND)
        :return:
        """
        if balance_vnd <= self.decimal_balance_vnd and balance_vnd <= self.control_decimal_balance_vnd:
            self.decimal_balance_vnd -= balance_vnd
            self.decimal_investment_vnd -= balance_vnd
            self.control_decimal_balance_vnd -= balance_vnd
            self.log(f'Withdraw {balance_vnd} VND', BotLog.Signal.WITHDRAW)
        elif balance_vnd > self.decimal_balance_vnd:
            warnings.warn(f'Not enough balance_vnd to withdraw: {balance_vnd} > {self.decimal_balance_vnd}')
        elif balance_vnd > self.control_decimal_balance_vnd:
            warnings.warn(
                f'Not enough control_balance_vnd to withdraw: {balance_vnd} > {self.control_decimal_balance_vnd}'
            )

    def run(self):
        if self.is_active:
            newest_records = self.company.record_set.order_by('-utc_trading_date').first()
            while self.last_updated_record != newest_records:
                # Move to the next record after last_update_record
                self.last_updated_record = self.company.record_set.filter(
                    utc_trading_date__gt=self.last_updated_record.utc_trading_date).order_by('-utc_trading_date').last()

                # Feed new data to the algorithm
                try:
                    self.algorithm.update_data(
                        self.company.record_set.filter(utc_trading_date__lte=self.last_updated_record.utc_trading_date)
                    )

                    # BUY, SELL or HOLD?
                    log_str, result_signal = self.action(self.algorithm.action())

                    # Update statistics
                    self.statistics()
                except UserWarning as e:
                    log_str = str(e)
                    result_signal = BotLog.Signal.ERR

                self.log(log_str, result_signal)
        else:
            warnings.warn('This bot is currently inactive. (Run self.toggle() to active)')

    def action(self, signal: int):
        if signal == Algorithm.BUY:
            buy_cost = self.last_updated_record.close_vnd * self.stocks_per_trade * (1 + self.fee)
            if self.decimal_balance_vnd >= buy_cost:
                self.decimal_balance_vnd -= buy_cost
                self.stocks += self.stocks_per_trade
                log_str = 'BUY {} {}'.format(self.stocks_per_trade, self.company.code)
                result_signal = BotLog.Signal.BUY
            else:
                log_str = 'Cannot afford to BUY {} {}'.format(self.stocks_per_trade, self.company.code)
                result_signal = BotLog.Signal.NOT_BUY
        elif signal == Algorithm.SELL:
            if self.stocks >= self.stocks_per_trade:
                self.decimal_balance_vnd += self.last_updated_record.close_vnd * self.stocks_per_trade * (1 - self.fee)
                self.stocks -= self.stocks_per_trade
                log_str = 'SELL {} {}'.format(self.stocks_per_trade, self.company.code)
                result_signal = BotLog.Signal.SELL
            else:
                log_str = 'Not enough stocks to SELL {} {}'.format(self.stocks_per_trade, self.company.code)
                result_signal = BotLog.Signal.NOT_SELL
        elif signal == Algorithm.HOLD:
            log_str = 'HOLD'
            result_signal = BotLog.Signal.HOLD
        else:
            raise UserWarning('Invalid signal: {}'.format(signal))

        return log_str, result_signal

    def log(self, log_str: str, result_signal: BotLog.Signal):
        """Log bot's actions out into a txt file if not tracking through Database"""
        print('=============================')
        print(log_str)
        if self.is_tracking:
            BotLog.objects.create(
                bot=self.model,
                last_updated_record=self.last_updated_record,
                decimal_balance_vnd=self.decimal_balance_vnd,
                stocks=self.stocks,
                signal=result_signal,
                log_str='{}: {}'.format(timezone.now(), log_str),
                decimal_investment_vnd=self.decimal_investment_vnd,
                all_time_min_total_vnd=self.all_time_min_total_vnd,
                all_time_max_total_vnd=self.all_time_max_total_vnd,
                control_decimal_balance_vnd=self.control_decimal_balance_vnd,
                control_stocks=self.control_stocks,
            )
        else:
            self.write_txt(log_str)

    def write_txt(self, log_str: str):
        with open(
                BASE_DIR / 'thade/trade_bot/logs/{}_{}_{}.txt'.format(self.name, self.company.code, self.algorithm),
                'a'
        ) as f:
            f.write('{} - {}: {}\n'.format(timezone.now(), self.last_updated_record.rid, log_str))

    def statistics(self):
        value_in_stocks = self.last_updated_record.close_vnd * self.stocks
        total = self.decimal_balance_vnd + value_in_stocks
        self.all_time_min_total_vnd = min(self.all_time_min_total_vnd, total)
        self.all_time_max_total_vnd = max(self.all_time_max_total_vnd, total)

        buy_stocks = int(self.control_decimal_balance_vnd // (self.last_updated_record.close_vnd * (1 + self.fee)))
        self.control_decimal_balance_vnd -= buy_stocks * self.last_updated_record.close_vnd * (1 + self.fee)
        self.control_stocks += buy_stocks

    def output_statistics(self) -> str:
        value_in_stocks = self.last_updated_record.close_vnd * self.stocks
        total = self.decimal_balance_vnd + value_in_stocks
        roi = (total / self.decimal_investment_vnd - 1) * 100

        control_value_in_stocks = self.last_updated_record.close_vnd * self.control_stocks
        control_total = self.control_decimal_balance_vnd + control_value_in_stocks
        control_roi = (control_total / self.decimal_investment_vnd - 1) * 100

        output_str = '\n'
        output_str += '_____BOT: {} - {}_____\n'.format(self.name, self.bid)
        output_str += '\n===================ASSETS===================\n'
        output_str += '{:15}: {:.1f}\n'.format('Balance', self.decimal_balance_vnd)
        output_str += '{:15}: {:.1f}\n'.format('Stocks', self.stocks)
        output_str += '{:15}: {:.1f}\n'.format('Value in Stocks', value_in_stocks)
        output_str += '{:15}: {:.1f}\n'.format('Total', total)
        output_str += '{:15}: {:.2f}%\n'.format('ROI', roi)

        output_str += '\n==================SCENARIO==================\n'
        output_str += '{:15}: {:.1f}\n'.format('Min Balance', self.all_time_min_total_vnd)
        output_str += '{:15}: {:.1f}\n'.format('Max Balance', self.all_time_max_total_vnd)

        output_str += '\n==================CONTROL===================\n'
        output_str += '{:15}: {:.1f}\n'.format('Value in Stocks', control_value_in_stocks)
        output_str += '{:15}: {:.1f}\n'.format('Total', control_total)
        output_str += '{:15}: {:.2f}%\n'.format('ROI', control_roi)
        return output_str

    def __str__(self):
        return self.bid


def get_trade_bot(bot: Bot):
    """Get TradeBot object from Bot model"""
    last_log: BotLog = bot.botlog_set.last()

    if bot.algorithm == 'MovingAverage':
        bot_algorithm = MovingAverage()
    elif bot.algorithm == 'Algorithm':
        bot_algorithm = Algorithm()
    else:
        warnings.warn(f'Unknown algorithm (default to Algorithm()): {bot.algorithm}')
        bot_algorithm = Algorithm()

    return TradeBot(
        balance_vnd=last_log.decimal_balance_vnd,
        company=bot.company,
        fee=bot.fee,
        algorithm=bot_algorithm,
        name=bot.name,
        stocks=last_log.stocks,
        stocks_per_trade=bot.stocks_per_trade,
        deploy_date=bot.deploy_date,
        decimal_investment_vnd=last_log.decimal_investment_vnd,
        all_time_min_total_vnd=last_log.all_time_min_total_vnd,
        all_time_max_total_vnd=last_log.all_time_max_total_vnd,
        control_decimal_balance_vnd=last_log.control_decimal_balance_vnd,
        control_stocks=last_log.control_stocks,
        last_update_record=last_log.last_updated_record,
        model=bot
    )


def debug_bot():
    moving_avg_bot = TradeBot(
        balance_vnd=Decimal(200 * 1000000),
        company=Company.objects.get(code='VHM'),
        fee=Decimal(0.0035),
        algorithm=MovingAverage(),
        deploy_date=timezone.now() - timezone.timedelta(days=365 * 4)
    )

    # moving_avg_bot.track()

    moving_avg_bot.toggle()
    moving_avg_bot.run()
    print(moving_avg_bot.output_statistics())
    # moving_avg_bot.delete_all_logs()
