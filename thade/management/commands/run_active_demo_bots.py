from django.core.management.base import BaseCommand
from thade.trade_bot.sandbox import run_active_demo_bots


class Command(BaseCommand):
    help = "Run all active demo bots in database"

    def add_arguments(self, parser):
        parser.add_argument(
            '--update',
            type=bool,
            default=False,
            help="Update active TradeBots' company records",
        )

    def handle(self, *args, **options):
        run_active_demo_bots(options['update'])
