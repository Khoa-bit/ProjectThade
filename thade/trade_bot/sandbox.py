from decimal import Decimal
from time import sleep

from django.utils import timezone

from thade.backtesting.scrape_stock import update_records, fetch_records
from thade.models import Company, Bot
from thade.trade_bot.MovingAverage import MovingAverage
from thade.trade_bot.TradeBot import TradeBot, get_trade_bot

from multiprocessing import Process
from threading import Thread


def run_bot(bot: TradeBot):
    bot.run()


def update_bot_records(code: str):
    update_records(code)


def run_demo_bots(balance_vnd=Decimal(20 * 1000000), days=365):
    codes = ['MWG', 'MSN', 'VJC', 'VHM', 'NVL', 'VIC', 'VCB', 'FPT']
    bots = []

    processes_update = []

    # Fetch, update records
    for code in codes:
        p = Process(target=update_bot_records, kwargs={'code': code})
        processes_update.append(p)
        sleep(1)
        p.start()

    # complete the processes
    for p in processes_update:
        p.join()

    # Instantiate TradeBots
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

    # Run TradeBots
    for bot in bots:
        t = Thread(target=run_bot, kwargs={'bot': bot})
        threads_run.append(t)
        t.start()

    # complete the processes
    for t in threads_run:
        t.join()

    for bot in bots:
        print(bot.output_statistics())


def run_active_demo_bots(update=False):
    bots = []
    active_bots_queryset = Bot.objects.filter(is_active=True)

    # Update active TradeBots' company records
    if update:
        processes_update = []
        for bot_model in active_bots_queryset:
            p = Process(target=fetch_records, kwargs={'company_instance': bot_model.company})
            processes_update.append(p)
            p.start()
            sleep(1)

        # complete the processes
        for p in processes_update:
            p.join()

    threads_run = []
    for bot_model in active_bots_queryset:
        bot = get_trade_bot(bot_model)
        bots.append(bot)
        t = Thread(target=run_bot, kwargs={'bot': bot})
        threads_run.append(t)
        t.start()

    # complete the threads
    for t in threads_run:
        t.join()

    for bot in bots:
        print(bot.output_statistics())


def run_a_demo_bot():
    bot = TradeBot(
        balance_vnd=Decimal(20 * 1000000),
        company=Company.objects.get(code='MWG'),
        fee=Decimal(0.0035),
        algorithm=MovingAverage(),
        deploy_date=timezone.now() - timezone.timedelta(days=365)
    )
    bot.track()
    bot.toggle()
    run_bot(bot)
    bot.output_statistics()


if __name__ == 'django.core.management.commands.shell':
    print('\n===============START===============\n')
    # run_a_demo_bot()
    # run_demo_bots()
    print('\n================END================\n')
