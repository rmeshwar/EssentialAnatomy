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
        excluded_categories = {"Other (please specify)", "Other (provide below):", "MISC"}
        
        # Skip the first three rows
        df = df.iloc[1:]

        # Filter only the completed responses
        df = df[df.iloc[:, 4] == 100]  # Column E is the 5th column, index 4

        rating_map = {
            'Not Important': 1, '1': 1, 1: 1,
            'Less Important': 2, '2': 2, 2: 2,
            'Moderately Important': 3, '3': 3, 3: 3,
            'Average Importance': 4, '4': 4, 4: 4,
            'More Important': 5, '5': 5, 5: 5,
            'Very Important': 6, '6': 6, 6: 6,
            'Essential': 7, '7': 7, 7: 7
        }

        degree_to_program_map = {
            "BDS": "Dentistry",
            "DDS": "Dentistry",
            "DO": "Medicine - Osteopathic",
            "DPT": "Physical Therapy",
            "MBBS": "Medicine - Allopathic",
            "MD": "Medicine - Allopathic",
            "PA-C": "Physician Assistant",
            "PharmD": "Pharmacy"
        }

        program_category_map = {
            "Medicine - Allopathic": "MD",
            "Medicine - Osteopathic": "DO",
            "Physician Assistant": "PA",
            "Physical Therapy": "PT",
            "Dentistry": "DDS",
            "Anatomy Graduate": "GRD",
            "Anatomy Undergraduate": "UG",
            "Pharmacy": "PharmD"
        }

        max_responder_id = ResponderClinician.objects.aggregate(models.Max('responder_id'))['responder_id__max'] or 0

        count = 0
        for index, row in df.iterrows():
            print(f"Processing row {index + 2}")  # Debugging output

            # Get the terminal degree (Column R is index 17)
            terminal_degree = row.iloc[17]
            if terminal_degree == "Other (provide below)":
                terminal_degree = row.iloc[18]  # Column S is index 18 if "Other"

            # Check Clinician Type (Column V is index 21)
            clinician_type = row.iloc[21]

            if clinician_type == "Clinician (practicing)":
                # Get professional health program from Column W (index 22)
                professional_health_program = row.iloc[22]
            elif clinician_type == "Clinician (non-practicing)":
                # Derive professional health program based on degree in Column R (index 17)
                professional_health_program = degree_to_program_map.get(terminal_degree, "MISC")

                # Exclude invalid categories
                if professional_health_program in excluded_categories:
                    print(f"Skipping responder due to excluded professional health program: {professional_health_program}")
                    continue  # Skip this row
            else:
                professional_health_program = "MISC"
            
            # Map the program category
            program_category = program_category_map.get(professional_health_program, "MISC")

            # Exclude if still in excluded categories
            if program_category in excluded_categories:
                print(f"Skipping responder due to excluded program category: {program_category}")
                continue

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

                # print(f"Row {index + 2}: Subgroup {i} -> Rating Text: {rating_text} -> Rating: {rating}")


                if rating:
                    try:
                        # if not Subsection.objects.filter(id=i).exists():
                        #     print(f"Subsection with ID {i} does NOT exist in the database!")
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

                # print(f"Row {index + 2}: SubSubgroup {i} -> Rating Text: {rating_text} -> Rating: {rating}")


                if rating:
                    try:
                        # if not ResponseTopic.objects.filter(id=i).exists():
                        #     print(f"ResponseTopic with ID {i} does NOT exist in the database!")
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