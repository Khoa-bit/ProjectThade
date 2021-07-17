from django.core.management.base import BaseCommand
from thade.backtesting.scrape_stock import update_records


class Command(BaseCommand):
    help = "Update company records"

    def add_arguments(self, parser):
        parser.add_argument(
            '--company_code',
            type=str,
            help="The company's code to update its records"
        )

    def handle(self, *args, **options):
        update_records(options['company_code'])
