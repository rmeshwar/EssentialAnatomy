from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Runs the full pipeline of importing and processing anatomy and clinician survey data.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--anat',
            type=str,
            required=True,
            help='Path to the anatomy Excel file (e.g. D:/Downloads/ea_anat.xlsx)'
        )
        parser.add_argument(
            '--clin',
            type=str,
            required=True,
            help='Path to the clinician Excel file (e.g. D:/Downloads/ea_clin.xlsx)'
        )

    def handle(self, *args, **options):
        anat_path = options['anat']
        clin_path = options['clin']

        try:
            self.stdout.write(self.style.NOTICE(f'Importing anatomist responses from {anat_path}...'))
            call_command('import_anatomist_response', anat_path)

            self.stdout.write(self.style.NOTICE(f'Importing clinician responses from {clin_path}...'))
            call_command('import_clinician_response', clin_path)

            self.stdout.write(self.style.NOTICE('Processing anatomist results...'))
            call_command('process_anatomist_results')

            self.stdout.write(self.style.NOTICE('Processing clinician results...'))
            call_command('process_clinician_results')

            self.stdout.write(self.style.SUCCESS('All imports and processing completed successfully!'))

        except CommandError as e:
            self.stderr.write(self.style.ERROR(f'Error: {str(e)}'))
