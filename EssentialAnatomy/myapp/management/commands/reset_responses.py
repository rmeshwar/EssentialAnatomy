from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Reset the structure of the database by truncating tables and resetting auto-increment IDs'

    def handle(self, *args, **kwargs):
        tables = [
            'myapp_subgroupresponseanatomy',
            'myapp_subsubgroupresponseanatomy',
            'myapp_subgroupresponseclinician',
            'myapp_subsubgroupresponseclinician',
        ]

        with connection.cursor() as cursor:
            cursor.execute('SET FOREIGN_KEY_CHECKS = 0;')
            for table in tables:
                cursor.execute(f'TRUNCATE TABLE {table}')
                cursor.execute(f'ALTER TABLE {table} AUTO_INCREMENT = 1')
            cursor.execute('SET FOREIGN_KEY_CHECKS = 1;')

        self.stdout.write(self.style.SUCCESS('Successfully reset the survey responses'))
