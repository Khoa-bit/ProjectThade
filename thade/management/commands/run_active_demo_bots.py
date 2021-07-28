from django.core.management.base import BaseCommand
from thade.trade_bot.sandbox import run_active_demo_bots


class Command(BaseCommand):
    help = "Run all active demo bots in database"

    def handle(self, *args, **options):
        run_active_demo_bots()
