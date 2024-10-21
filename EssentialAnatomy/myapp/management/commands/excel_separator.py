import pandas as pd
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Split entries in row 3 based on " - " and place the second part in row 4.'

    def add_arguments(self, parser):
        parser.add_argument('input_file', type=str, help='Path to the input Excel file')
        parser.add_argument('output_file', type=str, help='Path to the output Excel file')

    def handle(self, *args, **options):
        input_file = options['input_file']
        output_file = options['output_file']
        self.split_row_based_on_separator(input_file, output_file)

    def split_row_based_on_separator(self, input_file, output_file):
        # Read the Excel file using openpyxl engine
        df = pd.read_excel(input_file, engine='openpyxl', header=None)

        # Ensure that the DataFrame has at least 4 rows
        if len(df) < 4:
            additional_rows = 4 - len(df)
            for _ in range(additional_rows):
                df.loc[len(df)] = [None] * len(df.columns)

        # Iterate over each cell in row 3 (index 2)
        for col in df.columns:
            cell_value = df.at[2, col]
            if pd.notna(cell_value) and " - " in cell_value:
                parts = cell_value.split(" - ", 1)
                df.at[2, col] = parts[0]
                df.at[3, col] = parts[1]

        # Write the modified DataFrame to a new Excel file
        df.to_excel(output_file, index=False, header=False, engine='openpyxl')


# input_file = 'D:/Downloads/essential_anatomy_sections.xlsx'
# output_file = 'D:/Downloads/edited_sections.xlsx'
