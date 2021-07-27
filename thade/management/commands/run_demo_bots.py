from django.core.management.base import BaseCommand

from thade.trade_bot.sandbox import run_demo_bots


class Command(BaseCommand):
    help = "Update company records"

    def add_arguments(self, parser):
        parser.add_argument(
            '--balance_vnd',
            type=int,
            help="Balance for each bot to start with",
        )

        parser.add_argument(
            '--days',
            type=int,
            help="Days from now that the bot is deployed"
        )

    def handle(self, *args, **options):
        run_demo_bots(
            balance_vnd=options['balance_vnd'] or 20 * 1000000,
            days=options['days'] or 365
        )
