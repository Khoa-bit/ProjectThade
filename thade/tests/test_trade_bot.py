import warnings
import os
from glob import glob

import yaml
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone

from projectthade.settings import BASE_DIR
from thade.tests.models_factory import seed, CompanyFactory, RecordFactory, BotLogFactory, BotFactory
from thade.models import Bot, BotLog
from thade.trade_bot.Algorithm import Algorithm
from thade.trade_bot.MovingAverage import MovingAverage
from thade.trade_bot.TradeBot import TradeBot, get_trade_bot

# Global constant variables
TEST = yaml.safe_load(open(BASE_DIR / 'config.yaml'))['TEST']
NAIVE_DATETIME = TEST['NAIVE_DATETIME_ISO']
AWARE_DATETIME = TEST['AWARE_DATETIME_ISO']


class AlgorithmTests(TestCase):
    def test_default_attributes(self):
        self.assertEqual(Algorithm.BUY, 0)
        self.assertEqual(Algorithm.SELL, 1)
        self.assertEqual(Algorithm.HOLD, 2)

        abstract_algorithm = Algorithm()
        self.assertEqual(abstract_algorithm.BUY, 0)
        self.assertEqual(abstract_algorithm.SELL, 1)
        self.assertEqual(abstract_algorithm.HOLD, 2)
        self.assertEqual(abstract_algorithm.TRADE_FEE, 0.0)
        abstract_algorithm.set_fee(Decimal(0.0035))
        self.assertEqual(abstract_algorithm.TRADE_FEE, Decimal(0.0035))

        abstract_algorithm = Algorithm(Decimal(0.0123))
        self.assertEqual(abstract_algorithm.TRADE_FEE, Decimal(0.0123))

    def test_data_QuerySet(self):
        company = seed()
        print(company.code)

        abstract_algorithm = Algorithm()
        abstract_algorithm.update_data(company.record_set.all())

        self.assertQuerysetEqual(abstract_algorithm.data, company.record_set.all(), ordered=False)


class MovingAverageTests(TestCase):
    def setUp(self):
        from thade.tests.records_fixture import close_records, moving_50, moving_200, signals

        self.company = CompanyFactory()
        for i, close_record in enumerate(close_records):
            RecordFactory(company=self.company, close_vnd=close_record)

        self.close_records = close_records
        self.moving_50 = moving_50
        self.moving_200 = moving_200
        self.signals = signals

    def test_update_extract_compute_action_on_first_200_records(self):
        moving_average = MovingAverage()

        moving_average.update_data(self.company.record_set.all())
        self.assertQuerysetEqual(moving_average.data, self.company.record_set.order_by('-utc_trading_date'))
        self.assertQuerysetEqual(moving_average.close_50, self.close_records[:50])
        self.assertQuerysetEqual(moving_average.close_200, self.close_records[:200])

        moving_average.compute()
        self.assertEqual(moving_average.moving_50, 107772)
        self.assertEqual(moving_average.moving_200, 95046)

        self.assertEqual(moving_average.action(), Algorithm.BUY)

    def test_compute_action_on_all_500_records(self):
        moving_average = MovingAverage()

        last_updated_record = self.company.record_set.order_by('-utc_trading_date').last()
        newest_records = self.company.record_set.order_by('-utc_trading_date').first()
        test_moving_50 = []
        test_moving_200 = []
        test_signals = []
        while last_updated_record != newest_records:
            # Move to the next record after last_update_record
            last_updated_record = self.company.record_set.filter(
                utc_trading_date__gt=last_updated_record.utc_trading_date).order_by('-utc_trading_date').last()

            # Feed new data to the algorithm
            try:
                moving_average.update_data(
                    self.company.record_set.filter(utc_trading_date__lte=last_updated_record.utc_trading_date)
                )

                test_signals.append(moving_average.action())
                test_moving_50.append(moving_average.moving_50)
                test_moving_200.append(moving_average.moving_200)
            except UserWarning:
                pass

        test_moving_50.reverse()
        test_moving_200.reverse()
        test_signals.reverse()
        self.assertListEqual(test_moving_50, self.moving_50)
        self.assertListEqual(test_moving_200, self.moving_200)
        self.assertListEqual(test_signals, self.signals)


