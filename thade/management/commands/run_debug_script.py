from django.core.management.base import BaseCommand
from thade.trade_bot.TradeBot import debug_bot


class Command(BaseCommand):
    help = "Run or Debug script"

    def handle(self, *args, **options):
        debug_bot()
