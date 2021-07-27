from decimal import Decimal
from time import sleep

from django.utils import timezone

from thade.backtesting.scrape_stock import update_records
from thade.models import Company
from thade.trade_bot.MovingAverage import MovingAverage
from thade.trade_bot.TradeBot import TradeBot

from multiprocessing import Process
from threading import Thread


def run_bot(bot: TradeBot):
    bot.run()


def update_bot_records(code: str):
    update_records(code)


def run_demo_bots(balance_vnd=20 * 1000000, days=365):
    codes = ['MWG', 'MSN', 'VJC', 'VHM', 'NVL', 'VIC', 'VCB', 'FPT']
    bots = []

    # processes_update = []
    #
    # # instantiating process with arguments
    # for code in codes:
    #     p = Process(target=update_bot_records, kwargs={'code': code})
    #     processes_update.append(p)
    #     sleep(0.5)
    #     p.start()
    #
    # # complete the processes
    # for p in processes_update:
    #     p.join()

    for code in codes:
        bot = TradeBot(
            balance_vnd=balance_vnd,
            company=Company.objects.get(code=code),
            fee=Decimal(0.0035),
            algorithm=MovingAverage(),
            deploy_date=timezone.now() - timezone.timedelta(days=days)
        )
        bot.track()
        bot.toggle()
        bots.append(bot)

    print('+====================================+')
    threads_run = []

    # instantiating process with arguments
    for bot in bots:
        t = Thread(target=run_bot, kwargs={'bot': bot})
        threads_run.append(t)
        sleep(1)
        t.start()

    # complete the processes
    for t in threads_run:
        t.join()

    for bot in bots:
        print(bot.output_statistics())


def run_a_demo_bot():
    bot = TradeBot(
        balance_vnd=20 * 1000000,
        company=Company.objects.get(code='MWG'),
        fee=Decimal(0.0035),
        algorithm=MovingAverage(),
        deploy_date=timezone.now() - timezone.timedelta(days=365)
    )
    bot.track()
    bot.toggle()
    run_bot(bot)
    bot.output_statistics()


print('\n===============START===============\n')
# run_a_demo_bot()
run_demo_bots()
print('\n================END================\n')