class TradeBotTests(TestCase):
    def setUp(self):
        from thade.tests.records_fixture import close_records

        # Set up company and fix records' period from 2019-08-21T02:00:00+00:00 to 2021-01-01T02:00:00+00:00
        self.company = CompanyFactory()
        for i, close_record in enumerate(close_records):
            utc_trading_date = AWARE_DATETIME.replace(
                hour=2, minute=0, second=0, microsecond=0) - timezone.timedelta(days=i)

            RecordFactory(company=self.company,
                          close_vnd=close_record,
                          utc_trading_date=utc_trading_date)

    @classmethod
    def tearDownClass(cls):
        for file in glob(str(BASE_DIR / r"thade/trade_bot/logs/Jester_*.txt")):
            os.remove(file)

    def test_name_longer_than_34_chars(self):
        long_name = 'thisisanamethatislongerthan34characters'
        with self.assertRaisesMessage(
                UserWarning,
                "Bot's name must be a WORD having less then 34 characters: {}".format(long_name)
        ):
            TradeBot(
                name=long_name,
                balance_vnd=Decimal(200 * 1000000),
                company=CompanyFactory(code='VHM'),
                fee=Decimal(0.0035),
                algorithm=Algorithm(),
                deploy_date=AWARE_DATETIME
            )

    def test_name_with_spaces(self):
        space_name = 'spaces are in this name'
        with self.assertRaisesMessage(
                UserWarning,
                "Bot's name must be a WORD having less then 34 characters: {}".format(space_name)
        ):
            TradeBot(
                name=space_name,
                balance_vnd=Decimal(200 * 1000000),
                company=CompanyFactory(code='VHM'),
                fee=Decimal(0.0035),
                algorithm=Algorithm(),
                deploy_date=AWARE_DATETIME
            )

    def test_generated_bid(self):
        bot = TradeBot(
            name='Jester',
            balance_vnd=Decimal(200 * 1000000),
            company=self.company,
            fee=Decimal(0.0035),
            algorithm=Algorithm(),
            deploy_date=AWARE_DATETIME
        )

        self.assertEqual(bot.bid, '{}-{:%Y%m%d-%H%M%S%z}-JESTER'.format(self.company.code, AWARE_DATETIME))

    def test_last_updated_record_from_deploy_date_after_officially_on_stock_market(self):
        with warnings.catch_warnings(record=True) as w:
            TradeBot(
                name='Jester',
                balance_vnd=Decimal(200 * 1000000),
                company=self.company,
                fee=Decimal(0.0035),
                algorithm=Algorithm(),
                deploy_date=AWARE_DATETIME
            )
            self.assertEqual(len(w), 0, 'There should not be any warnings')

    def test_last_updated_record_from_deploy_date_before_officially_on_stock_market(self):
        with warnings.catch_warnings(record=True) as w:
            before_official_deploy_date = AWARE_DATETIME - timezone.timedelta(days=501)
            bot = TradeBot(
                name='Jester',
                balance_vnd=Decimal(200 * 1000000),
                company=self.company,
                fee=Decimal(0.0035),
                algorithm=Algorithm(),
                deploy_date=before_official_deploy_date
            )
            self.assertEqual(w[-1].category, UserWarning)
            self.assertEqual(str(w[-1].message),
                             'The deploy date is earlier than when {0} first went official on the stock market:'
                             ' {1} < {2}\n=> last_updated_record = {2}'.format(self.company,
                                                                               before_official_deploy_date,
                                                                               bot.last_updated_record
                                                                               )
                             )

    def test_input_invalid_last_updated_record(self):
        company = CompanyFactory(code='VHM')
        last_update_record_not_in_db = RecordFactory.build(company=company)
        with self.assertRaisesMessage(
                UserWarning,
                'last_update_record must exists in database and'
                f' belongs the same company as the bot: {last_update_record_not_in_db}'
        ):
            TradeBot(
                name='Jester',
                balance_vnd=Decimal(200 * 1000000),
                company=company,
                fee=Decimal(0.0035),
                algorithm=Algorithm(),
                deploy_date=AWARE_DATETIME,
                last_update_record=last_update_record_not_in_db
            )

        last_update_record_different_company = RecordFactory(company=CompanyFactory(code='AAA'))
        with self.assertRaisesMessage(
                UserWarning,
                'last_update_record must exists in database and'
                f' belongs the same company as the bot: {last_update_record_different_company}'
        ):
            TradeBot(
                name='Jester',
                balance_vnd=Decimal(200 * 1000000),
                company=company,
                fee=Decimal(0.0035),
                algorithm=Algorithm(),
                deploy_date=AWARE_DATETIME,
                last_update_record=last_update_record_different_company
            )

    def test_input_valid_last_updated_record(self):
        company = CompanyFactory(code='VHM')
        last_update_record = RecordFactory(company=company)
        bot = TradeBot(
            name='Jester',
            balance_vnd=Decimal(200 * 1000000),
            company=company,
            fee=Decimal(0.0035),
            algorithm=Algorithm(),
            deploy_date=AWARE_DATETIME,
            last_update_record=last_update_record
        )

        self.assertEqual(bot.last_updated_record, last_update_record)

    def test_input_invalid_model(self):
        company = CompanyFactory(code='VHM')
        model_not_in_db = BotFactory.build(company=company)
        with self.assertRaisesMessage(
                UserWarning,
                'Bot model must exists in database and'
                f' has the same bid as the bot: {model_not_in_db}'
        ):
            TradeBot(
                name='Jester',
                balance_vnd=Decimal(200 * 1000000),
                company=company,
                fee=Decimal(0.0035),
                algorithm=Algorithm(),
                deploy_date=AWARE_DATETIME,
                model=model_not_in_db
            )

        model_different_bid = BotFactory(company=CompanyFactory(code='AAA'))
        with self.assertRaisesMessage(
                UserWarning,
                'Bot model must exists in database and'
                f' has the same bid as the bot: {model_different_bid}'
        ):
            TradeBot(
                name='Jester',
                balance_vnd=Decimal(200 * 1000000),
                company=company,
                fee=Decimal(0.0035),
                algorithm=Algorithm(),
                deploy_date=AWARE_DATETIME,
                model=model_different_bid
            )

    def test_input_valid_model(self):
        company = CompanyFactory(code='VHM')
        RecordFactory.create_batch(10, company=company)
        model = BotFactory(name='Jester', company=company, deploy_date=AWARE_DATETIME)
        bot = TradeBot(
            name='Jester',
            balance_vnd=Decimal(200 * 1000000),
            company=company,
            fee=Decimal(0.0035),
            algorithm=Algorithm(),
            deploy_date=AWARE_DATETIME,
            model=model
        )

        self.assertEqual(bot.model, model)

    def test_track(self):
        bot = TradeBot(
            name='Jester',
            balance_vnd=Decimal(200 * 1000000),
            company=self.company,
            fee=Decimal(0.0035),
            algorithm=Algorithm(),
            deploy_date=AWARE_DATETIME
        )
        self.assertFalse(bot.is_tracking)
        self.assertQuerysetEqual(Bot.objects.all(), [])
        bot.track()
        self.assertTrue(bot.is_tracking)
        self.assertQuerysetEqual(Bot.objects.all(), [bot.model])

    def test_delete_all_log(self):
        bot = TradeBot(
            name='Jester',
            balance_vnd=Decimal(200 * 1000000),
            company=self.company,
            fee=Decimal(0.0035),
            algorithm=Algorithm(),
            deploy_date=AWARE_DATETIME
        )

        bot.track()
        self.assertEqual(BotLog.objects.count(), 1)
        for i in range(30):
            BotLogFactory(bot=bot.model)

        self.assertEqual(BotLog.objects.count(), 31)
        self.assertQuerysetEqual(Bot.objects.all(), [bot.model])
        bot.delete_all_logs()
        self.assertQuerysetEqual(Bot.objects.all(), [], "Bot model is removed from database")
        self.assertEqual(BotLog.objects.count(), 0, "All of its BotLog models are delete together with the Bot models")

    def test_toggle(self):
        bot = TradeBot(
            name='Jester',
            balance_vnd=Decimal(200 * 1000000),
            company=self.company,
            fee=Decimal(0.0035),
            algorithm=Algorithm(),
            deploy_date=AWARE_DATETIME
        )

        self.assertFalse(bot.is_active)
        bot.toggle()
        self.assertTrue(bot.is_active)
        bot.toggle()
        self.assertFalse(bot.is_active)

        bot.track()
        self.assertFalse(bot.is_active)
        self.assertFalse(bot.model.is_active)
        self.assertFalse(Bot.objects.first().is_active)
        bot.toggle()
        self.assertTrue(bot.is_active)
        self.assertTrue(bot.model.is_active)
        self.assertTrue(Bot.objects.first().is_active)

    def test_invest(self):
        bot = TradeBot(
            name='Jester',
            balance_vnd=Decimal(200 * 1000000),
            company=self.company,
            fee=Decimal(0.0035),
            algorithm=Algorithm(),
            deploy_date=AWARE_DATETIME
        )

        self.assertEqual(round(bot.decimal_balance_vnd, 1), Decimal(200 * 1000000))
        self.assertEqual(round(bot.decimal_investment_vnd, 1), Decimal(200 * 1000000))
        self.assertEqual(round(bot.control_decimal_balance_vnd, 1), Decimal(200 * 1000000))
        bot.invest(Decimal(1 * 1000000))
        self.assertEqual(round(bot.decimal_balance_vnd, 1), Decimal(201 * 1000000))
        self.assertEqual(round(bot.decimal_investment_vnd, 1), Decimal(201 * 1000000))
        self.assertEqual(round(bot.control_decimal_balance_vnd, 1), Decimal(201 * 1000000))
        self.assertTrue(os.path.exists(BASE_DIR / f"thade/trade_bot/logs/Jester_{self.company.code}_Algorithm.txt"),
                        'A log file should be created when not tracking through database')

        bot.track()
        bot.invest(Decimal(5 * 1000000))
        self.assertEqual(round(bot.decimal_balance_vnd, 1), Decimal(206 * 1000000))
        self.assertEqual(round(bot.decimal_investment_vnd, 1), Decimal(206 * 1000000))
        self.assertEqual(round(bot.control_decimal_balance_vnd, 1), Decimal(206 * 1000000))
        bl = bot.model.botlog_set.all()
        self.assertEqual(bl[0].signal, BotLog.Signal.DEPLOY)
        self.assertEqual(bl[1].signal, BotLog.Signal.INVEST)
        self.assertEqual(round(bl[1].decimal_balance_vnd, 1), Decimal(206 * 1000000))
        self.assertEqual(round(bl[1].decimal_investment_vnd, 1), Decimal(206 * 1000000))
        self.assertEqual(round(bl[1].control_decimal_balance_vnd, 1), Decimal(206 * 1000000))

    def test_withdraw(self):
        bot = TradeBot(
            name='Jester',
            balance_vnd=Decimal(200 * 1000000),
            company=self.company,
            fee=Decimal(0.0035),
            algorithm=Algorithm(),
            deploy_date=AWARE_DATETIME
        )

        self.assertEqual(round(bot.decimal_balance_vnd, 1), Decimal(200 * 1000000))
        self.assertEqual(round(bot.decimal_investment_vnd, 1), Decimal(200 * 1000000))
        self.assertEqual(round(bot.control_decimal_balance_vnd, 1), Decimal(200 * 1000000))
        bot.withdraw(1 * 1000000)
        self.assertEqual(round(bot.decimal_balance_vnd, 1), Decimal(199 * 1000000))
        self.assertEqual(round(bot.decimal_investment_vnd, 1), Decimal(199 * 1000000))
        self.assertEqual(round(bot.control_decimal_balance_vnd, 1), Decimal(199 * 1000000))
        self.assertTrue(os.path.exists(BASE_DIR / f"thade/trade_bot/logs/Jester_{self.company.code}_Algorithm.txt"),
                        'A log file should be created when not tracking through database')

        bot.track()
        bot.withdraw(5 * 1000000)
        self.assertEqual(round(bot.decimal_balance_vnd, 1), Decimal(194 * 1000000))
        self.assertEqual(round(bot.decimal_investment_vnd, 1), Decimal(194 * 1000000))
        self.assertEqual(round(bot.control_decimal_balance_vnd, 1), Decimal(194 * 1000000))
        bl = bot.model.botlog_set.all()[1]
        self.assertEqual(bl.signal, BotLog.Signal.WITHDRAW)
        self.assertEqual(round(bl.decimal_balance_vnd, 1), Decimal(194 * 1000000))
        self.assertEqual(round(bl.decimal_investment_vnd, 1), Decimal(194 * 1000000))
        self.assertEqual(round(bl.control_decimal_balance_vnd, 1), Decimal(194 * 1000000))

    def test_action_BUY(self):
        bot = TradeBot(
            name='Jester',
            balance_vnd=Decimal(200 * 1000000),
            company=self.company,
            fee=Decimal(0.0035),
            algorithm=Algorithm(),
            deploy_date=AWARE_DATETIME
        )

        log_str, result_signal = bot.action(Algorithm.BUY)
        self.assertEqual(round(bot.decimal_balance_vnd, 1), Decimal(200 * 1000000 - 5469075.0))
        self.assertEqual(bot.stocks, 50)
        self.assertEqual(log_str, f'BUY 50 {self.company.code}')
        self.assertEqual(result_signal, BotLog.Signal.BUY)

    def test_action_NOT_BUY(self):
        bot = TradeBot(
            name='Jester',
            balance_vnd=Decimal(0),
            company=self.company,
            fee=Decimal(0.0035),
            algorithm=Algorithm(),
            deploy_date=AWARE_DATETIME
        )

        log_str, result_signal = bot.action(Algorithm.BUY)
        self.assertEqual(round(bot.decimal_balance_vnd, 1), Decimal(0))
        self.assertEqual(bot.stocks, 0)
        self.assertEqual(log_str, f'Cannot afford to BUY 50 {self.company.code}')
        self.assertEqual(result_signal, BotLog.Signal.NOT_BUY)

    def test_action_SELL(self):
        bot = TradeBot(
            name='Jester',
            balance_vnd=Decimal(0),
            stocks=200,
            company=self.company,
            fee=Decimal(0.0035),
            algorithm=Algorithm(),
            deploy_date=AWARE_DATETIME
        )

        log_str, result_signal = bot.action(Algorithm.SELL)
        self.assertEqual(round(bot.decimal_balance_vnd, 1), Decimal(5430925.0))
        self.assertEqual(bot.stocks, 150)
        self.assertEqual(log_str, f'SELL 50 {self.company.code}')
        self.assertEqual(result_signal, BotLog.Signal.SELL)

    def test_action_NOT_SELL(self):
        bot = TradeBot(
            name='Jester',
            balance_vnd=Decimal(0),
            company=self.company,
            fee=Decimal(0.0035),
            algorithm=Algorithm(),
            deploy_date=AWARE_DATETIME
        )

        log_str, result_signal = bot.action(Algorithm.SELL)
        self.assertEqual(round(bot.decimal_balance_vnd, 1), Decimal(0))
        self.assertEqual(bot.stocks, 0)
        self.assertEqual(log_str, f'Not enough stocks to SELL 50 {self.company.code}')
        self.assertEqual(result_signal, BotLog.Signal.NOT_SELL)

    def test_action_HOLD(self):
        bot = TradeBot(
            name='Jester',
            balance_vnd=Decimal(0),
            stocks=200,
            company=self.company,
            fee=Decimal(0.0035),
            algorithm=Algorithm(),
            deploy_date=AWARE_DATETIME
        )

        log_str, result_signal = bot.action(Algorithm.HOLD)
        self.assertEqual(round(bot.decimal_balance_vnd, 1), Decimal(0))
        self.assertEqual(bot.stocks, 200)
        self.assertEqual(log_str, 'HOLD')
        self.assertEqual(result_signal, BotLog.Signal.HOLD)

    def test_action_ERR(self):
        bot = TradeBot(
            name='Jester',
            balance_vnd=Decimal(200 * 1000000),
            company=self.company,
            fee=Decimal(0.0035),
            algorithm=Algorithm(),
            deploy_date=AWARE_DATETIME
        )

        with self.assertRaisesMessage(UserWarning, 'Invalid signal: 777'):
            bot.action(777)

        self.assertEqual(round(bot.decimal_balance_vnd, 1), Decimal(200 * 1000000))
        self.assertEqual(bot.stocks, 0)

    def test_statistic(self):
        bot = TradeBot(
            name='Jester',
            balance_vnd=Decimal(200 * 1000000),
            stocks=200,
            company=self.company,
            fee=Decimal(0.0035),
            algorithm=Algorithm(),
            deploy_date=AWARE_DATETIME
        )

        bot.statistics()
        self.assertEqual(bot.all_time_min_total_vnd, Decimal(200000000))
        self.assertEqual(bot.all_time_max_total_vnd, Decimal(221800000))
        self.assertEqual(round(bot.control_decimal_balance_vnd, 1), Decimal(50618))
        self.assertEqual(bot.control_stocks, 2028)

    def test_write_txt(self):
        bot = TradeBot(
            name='Jester',
            balance_vnd=Decimal(200 * 1000000),
            company=self.company,
            fee=Decimal(0.0035),
            algorithm=Algorithm(),
            deploy_date=AWARE_DATETIME
        )

        log_str_deploy = f'{bot.name} is deployed'
        log_str_test = 'This is a test log string :3'
        bot.write_txt(log_str_test)

        self.assertTrue(os.path.exists(BASE_DIR / f"thade/trade_bot/logs/Jester_{self.company.code}_Algorithm.txt"),
                        'A log file should be created when not tracking through database')
        with open(BASE_DIR / f"thade/trade_bot/logs/Jester_{self.company.code}_Algorithm.txt", 'r') as f:
            self.assertIn(log_str_deploy, f.readline())
            self.assertIn(log_str_test, f.readline())

    def test_output_statistics(self):
        bot = TradeBot(
            name='Jester',
            balance_vnd=Decimal(200 * 1000000),
            stocks=200,
            company=self.company,
            fee=Decimal(0.0035),
            algorithm=Algorithm(),
            deploy_date=AWARE_DATETIME
        )

        output_str = '\n'
        output_str += '_____BOT: {} - {}_____\n'.format(bot.name, bot.bid)
        output_str += '\n===================ASSETS===================\n'
        output_str += '{:15}: {:.1f}\n'.format('Balance', 200000000)
        output_str += '{:15}: {:.1f}\n'.format('Stocks', 200)
        output_str += '{:15}: {:.1f}\n'.format('Value in Stocks', 21800000)
        output_str += '{:15}: {:.1f}\n'.format('Total', 221800000)
        output_str += '{:15}: {:.2f}%\n'.format('ROI', 10.90)

        output_str += '\n==================SCENARIO==================\n'
        output_str += '{:15}: {:.1f}\n'.format('Min Balance', 200000000)
        output_str += '{:15}: {:.1f}\n'.format('Max Balance', 221800000)

        output_str += '\n==================CONTROL===================\n'
        output_str += '{:15}: {:.1f}\n'.format('Value in Stocks', 221052000)
        output_str += '{:15}: {:.1f}\n'.format('Total', 221102618.0)
        output_str += '{:15}: {:.2f}%\n'.format('ROI', 10.55)

        bot.statistics()
        self.assertEqual(bot.output_statistics(), output_str)

    def test_log_without_tracking_through_db(self):
        bot = TradeBot(
            name='Jester',
            balance_vnd=Decimal(200 * 1000000),
            stocks=200,
            company=self.company,
            fee=Decimal(0.0035),
            algorithm=Algorithm(),
            deploy_date=AWARE_DATETIME
        )

        log_str_deploy = f'{bot.name} is deployed'
        log_str_buy, result_signal = bot.action(Algorithm.BUY)
        bot.log(log_str_buy, result_signal)
        log_str_sell, result_signal = bot.action(Algorithm.SELL)
        bot.log(log_str_sell, result_signal)
        log_str_hold, result_signal = bot.action(Algorithm.HOLD)
        bot.log(log_str_hold, result_signal)
        try:
            log_str_err, result_signal = bot.action(777)
        except UserWarning as e:
            log_str_err = str(e)
            result_signal = BotLog.Signal.ERR
        bot.log(log_str_err, result_signal)

        self.assertTrue(os.path.exists(BASE_DIR / f"thade/trade_bot/logs/Jester_{self.company.code}_Algorithm.txt"),
                        'A log file should be created when not tracking through database')
        with open(BASE_DIR / f"thade/trade_bot/logs/Jester_{self.company.code}_Algorithm.txt", 'r') as f:
            self.assertIn(log_str_deploy, f.readline())
            self.assertIn(log_str_buy, f.readline())
            self.assertIn(log_str_sell, f.readline())
            self.assertIn(log_str_hold, f.readline())
            self.assertIn(log_str_err, f.readline())

        os.remove(BASE_DIR / f"thade/trade_bot/logs/Jester_{self.company.code}_Algorithm.txt")  # Clean log

    def test_log_with_tracking_through_db(self):
        bot = TradeBot(
            name='Jester',
            balance_vnd=Decimal(200 * 1000000),
            stocks=200,
            company=self.company,
            fee=Decimal(0.0035),
            algorithm=Algorithm(),
            deploy_date=AWARE_DATETIME
        )

        bot.track()
        log_str_deploy = f'{bot.name} is deployed'
        log_str_buy, result_signal = bot.action(Algorithm.BUY)
        bot.log(log_str_buy, result_signal)
        log_str_sell, result_signal = bot.action(Algorithm.SELL)
        bot.log(log_str_sell, result_signal)
        log_str_hold, result_signal = bot.action(Algorithm.HOLD)
        bot.log(log_str_hold, result_signal)
        try:
            log_str_err, result_signal = bot.action(777)
        except UserWarning as e:
            log_str_err = str(e)
            result_signal = BotLog.Signal.ERR
        bot.log(log_str_err, result_signal)

        self.assertTrue(os.path.exists(BASE_DIR / f"thade/trade_bot/logs/Jester_{self.company.code}_Algorithm.txt"),
                        'A log file should be created when not tracking through database')
        with open(BASE_DIR / f"thade/trade_bot/logs/Jester_{self.company.code}_Algorithm.txt", 'r') as f:
            self.assertIn(log_str_deploy, f.readline())
            self.assertIn('Moved to database', f.readline())

        self.assertEqual(bot.model.botlog_set.all()[0].signal, BotLog.Signal.DEPLOY)
        self.assertIn(log_str_deploy, bot.model.botlog_set.all()[0].log_str)
        self.assertEqual(bot.model.botlog_set.all()[1].signal, BotLog.Signal.BUY)
        self.assertIn(log_str_buy, bot.model.botlog_set.all()[1].log_str)
        self.assertEqual(bot.model.botlog_set.all()[2].signal, BotLog.Signal.SELL)
        self.assertIn(log_str_sell, bot.model.botlog_set.all()[2].log_str)
        self.assertEqual(bot.model.botlog_set.all()[3].signal, BotLog.Signal.HOLD)
        self.assertIn(log_str_hold, bot.model.botlog_set.all()[3].log_str)
        self.assertEqual(bot.model.botlog_set.all()[4].signal, BotLog.Signal.ERR)
        self.assertIn(log_str_err, bot.model.botlog_set.all()[4].log_str)

    def test_run_when_bot_inactive(self):
        bot = TradeBot(
            name='Jester',
            balance_vnd=Decimal(200 * 1000000),
            company=self.company,
            fee=Decimal(0.0035),
            algorithm=Algorithm(),
            deploy_date=AWARE_DATETIME - timezone.timedelta(days=30)
        )

        self.assertFalse(bot.is_active)
        with warnings.catch_warnings(record=True) as w:
            bot.run()
            self.assertEqual(w[-1].category, UserWarning)
            self.assertEqual(str(w[-1].message), 'This bot is currently inactive. (Run self.toggle() to active)')

    def test_run_when_bot_active(self):
        bot = TradeBot(
            name='Jester',
            balance_vnd=Decimal(200 * 1000000),
            company=self.company,
            fee=Decimal(0.0035),
            algorithm=Algorithm(),
            deploy_date=AWARE_DATETIME - timezone.timedelta(days=30)
        )

        bot.track()
        bot.toggle()

        bot.run()
        bot_log = BotLog.objects.order_by('-last_updated_record__utc_trading_date')
        self.assertEqual(bot_log.count(), 31)
        for i in range(31):
            temp_log = bot_log[i]
            self.assertEqual(temp_log.last_updated_record.utc_trading_date,
                             AWARE_DATETIME.replace(
                                 hour=2, minute=0, second=0, microsecond=0) - timezone.timedelta(days=i))

    def test_run_moving_average(self):
        from thade.tests.records_fixture import bot_log_signals, stocks, balance_vnd

        bot = TradeBot(
            name='Jester',
            balance_vnd=Decimal(200 * 1000000),
            stocks=500,
            company=self.company,
            fee=Decimal(0.0035),
            algorithm=MovingAverage(),
            deploy_date=AWARE_DATETIME - timezone.timedelta(days=499)
        )

        bot.track()
        bot.toggle()

        bot.run()
        bot_log = BotLog.objects.order_by('-last_updated_record__utc_trading_date')
        self.assertEqual(bot_log.count(), 500)

        test_bot_log_signals = BotLog.objects.order_by(
            '-last_updated_record__utc_trading_date').values_list('signal', flat=True)
        test_stocks = BotLog.objects.order_by(
            '-last_updated_record__utc_trading_date')[:302].values_list('stocks', flat=True)
        test_decimal_balance_vnd = BotLog.objects.order_by(
            '-last_updated_record__utc_trading_date')[:302].values_list('decimal_balance_vnd', flat=True)
        self.assertQuerysetEqual(test_bot_log_signals, bot_log_signals)
        self.assertQuerysetEqual(test_stocks, stocks)
        self.assertQuerysetEqual(test_decimal_balance_vnd, balance_vnd)

    def test_get_trade_bot(self):
        bot = BotFactory(company=self.company)
        for i in range(20):
            BotLogFactory(bot=bot, last_updated_record=bot.company.record_set.all()[i])

        last_log: BotLog = bot.botlog_set.last()

        trade_bot = get_trade_bot(bot)

        self.assertEqual(trade_bot.bid, bot.bid)
        self.assertEqual(trade_bot.name, bot.name)
        self.assertEqual(trade_bot.decimal_balance_vnd, last_log.decimal_balance_vnd)
        self.assertEqual(trade_bot.company, bot.company)
        self.assertEqual(trade_bot.fee, bot.fee)
        self.assertEqual(trade_bot.deploy_date, bot.deploy_date)
        self.assertEqual(trade_bot.stocks, last_log.stocks)
        self.assertEqual(trade_bot.stocks_per_trade, bot.stocks_per_trade)
        self.assertEqual(trade_bot.decimal_investment_vnd, last_log.decimal_investment_vnd)
        self.assertEqual(trade_bot.all_time_min_total_vnd, last_log.all_time_min_total_vnd)
        self.assertEqual(trade_bot.all_time_max_total_vnd, last_log.all_time_max_total_vnd)
        self.assertEqual(trade_bot.control_decimal_balance_vnd, last_log.control_decimal_balance_vnd)
        self.assertEqual(trade_bot.control_stocks, last_log.control_stocks)
        self.assertEqual(trade_bot.last_updated_record, last_log.last_updated_record)
        self.assertEqual(trade_bot.is_active, bot.is_active)
        self.assertTrue(trade_bot.is_tracking)
        self.assertEqual(trade_bot.model, bot)
