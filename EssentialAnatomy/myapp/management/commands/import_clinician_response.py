import pandas as pd
from django.core.management.base import BaseCommand
from django.db import models
from myapp.models import ResponderClinician, Subsection, SubgroupResponseClinician, ResponseTopic, SubSubgroupResponseClinician

class Command(BaseCommand):
    help = 'Import clinician survey responses from Excel file'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to the Excel file')

    def handle(self, *args, **kwargs):
        file_path = kwargs['file_path']
        self.import_responses(file_path)

    def import_responses(self, file_path):
        df = pd.read_excel(file_path, engine='openpyxl')

        # Skip the first three rows and limit to the first 20 responders
        df = df.iloc[1:11]

        # Filter only the completed responses
        df = df[df.iloc[:, 4] == 100]  # Column E is the 5th column, index 4

        rating_map = {
            'Not Important': 1,
            'Less Important': 2,
            'Moderately Important': 3,
            'Average Importance': 4,
            'More Important': 5,
            'Very Important': 6,
            'Essential': 7
        }

        program_category_map = {
            "Medicine - Allopathic": "MD",
            "Medicine - Osteopathic": "DO",
            "Physician Assistant": "PA",
            "Physical Therapy": "PT",
            "Dentistry": "DDS",
            "Anatomy Graduate": "GRD",
            "Anatomy Undergraduate": "UG"
        }

        max_responder_id = ResponderClinician.objects.aggregate(models.Max('responder_id'))['responder_id__max'] or 0

        count = 0
        for index, row in df.iterrows():
            print(f"Processing row {index + 2}")  # Debugging output

            # Get the terminal degree (still in column R)
            terminal_degree = row.iloc[17]  # Column R is index 17
            if terminal_degree == "Other (provide below)":
                terminal_degree = row.iloc[18]  # Column S is index 18 if "Other"

            # Get professional health program (X if not empty, otherwise W)
            professional_health_program = row.iloc[23] if pd.notna(row.iloc[23]) else row.iloc[22]  # Column X is index 23, Column W is index 22

            # Map the program category
            program_category = program_category_map.get(professional_health_program, "MISC")

            # Get the primary field (Column AA is index 26)
            primary_field = row.iloc[26]

            # Get the subfield (First entry from columns AB-AT, AX-BQ, BU, BW, BY, CA, CC)
            subfield_columns = [27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 44, 45, 49, 51, 53, 55, 57]
            subfield = next((row.iloc[col] for col in subfield_columns if pd.notna(row.iloc[col])), None)

            # Create or get the responder record in ResponderClinician
            max_responder_id += 1
            responder, created = ResponderClinician.objects.get_or_create(
                responder_id=max_responder_id,
                terminal_degree=terminal_degree,
                professional_health_program=professional_health_program,
                program_category=program_category,
                primary_field=primary_field,
                subfield=subfield
            )
            if created:
                count += 1

            # Import Subgroup Responses (Columns CL to EG, index 88 to 137)
            for i, col in enumerate(range(89, 137), start=1):
                rating_text = row.iloc[col]
                rating = rating_map.get(rating_text)

                if rating:
                    try:
                        subgroup = Subsection.objects.get(id=i)
                        SubgroupResponseClinician.objects.create(
                            responder=responder,
                            subgroup=subgroup,
                            rating=rating
                        )
                    except Subsection.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f'Subsection with ID "{i}" not found'))

            print(f"Added Subgroup Response for row {index + 2}")

            # Import Subsubgroup Responses (Columns EH to AWS, index 138 to 1441)
            for i, col in enumerate(range(137, 1293), start=1):
                rating_text = row.iloc[col]
                rating = rating_map.get(rating_text)

                if rating:
                    try:
                        subsubgroup = ResponseTopic.objects.get(id=i)
                        SubSubgroupResponseClinician.objects.create(
                            responder=responder,
                            subsubgroup=subsubgroup,
                            rating=rating
                        )
                    except ResponseTopic.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f'ResponseTopic with ID "{i}" not found'))

            print(f"Added SubSubgroup Response for row {index + 2}")

        self.stdout.write(self.style.SUCCESS(f'Successfully imported {count} new responder(s)'))

