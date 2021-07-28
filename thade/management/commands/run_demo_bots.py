from decimal import Decimal

from django.core.management.base import BaseCommand

from thade.trade_bot.sandbox import run_demo_bots


class Command(BaseCommand):
    help = "Update company records"

    def add_arguments(self, parser):
        parser.add_argument(
            '--balance_vnd',
            type=int,
            default=Decimal(20 * 1000000),
            help="Balance for each bot to start with",
        )

        parser.add_argument(
            '--days',
            type=int,
            default=365,
            help="Days from now that the bot is deployed"
        )

    def handle(self, *args, **options):
        run_demo_bots(
            balance_vnd=options['balance_vnd'],
            days=options['days']
        )
